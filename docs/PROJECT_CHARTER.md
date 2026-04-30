# peerforge Project Charter

## Goal

`peerforge` exists to coordinate equal-peer CLI agents on real engineering work.

The target system should let agents:

- discuss and refine tasks together
- read and update a shared task board
- report readiness and availability
- safely claim work without collisions
- execute work from the board with reproducible transcripts
- maintain the Git repository through branches, reviews, and pull requests
- share skills, patterns, and operational lessons back into the repo

For the concrete Git workflow, issue format, and PR checklist, see [../CONTRIBUTING.md](/mnt/d/Work/01-code/muti_team/CONTRIBUTING.md).

## Near-Term Product Direction

The current phase is to turn the repository from a coordination prototype into a usable engineering control plane.

### Milestone 1

Reliable task dispatch from the board.

Deliverables:

- `task-run-next` command
- ready-only dispatch
- repo-local runtime bootstrap
- stable transcript writeback to board tasks

Status:

- largely complete

### Milestone 2

Safe scheduling and agent state.

Deliverables:

- board file locking for every board write path
- atomic task claim semantics with single-owner outcomes
- minimal heartbeat registry with `ready|busy|offline`
- clearer no-op and conflict outcomes for `task-run-next`
- improved OpenClaw readiness behavior

Implementation order:

1. serialize board writes with file locking
2. add claim and lease fields to tasks
3. add heartbeat registry and readiness integration
4. tighten stale-lease and conflict outcomes

Behavior that must be locked before coding:

- `task-run-next` remains an additive workflow entry, not a replacement for `run-task`
- `task-add`, `task-update`, and `task-run-next` are the only board writers
- `check` and `ready` stay read-only
- claim conflicts must return a deterministic no-op or conflict outcome
- heartbeat state stays under `.peerforge/` and separate from the board

### Milestone 3

Repository-native collaboration workflow.

Deliverables:

- lightweight issue model
- branch naming convention
- PR checklist
- skill and lessons log

## Agent Roles

### codex

- implementation-heavy changes
- command wiring
- CLI behavior
- repository refactors

### hermes

- verification logic
- test strategy
- task decomposition feedback
- workflow review

### openclaw

- runtime integration behavior
- readiness and orchestration edge cases
- future registry/heartbeat shape

### claude

- optional context/review peer when repo-local execution becomes stable

## Working Agreement

- Board updates are single-writer operations.
- Every feature should map to a concrete board task.
- Every dispatched task should produce a transcript.
- Prefer small, isolated branches for implementation work.
- Merge only after the branch has a clear scope and a concise close-out summary.

## Skill Sharing

Agents should record reusable lessons in repository docs instead of keeping them implicit.

Recommended places:

- `docs/PROJECT_CHARTER.md` for operating agreements
- `CONTRIBUTING.md` for branch, issue, and PR rules
- `README.md` or `README.zh-CN.md` for user-facing lessons
- `peerforge/README.md` for bus and runtime changes

## Immediate Queue

1. add atomic task claim and lease fields to board tasks
2. serialize board mutations with file locking
3. add heartbeat-based `ready|busy|offline` registry for agents
4. stabilize OpenClaw readiness into regular `ready` output
5. keep the lightweight issue/branch/PR workflow current in repo docs
