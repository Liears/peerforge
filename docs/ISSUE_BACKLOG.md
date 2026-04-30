# peerforge Issue Backlog

This backlog reflects the current post-discussion plan from `codex`, `hermes`, and `openclaw`.

## Planning Rules

- Use branch names in the form `feat/<issue-id>-<slug>`, `fix/<issue-id>-<slug>`, or `docs/<issue-id>-<slug>`.
- Keep one branch per issue.
- Define success as a local command that can be run and verified without manual state editing.
- Prefer the smallest issue that unblocks the next dependency.

## P0: Scheduler Safety and Readiness

These issues should land before broader workflow automation.

### 1. feat: serialize board mutations

- Suggested branch:
  - `feat/<issue-id>-board-file-locking`
- Suggested owner:
  - `hermes`
- Depends on:
  - none
- Scope:
  - add a board write lock
  - serialize `task-add`, `task-update`, `task-run-next`, and any claim/reclaim path
- Minimum delivery:
  - concurrent writers no longer corrupt `board.json`
  - lock acquisition is scoped to one mutation at a time
  - a simple smoke command can prove the lock is active

### 2. feat: add atomic task claim

- Suggested branch:
  - `feat/<issue-id>-atomic-task-claim`
- Suggested owner:
  - `codex`
- Depends on:
  - `serialize board mutations`
- Scope:
  - add `claimed_by`
  - add `claimed_at`
  - add `lease_expires_at`
  - claim the task before dispatch starts
- Minimum delivery:
  - a claimed task is visible in `board.json`
  - a second runner cannot claim the same task while the lease is active
  - `task-run-next` fails fast or skips cleanly when no claim is available

### 3. feat: add stale-lease reclaim

- Suggested branch:
  - `feat/<issue-id>-stale-lease-reclaim`
- Suggested owner:
  - `codex`
- Depends on:
  - `add atomic task claim`
- Scope:
  - requeue expired claims
  - increment `attempts`
  - record why the claim was reclaimed
- Minimum delivery:
  - an expired claim can be recovered without manual board edits
  - reclaim outcome is visible in task state or transcript

### 4. feat: add heartbeat registry

- Suggested branch:
  - `feat/<issue-id>-heartbeat-registry`
- Suggested owner:
  - `openclaw`
- Depends on:
  - `serialize board mutations`
- Scope:
  - define `ready|busy|offline`
  - store heartbeat state under `.peerforge/`
  - write/update heartbeat status around dispatch boundaries
- Minimum delivery:
  - each agent has a local heartbeat record
  - heartbeat state is readable by the dispatcher
  - runtime state stays inside `.peerforge/`

### 5. fix: stabilize readiness selection

- Suggested branch:
  - `fix/<issue-id>-readiness-selection`
- Suggested owner:
  - `hermes`
- Depends on:
  - `add heartbeat registry`
- Scope:
  - combine probe output with heartbeat state
  - reduce probe flakiness and false positives
  - tighten `--ready-only` dispatch behavior
- Minimum delivery:
  - `ready` returns the same set that dispatch will actually use
  - known-bad agents are excluded before task execution

## P1: Git Workflow Automation

### 6. feat: branch-aware task execution

- Suggested branch:
  - `feat/<issue-id>-branch-aware-task-run`
- Suggested owner:
  - `codex`
- Depends on:
  - `add atomic task claim`
  - `stabilize readiness selection`
- Scope:
  - create or announce a task branch before execution
  - attach branch name to the task result
  - keep transcript and branch metadata together
- Minimum delivery:
  - a task run emits a deterministic branch name
  - branch metadata is written back to the task or summary output

### 7. docs: add agent playbook

- Suggested branch:
  - `docs/<issue-id>-agent-playbook`
- Suggested owner:
  - `claude`
- Depends on:
  - none
- Scope:
  - shared prompts
  - CLI quirks
  - verification patterns
  - where to store reusable lessons
- Minimum delivery:
  - one short doc that any agent can use to start work consistently

## Suggested Delivery Order

1. `serialize board mutations`
2. `add atomic task claim`
3. `add stale-lease reclaim`
4. `add heartbeat registry`
5. `stabilize readiness selection`
6. `branch-aware task execution`
7. `agent playbook`
