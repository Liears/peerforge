import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from peerforge import bus, chat


class ChatThreadTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.root = Path(self.tmpdir.name) / ".peerforge"
        self.root.mkdir(parents=True, exist_ok=True)
        self.runtime_dir = self.root / "runtime"
        self.session_dir = self.root / "sessions"
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.config_path = self.root / "config.json"
        self.config_path.write_text(
            json.dumps(
                {
                    "workdir": self.tmpdir.name,
                    "session_dir": str(self.session_dir),
                    "runtime_dir": str(self.runtime_dir),
                    "agents": [
                        {"name": "codex", "type": "command", "command": ["echo", "{prompt}"]},
                        {"name": "hermes", "type": "command", "command": ["echo", "{prompt}"]},
                    ],
                }
            )
            + "\n",
            encoding="utf-8",
        )

    def test_parse_mentions_supports_named_agents_and_all(self) -> None:
        names = ["codex", "claude", "hermes", "openclaw"]
        self.assertEqual(chat.parse_mentions("@codex ask @hermes to review", names), ["codex", "hermes"])
        self.assertEqual(chat.parse_mentions("@all review this", names), ["@all"])

    def test_post_user_message_routes_and_persists_events(self) -> None:
        def fake_probe(_self):
            return {"status": "ready"}

        def fake_run(self, _prompt: str):
            if self.name == "codex":
                return bus.AgentResult(
                    ok=True,
                    status="continue",
                    summary="codex wants hermes to review",
                    messages=[{"to": ["hermes"], "kind": "question", "body": "Please review this change"}],
                    raw_output='{"status":"continue"}',
                )
            return bus.AgentResult(
                ok=True,
                status="done",
                summary="hermes reviewed it",
                messages=[],
                raw_output='{"status":"done"}',
            )

        with mock.patch.object(bus.AgentAdapter, "probe", new=fake_probe):
            with mock.patch.object(bus.AgentAdapter, "run", new=fake_run):
                payload = chat.post_user_message(self.root, self.config_path, "@codex review the router")

        events = payload["events"]
        event_types = [row["type"] for row in events]
        self.assertIn("user.input", event_types)
        self.assertIn("tool.call", event_types)
        self.assertIn("tool.result", event_types)
        self.assertIn("chat.message", event_types)

        chat_events = [row for row in events if row["type"] == "chat.message"]
        self.assertEqual(chat_events[0]["source"], "codex")
        self.assertEqual(chat_events[0]["target"], ["@hermes"])

        heartbeat = bus.read_heartbeat(self.runtime_dir, "codex")
        self.assertIsNotNone(heartbeat)
        self.assertEqual(heartbeat["state"], "ready")


if __name__ == "__main__":
    unittest.main()
