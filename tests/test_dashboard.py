import json
import tempfile
import unittest
from pathlib import Path

from peerforge import dashboard


class DashboardDataTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.root = Path(self.tmpdir.name) / ".peerforge"
        (self.root / "sessions").mkdir(parents=True, exist_ok=True)

    def write_session(self, session_id: str, *, title: str, created_at: str, rows: list[dict]) -> None:
        session_dir = self.root / "sessions" / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        (session_dir / "summary.json").write_text(
            json.dumps(
                {
                    "title": title,
                    "task": "Review scheduler output",
                    "created_at": created_at,
                    "agents": ["codex", "hermes"],
                    "final_statuses": {"codex": "continue", "hermes": "done"},
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (session_dir / "transcript.jsonl").write_text(
            "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
            encoding="utf-8",
        )

    def test_list_sessions_sorts_latest_first(self) -> None:
        self.write_session(
            "older",
            title="Older run",
            created_at="2026-04-30T00:00:00+00:00",
            rows=[{"from": "user", "created_at": "2026-04-30T00:00:00+00:00"}],
        )
        self.write_session(
            "newer",
            title="Newer run",
            created_at="2026-04-30T01:00:00+00:00",
            rows=[{"from": "user", "created_at": "2026-04-30T01:00:00+00:00"}],
        )

        sessions = dashboard.list_sessions(self.root)

        self.assertEqual([row["id"] for row in sessions], ["newer", "older"])

    def test_load_session_returns_summary_and_messages(self) -> None:
        rows = [
            {"from": "user", "to": ["codex"], "kind": "task", "body": "Do work", "created_at": "2026-04-30T01:00:00+00:00"},
            {"from": "codex", "to": ["*"], "kind": "status", "body": "Working", "created_at": "2026-04-30T01:00:01+00:00"},
        ]
        self.write_session(
            "run-1",
            title="Run 1",
            created_at="2026-04-30T01:00:00+00:00",
            rows=rows,
        )

        payload = dashboard.load_session(self.root, "run-1")

        self.assertEqual(payload["session"]["title"], "Run 1")
        self.assertEqual(len(payload["messages"]), 2)
        self.assertEqual(payload["messages"][1]["body"], "Working")

    def test_load_board_defaults_to_empty_tasks(self) -> None:
        self.assertEqual(dashboard.load_board(self.root), {"tasks": []})


if __name__ == "__main__":
    unittest.main()
