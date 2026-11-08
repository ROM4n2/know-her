# WORKMEMORY INDEX — know-her

## Configuration

- HOT_RETENTION_EVENTS: 50    # work.log 热层保留事件数；轮转阈值 = 本值 × 1.5

## 文件清单

| 文件 | 职责 |
| --- | --- |
| `PROTOCOL.md` | 协议本体（读一次即可，之后按本索引工作） |
| `PROJECT_OVERVIEW.md` | 60 秒项目 primer（新 agent 第二读） |
| `work.log` | HOT 事件流（append-only，第三读） |
| `archive/` | WARM 层（按月 `work-YYYY-MM.log` 分片，只按下方索引按需加载） |
| `cold/` | COLD 层（按月 digest，仅显式要求时生成） |
| `handoff_*.md` | 跨 agent 交接包 |

## 主题索引（archive/digest 内容导航）

| 主题 | 来源文件 |
| --- | --- |
| 2026-09 的超长事件与 ISO 时间头事件 | `archive/work-2026-09.log`（2026-11-03 轮转） |
| 2026-10 的 ISO 时间头事件 | `archive/work-2026-10.log`（2026-11-03 轮转） |
| 其余早期决策与排障记录 | `work.log`（HOT；保留 21 事件） |

## Active handoffs

（无）

## 蒸馏登记（WORKMEMORY → vault）

| 日期 | 主题 | vault 归属 |
| --- | --- | --- |

（初始为空；`/vault-save` 沉淀后回写此表，vault 侧引用用 `vault://` 前缀）
