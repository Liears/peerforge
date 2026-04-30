# peerforge

`peerforge` 是一个本地多 agent 协作项目，用来让多个平等的 CLI agent 围绕同一工程任务协同工作。

当前重点：

- 为 `codex`、`claude`、`hermes`、`openclaw` 提供仓库内隔离运行态
- 提供共享消息总线与 transcript 落盘
- 支持 PM 风格任务板流程
- 支持健康检查与仅用可用 agent 执行

核心模块：

- [peerforge/README.md](/mnt/d/Work/01-code/muti_team/peerforge/README.md)

快速开始：

```bash
cp examples/config.example.json .peerforge/config.json
python3 peerforge/bus.py bootstrap --config .peerforge/config.json --mode copy
python3 peerforge/bus.py init --root .peerforge
python3 peerforge/bus.py run-ready --config .peerforge/config.json --agents codex,hermes --bootstrap --task "讨论下一步实现任务。" --rounds 2
```
