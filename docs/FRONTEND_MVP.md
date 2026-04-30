# peerforge Frontend MVP

Phase 1 frontend is a group-chat control console.

It is not a generic chat app and not a full operations platform.

## Layout

### Center: Chat Timeline

The primary view.

Shows:

- user messages
- agent replies
- agent-to-agent `@` handoffs
- tool call cards
- tool result cards
- system notices

Each entry shows:

- source
- target chips
- timestamp
- round
- event kind

### Left: Task Context

Read-only board context.

Shows:

- task list
- task status
- owner
- claim holder
- lease expiry
- last transcript path

Phase 1 does not require full board mutation from the UI.

### Right: Agent State

Shows one card per agent:

- agent name
- `ready|busy|offline`
- current task, if any
- last heartbeat update
- last active timestamp

### Bottom: Input Bar

Single input for live routing.

Supports:

- `@codex`
- `@claude`
- `@hermes`
- `@openclaw`
- `@all`

Phase 1 only requires message sending, not a full command language.

## Highlight Rules

Always highlight:

- directed `@agent` messages
- `@all` broadcast
- tool failures
- timeouts
- task claim and release events
- `busy` and `offline` agent states

Default collapsed:

- long tool output
- repeated success notices
- repeated heartbeat refreshes

## Interaction Rules

- input `@agent` creates a routed message, not a visual mention only
- clicking a task filters or anchors the timeline context
- clicking an agent highlights its recent events
- page refresh must preserve the current live thread history

## Phase 1 UX Goals

The user should be able to answer these questions immediately:

- who is talking to whom
- which agent is busy
- what tool was invoked
- whether the system is blocked or progressing
- what task is currently in focus

## Phase 1 Non-Goals

Not required yet:

- multiple rooms
- drag-and-drop task planning
- advanced filtering/search
- rich text editor
- websocket streaming
- direct GitHub issue/PR actions from the UI
