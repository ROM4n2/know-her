# 架构设计规格书：日更可持续性 —— 每日新鲜组合与增量候选供给管道

- **文档状态**：**APPROVED**（用户 2026-09-27 批准，可进入实施计划阶段）
- **日期**：2026-09-27
- **架构方案**：方案 A（每日新鲜组合，M1）+ 方案 B（增量候选供给管道，M2）；方案 C（内容形态工厂）显式留位、本里程碑不实现
- **设计基线**：**ADR-0002**（用户 2026-09-27 拍板）。本规格书以「每日性健康科普与愉悦探索分享站 + 策展导读为主 + 零侵权 + 轻量 Schema」为准；`IDEA.md` 中「四段医学审核 / 不追求自动发布」的旧口径在本里程碑**不适用**，不得作为设计依据。
- **「新鲜」的可判定定义**（用户拍板 ③）：**每周 2~3 篇新长文 + 每天首页存在可判定的变化**。

---

## 1. Problem Statement & User Value（问题陈述与用户价值）

### 1.1 四条实测约束（本轮探测数据，非推测）

| # | 事实 | 实测证据 |
|---|---|---|
| C1 | **现有供给池 48 天后永久断粮** | 两信源关键词初筛后未收录候选：WHO 5 篇 + 默沙东 43 篇；`curate_harvester.py` 仅抓**入口页单页**（WHO 入口 213 条链接只筛出 5 条），无 sitemap / 分页 / 日期增量 → 池子不增长 |
| C2 | **人工提炼是硬天花板** | 每篇需人写 3~5 条提炼要点（本次 PR #2 实测 15~30 分钟量级）。日更 = 365 次人工会话/年，而 bus factor = 1 |
| C3 | **日更闭环已静默漂移** | 文章 **26** 篇 vs 速测题 **25** 道：新合并的 `body-female-genital-mutilation` **无速测题**；无任何门禁拦截此类漂移 |
| C4 | **首页轮换周期被内容总量锁死** | `getTodayIndex()` = `(day-1) % totalCount`，文章池 N=26 → **第 27 天起读者看到重复内容**，与 README「每日精选」承诺错位 |

### 1.2 目标用户与场景（Product-UX 镜）

- **主 Persona**：中文女性读者（18–35 岁），每日在通勤或睡前打开首页约 30 秒——看「今日精选」、做「30 秒速测」打卡，偶尔深读一篇长文。
- **次 Persona**：海外华人读者（可达 github.io，搜索质量缺口最大，ADR-0002 已列为次级情境）。
- **维护者 Persona**：单人维护者，每周可投入约 90 分钟批量内容作业，**不可能**每天投入提炼会话。

### 1.3 Cost of Doing Nothing（不做的代价）

1. **第 27 天起「每日」承诺失效**：读者看到重复内容 → 「每日精选」退化为静态清单，信任折旧；
2. **48 天后内容停止增长**：零 SEO 积累，项目的增长路径（靠长尾搜索被发现）被自身供给能力掐断；
3. **漂移持续累积**：每新增一篇文章就多一次「无速测题」的日更退化（C3），且无人察觉；
4. **维护者预期失控**：以「每天一篇」为 KPI 会逼出模板填充式合成正文——这正是项目自身调研已定性的**信任事故**（P0 止血项）。

---

## 2. User Journey & Core Flow（用户旅程与核心交互）

### 2.1 读者每日旅程（Happy Path ≤ 3 步）

```
打开首页 → 今日精选 + 每日 30 秒速测 + 每日一词（当日组合唯一） → 打卡 / 深读 / 跳转词典
```

1. **Step 1**：进入首页，`DailyCard` 展示今日精选文章与当日速测题 → 立即获得「今天有新东西」的信号；
2. **Step 2**：新增 `DailyTerm` 展示「每日一词」（28 词条池轮换）→ 30 秒内获得一个可带走的医学常识；
3. **Step 3**：完成速测获得即时解析与连续打卡天数（`localStorage` 本地存储，零隐私外传）→ 形成次日回访动机。

> **新鲜感的判定**：当日三元组 `(文章索引, 速测索引, 词条索引)` 构成「当日指纹」，其不重复周期 = `lcm(26, 25, 28) = 9100 天 ≈ 24.9 年`（数学证明见 §3.1.3）。即：**无需新增任何人工成本，首页内容在可预见年限内不会重复**。

