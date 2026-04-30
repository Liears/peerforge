# peerforge

`peerforge` is a local multi-agent coordination project for running equal-peer CLI agents against shared engineering tasks.

Current focus:

- repo-local runtime isolation for `codex`, `claude`, `hermes`, and `openclaw`
- a shared message bus with persisted transcripts
- PM-style task board workflows
- readiness checks and ready-only execution

Core module:

- [agents-bus/README.md](/mnt/d/Work/01-code/muti_team/agents-bus/README.md)

Quick start:

```bash
cp agents-bus/config.example.json agents-bus/config.json
python3 agents-bus/bus.py bootstrap --config agents-bus/config.json --mode copy
python3 agents-bus/bus.py init --root agents-bus
python3 agents-bus/bus.py run-ready --config agents-bus/config.json --agents codex,hermes --bootstrap --task "Discuss the next implementation step." --rounds 2
```
