# peerforge

`peerforge` 是一个本地多 agent 协作项目，用来让多个平等的 CLI agent 围绕同一工程任务协同工作。

当前重点：

- 为 `codex`、`claude`、`hermes`、`openclaw` 提供仓库内隔离运行态
- 提供共享消息总线与 transcript 落盘
- 支持 PM 风格任务板流程
- 支持健康检查与仅用可用 agent 执行
- 使用 `.peerforge/` 作为默认本地运行态根目录
- 提供轻量 Git 工作流，覆盖分支、Issue、PR 和经验共享

核心模块：

- [peerforge/README.md](/mnt/d/Work/01-code/muti_team/peerforge/README.md)
- [docs/PROJECT_CHARTER.md](/mnt/d/Work/01-code/muti_team/docs/PROJECT_CHARTER.md)
- [CONTRIBUTING.md](/mnt/d/Work/01-code/muti_team/CONTRIBUTING.md)

`CONTRIBUTING.md` 用于分支、Issue、PR 和经验共享规则。`docs/PROJECT_CHARTER.md` 用于说明当前项目目标和近期路线图。

快速开始：

```bash
cp examples/config.example.json .peerforge/config.json
python3 peerforge/bus.py bootstrap --config .peerforge/config.json --mode copy
python3 peerforge/bus.py init --root .peerforge
python3 peerforge/bus.py task-run-next --root .peerforge --config .peerforge/config.json --agents codex,hermes --ready-only --bootstrap
```

`task-run-next` 会从 `.peerforge/board.json` 中取出下一个待办任务，选择当前可用的 agent 执行讨论，并把 transcript 回写到任务项里。
