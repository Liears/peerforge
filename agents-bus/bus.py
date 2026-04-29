#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys
import textwrap
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def timeout_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def parse_json_block(text: str) -> dict[str, Any] | None:
    text = text.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None
    return None


def normalize_slug(text: str) -> str:
    chars = []
    for char in text.lower():
        if char.isalnum():
            chars.append(char)
        elif not chars or chars[-1] != "-":
            chars.append("-")
    value = "".join(chars).strip("-")
    return value or "task"


def expand_template(value: str, variables: dict[str, str]) -> str:
    for key, item in variables.items():
        value = value.replace("{" + key + "}", item)
    return value


def build_agent_prompt(
    agent_name: str,
    task: str,
    peers: list[str],
    history: list[dict[str, Any]],
    round_idx: int,
) -> str:
    history_text = []
    for row in history:
        history_text.append(
            f"[{row['created_at']}] {row['from']} -> {','.join(row['to'])} | {row['kind']}: {row['body']}"
        )

    history_block = "\n".join(history_text) if history_text else "(no history)"
    peer_text = ", ".join(peers)
    return textwrap.dedent(
        f"""
        You are agent "{agent_name}" in a peer-to-peer multi-agent group.

        Shared task:
        {task}

        Peers:
        {peer_text}

        Current round:
        {round_idx}

        Protocol:
        - You are equal to the other agents.
        - You may question, critique, propose, hand off, or finalize.
        - You may send direct messages to one or more peers.
        - Use ["*"] to broadcast to all peers except yourself.
        - Return JSON only.
        - Keep messages concrete and short.
        - Avoid repeating a message unless there is genuinely new information.
        - If you believe your part is done, set status to "done".

        Recent history:
        {history_block}

        Return exactly this shape:
        {{
          "status": "continue",
          "summary": "one short sentence",
          "messages": [
            {{
              "to": ["peer_name_or_*"],
              "kind": "proposal",
              "body": "message text"
            }}
          ]
        }}
        """
    ).strip()


@dataclass
class AgentResult:
    ok: bool
    status: str
    summary: str
    messages: list[dict[str, Any]]
    raw_output: str
    error: str | None = None


