# peerforge Architecture

`peerforge` is a local control plane for a small team of equal-peer CLI agents.

Phase 1 intentionally stays small:

- one live chat thread
- one input box
- `@agent` and `@all` routing
- agent-to-agent replies
- tool call and tool result visibility
- persistent event log
- read-only board and agent-state sidebars

## Layer Model

Phase 1 has five layers.

### Event Layer

Everything becomes an event:

- user input
- chat messages
- tool calls
- tool results
- system notices
- task state changes
- heartbeat changes

The event log is the main replay source for the frontend.

### Route Layer

The router is responsible for:

- parsing `@agent` and `@all`
- choosing target agents
- enforcing single-thread message order
- invoking agents
- re-routing agent-to-agent replies

The router does not own task truth or liveness truth.

### State Layer

State remains split by source of truth:

- `.peerforge/board.json`
  - task truth
  - claim and lease truth
- `.peerforge/runtime/heartbeats/*.json`
  - `ready|busy|offline`
  - runtime liveness only
- `.peerforge/threads/<thread-id>/events.jsonl`
  - live thread truth
  - user messages, agent replies, tool events, system notices
- `.peerforge/sessions/*/transcript.jsonl`
  - batch task-run history
  - existing `bus.py` execution history

### Execution Layer

`peerforge/bus.py` remains the execution kernel:

- agent adapters
- readiness probes
- heartbeat helpers
- board mutation helpers

Phase 1 adds a thin chat loop on top of that kernel instead of replacing it.

### UI Layer

The dashboard becomes a control console:

- chat timeline in the center
- board/task context on one side
- agent state on one side
- one input box for `@agent` messages

The UI is intent-driven. It does not mutate state directly.

## Data Boundaries

Keep these hard boundaries:

- board ownership lives only in `board.json`
- liveness lives only in heartbeat files
- live conversation lives only in thread events
- batch task execution history lives only in session transcripts
- the frontend never invents state from mixed sources

If the board and heartbeat disagree, trust the board for ownership.

If the thread and board disagree, trust the board for task state and the thread for conversation history.

## Phase 1 Runtime Flow

The live thread loop is:

1. user sends a message
2. router parses `@agent` targets
3. router selects ready agents
4. router appends a `user.input` event
5. router appends `tool.call` for each agent invocation
6. agent output is normalized into:
   - `chat.message`
   - `system.notice`
   - `tool.result`
7. agent-to-agent replies are routed back into the same thread
8. thread state and heartbeat state are updated
9. frontend reloads the event stream

Phase 1 stays single-threaded on purpose so the ordering remains explainable.

## Existing Modules

### `peerforge/bus.py`

Owns:

- agent invocation
- board lock and claim logic
- readiness and heartbeat helpers
- batch task-run flows

### `peerforge/dashboard.py`

Owns:

- local HTTP serving
- read APIs for board, sessions, and live threads
- write API for chat input

### `peerforge/chat.py`

Owns:

- thread event log
- `@agent` parsing
- single-thread router loop
- live chat session state

## Phase 1 Non-Goals

Not part of Phase 1:

- multiple live rooms
- distributed coordination
- websocket streaming
- direct GitHub issue or PR creation from the UI
- complex task board editing from the frontend
- analytics or observability dashboards