### 2.2 维护者每周旅程（Happy Path ≤ 3 步，M2 生效后）

```
工作日晨间看候选池 → 挑 2~3 篇生成骨架 → 补要点与速测题 → 提 PR（CI 门禁自动把关）
```

1. **Step 1**：`pnpm curate:pool` 输出候选池清单，**按分类缺口优先排序**（补齐四大分类中当前篇数最少者）；
2. **Step 2**：`pnpm curate:draft <url>` 生成 MDX 骨架，**同时写入速测题占位**到 `src/data/dailyQuiz.ts`；
3. **Step 3**：人工通读原文补 3~5 条要点、补完速测题题干 → 提 PR；`pnpm test` 门禁阻断一切遗漏（缺题、缺许可、缺来源）。

### 2.3 摩擦点与缓解

| 摩擦点 | 缓解设计 |
|---|---|
| 维护者不知「该写哪一篇」 | `curate:pool` 按**分类缺口**排序，直接给出「当前最缺料分类」的前 N 条 |
| 「新鲜」无法验收 | 门禁断言组合指纹唯一性 + 文章↔速测题 1:1，把「新鲜」变成可执行断言 |
| 新文章被轮换埋没 | 「今日上新」规则：`pubDate` 距今 ≤ 7 天的文章优先占据今日精选位 |
| 信源合法性靠自我声明 | 信源 `admission` **fail-closed**：未填 `license` 视为未准入，抓取器直接跳过 |

### 2.4 错误反馈与恢复

- 门禁失败时输出**可执行修复指令**（例：`❌ 文章 X 缺少速测题 → 请在 src/data/dailyQuiz.ts 增加 key 'X'`），而非仅报错码；
- `curate:pool` 在候选池为空时**明确报错并给出下一步**（「所有准入信源候选已耗尽，请执行 `curate:admit <source-id>` 准入新信源」），不静默返回空表。

---

## 3. Architecture & Data Models（架构与数据模型）

### 3.1 方案 A：每日新鲜组合（M1）

#### 3.1.1 组件与边界

| 组件 | 职责 | 接口签名 |
|---|---|---|
| `src/data/rotation.ts`（新建） | 轮换数学的**唯一真值源**：积日、周序号、指纹 | `getDayOfYear(date?): number`、`getWeekIndex(totalWeeks: number, date?): number`、`getTodayIndex(totalCount, date?): number`、`getCombinedFingerprint(date?): string`、`ROTATION_POOLS: {articles:number; quiz:number; glossary:number}` |
| `src/components/DailyCard.astro`（改造） | 今日精选 + 速测 + 今日上新置顶 | Props `{ article, quiz, freshArticle? }` |
| `src/components/DailyTerm.astro`（新建） | 每日一词（词条名 + 释义 + 词典锚点） | Props `{ term: CollectionEntry<'glossary'> }` |
| `src/pages/index.astro`（改造） | 组装三者，计算当日池索引 | 无 |

> **Ladder of Reuse**：不引入任何第三方日期库。`getDayOfYear` 已存在并固定 UTC+8 口径，直接提升为 `rotation.ts` 的导出，`dailyQuiz.ts` 改为 re-export 以保持向后兼容。

#### 3.1.2 数据与持久化

- **无新增持久化**：轮换为纯函数（日期 → 索引），无状态、无 DB、无 `localStorage` 写入（打卡沿用现有 `DailyCard` 的 `safeGetItem/safeSetItem` 容灾实现）。
- **池来源**：`articles`（`getCollection('articles')` 排除 `_` 开头）、`DAILY_QUIZZES`、`glossary`（`getCollection('glossary')`）。

#### 3.1.3 唯一性证明（可验证不变量）

设三池规模为 `a=26, q=25, g=28`，当日指纹 = `(day-1) mod a, (day-1) mod q, (day-1) mod g`。

- 指纹重复 ⟺ `d ≡ 0 (mod a) ∧ d ≡ 0 (mod q) ∧ d ≡ 0 (mod g)`，最小正周期 = `lcm(a,q,g)`；
- `26 = 2×13`，`25 = 5²`，`28 = 2²×7` → `lcm = 2²×5²×7×13 = 9100`（天）；
- 断言 `lcm(pools) ≥ 3650`（≥10 年不重复）由 `scripts/test_daily_loop.py` 强制，**池规模变化时自动重算**。