class AgentAdapter:
    def __init__(self, spec: dict[str, Any], workdir: Path, runtime_root: Path, timeout_seconds: int):
        self.spec = spec
        self.name = spec["name"]
        self.type = spec["type"]
        self.workdir = workdir
        self.runtime_root = runtime_root
        self.timeout_seconds = timeout_seconds
        self.agent_runtime_dir = (runtime_root / self.name).resolve()
        self.agent_runtime_dir.mkdir(parents=True, exist_ok=True)

    def template_vars(self, prompt: str = "") -> dict[str, str]:
        return {
            "workdir": str(self.workdir),
            "runtime_root": str(self.runtime_root),
            "agent_runtime_dir": str(self.agent_runtime_dir),
            "prompt": prompt,
        }

    def env(self, prompt: str = "") -> dict[str, str]:
        env = os.environ.copy()
        variables = self.template_vars(prompt)
        for key, value in self.spec.get("env", {}).items():
            env[str(key)] = expand_template(str(value), variables)
        return env

    def run(self, prompt: str) -> AgentResult:
        try:
            argv = self.build_argv(prompt)
            proc = subprocess.run(
                argv,
                cwd=self.workdir,
                env=self.env(prompt),
                text=True,
                capture_output=True,
                timeout=self.timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            return AgentResult(
                ok=False,
                status="error",
                summary="timeout",
                messages=[],
                raw_output=timeout_text(exc.stdout) + "\n" + timeout_text(exc.stderr),
                error=f"timeout after {self.timeout_seconds}s",
            )
        except FileNotFoundError as exc:
            return AgentResult(
                ok=False,
                status="error",
                summary="missing command",
                messages=[],
                raw_output="",
                error=str(exc),
            )

        combined = (proc.stdout or "").strip()
        if proc.stderr:
            combined = combined + ("\n" if combined else "") + proc.stderr.strip()

        if proc.returncode != 0:
            return AgentResult(
                ok=False,
                status="error",
                summary="command failed",
                messages=[],
                raw_output=combined,
                error=f"exit code {proc.returncode}",
            )

        parsed = self.parse_output(proc.stdout or "")
        if parsed is None:
            return AgentResult(
                ok=False,
                status="error",
                summary="invalid json reply",
                messages=[],
                raw_output=combined,
                error="could not parse protocol JSON",
            )

        messages = parsed.get("messages", [])
        if not isinstance(messages, list):
            messages = []

        return AgentResult(
            ok=True,
            status=str(parsed.get("status", "continue")),
            summary=str(parsed.get("summary", "")),
            messages=messages,
            raw_output=combined,
        )

    def probe(self) -> dict[str, Any]:
        try:
            argv = self.build_probe_argv()
            proc = subprocess.run(
                argv,
                cwd=self.workdir,
                env=self.env(),
                text=True,
                capture_output=True,
                timeout=min(self.timeout_seconds, 15),
            )
        except subprocess.TimeoutExpired as exc:
            return {
                "ok": False,
                "status": "timeout",
                "command": " ".join(argv),
                "details": (timeout_text(exc.stdout) + "\n" + timeout_text(exc.stderr)).strip(),
            }
        except FileNotFoundError as exc:
            return {
                "ok": False,
                "status": "missing_command",
                "command": self.type,
                "details": str(exc),
            }

        combined = (proc.stdout or "").strip()
        if proc.stderr:
            combined = combined + ("\n" if combined else "") + proc.stderr.strip()

        status = "ready" if proc.returncode == 0 else "error"
        lower = combined.lower()
        if "not logged in" in lower:
            status = "needs_login"
        elif "no api keys" in lower or "no api key" in lower or "no providers found" in lower:
            status = "needs_provider"
        elif "operation not permitted" in lower or "failed to connect to websocket" in lower:
            status = "network_blocked"
        elif "unknown agent id" in lower or "pass --to" in lower:
            status = "needs_agent_binding"

        return {
            "ok": proc.returncode == 0,
            "status": status,
            "command": " ".join(argv),
            "details": combined[-4000:],
        }

    def build_argv(self, prompt: str) -> list[str]:
        variables = self.template_vars(prompt)

        if self.type == "codex":
            return [
                "codex",
                "exec",
                "--skip-git-repo-check",
                "--sandbox",
                "workspace-write",
                "--json",
                "--cd",
                str(self.workdir),
                prompt,
            ]

        if self.type == "claude":
            return [
                "claude",
                "-p",
                "--output-format",
                "json",
                prompt,
            ]

        if self.type == "hermes":
            return [
                "hermes",
                "chat",
                "-q",
                prompt,
                "-Q",
            ]

        if self.type == "openclaw":
            agent_id = self.spec.get("agent_id")
            if not agent_id:
                raise FileNotFoundError("openclaw agent_id is missing")
            return [
                "openclaw",
                "agent",
                "--local",
                "--agent",
                str(agent_id),
                "--message",
                prompt,
                "--json",
            ]

        if self.type == "command":
            cmd = self.spec.get("command")
            if not isinstance(cmd, list) or not cmd:
                raise FileNotFoundError("custom command is missing")
            return [expand_template(str(part), variables) for part in cmd]

        raise FileNotFoundError(f"unsupported adapter type: {self.type}")

    def build_probe_argv(self) -> list[str]:
        if self.type == "codex":
            return ["codex", "--version"]
        if self.type == "claude":
            return ["claude", "-p", "--output-format", "json", "--no-session-persistence", "ping"]
        if self.type == "hermes":
            return ["hermes", "chat", "-q", "ping", "-Q"]
        if self.type == "openclaw":
            agent_id = self.spec.get("agent_id")
            if agent_id:
                return ["openclaw", "agent", "--local", "--agent", str(agent_id), "--message", "ping", "--json"]
            return ["openclaw", "agents", "list", "--json"]
        if self.type == "command":
            return self.build_argv('{"status":"done","summary":"probe","messages":[]}')
        raise FileNotFoundError(f"unsupported adapter type: {self.type}")

    def parse_output(self, stdout: str) -> dict[str, Any] | None:
        if self.type == "codex":
            return self._parse_codex_jsonl(stdout)
        if self.type == "claude":
            return self._parse_claude_json(stdout)
        return parse_json_block(stdout)

    def _parse_codex_jsonl(self, stdout: str) -> dict[str, Any] | None:
        last_text = None
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue

            if not isinstance(row, dict):
                continue

            msg = row.get("msg") or row.get("message")
            if isinstance(msg, dict):
                content = msg.get("content")
                if isinstance(content, str):
                    last_text = content
            elif isinstance(msg, str):
                last_text = msg
            elif isinstance(row.get("content"), str):
                last_text = row["content"]

        return parse_json_block(last_text or stdout)

    def _parse_claude_json(self, stdout: str) -> dict[str, Any] | None:
        obj = parse_json_block(stdout)
        if not isinstance(obj, dict):
            return None

        for key in ("result", "content", "text", "output"):
            if key in obj and isinstance(obj[key], str):
                nested = parse_json_block(obj[key])
                if nested is not None:
                    return nested
        return obj if "messages" in obj else None


class Bus:
    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.workdir = Path(config["workdir"]).resolve()
        self.session_root = Path(config["session_dir"]).resolve()
        self.runtime_root = Path(config.get("runtime_dir", self.session_root.parent / "runtime")).resolve()
        self.timeout_seconds = int(config.get("timeout_seconds", 45))
        self.history_limit = int(config.get("history_limit", 16))
        self.session_root.mkdir(parents=True, exist_ok=True)
        self.runtime_root.mkdir(parents=True, exist_ok=True)
        self.adapters = [
            AgentAdapter(spec, self.workdir, self.runtime_root, self.timeout_seconds)
            for spec in config["agents"]
            if spec.get("enabled", True)
        ]

    def run(self, task: str, rounds: int, title: str | None = None) -> Path:
        session_id = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8]
        session_dir = self.session_root / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        log_path = session_dir / "transcript.jsonl"
        summary_path = session_dir / "summary.json"

        agent_names = [a.name for a in self.adapters]
        seed = {
            "id": uuid.uuid4().hex,
            "created_at": now_iso(),
            "from": "user",
            "to": agent_names,
            "kind": "task",
            "body": task,
            "round": 0,
            "title": title or task[:80],
        }
        append_jsonl(log_path, seed)
        history = [seed]
        statuses = {name: "continue" for name in agent_names}
        seen_index = {name: 0 for name in agent_names}

        for round_idx in range(1, rounds + 1):
            progress = False
            for adapter in self.adapters:
                if statuses.get(adapter.name) == "done":
                    continue
                if not self._has_pending_messages(adapter.name, history, seen_index[adapter.name]):
                    continue

                prompt = build_agent_prompt(adapter.name, task, agent_names, history[-self.history_limit :], round_idx)
                seen_index[adapter.name] = len(history)
                result = adapter.run(prompt)

                if not result.ok:
                    row = {
                        "id": uuid.uuid4().hex,
                        "created_at": now_iso(),
                        "from": adapter.name,
                        "to": ["*"],
                        "kind": "error",
                        "body": result.error or "unknown error",
                        "round": round_idx,
                        "raw_output": result.raw_output[-4000:],
                    }
                    append_jsonl(log_path, row)
                    history.append(row)
                    progress = True
                    continue

                statuses[adapter.name] = result.status
                summary_row = {
                    "id": uuid.uuid4().hex,
                    "created_at": now_iso(),
                    "from": adapter.name,
                    "to": ["*"],
                    "kind": "status",
                    "body": result.summary,
                    "round": round_idx,
                    "state": result.status,
                }
                append_jsonl(log_path, summary_row)
                history.append(summary_row)
                progress = True

                for msg in result.messages:
                    recipients = msg.get("to", ["*"])
                    if recipients == ["*"]:
                        recipients = [name for name in agent_names if name != adapter.name]
                    if isinstance(recipients, str):
                        recipients = [recipients]
                    row = {
                        "id": uuid.uuid4().hex,
                        "created_at": now_iso(),
                        "from": adapter.name,
                        "to": recipients,
                        "kind": str(msg.get("kind", "message")),
                        "body": str(msg.get("body", "")),
                        "round": round_idx,
                    }
                    append_jsonl(log_path, row)
                    history.append(row)

            if not progress or all(status == "done" for status in statuses.values()):
                break

        write_json(
            summary_path,
            {
                "title": title or task[:80],
                "task": task,
                "created_at": seed["created_at"],
                "agents": agent_names,
                "final_statuses": statuses,
                "transcript": str(log_path),
            },
        )
        return log_path

    def _has_pending_messages(self, agent_name: str, history: list[dict[str, Any]], start: int) -> bool:
        for row in history[start:]:
            recipients = row.get("to", [])
            if "*" in recipients or agent_name in recipients:
                if row.get("from") != agent_name:
                    return True
        return False


