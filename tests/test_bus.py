import argparse
import json
import tempfile
import unittest
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


if __name__ == "__main__":
    unittest.main()
