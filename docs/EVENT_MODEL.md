# peerforge Event Model

Phase 1 uses a single event envelope for the live chat thread.

## Envelope

```json
{
  "id": "evt_123",
  "thread_id": "main",
  "created_at": "2026-04-30T12:00:00+00:00",
  "type": "chat.message",
  "source": "codex",
  "target": ["hermes"],
  "round": 2,
  "payload": {
    "kind": "proposal",
    "body": "I suggest we split the rendering and routing work."
  },
  "meta": {
    "status": "continue"
  }
}
```

## Required Fields

- `id`
- `thread_id`
- `created_at`
- `type`
- `source`
- `target`
- `payload`

## Optional Fields

- `round`
- `task_id`
- `session_id`
- `meta`

## Phase 1 Event Types

### `session.started`

Marks creation of the live thread.

### `user.input`

Raw user intent before agent routing.

Payload:

- `body`
- `mentions`

### `chat.message`

A user-facing routed message.

Payload:

- `kind`
- `body`

Kinds may include:

- `message`
- `proposal`
- `question`
- `answer`
- `status`

### `tool.call`

One agent invocation attempt.

Payload:

- `tool`
- `agent`
- `command_preview`

### `tool.result`

Completion of one tool invocation.

Payload:

- `tool`
- `agent`
- `ok`
- `summary`
- `duration_ms`
- `error`
- `raw_output`

### `system.notice`

Structured platform event.

Payload:

- `level`
- `code`
- `message`

Examples:

- `no_ready_agents`
- `no_mentions_detected`
- `route_complete`
- `agent_timeout`

### `heartbeat.updated`

Runtime liveness state change.

Payload:

- `agent`
- `state`
- `task_id`

### `task.status_changed`

Task lifecycle update reflected into the live timeline.

Payload:

- `task_id`
- `from_status`
- `to_status`

## Rendering Rules

- `chat.message` renders as a chat bubble
- `tool.call` and `tool.result` render as execution cards
- `system.notice` renders as a subdued system row
- `heartbeat.updated` renders in the state pane and may be echoed in the timeline
- `target` renders as `@agent` chips or `@all`

## Source-of-Truth Rules

- event log is the truth for live conversation
- `board.json` is the truth for task status and claim ownership
- heartbeat files are the truth for liveness

The frontend must not infer task truth from event text alone.
