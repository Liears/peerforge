# peerforge Agent Playbook

This playbook is for `codex`, `hermes`, `openclaw`, and `claude`.

The goal is to keep collaboration practical:

- use the repo as the shared control plane
- keep work visible in the board and in Git
- make decisions in the bus, then execute them in branches and PRs
- write down reusable lessons once, instead of re-explaining them in chat

For the formal branch, issue, PR, and skill-sharing rules, see [../CONTRIBUTING.md](/mnt/d/Work/01-code/muti_team/CONTRIBUTING.md).
For the current project goal and milestones, see [../docs/PROJECT_CHARTER.md](/mnt/d/Work/01-code/muti_team/docs/PROJECT_CHARTER.md).

## Repo Rules

- Treat `peerforge` as a coordination system for equal peers, not a boss/worker tree.
- Keep `.peerforge/` as the shared runtime root.
- Use the task board for concrete work items.
- Keep transcripts attached to task execution whenever the bus runs work.
- Do not overwrite someone else’s branch or local changes.
- Do not change code when the task is documentation/process-only.

## Common Commands

Use these commands as the default workflow:

```bash
python3 peerforge/bus.py check --config .peerforge/config.json
python3 peerforge/bus.py ready --config .peerforge/config.json
python3 peerforge/bus.py task-list --root .peerforge
python3 peerforge/bus.py task-next --root .peerforge
python3 peerforge/bus.py task-run-next --root .peerforge --config .peerforge/config.json --agents codex,hermes --ready-only --bootstrap
```

Useful supporting commands:

```bash
python3 peerforge/bus.py bootstrap --config .peerforge/config.json --mode copy
python3 peerforge/bus.py run-ready --config .peerforge/config.json --bootstrap --task "..." --rounds 2
python3 peerforge/bus.py task-add --root .peerforge --title "..." --description "..."
python3 peerforge/bus.py task-update <task-id> --root .peerforge --status in_review
```

## When To Open A Branch

Open a branch when the change:

- touches code
- spans more than one commit
- needs review or verification
- is likely to conflict with concurrent work
- should be attached to an Issue and PR

Branch names should follow:

- `feat/<issue-id>-<slug>`
- `fix/<issue-id>-<slug>`
- `docs/<issue-id>-<slug>`
- `chore/<issue-id>-<slug>`
- `refactor/<issue-id>-<slug>`
- `spike/<issue-id>-<slug>`

If the work is only a quick doc tweak or a board note, keep it on the current branch if that is safer and cleaner.

## When To Update The Board

Update `.peerforge/board.json` when:

- a task is accepted
- a task is split into smaller tasks
- a task changes owner or status
- a task has a transcript that should be recorded
- a task is done, blocked, or needs review

Prefer board updates at these moments:

- before dispatching a task through `task-run-next`
- immediately after a transcript is produced
- when a reviewer requests a status change

Do not run multiple board mutation commands in parallel.

## Issue Flow

Create or update an Issue when:

- the task is larger than one small commit
- multiple agents need a shared reference point
- review or prioritization matters
- the change may continue across sessions

Issue titles should be short and typed:

- `feat: add heartbeat registry`
- `fix: stabilize openclaw readiness`
- `docs: refine agent playbook`
- `chore: tighten bootstrap defaults`

Issue bodies should include:

- goal
- why it matters
- acceptance criteria
- owner or suggested agent
- linked board task, if any

## PR Flow

Open a PR after the branch has a clear, reviewable scope.

Each PR should answer:

- what changed
- why it changed
- how it was verified
- what remains risky or incomplete

Keep PRs small. Prefer one branch per task, one task per PR.

Use the PR template and link the related Issue.

## Collaboration Pattern

Use this sequence for normal work:

1. Confirm the goal in the bus.
2. Decide whether the task needs a board entry, an Issue, or both.
3. Open a branch if the work is more than a small doc-only edit.
4. Implement the change.
5. Update the board with status and transcript.
6. Open or update the PR.
7. Capture any reusable lesson in the right doc.

## Agent-Specific Notes

### codex

- Best suited for implementation and command wiring.
- Use it for code changes, small refactors, and repo edits.

### hermes

- Best suited for review, edge cases, and test strategy.
- Use it to sanity-check behavior and failure modes.

### openclaw

- Best suited for orchestration and runtime state handling.
- Use it for task routing, readiness, and registry-related work.

### claude

- Best suited for design review, documentation, and edge-case reasoning when repo-local execution is healthy.
- Use it when you want a second opinion on structure or wording.

## Knowledge Sharing

If a peer finds something reusable, write it down in one of these places:

- `CONTRIBUTING.md` for workflow rules
- `docs/PROJECT_CHARTER.md` for goals and milestones
- `docs/AGENT_PLAYBOOK.md` for operating instructions
- `README.md` or `README.zh-CN.md` for user-facing guidance
- `peerforge/README.md` for bus-specific details

Good reusable notes are:

- a command that makes readiness stable
- a timeout value that avoids hangs
- a branch or PR pattern that reduces confusion
- a board update rule that prevents collisions

If a lesson cannot be reused, keep it out of the permanent docs.
