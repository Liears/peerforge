#!/usr/bin/env python3
import argparse
import json
import posixpath
import threading
from dataclasses import dataclass
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

try:
    from peerforge import bus, chat
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    import bus  # type: ignore
    import chat  # type: ignore


UI_DIR = Path(__file__).resolve().parent / "ui"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def board_path(root: Path) -> Path:
    return root / "board.json"


def sessions_root(root: Path) -> Path:
    return root / "sessions"


def summarize_session(session_dir: Path) -> dict:
    summary_path = session_dir / "summary.json"
    transcript_path = session_dir / "transcript.jsonl"
    summary = read_json(summary_path) if summary_path.exists() else {}
    rows = read_jsonl(transcript_path) if transcript_path.exists() else []
    agents = summary.get("agents") or sorted({row.get("from") for row in rows if row.get("from") not in {"user"}})
    created_at = summary.get("created_at") or (rows[0].get("created_at") if rows else None)
    return {
        "id": session_dir.name,
        "title": summary.get("title") or session_dir.name,
        "task": summary.get("task", ""),
        "created_at": created_at,
        "agents": agents,
        "final_statuses": summary.get("final_statuses", {}),
        "message_count": len(rows),
        "transcript": str(transcript_path),
    }


def list_sessions(root: Path) -> list[dict]:
    session_dir = sessions_root(root)
    if not session_dir.exists():
        return []
    rows = [summarize_session(path) for path in session_dir.iterdir() if path.is_dir()]
    rows.sort(key=lambda row: row.get("created_at") or row["id"], reverse=True)
    return rows


def load_session(root: Path, session_id: str) -> dict:
    session_dir = sessions_root(root) / session_id
    if not session_dir.exists():
        raise FileNotFoundError(session_id)
    transcript_path = session_dir / "transcript.jsonl"
    summary_path = session_dir / "summary.json"
    messages = read_jsonl(transcript_path) if transcript_path.exists() else []
    summary = read_json(summary_path) if summary_path.exists() else {}
    return {
        "session": summarize_session(session_dir),
        "summary": summary,
        "messages": messages,
    }


def load_board(root: Path) -> dict:
    path = board_path(root)
    if not path.exists():
        return {"tasks": []}
    return read_json(path)


@dataclass
class DashboardConfig:
    root: Path
    config_path: Path
    host: str
    port: int
    api_lock: threading.Lock


class DashboardHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, config: DashboardConfig, **kwargs):
        self.dashboard_config = config
        super().__init__(*args, directory=str(UI_DIR), **kwargs)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            self.handle_api(parsed)
            return
        if parsed.path in {"/", ""}:
            self.path = "/index.html"
        super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if not parsed.path.startswith("/api/"):
            self.send_error(HTTPStatus.NOT_FOUND, "unknown endpoint")
            return
        self.handle_post_api(parsed)

    def handle_api(self, parsed) -> None:
        if parsed.path == "/api/sessions":
            params = parse_qs(parsed.query)
            limit = int(params.get("limit", ["50"])[0])
            payload = {"sessions": list_sessions(self.dashboard_config.root)[:limit]}
            self.send_json(payload)
            return

        if parsed.path == "/api/board":
            self.send_json(load_board(self.dashboard_config.root))
            return

        if parsed.path == "/api/agents":
            payload = {"agents": chat.live_agent_status(bus.read_json(self.dashboard_config.config_path), probe=False)}
            self.send_json(payload)
            return

        if parsed.path == "/api/live-thread":
            self.send_json(chat.load_thread(self.dashboard_config.root))
            return

        if parsed.path.startswith("/api/sessions/"):
            session_id = parsed.path.removeprefix("/api/sessions/")
            session_id = posixpath.normpath(session_id).strip("/")
            if "/" in session_id or session_id.startswith("."):
                self.send_error(HTTPStatus.BAD_REQUEST, "invalid session id")
                return
            try:
                payload = load_session(self.dashboard_config.root, session_id)
            except FileNotFoundError:
                self.send_error(HTTPStatus.NOT_FOUND, "session not found")
                return
            self.send_json(payload)
            return

        self.send_error(HTTPStatus.NOT_FOUND, "unknown api endpoint")

    def handle_post_api(self, parsed) -> None:
        if parsed.path == "/api/live-thread/messages":
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length else b"{}"
            try:
                payload = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                self.send_error(HTTPStatus.BAD_REQUEST, "invalid json body")
                return
            body = str(payload.get("body", "")).strip()
            if not body:
                self.send_error(HTTPStatus.BAD_REQUEST, "body is required")
                return
            with self.dashboard_config.api_lock:
                result = chat.post_user_message(
                    self.dashboard_config.root,
                    self.dashboard_config.config_path,
                    body,
                )
            self.send_json(result)
            return

        self.send_error(HTTPStatus.NOT_FOUND, "unknown api endpoint")

    def send_json(self, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:
        return


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Serve the peerforge dashboard")
    parser.add_argument("--root", default=".peerforge", help="Runtime root containing board.json and sessions/")
    parser.add_argument("--config", default=".peerforge/config.json", help="Config JSON used for agent routing and status")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host")
    parser.add_argument("--port", type=int, default=8765, help="Bind port")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = DashboardConfig(
        root=Path(args.root).resolve(),
        config_path=Path(args.config).resolve(),
        host=args.host,
        port=args.port,
        api_lock=threading.Lock(),
    )
    server = ThreadingHTTPServer(
        (config.host, config.port),
        partial(DashboardHandler, config=config),
    )
    print(f"http://{config.host}:{config.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
