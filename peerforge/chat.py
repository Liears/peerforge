#!/usr/bin/env python3
import json
import re
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from peerforge import bus
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    import bus  # type: ignore


LIVE_THREAD_ID = "main"
MAX_ROUTE_STEPS = 12
DEFAULT_ROUTE_ROUNDS = 4
MENTION_RE = re.compile(r"@([a-zA-Z0-9_-]+)")
THREAD_LOCK = threading.Lock()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def thread_root(root: Path, thread_id: str = LIVE_THREAD_ID) -> Path:
    return root / "threads" / thread_id


def thread_events_path(root: Path, thread_id: str = LIVE_THREAD_ID) -> Path:
    return thread_root(root, thread_id) / "events.jsonl"


def thread_state_path(root: Path, thread_id: str = LIVE_THREAD_ID) -> Path:
    return thread_root(root, thread_id) / "state.json"


def ensure_thread(root: Path, thread_id: str = LIVE_THREAD_ID) -> dict[str, Any]:
    base = thread_root(root, thread_id)
    base.mkdir(parents=True, exist_ok=True)
    state_path = thread_state_path(root, thread_id)
    events_path = thread_events_path(root, thread_id)
    if state_path.exists():
        return json.loads(state_path.read_text(encoding="utf-8"))

    state = {
        "id": thread_id,
        "title": "Main agent thread",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "status": "idle",
        "participants": [],
        "last_event_id": None,
    }
    write_thread_state(root, state, thread_id)
    append_event(
        root,
        {
            "id": f"evt_{uuid.uuid4().hex}",
            "thread_id": thread_id,
            "created_at": now_iso(),
            "type": "session.started",
            "source": "system",
            "target": ["@all"],
            "payload": {"message": "Live thread initialized"},
            "meta": {},
        },
    )
    if not events_path.exists():
        events_path.touch()
    return state


