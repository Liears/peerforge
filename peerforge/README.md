# peerforge Bus

This directory contains the core peer-to-peer coordination module for `peerforge`.

It currently targets four CLI agents:

- `codex`
- `claude`
- `hermes`
- `openclaw`

The design goal is equality at the protocol layer:

- every agent is a peer
- every agent can address another agent directly
- every agent can broadcast to the whole group
- every agent can propose, question, criticize, hand off, or finalize work

A lightweight orchestrator still exists, but only to:

- invoke CLI tools
- persist message history
- route messages to recipients
- enforce round limits and timeouts
- survive partial failures

It is not the "boss" in the conversation. It is a transport and safety layer.

For contribution workflow and Git conventions, see [../CONTRIBUTING.md](/mnt/d/Work/01-code/muti_team/CONTRIBUTING.md).
For the project goal and current milestone queue, see [../docs/PROJECT_CHARTER.md](/mnt/d/Work/01-code/muti_team/docs/PROJECT_CHARTER.md).
For the concrete P0/P1 issue breakdown, see [../docs/ISSUE_BACKLOG.md](/mnt/d/Work/01-code/muti_team/docs/ISSUE_BACKLOG.md).

## Files

- `bus.py`: orchestrator and built-in adapters
- `dashboard.py`: local HTTP server for the transcript and board dashboard
- `../examples/config.example.json`: sample config for four peers
- `../examples/config.mock.json`: self-contained smoke-test config
- `../examples/board.example.json`: example PM task board
- `mock_peer.py`: deterministic mock peer for protocol validation

At the project level, you can still use it as a PM layer:

- keep a task board in `.peerforge/board.json`
- run selected tasks through the bus
- attach each transcript back to the task entry

## Protocol

Each agent is prompted to return JSON only:

```json
{
  "status": "continue",
  "summary": "short state update",
  "messages": [
    {
      "to": ["claude"],
      "kind": "question",
      "body": "Can you verify the implementation detail?"
    },
    {
      "to": ["*"],
      "kind": "proposal",
      "body": "I suggest we split the task into adapter and protocol work."
    }
  ]
}
```

Rules:

- `to` may be `["*"]` for broadcast
- `kind` is free-form but should be concise
- `body` is the actual content
- `status` should be `continue` or `done`

## Quick Start

1. Copy the example config.
2. Bootstrap repo-local runtime state from your existing global agent installs.
3. Adjust any agent command details that differ on your machine.
4. Optionally initialize the local task board.
5. Run a short round-table.

```bash
cp examples/config.example.json .peerforge/config.json
python3 peerforge/bus.py bootstrap --config .peerforge/config.json --mode copy
python3 peerforge/bus.py init --root .peerforge
python3 peerforge/bus.py task-run-next --root .peerforge --config .peerforge/config.json --agents codex,hermes --ready-only --bootstrap
```

Smoke test without real providers:

```bash
python3 peerforge/bus.py run --config examples/config.mock.json --task "Debate task split." --rounds 2
```

If you discover a reusable command, timeout tweak, or workflow pattern, record it in `CONTRIBUTING.md` or the relevant README instead of keeping it in chat.

## PM Workflow

Create and inspect tasks:

```bash
python3 peerforge/bus.py task-add --root .peerforge --title "Implement adapter retry policy" --description "Decide retry conditions and code the runner changes."
python3 peerforge/bus.py task-list --root .peerforge
python3 peerforge/bus.py task-next --root .peerforge
python3 peerforge/bus.py task-run-next --root .peerforge --config .peerforge/config.json --agents codex,hermes --ready-only --bootstrap
```

Run one task through the agent group:

```bash
python3 peerforge/bus.py run-task wire-real-clis --root .peerforge --config .peerforge/config.json --rounds 2
```

Recommended one-shot PM flow:

```bash
python3 peerforge/bus.py task-run-next --root .peerforge --config .peerforge/config.json --agents codex,hermes --ready-only --bootstrap
```

Limit a run to the peers that are currently healthy:

```bash
python3 peerforge/bus.py run --config .peerforge/config.json --ready-only --task "Implement and verify a small fix." --rounds 2
python3 peerforge/bus.py run-ready --config .peerforge/config.json --bootstrap --task "Implement and verify a small fix." --rounds 2
```

Each task can capture:

- `last_run_at`
- `last_transcript`
- `status`

Current constraint:

- treat `.peerforge/board.json` updates as single-writer operations; do not run multiple `task-add` or `task-update` commands in parallel

Check which peers are actually ready before dispatch:

```bash
python3 peerforge/bus.py check --config .peerforge/config.json
python3 peerforge/bus.py ready --config .peerforge/config.json
```

Bootstrap repo-local runtime state from your existing user-level installs:

```bash
python3 peerforge/bus.py bootstrap --config .peerforge/config.json --mode copy
```

Current bootstrap behavior:

- `codex`: copies `auth.json` and `config.toml`
- `claude`: copies and sanitizes `settings.json` to remove inherited `ANTHROPIC_*` proxy overrides
- `hermes`: copies `config.yaml` and `.env`
- `openclaw`: copies `openclaw.json`, `agents/`, `identity/`, and `devices/`, then rewrites workspace to the current project

## Current Environment Notes

In the current workspace, I verified:

- `codex` CLI exists
- `claude` CLI exists
- `hermes` CLI exists
- `openclaw` CLI exists

I also observed current machine-level limitations:

- `hermes` fails in this sandbox if it uses the default `/root/.hermes` tree
- `openclaw` requires a configured agent id or session binding before `openclaw agent` can run a turn
- `codex` is safest when launched with a repo-local `HOME`
- `claude` non-interactive calls did not return quickly here, so timeout handling matters

The sample config redirects runtime state into `.peerforge/runtime/`:

- `codex`: `HOME` plus XDG dirs
- `claude`: `CLAUDE_CONFIG_DIR`, `CLAUDE_CODE_DEBUG_LOGS_DIR`, and tmp dirs
- `hermes`: `HOME`
- `openclaw`: `OPENCLAW_STATE_DIR` and `OPENCLAW_CONFIG_PATH`

In the current machine state, bootstrap + smoke tests confirmed:

- `codex` can return protocol JSON from repo-local state
- `hermes` can return protocol JSON from repo-local state
- `openclaw` can return protocol JSON from repo-local state
- `claude` is still not usable in repo-local mode on this machine; bootstrap now makes it fail fast instead of hanging on inherited proxy settings

The bus is written to tolerate those failures and keep the other peers talking.

## Dashboard

Start the local dashboard:

```bash
python3 peerforge/dashboard.py --root .peerforge --port 8765
```

The dashboard reads:

- `.peerforge/board.json`
- `.peerforge/sessions/*/summary.json`
- `.peerforge/sessions/*/transcript.jsonl`

It provides:

- a board task summary strip
- a session list
- a group-chat transcript view with sender, recipients, round number, and message kind
- automatic refresh for ongoing local runs
