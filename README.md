# peerforge

`peerforge` is a local multi-agent coordination project for running equal-peer CLI agents against shared engineering tasks.

中文说明见 [README.zh-CN.md](/mnt/d/Work/01-code/muti_team/README.zh-CN.md)。

Current focus:

- repo-local runtime isolation for `codex`, `claude`, `hermes`, and `openclaw`
- a shared message bus with persisted transcripts
- PM-style task board workflows
- readiness checks and ready-only execution

Core module:

- [peerforge/README.md](/mnt/d/Work/01-code/muti_team/peerforge/README.md)

Quick start:

```bash
cp examples/config.example.json .peerforge/config.json
python3 peerforge/bus.py bootstrap --config .peerforge/config.json --mode copy
python3 peerforge/bus.py init --root .peerforge
python3 peerforge/bus.py run-ready --config .peerforge/config.json --agents codex,hermes --bootstrap --task "Discuss the next implementation step." --rounds 2
```
