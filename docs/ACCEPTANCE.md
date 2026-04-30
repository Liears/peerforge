# Phase 1 Acceptance

Phase 1 is accepted only if the minimal multi-agent loop works end to end.

## Must Have

### 1. Single Live Thread

- one live thread exists
- a user message appears in that thread immediately
- agent replies return to the same thread
- page refresh preserves the full event history

### 2. `@agent` Routing

- `@codex`, `@claude`, `@hermes`, `@openclaw` are recognized as routing targets
- `@all` broadcasts to all ready agents
- agent replies can target another agent
- targets are visible in the UI as recipient chips

### 3. Tool Event Visibility

- each invocation writes a `tool.call`
- each completion writes a `tool.result`
- tool results are rendered separately from normal chat
- failures are visibly distinct from success

### 4. System State Visibility

- the console shows basic agent runtime state
- `ready`, `busy`, and `offline` are distinguishable
- system notices such as no-ready-agent or agent error are visible

### 5. Full Replay

- the UI shows:
  - user input
  - agent replies
  - tool events
  - system notices
  - recipient routing
- ordering remains explainable after refresh

### 6. Persistent Trail

- the live thread writes to `.peerforge/threads/main/events.jsonl`
- board state remains readable from `.peerforge/board.json`
- agent state remains readable from `.peerforge/runtime/heartbeats/*.json`

## Allowed To Defer

- multiple live rooms
- advanced board editing from the UI
- websocket streaming
- rich text editor features
- GitHub issue and PR actions inside the UI
- analytics and audit dashboards

## Failure Conditions

Phase 1 is not accepted if any of these happen:

- `@agent` only highlights in the UI but does not affect routing
- tool calls are hidden inside plain chat text
- event history is lost on refresh
- agent replies are written out of order in an unexplainable way
- UI state contradicts persisted board or heartbeat state