def write_thread_state(root: Path, state: dict[str, Any], thread_id: str = LIVE_THREAD_ID) -> None:
    path = thread_state_path(root, thread_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_events(root: Path, thread_id: str = LIVE_THREAD_ID) -> list[dict[str, Any]]:
    path = thread_events_path(root, thread_id)
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def append_event(root: Path, event: dict[str, Any], thread_id: str = LIVE_THREAD_ID) -> None:
    path = thread_events_path(root, thread_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def load_thread(root: Path, thread_id: str = LIVE_THREAD_ID) -> dict[str, Any]:
    ensure_thread(root, thread_id)
    state = json.loads(thread_state_path(root, thread_id).read_text(encoding="utf-8"))
    events = read_events(root, thread_id)
    return {"thread": state, "events": events}


def parse_mentions(body: str, agent_names: list[str]) -> list[str]:
    if not body:
        return []
    found: list[str] = []
    allowed = {name.lower(): name for name in agent_names}
    for match in MENTION_RE.findall(body):
        lowered = match.lower()
        if lowered == "all":
            return ["@all"]
        if lowered in allowed and allowed[lowered] not in found:
            found.append(allowed[lowered])
    return found


def render_targets(targets: list[str]) -> list[str]:
    rendered = []
    for target in targets:
        if target == "@all":
            rendered.append("@all")
        elif str(target).startswith("@"):
            rendered.append(str(target))
        else:
            rendered.append(f"@{target}")
    return rendered


def create_event(
    event_type: str,
    source: str,
    target: list[str],
    payload: dict[str, Any],
    *,
    thread_id: str = LIVE_THREAD_ID,
    round_idx: int | None = None,
    meta: dict[str, Any] | None = None,
    task_id: str | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": f"evt_{uuid.uuid4().hex}",
        "thread_id": thread_id,
        "created_at": now_iso(),
        "type": event_type,
        "source": source,
        "target": target,
        "payload": payload,
        "meta": meta or {},
    }
    if round_idx is not None:
        row["round"] = round_idx
    if task_id:
        row["task_id"] = task_id
    return row


def event_brief(event: dict[str, Any]) -> str:
    event_type = event.get("type", "unknown")
    payload = event.get("payload", {})
    source = event.get("source", "system")
    target = ",".join(render_targets(list(event.get("target", []))))
    if event_type in {"user.input", "chat.message"}:
        kind = payload.get("kind", event_type)
        body = payload.get("body", "")
        return f"[{event['created_at']}] {source} -> {target} | {kind}: {body}"
    if event_type == "tool.call":
        return f"[{event['created_at']}] {source} -> {target} | tool.call: {payload.get('tool')} {payload.get('command_preview', '')}"
    if event_type == "tool.result":
        return f"[{event['created_at']}] {source} -> {target} | tool.result: {payload.get('summary', '')}"
    if event_type == "system.notice":
        return f"[{event['created_at']}] system -> {target} | notice: {payload.get('message', '')}"
    return f"[{event['created_at']}] {source} -> {target} | {event_type}"


def build_live_prompt(
    agent_name: str,
    peers: list[str],
    events: list[dict[str, Any]],
    round_idx: int,
    title: str,
) -> str:
    history_block = "\n".join(event_brief(row) for row in events[-16:]) or "(no history)"
    peer_text = ", ".join(peers)
    return f"""
You are agent "{agent_name}" in the live peerforge chat thread "{title}".

Peers:
{peer_text}

Current round:
{round_idx}

Protocol:
- You are an equal peer in a multi-agent chat.
- Respond with JSON only.
- You may send directed replies to one or more peers.
- Use ["*"] to broadcast to all peers except yourself.
- Keep messages concrete and short.
- If you do not need help, you may set status to "done".

Recent event history:
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
""".strip()


def config_agent_names(config: dict[str, Any]) -> list[str]:
    return [agent["name"] for agent in config.get("agents", []) if agent.get("enabled", True)]


def live_agent_status(config: dict[str, Any], probe: bool = False) -> list[dict[str, Any]]:
    runtime_root = Path(config.get("runtime_dir", ".peerforge/runtime")).resolve()
    bus_instance = bus.Bus(config)
    rows: list[dict[str, Any]] = []
    for adapter in bus_instance.adapters:
        heartbeat = bus.read_heartbeat(runtime_root, adapter.name)
        probe_status = adapter.probe().get("status", "error") if probe else "skipped"
        heartbeat_state = bus.heartbeat_state(heartbeat) if heartbeat is not None else "unknown"
        rows.append(
            {
                "name": adapter.name,
                "type": adapter.type,
                "probe": probe_status,
                "heartbeat": heartbeat_state,
                "heartbeat_raw": heartbeat,
            }
        )
    return rows


def _ready_targets(config: dict[str, Any], requested: list[str]) -> list[str]:
    if "@all" in requested:
        requested = config_agent_names(config)
    status_rows = live_agent_status(config, probe=False)
    states = {row["name"]: row["heartbeat"] for row in status_rows}
    selected: list[str] = []
    for name in requested:
        state = states.get(name, "unknown")
        if state not in {"busy", "offline"}:
            selected.append(name)
    return selected


def post_user_message(root: Path, config_path: Path, body: str, thread_id: str = LIVE_THREAD_ID) -> dict[str, Any]:
    with THREAD_LOCK:
        state = ensure_thread(root, thread_id)
        config = bus.read_json(config_path)
        agent_names = config_agent_names(config)
        mentioned = parse_mentions(body, agent_names)
        requested = mentioned or ["@all"]

        user_event = create_event(
            "user.input",
            "user",
            requested,
            {"body": body, "mentions": requested},
            thread_id=thread_id,
            round_idx=0,
        )
        append_event(root, user_event, thread_id)

        ready_targets = _ready_targets(config, requested)
        if not ready_targets:
            append_event(
                root,
                create_event(
                    "system.notice",
                    "system",
                    render_targets(requested),
                    {"level": "warning", "code": "no_ready_agents", "message": "No ready agents matched the message"},
                    thread_id=thread_id,
                ),
                thread_id,
            )
            state["updated_at"] = now_iso()
            state["status"] = "idle"
            state["last_event_id"] = user_event["id"]
            write_thread_state(root, state, thread_id)
            return load_thread(root, thread_id)

        live_bus = bus.Bus(config)
        adapters = {adapter.name: adapter for adapter in live_bus.adapters}
        pending = [{"target": name, "source": "user", "kind": "message", "body": body, "round": 1} for name in ready_targets]
        route_steps = 0

        append_event(
            root,
            create_event(
                "system.notice",
                "system",
                render_targets(ready_targets),
                {"level": "info", "code": "route_started", "message": "Routing message to ready agents"},
                thread_id=thread_id,
            ),
            thread_id,
        )

        while pending and route_steps < MAX_ROUTE_STEPS:
            item = pending.pop(0)
            route_steps += 1
            target = item["target"]
            adapter = adapters.get(target)
            if adapter is None:
                append_event(
                    root,
                    create_event(
                        "system.notice",
                        "system",
                        [f"@{target}"],
                        {"level": "error", "code": "missing_agent", "message": f"Agent {target} is not configured"},
                        thread_id=thread_id,
                        round_idx=item["round"],
                    ),
                    thread_id,
                )
                continue

            events = read_events(root, thread_id)
            prompt = build_live_prompt(target, agent_names, events, item["round"], state["title"])
            command_preview = adapter.type

            append_event(
                root,
                create_event(
                    "tool.call",
                    target,
                    [f"@{target}"],
                    {"tool": adapter.type, "agent": target, "command_preview": command_preview},
                    thread_id=thread_id,
                    round_idx=item["round"],
                ),
                thread_id,
            )
            bus.write_heartbeat(live_bus.runtime_root, target, "busy", task_id=None, claim_token=None, message="chat dispatch")
            heartbeat_event = create_event(
                "heartbeat.updated",
                "system",
                [f"@{target}"],
                {"agent": target, "state": "busy"},
                thread_id=thread_id,
                round_idx=item["round"],
            )
            append_event(root, heartbeat_event, thread_id)

            started = time.monotonic()
            result = adapter.run(prompt)
            duration_ms = int((time.monotonic() - started) * 1000)

            append_event(
                root,
                create_event(
                    "tool.result",
                    target,
                    [f"@{target}"],
                    {
                        "tool": adapter.type,
                        "agent": target,
                        "ok": result.ok,
                        "summary": result.summary,
                        "duration_ms": duration_ms,
                        "error": result.error,
                        "raw_output": result.raw_output[-2000:],
                    },
                    thread_id=thread_id,
                    round_idx=item["round"],
                ),
                thread_id,
            )

            if not result.ok:
                bus.write_heartbeat(live_bus.runtime_root, target, "offline", message=result.error or "agent error")
                append_event(
                    root,
                    create_event(
                        "heartbeat.updated",
                        "system",
                        [f"@{target}"],
                        {"agent": target, "state": "offline"},
                        thread_id=thread_id,
                        round_idx=item["round"],
                    ),
                    thread_id,
                )
                append_event(
                    root,
                    create_event(
                        "system.notice",
                        "system",
                        [f"@{target}"],
                        {"level": "error", "code": "agent_error", "message": result.error or "Agent invocation failed"},
                        thread_id=thread_id,
                        round_idx=item["round"],
                    ),
                    thread_id,
                )
                continue

            bus.write_heartbeat(live_bus.runtime_root, target, "ready", message="idle")
            append_event(
                root,
                create_event(
                    "heartbeat.updated",
                    "system",
                    [f"@{target}"],
                    {"agent": target, "state": "ready"},
                    thread_id=thread_id,
                    round_idx=item["round"],
                ),
                thread_id,
            )

            append_event(
                root,
                create_event(
                    "system.notice",
                    "system",
                    [f"@{target}"],
                    {"level": "info", "code": "agent_status", "message": result.summary, "status": result.status},
                    thread_id=thread_id,
                    round_idx=item["round"],
                ),
                thread_id,
            )

            for msg in result.messages:
                recipients = msg.get("to", ["*"])
                if recipients == ["*"]:
                    recipients = [name for name in agent_names if name != target]
                if isinstance(recipients, str):
                    recipients = [recipients]
                normalized_targets = [f"@{name}" for name in recipients]
                append_event(
                    root,
                    create_event(
                        "chat.message",
                        target,
                        normalized_targets,
                        {"kind": str(msg.get("kind", "message")), "body": str(msg.get("body", ""))},
                        thread_id=thread_id,
                        round_idx=item["round"],
                        meta={"status": result.status},
                    ),
                    thread_id,
                )
                for recipient in recipients:
                    if recipient in agent_names and recipient != target and item["round"] < DEFAULT_ROUTE_ROUNDS:
                        pending.append(
                            {
                                "target": recipient,
                                "source": target,
                                "kind": str(msg.get("kind", "message")),
                                "body": str(msg.get("body", "")),
                                "round": item["round"] + 1,
                            }
                        )

        append_event(
            root,
            create_event(
                "session.ended",
                "system",
                ["@all"],
                {"message": "Route loop completed", "steps": route_steps},
                thread_id=thread_id,
            ),
            thread_id,
        )
        state["updated_at"] = now_iso()
        state["status"] = "idle"
        state["participants"] = agent_names
        write_thread_state(root, state, thread_id)
        return load_thread(root, thread_id)