**推论（护栏）**：若任一池规模缩到使 `lcm < 3650`，门禁失败并提示扩池——把「新鲜度」变成 CI 可守的不变量而非口号。

### 3.2 方案 B：增量候选供给管道（M2）

#### 3.2.1 信源清单 v2（`scripts/sources.json`）

```jsonc
{
  "id": "plannedparenthood",
  "name": "Planned Parenthood 学习中心",
  "base_url": "https://www.plannedparenthood.org",
  "discovery": {
    "mode": "sitemap",                 // "anchor" | "sitemap" | "feed"
    "url": "https://www.plannedparenthood.org/sitemap.xml",
    "link_pattern": "/learn/",         // 正则，仅保留匹配路径
    "max_pages": 3                     // sitemap index 递归深度上限
  },
  "keywords": ["避孕", "性健康", "愉悦", "consent"],
  "category_map": { "避孕": "contraception", "愉悦": "pleasure" },
  "default_category": "body",
  "admission": {
    "status": "probing",               // "admitted" | "probing" | "rejected"
    "license": "",                     // 留空 = 未准入（fail-closed）
    "license_url": "",
    "verified_at": "",
    "verified_by_run": ""              // 准入核验所在 CI run URL
  }
}
```

**三种发现模式的实测依据**（本机出口观测，2026-09-27）：

| 信源 | 出口实测 | 发现模式依据 |
|---|---|---|
| plannedparenthood.org | 200；`/sitemap.xml` **200** | → `sitemap` 模式 |
| guokr.com | 200；`/feed/` **200** | → `feed` 模式 |
| dxy.com | 200；sitemap/feed/rss 皆 404 | → 退回 `anchor` 模式（站点自有栏目页） |
| knowsex.net / res.knowsex.org | 200；三者皆 404 | → 退回 `anchor` 模式 |
| WHO / 默沙东 | 200 | → 沿用现有 `anchor` 模式（向后兼容） |
| cdc.gov / unesco.org (403)、nhc.gov.cn (412) | 出口反自动化 | 准入核验**必须在 CI 出口执行**，本机结果不可信 |

> **兼容性**：`discovery` 字段缺省时按 `{mode:"anchor", url: entry_url, link_pattern: link_pattern}` 处理，**现有两条信源配置不改即可继续工作**（零破坏升级）。

#### 3.2.2 候选池台账 `scripts/.curate-ledger.json` v2

```jsonc
{
  "version": 2,
  "processed_urls": [
    { "url": "https://...", "status": "published", "source_id": "who-fact-sheets",
      "first_seen": "2026-09-24", "last_probed": "2026-09-27", "http_status": 200 }
  ]
}
```

- **状态机**：`pending`（已发现未处理）→ `published` / `rejected`；不变量：同一 `url` 全局唯一，`status` 单向流转（`published` 不回退到 `pending`）；
- **迁移**：`migrate_ledger_v1_to_v2(data)` 为**幂等纯函数**（v1 字符串数组 → v2 对象数组，`status` 默认 `published`，缺失日期填空串），重复调用结果一致；
- 读写入口收敛为 `load_ledger()` / `save_ledger()`，其他模块不得直接读写文件。

#### 3.2.3 新增 CLI（人工批量作业的唯一入口）

| 命令 | 行为 |
|---|---|
| `pnpm curate:pool [--source <id>] [--limit N]` | 输出候选池表格（标题 / 来源 / 推定分类 / 首次发现 / 最近探活），**按分类缺口优先排序**（四分类当前篇数升序，同分类按首次发现升序） |
| `pnpm curate:draft <url>` | 生成 MDX 骨架（复用现有 `compose_mdx_content`）+ **同时向 `dailyQuiz.ts` 追加速测题占位条目**（含 `// TODO` 仅作为人工补题锚点，不进入站点渲染） |
| `pnpm curate:admit <source-id>` | 对单一信源执行准入核验：可达性 + 许可页抓取证据 → 输出待人工确认的 `admission` 草案（**不自动写入**，人工填 `license` 后才生效） |

**人工节律折算**：周更 2~3 篇 = 每周 1 次约 90 分钟批量会话 ≈ **≤100 次/年**（对比日更 365 次），在 bus factor=1 下可持续。

### 3.3 防漂移门禁（M1 + M2 共用的不变量层）

新建 `scripts/test_daily_loop.py`，接入 `pnpm test:graph`，断言五组：

