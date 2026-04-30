# Contributing to peerforge

`peerforge` is a small local coordination system for equal peers: `codex`, `claude`, `hermes`, and `openclaw`.

The goal is practical collaboration, not ceremony:

- keep the repository easy to run locally
- use small, reviewable branches
- keep work items tied to Issues and PRs
- share useful prompts, scripts, and fixes back into the repo

## Project Goal

The current project goal is to make the repo itself the coordination surface:

- one shared runtime root: `.peerforge/`
- one shared task board: `.peerforge/board.json`
- one shared transcript trail per task
- one lightweight Git flow for branch work, review, and merge

When the team discusses work, prioritize:

- repo reliability
- agent readiness and routing
- task board and transcript ergonomics
- GitHub workflow clarity

## Verification Contract

Before changing task dispatch or board state, lock these behaviors in docs and tests:

- `task-run-next` stays the primary one-shot PM flow for "pick next task and dispatch it"
- `task-add`, `task-update`, and `task-run-next` are the only board mutators
- `check` and `ready` remain read-only probes
- board claims must be single-owner, with no duplicate claim outcome under contention
- `.peerforge/` remains the default runtime root for sessions, runtime state, and the board
- heartbeat state is runtime data, not board data

Recommended test coverage for workflow changes:

- CLI compatibility smoke test for existing commands
- concurrent claim test for `task-run-next`
- file-lock test for board writes
- heartbeat registry test for `ready|busy|offline` transitions
- transcript writeback test for task entries

## Agent Roles

Keep roles flexible. Use the best available peer for the job.

- `codex`: implementation, wiring, and repo changes
- `hermes`: review, refactors, and stability checks
- `openclaw`: workflow automation, orchestration, and state handling
- `claude`: design review, edge cases, and documentation when it is available

No agent should be treated as the permanent owner of a subsystem. Ownership is by task, not by identity.

## Branch Naming

Use short, searchable branch names:

- `feat/<issue-id>-<slug>`
- `fix/<issue-id>-<slug>`
- `docs/<issue-id>-<slug>`
- `chore/<issue-id>-<slug>`
- `refactor/<issue-id>-<slug>`
- `spike/<issue-id>-<slug>`

Examples:

- `feat/12-task-run-next`
- `fix/19-openclaw-ready-check`
- `docs/21-chinese-readme`

Rules:

- one branch per issue or tightly related set of changes
- keep branches short-lived
- avoid mixing docs-only and code-heavy changes unless they are obviously coupled

## Issue Naming

Use a simple prefix format in titles:

- `feat: add task-run-next command`
- `fix: prevent duplicate task claims`
- `docs: add collaboration workflow`
- `chore: tighten bootstrap defaults`

Recommended issue body:

- goal
- why it matters
- acceptance criteria
- affected files or module
- suggested agent owner

If the issue is exploratory, prefix it with `spike:` and keep the scope intentionally small.

## PR Structure

Keep PRs small and explicit.

Recommended PR title:

- `feat: add task-run-next`
- `fix: stabilize openclaw ready check`

Recommended PR body:

- what changed
- why it changed
- how it was verified
- follow-ups, if any
- linked issue

Suggested PR checklist:

- [ ] change is scoped to one task
- [ ] branch name matches the issue
- [ ] behavior was verified locally
- [ ] docs or examples were updated if needed
- [ ] transcript or issue references are attached when relevant

Review rule:

- one agent implements
- one agent reviews
- a third agent can sanity-check docs, edge cases, or ergonomics

## Coordination Flow

Use this loop for normal work:

1. Agree on the task goal in one short discussion.
2. Create or update the Issue.
3. Pick one branch and one owner.
4. Implement the change.
5. Review through a PR.
6. Merge and record any reusable lesson.

For task-board driven work, prefer:

- discuss in the bus
- create or update the task entry
- create a matching GitHub Issue if the work will span multiple commits or needs review
- open a branch before coding
- attach the transcript or summary to the PR

## Sharing Skills and Experience

When a peer discovers something reusable, capture it quickly:

- a command that unblocks bootstrap
- a CLI flag that improves reliability
- a retry or timeout pattern
- a repo layout or review trick

Store the result in one of these places:

- the PR description
- the matching Issue
- `README.md` or `README.zh-CN.md` if it is user-facing
- `peerforge/README.md` if it affects the bus or workflow

Keep shared knowledge short and actionable. If it cannot be reused, do not promote it to a process rule.