def board_path(root: Path) -> Path:
    return root / "board.json"


def default_board() -> dict[str, Any]:
    return {"tasks": []}


def read_board(root: Path) -> dict[str, Any]:
    path = board_path(root)
    if not path.exists():
        return default_board()
    return read_json(path)


def write_board(root: Path, board: dict[str, Any]) -> None:
    write_json(board_path(root), board)


def cmd_init(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    write_board(root, default_board())
    runtime = root / "runtime"
    sessions = root / "sessions"
    runtime.mkdir(parents=True, exist_ok=True)
    sessions.mkdir(parents=True, exist_ok=True)
    print(str(root))
    return 0


def cmd_task_add(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    board = read_board(root)
    task_id = normalize_slug(args.title)
    suffix = 1
    existing = {item["id"] for item in board["tasks"]}
    unique_id = task_id
    while unique_id in existing:
        suffix += 1
        unique_id = f"{task_id}-{suffix}"

    row = {
        "id": unique_id,
        "title": args.title,
        "description": args.description,
        "status": args.status,
        "owner": args.owner,
        "created_at": now_iso(),
        "depends_on": args.depends_on or [],
    }
    board["tasks"].append(row)
    write_board(root, board)
    print(unique_id)
    return 0


def cmd_task_list(args: argparse.Namespace) -> int:
    board = read_board(Path(args.root).resolve())
    rows = board.get("tasks", [])
    if args.status:
        rows = [row for row in rows if row.get("status") == args.status]
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    return 0


def cmd_task_update(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    board = read_board(root)
    for row in board.get("tasks", []):
        if row["id"] != args.task_id:
            continue
        if args.status:
            row["status"] = args.status
        if args.owner is not None:
            row["owner"] = args.owner
        write_board(root, board)
        print(row["id"])
        return 0
    raise SystemExit(f"task not found: {args.task_id}")


def cmd_run(args: argparse.Namespace) -> int:
    config = read_json(Path(args.config))
    bus = Bus(config)
    log_path = bus.run(task=args.task, rounds=args.rounds, title=args.title)
    print(str(log_path))
    return 0


def cmd_run_task(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    config = read_json(Path(args.config))
    board = read_board(root)
    for row in board.get("tasks", []):
        if row["id"] != args.task_id:
            continue
        task_text = f"{row['title']}\n\n{row['description']}"
        bus = Bus(config)
        log_path = bus.run(task=task_text, rounds=args.rounds, title=row["title"])
        row["status"] = "in_review"
        row["last_run_at"] = now_iso()
        row["last_transcript"] = str(log_path)
        write_board(root, board)
        print(str(log_path))
        return 0
    raise SystemExit(f"task not found: {args.task_id}")


def cmd_check(args: argparse.Namespace) -> int:
    config = read_json(Path(args.config))
    bus = Bus(config)
    rows = []
    for adapter in bus.adapters:
        result = adapter.probe()
        result["name"] = adapter.name
        result["type"] = adapter.type
        rows.append(result)
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Peer-to-peer local multi-agent bus")
    sub = parser.add_subparsers(dest="command", required=True)

    init_parser = sub.add_parser("init", help="Initialize project state directories")
    init_parser.add_argument("--root", default="agents-bus", help="Project root directory")
    init_parser.set_defaults(func=cmd_init)

    run_parser = sub.add_parser("run", help="Run a multi-agent discussion")
    run_parser.add_argument("--config", required=True, help="Path to config JSON")
    run_parser.add_argument("--task", required=True, help="Shared task for the agents")
    run_parser.add_argument("--title", help="Optional human-readable title")
    run_parser.add_argument("--rounds", type=int, default=2, help="Maximum discussion rounds")
    run_parser.set_defaults(func=cmd_run)

    task_add_parser = sub.add_parser("task-add", help="Add a task to the board")
    task_add_parser.add_argument("--root", default="agents-bus", help="Project root directory")
    task_add_parser.add_argument("--title", required=True, help="Short task title")
    task_add_parser.add_argument("--description", required=True, help="Task details")
    task_add_parser.add_argument("--owner", default="pm", help="Task owner label")
    task_add_parser.add_argument("--status", default="todo", help="Initial status")
    task_add_parser.add_argument("--depends-on", nargs="*", help="Task ids this task depends on")
    task_add_parser.set_defaults(func=cmd_task_add)

    task_list_parser = sub.add_parser("task-list", help="List tasks from the board")
    task_list_parser.add_argument("--root", default="agents-bus", help="Project root directory")
    task_list_parser.add_argument("--status", help="Optional status filter")
    task_list_parser.set_defaults(func=cmd_task_list)

    task_update_parser = sub.add_parser("task-update", help="Update a task in the board")
    task_update_parser.add_argument("task_id", help="Task id")
    task_update_parser.add_argument("--root", default="agents-bus", help="Project root directory")
    task_update_parser.add_argument("--status", help="New status")
    task_update_parser.add_argument("--owner", help="New owner")
    task_update_parser.set_defaults(func=cmd_task_update)

    run_task_parser = sub.add_parser("run-task", help="Run a board task through the bus")
    run_task_parser.add_argument("task_id", help="Task id")
    run_task_parser.add_argument("--root", default="agents-bus", help="Project root directory")
    run_task_parser.add_argument("--config", required=True, help="Path to config JSON")
    run_task_parser.add_argument("--rounds", type=int, default=2, help="Maximum discussion rounds")
    run_task_parser.set_defaults(func=cmd_run_task)

    check_parser = sub.add_parser("check", help="Run readiness probes for configured agents")
    check_parser.add_argument("--config", required=True, help="Path to config JSON")
    check_parser.set_defaults(func=cmd_check)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