| 组 | 断言 |
|---|---|
| G1 内容-速测 1:1 | 每篇文章恰有 1 道速测题；无孤儿题（题有文章不存在）；失败时列出缺失清单 |
| G2 轮换池非空 | `articles / quiz / glossary` 三池均 ≥ 1 |
| G3 指纹唯一性 | `lcm(池规模) ≥ 3650`，并打印实际不重复天数 |
| G4 信源准入合法 | 每个信源 `discovery.mode` ∈ {anchor, sitemap, feed}；`admission.status` ∈ 合法集；`status == "admitted"` ⇒ `license` 非空（fail-closed） |
| G5 台账 schema | `version == 2`；每个条目字段完备；`url` 全局唯一；迁移函数幂等（同一 v1 输入两次迁移结果相同） |

### 3.4 Integration Points（集成点）

- **Python 标准库**：`urllib.request`（既有 `fetch_url`）、`xml.etree.ElementTree`（sitemap / RSS-Atom 解析）、`re`、`json`、`datetime` —— 零新增第三方依赖；
- **TypeScript**：无新增依赖；
- **CI**：`pnpm test`（既有链）自动覆盖新门禁；`curate:pool` / `curate:draft` 仅在本地人工作业使用，不进 CI 关键路径。

---

## 4. Edge Cases & Resilience（边界与韧性）

| 场景 | 处理 |
|---|---|
| 网络超时 / 5xx | 沿用既有口径：单次超时 10s，重试 3 次，退避 2s |
| 403 反爬 | 沿用 `curate.py` 既有五态判定：二次确认 403 记 `BOT_BLOCKED` 并**不计入死链**，不阻断准入流程 |
| sitemap 体积过大 | `> 5MB` 或条目 `> 5000` 时按 `max_pages` 截断并打印告警，不中断其余信源 |
| sitemap 为 gzip（`.xml.gz`） | 本里程碑**不支持**：跳过该信源并在报告中显式标注「需解码 gzip，降级到 anchor 模式」，禁止静默跳过 |
| sitemap index 嵌套 | 递归深度上限 `max_pages`（默认 3），超限即停，防无限递归 |
| feed 格式差异（RSS 2.0 / Atom） | 两条 XPath 分支：`item/link`（RSS）与 `entry/link[@href]`（Atom）；两者皆无法解析时报错并跳过该信源 |
| XML 解析异常 | 捕获 `ET.ParseError`，该信源降级为 `anchor` 模式并记录原因，不使整批失败 |
| 台账 v1 → v2 迁移 | 幂等纯函数；重复运行结果一致；迁移后立即写回并在日志打印条目数 |
| 历史数据污染 | 迁移时若 v1 存在重复 URL，按首次出现去重并打印被丢弃条数（不静默丢数据） |
| 时区 / 跨年 | 轮换固定 UTC+8（沿用现有 `getDayOfYear` 实现）；跨年由 `(day-1) % N` 自然续接，无特判分支 |
| 新文章发布当日缺速测题 | G1 门禁直接阻断（防 C3 漂移复发），错误信息给出待补 key 名 |
| 某日池为空（内容尚未录入） | `getTodayIndex` 返回 0 且 `DailyCard` 不渲染速测区；`DailyTerm` 在词条池为空时不挂载（既有降级风格） |
| 候选池耗尽 | `curate:pool` 显式报错并提示准入新信源（不静默返回空表） |
| 准入核验的出口差异 | 本机出口实测存在 403/412 误判 → 准入证据**必须来自 CI run**，`verified_by_run` 为空视为未完成准入 |

---

## 5. Test Strategy（测试策略）

### 5.1 单元测试

- `scripts/test_daily_loop.py`（新建）：G1–G5 五组断言（含真实调用 `lcm` 计算而非硬编码）；
- 迁移函数幂等性：`migrate_ledger_v1_to_v2(v1) == migrate_ledger_v1_to_v2(migrate_ledger_v1_to_v2(v1))`；
- 发现模式解析：用 `scripts/fixtures/` 下三个本地样本（sitemap 片段 / RSS 片段 / Atom 片段）验证 `discover_candidates()` 三种模式的提取结果，**测试不发起真实网络请求**（网络相关断言由 CI 巡检独立承担）。

### 5.2 集成场景

1. `pnpm curate:pool --source who-fact-sheets --limit 5` → 正确列出候选且不写盘（dry-run 语义）；
2. `pnpm curate:draft <fixture-url>` → 生成骨架且 `dailyQuiz.ts` 出现对应占位 key；
3. 构造「文章存在但速测题缺失」的临时夹具 → G1 必须失败（反向验证门禁有效性，不能只测通过路径）。

