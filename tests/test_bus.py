import argparse
import json
import tempfile
import unittest
import subprocess
import sys
import textwrap
import io
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from peerforge import bus


class BusTaskClaimTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.root = Path(self.tmpdir.name) / ".peerforge"
        self.root.mkdir(parents=True, exist_ok=True)
        self.session_dir = self.root / "sessions"
        self.runtime_dir = self.root / "runtime"
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.config_path = self.root / "config.json"
        self.config_path.write_text(
            json.dumps(
                {
                    "workdir": self.tmpdir.name,
                    "session_dir": str(self.session_dir),
                    "runtime_dir": str(self.runtime_dir),
                    "agents": [],
                }
            )
            + "\n",
            encoding="utf-8",
        )

    def write_board(self, tasks: list[dict]) -> None:
        bus.write_json(self.root / "board.json", {"tasks": tasks})

    def read_board(self) -> dict:
        return json.loads((self.root / "board.json").read_text(encoding="utf-8"))

    def write_heartbeat(self, agent: str, state: str, expires_at: str) -> None:
        path = self.runtime_dir / "heartbeats" / f"{agent}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "agent": agent,
                    "state": state,
                    "updated_at": "2026-04-30T00:00:00+00:00",
                    "expires_at": expires_at,
                }
            )
            + "\n",
            encoding="utf-8",
        )

    def test_task_run_next_claims_before_dispatch_and_clears_claim(self) -> None:
        self.write_board(
            [
                {
                    "id": "atomic-task-claim",
                    "title": "Atomic task claim",
                    "description": "Claim before dispatch",
                    "status": "todo",
                    "owner": "codex",
                    "created_at": "2026-04-30T00:00:00+00:00",
                    "depends_on": [],
                }
            ]
        )

        seen = {}

        def fake_run(_self, task: str, rounds: int, title: str | None = None) -> Path:
            board = self.read_board()
            row = board["tasks"][0]
            seen["status"] = row["status"]
            seen["claimed_by"] = row.get("claimed_by")
            seen["claim_token"] = row.get("claim_token")
            transcript = self.session_dir / "fake-transcript.jsonl"
            transcript.write_text("", encoding="utf-8")
            return transcript

        args = argparse.Namespace(
            root=str(self.root),
            config=str(self.config_path),
            rounds=1,
            agents=None,
            owner=None,
            claimer="dispatcher",
            lease_seconds=120,
            ready_only=False,
            bootstrap=False,
            bootstrap_mode="copy",
        )

        with mock.patch.object(bus.Bus, "run", new=fake_run):
            rc = bus.cmd_task_run_next(args)

        self.assertEqual(rc, 0)
        self.assertEqual(seen["status"], "in_progress")
        self.assertEqual(seen["claimed_by"], "dispatcher")
        self.assertTrue(seen["claim_token"])

        board = self.read_board()
        row = board["tasks"][0]
        self.assertEqual(row["status"], "in_review")
        self.assertIn("last_transcript", row)
        self.assertNotIn("claimed_by", row)
        self.assertNotIn("claim_token", row)

    def test_run_task_refuses_active_claim(self) -> None:
        self.write_board(
            [
                {
                    "id": "board-file-locking",
                    "title": "Board file locking",
                    "description": "Protect board writes",
                    "status": "todo",
                    "owner": "hermes",
                    "created_at": "2026-04-30T00:00:00+00:00",
                    "depends_on": [],
                    "claimed_by": "hermes",
                    "claimed_at": "2026-04-30T00:00:00+00:00",
                    "lease_expires_at": "2099-01-01T00:00:00+00:00",
                    "claim_token": "active-token",
                }
            ]
        )

        args = argparse.Namespace(
            task_id="board-file-locking",
            root=str(self.root),
            config=str(self.config_path),
            rounds=1,
            agents=None,
            claimer="dispatcher",
            lease_seconds=120,
            ready_only=False,
        )

        with self.assertRaises(SystemExit) as ctx:
            bus.cmd_run_task(args)

        self.assertIn("task already claimed by hermes", str(ctx.exception))

    def test_task_add_times_out_when_board_lock_is_held_by_another_process(self) -> None:
        original_board_lock = bus.board_lock

        def short_board_lock(root: Path, timeout_seconds: float = bus.BOARD_LOCK_TIMEOUT_SECONDS):
            return original_board_lock(root, timeout_seconds=0.05)

        lock_holder = subprocess.Popen(
            [
                sys.executable,
                "-c",
                textwrap.dedent(
                    f"""
                    import time
                    from pathlib import Path
                    from peerforge import bus

                    root = Path({str(self.root)!r})
                    with bus.board_lock(root, timeout_seconds=5):
                        print("locked", flush=True)
                        time.sleep(2)
                    """
                ),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            assert lock_holder.stdout is not None
            self.assertEqual(lock_holder.stdout.readline().strip(), "locked")

            args = argparse.Namespace(
                root=str(self.root),
                title="Locked task",
                description="Should time out behind the board lock",
                owner="pm",
                status="todo",
                depends_on=None,
            )

            with mock.patch.object(bus, "board_lock", new=short_board_lock):
                with self.assertRaises(SystemExit) as ctx:
                    bus.cmd_task_add(args)

            self.assertIn("timed out waiting for board lock", str(ctx.exception))
        finally:
            lock_holder.terminate()
            try:
                lock_holder.wait(timeout=5)
            except subprocess.TimeoutExpired:
                lock_holder.kill()
                lock_holder.wait(timeout=5)
            if lock_holder.stdout is not None:
                lock_holder.stdout.close()
            if lock_holder.stderr is not None:
                lock_holder.stderr.close()

    def test_healthy_agent_names_excludes_busy_heartbeat(self) -> None:
        config = {
            "workdir": self.tmpdir.name,
            "session_dir": str(self.session_dir),
            "runtime_dir": str(self.runtime_dir),
            "agents": [{"name": "codex", "type": "command", "command": ["true"]}],
        }
        self.write_heartbeat("codex", "busy", "2099-01-01T00:00:00+00:00")

        with mock.patch.object(bus.AgentAdapter, "probe", return_value={"status": "ready"}):
            ready = bus.healthy_agent_names(config)

        self.assertEqual(ready, [])

    def test_healthy_agent_names_excludes_expired_heartbeat(self) -> None:
        config = {
            "workdir": self.tmpdir.name,
            "session_dir": str(self.session_dir),
            "runtime_dir": str(self.runtime_dir),
            "agents": [{"name": "codex", "type": "command", "command": ["true"]}],
        }
        self.write_heartbeat("codex", "ready", "2000-01-01T00:00:00+00:00")

        with mock.patch.object(bus.AgentAdapter, "probe", return_value={"status": "ready"}):
            ready = bus.healthy_agent_names(config)

        self.assertEqual(ready, [])


class HeartbeatRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.root = Path(self.tmpdir.name) / ".peerforge"
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "runtime" / "heartbeats").mkdir(parents=True, exist_ok=True)
        self.config_path = self.root / "config.json"
        self.config_path.write_text(
            json.dumps(
                {
                    "workdir": self.tmpdir.name,
                    "session_dir": str(self.root / "sessions"),
                    "runtime_dir": str(self.root / "runtime"),
                    "agents": [
                        {"name": "alpha", "type": "command", "enabled": True},
                        {"name": "beta", "type": "command", "enabled": True},
                        {"name": "gamma", "type": "command", "enabled": True},
                    ],
                }
            )
            + "\n",
            encoding="utf-8",
        )

    def write_heartbeat(self, agent: str, *, state: str, expires_at: datetime) -> None:
        bus.write_json(
            self.root / "runtime" / "heartbeats" / f"{agent}.json",
            {
                "agent": agent,
                "state": state,
                "updated_at": (expires_at - timedelta(seconds=30)).isoformat(),
                "expires_at": expires_at.isoformat(),
            },
        )

    def heartbeat_state(self, agent: str, now: datetime) -> str:
        path = self.root / "runtime" / "heartbeats" / f"{agent}.json"
        if not path.exists():
            return "offline"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return "offline"

        state = data.get("state")
        expires_at = bus.parse_iso8601(data.get("expires_at"))
        if state not in {"ready", "busy", "offline"}:
            return "offline"
        if expires_at is None or now >= expires_at:
            return "offline"
        return str(state)

    def ready_agents_from_heartbeats(self, now: datetime) -> list[str]:
        rows = []
        for path in sorted((self.root / "runtime" / "heartbeats").glob("*.json")):
            agent = path.stem
            if self.heartbeat_state(agent, now) == "ready":
                rows.append(agent)
        return rows

    def test_expired_heartbeat_is_treated_as_offline(self) -> None:
        now = datetime.now(timezone.utc)
        self.write_heartbeat(
            "alpha",
            state="ready",
            expires_at=now - timedelta(seconds=1),
        )

        self.assertEqual(self.heartbeat_state("alpha", now), "offline")

        args = argparse.Namespace(config=str(self.config_path), agents=None)
        with mock.patch.object(
            bus,
            "healthy_agent_names",
            new=lambda _config: self.ready_agents_from_heartbeats(now),
        ):
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                rc = bus.cmd_ready(args)

        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(stdout.getvalue()), [])

    def test_busy_heartbeat_is_excluded_from_ready_agents(self) -> None:
        now = datetime.now(timezone.utc)
        self.write_heartbeat(
            "alpha",
            state="busy",
            expires_at=now + timedelta(minutes=1),
        )
        self.write_heartbeat(
            "beta",
            state="ready",
            expires_at=now + timedelta(minutes=1),
        )

        self.assertEqual(self.heartbeat_state("alpha", now), "busy")
        self.assertEqual(self.heartbeat_state("beta", now), "ready")

        args = argparse.Namespace(config=str(self.config_path), agents=None)
        with mock.patch.object(
            bus,
            "healthy_agent_names",
            new=lambda _config: self.ready_agents_from_heartbeats(now),
        ):
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                rc = bus.cmd_ready(args)

        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(stdout.getvalue()), ["beta"])


if __name__ == "__main__":
    unittest.main()
