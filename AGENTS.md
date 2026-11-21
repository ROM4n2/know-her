# Project Guidelines

## 共享工作记忆 (WORKMEMORY)

- `AGENTS.md` 只记录稳定规则与事实；问题、决策、踩坑和交接优先写入 WORKMEMORY。
- 非只读或涉及状态变更时，按 `WORKMEMORY/INDEX.md` 读 `PROJECT_OVERVIEW.md` 与 `work.log` 最新 ≤15 条事件；发现未闭合 WORK_START 先询问用户。
- 工作中：决策/踩坑/交接 MUST 以 ≤4KB 事件追加 WORKMEMORY/work.log（schema 见 WORKMEMORY/PROTOCOL.md）。
- 稳定经验再通过 `search_vault` / `dfs-save` 沉淀到知识库。
- 语义知识检索：调用 `search_vault` MCP；成熟知识沉淀走 /dfs-save。