### 5.3 验证命令

```bash
python -X utf8 scripts/test_daily_loop.py      # 新增门禁 5 组断言
pnpm check                                      # astro check 零错误
pnpm test                                       # 全链路：check + 6 套测试脚本 + curate:check + build
```

---

## 6. Fog of War & Scope Boundaries

### 6.1 Fog of War（尚未确定的未知）

- **CI 出口的真实候选池深度**：本机出口对 cdc.gov / unesco.org / nhc.gov.cn 返回 403/412，无法判断这些权威源在 CI 出口的真实可抓取性；需在 M2 首个准入任务中由 CI run 实测确认；
- **Scarleteen / AMAZE 的可达性**：本机出口 `000`（连接失败），无法区分「站点不可达」与「本机防火墙/DNS 异常」；其是否可作为「愉悦」分类补源需 CI 实测；
- **逐源许可条款文本**：本项目调研记录中 WHO 条款页两次抓取失败（条款现行文本未核实），各新信源的 `license` 字段必须由人工阅读许可页后填入，不得由机器推断。

### 6.2 Out of Scope（显式非目标）

1. **全自动发布导读**：项目自身调研已定性为不可行（模板填充 = 信任事故）；本规格书不提供任何「机器自动写要点」路径；
2. **AI 自动撰写提炼要点**：人工通读原文并重写是信任机制的组成部分，不在本里程碑自动化范围内；
3. **日更一篇新长文**：与 C2（人工天花板）直接冲突，用户已拍板不采用该新鲜度定义；
4. **方案 C 内容形态工厂**：本里程碑不实现。**预留接口**：现有全部内容形态数据均以 `article id` 为主键（`DAILY_QUIZZES[id]`、`glossary.related_article`、`positionMatrix.related_article`），未来 C 只需在 `rotation.ts` 的池注册表中新增池即可派生新形态，无需重构；
5. **多语言 / 繁体版**：ADR-0002 已定为后续阶段；
6. **自定义域名、PWA、newsletter 实站接入**：属分发实验（调研 P3），与本规格书无耦合；
7. **新增第三方抓取依赖**（requests / bs4 / feedparser）：违反零依赖约束，明确不使用。

---

## Self-Review Checklist

- [x] Zero "TODO" or "TBD" placeholders（`curate:draft` 注入的 `// TODO` 是**产品行为**：人工补题锚点，已在 §3.2.3 明确定义语义）；
- [x] No ambiguous assumptions or hidden scope creep（基线已由用户拍板 ADR-0002；新鲜度定义已拍板 ③；C 留位写法明确不实现）；
- [x] The Ladder of Reuse checked（复用既有 `getDayOfYear` / `fetch_url` / `compose_mdx_content` / `test_tools.py` 门禁范式；零新增依赖；Python 仅用标准库）；
- [x] 矛盾消解已记录：`IDEA.md` 旧口径 vs `ADR-0002` 的冲突在文档头显式裁定，避免后续设计歧义；
- [x] 每条设计决策均可回溯到 §1.1 的实测约束（C1–C4）或本轮真实探测证据。

---

## 里程碑与验收标准

| 里程碑 | 范围 | 验收标准 |
|---|---|---|
| **M1 每日新鲜组合 + 防漂移门禁** | `rotation.ts`、`DailyTerm.astro`、`DailyCard` 改造、今日上新置顶、`test_daily_loop.py` G1/G2/G3、补齐 FGM 缺失速测题 | `pnpm test` 全绿；G1/G2/G3 生效；首页当日出现「今日精选 + 速测 + 每日一词」三元组合；`lcm` 断言打印 ≥ 3650 |
| **M2 增量候选供给管道** | `sources.json` v2、三种发现模式、台账 v2 与迁移、`curate:pool` / `curate:draft` / `curate:admit`、G4/G5 | `pnpm test` 全绿；`curate:pool` 在现有 2 信源上输出 ≥40 条带分类排序的候选；至少 1 个新信源走完 `curate:admit` 并进入 `admitted`；候选池条目在 CI run 中有可达性证据 |

---

**下一步**：本规格书经用户审批后，交由 `/dfs-plan` 拆解为 TDD 实施计划（每个 Task 含 Step Breakdown 与验收命令）。
