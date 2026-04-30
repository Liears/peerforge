# peerforge Issue Seeds

Use these seeds to create GitHub Issues directly. They are aligned with `docs/ISSUE_BACKLOG.md`.

Ordering note:

- `feat: serialize board mutations` and `feat: add atomic task claim` are already delivered in the current board state.
- The next issue after `feat: add heartbeat registry` is `fix: stabilize readiness selection`.

## P0

### feat: serialize board mutations

- title: `feat: serialize board mutations`
- goal: Add a board write lock so all task-board mutations are serialized, including read-modify-write paths.
- acceptance criteria:
  - `task-add`, `task-update`, `task-claim-next`, `task-reclaim`, and `task-run-next` all use the same lock path
  - `check` and `ready` remain read-only
  - lock acquisition is explicit in tests
  - concurrent writers do not corrupt `board.json`
  - the lock covers read-modify-write, not just writes
- suggested branch: `feat/<issue-id>-board-file-locking`
- suggested owner: `hermes`

### feat: add atomic task claim

- title: `feat: add atomic task claim`
- goal: Claim a task under the board lock before dispatch starts, and make the claim durable in board state.
- acceptance criteria:
  - task rows include `claimed_by`, `claimed_at`, `lease_expires_at`, and `claim_token`
  - `task-run-next` claims first, then dispatches, then persists transcript results
  - a second runner cannot claim the same task while the lease is active
  - a late retry cannot overwrite a newer claim
  - completion or release clears the claim fields
- suggested branch: `feat/<issue-id>-atomic-task-claim`
- suggested owner: `codex`

### feat: add stale-lease reclaim

- title: `feat: add stale-lease reclaim`
- goal: Reclaim expired task claims without manual board edits.
- acceptance criteria:
  - expired claims are requeued automatically or by command
  - `attempts` is incremented on reclaim
  - reclaim output records the original owner and lease expiry
  - reclaim outcome is visible in task state or transcript
- suggested branch: `feat/<issue-id>-stale-lease-reclaim`
- suggested owner: `codex`

### feat: add heartbeat registry

- title: `feat: add heartbeat registry`
- goal: Store agent runtime health as local heartbeat state and make it visible to dispatch.
- acceptance criteria:
  - heartbeat states support `ready`, `busy`, and `offline`
  - heartbeat files live under `.peerforge/runtime/heartbeats/`
  - heartbeat records include `updated_at`, `expires_at`, `task_id`, and `claim_token`
  - readiness selection consumes the same status model that dispatch uses
  - heartbeat expiry does not auto-reclaim a task lease
- suggested branch: `feat/<issue-id>-heartbeat-registry`
- suggested owner: `openclaw`

### fix: stabilize readiness selection

- title: `fix: stabilize readiness selection`
- goal: Make `ready` and `--ready-only` dispatch agree on the actual usable agent set.
- acceptance criteria:
  - probe output and heartbeat state are combined in selection
  - false positives and probe flakiness are reduced
  - `ready` returns the same set that dispatch will use
  - busy or expired agents are excluded before claim attempts
- suggested branch: `fix/<issue-id>-readiness-selection`
- suggested owner: `hermes`

## P1

### feat: branch-aware task execution

- title: `feat: branch-aware task execution`
- goal: Create or announce a task branch before execution and keep branch metadata tied to the transcript.
- acceptance criteria:
  - a task run emits a deterministic branch name
  - branch metadata is written back to the task or summary output
  - transcript and branch metadata stay together
- suggested branch: `feat/<issue-id>-branch-aware-task-run`
- suggested owner: `codex`

### docs: add agent playbook

- title: `docs: add agent playbook`
- goal: Capture shared prompts, CLI quirks, and verification patterns in one short reusable doc.
- acceptance criteria:
  - the doc explains how to start work consistently
  - it records reusable prompts or command patterns
  - it records where to store lessons learned
- suggested branch: `docs/<issue-id>-agent-playbook`
- suggested owner: `claude`
