# peerforge

`peerforge` is a local multi-agent coordination project for running equal-peer CLI agents against shared engineering tasks.

中文说明见 [README.zh-CN.md](/mnt/d/Work/01-code/muti_team/README.zh-CN.md)。

Current focus:

- repo-local runtime isolation for `codex`, `claude`, `hermes`, and `openclaw`
- a shared message bus with persisted transcripts
- PM-style task board workflows
- readiness checks and ready-only execution
- `.peerforge/` as the primary local runtime root
- lightweight Git workflow for branches, issues, PRs, and shared agent notes

Core module:

- [peerforge/README.md](/mnt/d/Work/01-code/muti_team/peerforge/README.md)
- [docs/PROJECT_CHARTER.md](/mnt/d/Work/01-code/muti_team/docs/PROJECT_CHARTER.md)
- [docs/VERIFICATION.md](/mnt/d/Work/01-code/muti_team/docs/VERIFICATION.md)
- [docs/ISSUE_BACKLOG.md](/mnt/d/Work/01-code/muti_team/docs/ISSUE_BACKLOG.md)
- [CONTRIBUTING.md](/mnt/d/Work/01-code/muti_team/CONTRIBUTING.md)

Use `CONTRIBUTING.md` for branch, issue, PR, and skill-sharing rules. Use `docs/PROJECT_CHARTER.md` for the current project goal and near-term roadmap.

Quick start:

```bash
cp examples/config.example.json .peerforge/config.json
python3 peerforge/bus.py bootstrap --config .peerforge/config.json --mode copy
python3 peerforge/bus.py init --root .peerforge
python3 peerforge/bus.py task-run-next --root .peerforge --config .peerforge/config.json --agents codex,hermes --ready-only --bootstrap
```

`task-run-next` reads the next pending task from `.peerforge/board.json`, selects the requested ready agents, runs the discussion, and writes the transcript back to the task entry.
