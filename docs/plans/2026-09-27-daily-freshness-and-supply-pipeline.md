# 日更可持续性：每日新鲜组合与增量候选供给管道 实施计划 (Implementation Plan)

> **Goal**: 在 ADR-0002 基线下，把「每天都有新鲜内容」从不可验收的口号变为 CI 可守的数学不变量（每日三元组合指纹 ≥10 年不重复），并把内容供给从「入口页单页抓取」升级为「三模式增量发现 + 准入 fail-closed + 候选池台账」，使单人维护者以每周约 90 分钟批量作业维持周更 2~3 篇。
> **Tech Stack**: Astro 7.3.3 + TypeScript strict + Tailwind v4 + Python 3.11+ 标准库（`urllib` / `xml.etree.ElementTree` / `re` / `json` / `pathlib`）。
> **Spec Reference**: `docs/specs/2026-09-27-daily-freshness-and-supply-pipeline-design.md`（Status: APPROVED，用户 2026-09-27 批准）+ ADR-0002。
> **Global Constraints**:
> 1. **零新增第三方依赖**：Python 仅标准库；站点零新增 npm 依赖（拒绝 requests/bs4/feedparser）；
> 2. **零 Emoji / 零 innerHTML**：新增组件与站点内容禁止彩色 Emoji；组件禁止 `innerHTML`（`scripts/test_article_hygiene.py` 已有门禁）；
> 3. **零文案搬运**：候选草稿的 `summary` 与正文要点必须人工撰写，禁止沿用来源页面 description；
> 4. **准入 fail-closed**：信源 `admission.status != "admitted"` 或 `license` 为空 ⇒ 抓取器必须跳过该信源；
> 5. **零回归**：不改动既有 26 篇文章正文、不改动 7 大工具组件行为；`pnpm test` 必须保持 100% 全绿；
> 6. **UTF-8 统一**：所有 python 调用走 `python -X utf8`（package.json 已统一，新脚本沿用）；新增路径操作统一 `pathlib.Path`，禁止字符串拼接路径；
> 7. **门禁必须含反向用例**：任何新门禁脚本必须包含「构造坏数据 ⇒ 断言必须失败」的反向测试，否则该门禁视为无效。

---

## 🏛️ Decisions So Far

- **ADR-0002**（2026-09-24）：项目定位 = 每日性健康科普与愉悦探索分享站；策展导读为主 + 开放全文为辅；Schema 轻量。本计划基线以 ADR-0002 为准，`IDEA.md` 旧口径（四段审核/不追求自动发布）不适用。
- **用户拍板 2026-09-27**：① 基线 = ADR-0002；② 「新鲜」定义 = **每周 2~3 篇新长文 + 每天首页有可判定变化**；③ 方案 = **A（新鲜组合）+ B（增量供给）组合起步，C（形态工厂）留位**。
- **实测事实 C1–C4**（写入 Spec §1.1）：供给池仅剩 48 篇候选；人工提炼为硬天花板；文章 26 篇 vs 速测题 25 道已漂移；首页轮换周期 = 文章总数。
- **发现模式选型实测依据**：plannedparenthood.org `/sitemap.xml` = 200 ⇒ sitemap 模式；guokr.com `/feed/` = 200 ⇒ feed 模式；dxy.com / knowsex.net / res.knowsex.org 三者皆 404 ⇒ 保留 anchor 模式；cdc.gov/unesco.org 403、nhc.gov.cn 412 ⇒ **准入核验必须在 CI 出口执行**。
- **数学不变量（2026-09-27 Task-2 执行期修正）**：速测题与今日文章 1:1 绑定（G1 强制），**不是独立轮换维度**；真实周期 = `lcm(文章池, 词条池)` = `lcm(26,28) = 364 天`（约一年）。门禁阈值 `MIN_UNIQUE_CYCLE_DAYS = 90`（一季）+ 不退化断言 `A % G != 0 && G % A != 0`。原 `9100 天 / 3650 阈值` 建立在「速测题是独立维度」的错误前提上，已废弃（修正记录见 Spec §3.1.3）。
- **复用纪律**：复用既有 `getDayOfYear`（`dailyQuiz.ts:324-331`）、`fetch_url` / `clean_title` / `compose_mdx_content`（`curate_harvester.py`）、既有门禁脚本范式（`scripts/test_tools.py` 的 `errors: list` 收集 + `sys.exit(1)` 模式）。

---

## 🎯 Active Frontier (Unblocked Tasks)

### Task 1: 轮换数学单一真值源 `rotation.ts` + 指纹唯一性门禁 [Mode: AFK] [Role: TDD Builder]

**Files:**
- Create: `src/data/rotation.ts`
- Create: `scripts/test_daily_loop.py`
- Modify: `src/data/dailyQuiz.ts:321-341`（`getDayOfYear` / `getTodayIndex` 改为从 `rotation.ts` 转出，保持既有导入路径不破坏）

**Interfaces:**
- Consumes: 无（纯函数模块，零 import）
- Produces:
  - `export function getDayOfYear(date?: Date): number`（UTC+8 口径，行为与现实现完全一致）
  - `export function getTodayIndex(totalCount: number, date?: Date): number`
  - `export function getWeekIndex(totalWeeks: number, date?: Date): number`（`Math.floor((dayOfYear - 1) / 7) % totalWeeks`）
  - `export function lcm(values: number[]): number`（0 或空数组返回 0）
  - `export function computeFingerprint(date: Date, poolSizes: number[]): string`（形如 `"3-12"`；修正后语义上只传 `[文章池, 词条池]`）
  - `export const MIN_UNIQUE_CYCLE_DAYS = 90`（**修正后阈值**：一季；原 3650 建立在「速测题是独立维度」的错误前提上）

**Injected Instincts (Compile-Time Rule Injection):**
- [ ] `[Instinct: Parser-Defensive]`（vault `01-Rules/MARKDOWN-REGISTRY-VALIDATION.md §2`）：门禁脚本必须先喂「空池 / 单元素池」边界输入，确认能解析出非 0 结果，不得只测通过路径。
- [ ] `[Instinct: Reverse-Test]`：G3 断言必须包含反向用例——① 周期型：`(A,G)=(26,26)` ⇒ `lcm = 26 < 90`，必须报错；② 相位型：`(A,G)=(26,26)` 或 `(28,28)` ⇒ `A % G == 0`，必须报"同相位坍缩"错误；③ 正向对照：`(26,28)` ⇒ 364 ≥ 90 且互不整除，必须通过。
- [ ] `[Instinct: Python-Standards]`（vault `03-Languages/Python/PYTHON-STANDARDS.md §4.3`）：新增脚本路径操作统一 `pathlib.Path`，禁止 `dir + "/" + file` 字符串拼接。
- [ ] `[Instinct: Zero-Regression]`：`rotation.ts` 的 `getDayOfYear` 必须与 `dailyQuiz.ts:324-331` 现行实现逐位等价（含 `getTimezoneOffset()` 处理），否则打卡跨日判断会错位。

**Subagent Prompt Scaffold (for /dfs-exec):**
> "Implement Task 1: 轮换数学单一真值源与指纹唯一性门禁.
> Mode: AFK | Role: TDD Builder
> Goal: 把散落在 `dailyQuiz.ts` 的轮换数学收敛为 `src/data/rotation.ts` 纯函数模块，并新建 `scripts/test_daily_loop.py` 的 G3 组断言（**文章池 × 词条池 → lcm → ≥90 天不重复 + 两池不退化**），把「新鲜」变成 CI 可守的不变量。
> Target Files: Create `src/data/rotation.ts`；Create `scripts/test_daily_loop.py`；Modify `src/data/dailyQuiz.ts:321-341`（改为 re-export）。
> Injected Instincts: Parser-Defensive（空池/单元素边界自检）、Reverse-Test（坏池规模与同相位必须断言失败）、Python-Standards（`pathlib.Path`）、Zero-Regression（`getDayOfYear` 逐位等价）。
> TDD Steps:
> 1. 先写 `scripts/test_daily_loop.py`：从真实文件统计池规模（`src/content/articles/*.mdx` 排除 `_` 前缀、`src/content/glossary/*.md`；速测池仅用于 G1 与相位一致性校验，**不参与周期计算**），断言 `lcm([A, G]) >= 90` 且 `A % G != 0 && G % A != 0`，打印实际周期与软告警；同时加反向用例 `(26,26)` 与正向对照 `(26,28)`（RED）。
> 2. 运行 `python -X utf8 scripts/test_daily_loop.py` 验证 G3 失败于「`rotation` 真值源缺失/未 re-export」。
> 3. 创建 `src/data/rotation.ts`（纯函数，含 `lcm` 手写实现：`a*b/gcd`，避免依赖第三方大数库）。
> 4. 修改 `src/data/dailyQuiz.ts:321-341`：删除原实现，改为 `export { getDayOfYear, getTodayIndex } from './rotation';`，并把 `QuizItem` 相关代码保持不动。
> 5. 运行 `python -X utf8 scripts/test_daily_loop.py` 与 `pnpm check` 验证全绿。
> 6. 门禁自检：临时把词条池缩到使 `lcm < 90` 的数值，确认脚本 exit 1；恢复后确认 exit 0。
> Return: 测试执行物理凭据（命令 + exit code + stdout 片段 + `git diff --stat`）。"

**Step Breakdown:**
- [ ] **Step 1: Write the failing test (RED)**：`scripts/test_daily_loop.py` 建骨架 + G3 断言 + 反向用例。
- [ ] **Step 2: Run test and verify it fails with expected message**：`python -X utf8 scripts/test_daily_loop.py` 失败于 G3。
- [ ] **Step 3: Implement minimal production code (GREEN)**：创建 `rotation.ts`，改造 `dailyQuiz.ts` 为 re-export。
- [ ] **Step 4: Run tests and verify all green**：`python -X utf8 scripts/test_daily_loop.py && pnpm check`。
- [ ] **Step 5: Refactor & Flatten with guard clauses (REFACTOR)**：`lcm` 空数组/含 0 的守卫子句前置，嵌套 ≤2 层。
- [ ] **Step 6: Physical Evidence Gate**：捕获原始终端凭据（命令 + Exit code: 0 + 断言通过条数 + `git diff --stat`）。
- [ ] **Step 7: Git atomic commit**：`git add src/data/ scripts/ && git commit -m "feat(rotation): 收敛轮换数学为单一真值源并落地指纹唯一性门禁"`。

---

### Task 2: G1 文章↔速测题 1:1 门禁 + 补齐已漂移的 FGM 速测题 [Mode: AFK] [Role: TDD Builder]

**Files:**
- Modify: `scripts/test_daily_loop.py`（新增 G1 组；**修订轮追加**：按修正后口径重写 G3 组、抽出纯函数 `check_cycle_threshold`）
- Modify: `src/data/dailyQuiz.ts`（在 `DAILY_QUIZZES` 末尾追加 `'body-female-genital-mutilation'` 条目）
- Modify: `src/data/rotation.ts`（**修订轮追加**：`MIN_UNIQUE_CYCLE_DAYS` 3650 → 90 + 头注释口径更正）

**Interfaces:**
- Consumes: `DAILY_QUIZZES: Record<string, QuizItem>`、文章文件名集合
- Produces: G1 断言（无缺题、无孤儿题、失败时打印待补 key 清单）

**Injected Instincts (Compile-Time Rule Injection):**
- [ ] `[Instinct: Reverse-Test]`：必须构造「文章存在但速测题缺失」的临时夹具目录，断言 G1 在该夹具下**必须失败**（证明门禁真的有效，而非恰好通过）。
- [ ] `[Instinct: Human-Readable-Failure]`：失败输出必须给出可执行修复指令（`❌ 文章 X 缺少速测题 → 请在 src/data/dailyQuiz.ts 增加 key 'X'`）。
- [ ] `[Instinct: Zero-InnerHTML]`：本任务不新增组件，但 FGM 速测题文案不得含 Emoji。

**Subagent Prompt Scaffold (for /dfs-exec):**
> "Implement Task 2: 文章↔速测题 1:1 门禁与 FGM 速测题补齐.
> Mode: AFK | Role: TDD Builder
> Goal: 用 G1 门禁锁死「每篇文章恰有 1 道速测题」这一不变量，并修复已实测存在的漂移（26 篇文章 vs 25 道题，`body-female-genital-mutilation` 缺题）。
> Target Files: Modify `scripts/test_daily_loop.py`；Modify `src/data/dailyQuiz.ts`（追加 1 条 `QuizItem`，字段与既有条目同构：`articleId/question/options/correctIndex/explanation`）。
> Injected Instincts: Reverse-Test（夹具下必须失败）、Human-Readable-Failure、Zero-Emoji。
> TDD Steps:
> 1. 在 `scripts/test_daily_loop.py` 增加 `validate_quiz_coverage(errors)`：扫描文章 slug 集合与 `DAILY_QUIZZES` 键集合，双向差集非空即记错误；并在测试内构造临时夹具目录（1 篇文章 + 0 道题）调用同一函数，断言其**返回非空错误列表**（反向验证）。
> 2. 运行 `python -X utf8 scripts/test_daily_loop.py` 验证失败，错误信息精确指出 `body-female-genital-mutilation` 缺题（RED）。
> 3. 在 `src/data/dailyQuiz.ts` 的 `DAILY_QUIZZES` 末尾追加 FGM 速测题：题干须取自本次已撰写的 WHO 溯源要点（四种分型 / 医疗化 / 无宗教依据 三者择一），3 个选项 + 即时解析，零 Emoji。
> 4. 运行 `python -X utf8 scripts/test_daily_loop.py` 验证 G1 与 G3 全绿（GREEN）。
> 5. 守卫子句化：把「空文章集 / 空题集」的短路判断前置，避免除零与误报。
> Return: 物理执行凭据（命令 + exit code + 断言条数 + 新增题目的 `git diff` 片段）。"

**Step Breakdown:**
- [ ] **Step 1: Write the failing test (RED)**：新增 G1 组 + 反向夹具用例。
- [ ] **Step 2: Run test and verify it fails with expected message**：错误信息须点名缺失 slug。
- [ ] **Step 3: Implement minimal production code (GREEN)**：补 FGM 速测题（WHO 溯源、零 Emoji）。
- [ ] **Step 4: Run tests and verify all green**：`python -X utf8 scripts/test_daily_loop.py`。
- [ ] **Step 5: Refactor & Flatten with guard clauses (REFACTOR)**。
- [ ] **Step 6: Physical Evidence Gate**。
- [ ] **Step 7: Git atomic commit**：`git commit -m "fix(daily-loop): 落地文章↔速测题1:1门禁并补齐FGM缺失速测题"`。

---

### Task 3: G2 池非空门禁 + 每日一词组件 `DailyTerm.astro` + 首页组装 [Mode: AFK] [Role: TDD Builder]

**Files:**
- Modify: `scripts/test_daily_loop.py`（新增 G2 组）
- Create: `src/components/DailyTerm.astro`
- Modify: `src/pages/index.astro:20-44`（引入 glossary collection、按 id 确定性排序、`getTodayIndex` 轮换与条件挂载）

> **衔接说明（Task-2 验收后追加）**：`scripts/test_daily_loop.py` 中已存在但 G3 修订后暂无调用方的 `count_quiz_pool()`（第 57 行）**必须由本任务的 G2 组接管消费**（G2 断言「三池规模均 ≥ 1」需要速测池计数）；若 G2 最终不消费它，则由本任务一并删除，禁止留下无调用方的死代码。

**Interfaces:**
- Consumes: `getCollection('glossary')`、`rotation.getTodayIndex`
- Produces:
  - `DailyTerm.astro` Props `{ term: CollectionEntry<'glossary'> }`
  - 首页每日一词区块（锚点指向 `${base}glossary/#term-${term.id}`）

**Injected Instincts (Compile-Time Rule Injection):**
- [ ] `[Instinct: Zero-Emoji]`：新组件复用既有纸墨调色板（`#FAF8F5` / `#15140F` / `#2A2620` / `rose-600`），零彩色 Emoji。
- [ ] `[Instinct: Zero-InnerHTML]`：组件纯服务端渲染，无脚本、无 `innerHTML`（`test_article_hygiene.py` 会扫描）。
- [ ] `[Instinct: Paper-Ink-Consistency]`：卡片语言与 `DailyCard.astro` 保持一致（`rounded-3xl border-[#15140F]/15 shadow-[3px_3px_0...]`）。

**Subagent Prompt Scaffold (for /dfs-exec):**
> "Implement Task 3: 每日一词组件与 G2 池非空门禁.
> Mode: AFK | Role: TDD Builder
> Goal: 让首页在「今日精选 + 速测」之外增加**第二个独立的**轮换源（28 词条池），把首页当日组合周期从「文章池自身周期 26 天」提升到 `lcm(26,28) = 364 天`（约一年），并用 G2 门禁保证三池永不为空。**注意**：速测题与今日文章 1:1 绑定，不构成独立维度（修正记录见 Spec §3.1.3），故本任务的真实增益来自词条池而非速测池。
> Target Files: Modify `scripts/test_daily_loop.py`；Create `src/components/DailyTerm.astro`；Modify `src/pages/index.astro`。
> Injected Instincts: Zero-Emoji、Zero-InnerHTML、Paper-Ink-Consistency。
> TDD Steps:
> 1. 在 `scripts/test_daily_loop.py` 增加 G2：三池规模均 ≥ 1，并额外断言 **`lcm(文章池, 词条池) > 文章池`**（证明词条池**真的参与**周期计算，而非与文章池同相位/被整除的假接入——这是「加了组件但没接进指纹」的假绿防线）。
> 2. 运行 `python -X utf8 scripts/test_daily_loop.py` 验证 G2 失败（RED，因为脚本尚无第三池统计）。
> 3. 实现 G2 统计逻辑（读 `src/content/glossary/*.md` 计数），并创建 `src/components/DailyTerm.astro`（显示词条名 / `en_term` / 80 字内 `definition` / 词典锚点链接）。
> 4. 在 `src/pages/index.astro` 引入 `getCollection('glossary')`，按 `getTodayIndex(glossary.length)` 选词并挂载 `<DailyTerm />`。
> 5. 运行 `python -X utf8 scripts/test_daily_loop.py && pnpm check && pnpm build` 验证全绿（GREEN）。
> Return: 物理执行凭据（命令 + exit code + 构建页数 + `git diff --stat`）。"

**Step Breakdown:**
- [ ] **Step 1: Write the failing test (RED)**：G2 三池非空 + `lcm(文章池, 词条池) > 文章池`（证明词条池真的参与周期，非假接入）。
- [ ] **Step 2: Run test and verify it fails with expected message**。
- [ ] **Step 3: Implement minimal production code (GREEN)**：`DailyTerm.astro` + 首页组装。
- [ ] **Step 4: Run tests and verify all green**：`test_daily_loop.py` + `pnpm check` + `pnpm build`。
- [ ] **Step 5: Refactor & Flatten with guard clauses (REFACTOR)**：词条池为空时不挂载组件。
- [ ] **Step 6: Physical Evidence Gate**。
- [ ] **Step 7: Git atomic commit**：`git commit -m "feat(daily): 落地每日一词轮换组件并将首页当日组合周期扩展至364天"`。

---

### Task 4: 「今日上新」置顶规则 [Mode: AFK] [Role: TDD Builder]

> **设计修正（2026-09-27，Task-3 验收后由 Checker 席位风险提示驱动）**：
> 初版写的是「新文章**优先占据今日精选位**（替换轮换结果）」。该做法会**扰动轮换不变量**：替换后文章维度在 7 天窗口内被冻结为同一篇（`index.astro` 按 `pubDate` 降序排序 ⇒ 最新文恒在索引 0），而词条维度继续按日推进 ⇒ 冻结期内的 7 个 `(最新文, 词条)` 组合会在随后轮换命中索引 0 时**再次出现**（例如 `Y ≡ 1 (mod 26)` 且 `Y ≡ X (mod 28)` 有解），即 `lcm(26,28)=364` 的「364 天内不重复」承诺出现**期内重复**。
> **修正决策**：上新改为**附加展示**而非替换——「今日精选」的轮换索引（`getTodayIndex(articles.length)`）**完全不变**，若 7 天窗口内存在新文，则在 `DailyCard` 内**增补一条「今日上新」条带**（含标题与直达链接）。这样：① 产品目标（新文立刻可见，不被 26 天轮换埋没）达成；② 轮换不变量**零扰动**，G3 的 364 天承诺保持严格成立；③ 不需要新增第三个轮换维度。

**Files:**
- Modify: `src/components/DailyCard.astro:9-14`（Props 扩展）与 `:66-97`（上新条带位）
- Modify: `src/pages/index.astro`（7 天窗口计算 + **locale 无关的确定性排序改造**）
- Modify: `scripts/test_daily_loop.py`（新增 G6：上新窗口纯函数断言）

**Interfaces:**
- Consumes: `articles`（按 `pubDate` 降序已排序）
- Produces:
  - `rotation.pickFreshArticle<T>(items: T[], getDate: (t: T) => Date, today: Date, windowDays = 7): T | null`（**纯函数，仅用于附加条带，不参与轮换索引计算**）
  - `DailyCard.astro` Props 增加 `freshArticle?: CollectionEntry<'articles'>`

**Injected Instincts (Compile-Time Rule Injection):**
- [ ] `[Instinct: Timezone-Determinism]`：窗口判定必须用 `getDayOfYear` 的 UTC+8 口径，禁止直接用 `new Date()` 相减（跨时区会漏判）。
- [ ] `[Instinct: No-Layout-Shift]`：无上新时不得渲染空占位（条件渲染），避免首页高度抖动。

**Subagent Prompt Scaffold (for /dfs-exec):**
> "Implement Task 4: 今日上新置顶规则.
> Mode: AFK | Role: TDD Builder
> Goal: 解决「新文章被 26 天轮换埋没」——`pubDate` 距今 ≤7 天的文章优先占据今日精选位，并在卡片上给出可辨识的上新徽标。
> Target Files: Modify `src/components/DailyCard.astro`；Modify `src/pages/index.astro`；Modify `scripts/test_daily_loop.py`（G6 纯函数断言：7 天内命中 / 第 8 天不命中 / 多篇命中取最新 / 空数组返回 null）。
> Injected Instincts: Timezone-Determinism、No-Layout-Shift。
> TDD Steps:
> 1. 在 `scripts/test_daily_loop.py` 增加 G6：以 4 组固定日期输入断言 `pickFreshArticle` 语义（含边界：第 7 天命中、第 8 天不命中）。
> 2. 运行 `python -X utf8 scripts/test_daily_loop.py` 验证失败（RED，函数尚未实现）。
> 3. 在 `src/data/rotation.ts` 实现 `pickFreshArticle`（纯函数，零依赖）。
> 4. 改造 `DailyCard.astro`：新增可选 Props `freshArticle`，命中时渲染纸墨风格上新徽标（零 Emoji，用 `[ 今日上新 ]` 文案）；首页按规则传入。
> 5. 运行 `python -X utf8 scripts/test_daily_loop.py && pnpm check && pnpm build` 验证全绿（GREEN）。
> Return: 物理执行凭据。"

**Step Breakdown:**
- [ ] **Step 1: Write the failing test (RED)**：G6 四组边界断言。
- [ ] **Step 2: Run test and verify it fails with expected message**。
- [ ] **Step 3: Implement minimal production code (GREEN)**：`pickFreshArticle` + `DailyCard` 上新条带（附加展示，不改轮换索引）+ 首页接线；**并顺带把 `index.astro` 的 `localeCompare` 排序改为 locale 无关比较器**（`a.id < b.id ? -1 : a.id > b.id ? 1 : 0`），消除 ICU/locale 差异导致的轮换漂移风险（Task-3 验收 YELLOW-3）。
- [ ] **Step 4: Run tests and verify all green**。
- [ ] **Step 5: Refactor & Flatten with guard clauses (REFACTOR)**。
- [ ] **Step 6: Physical Evidence Gate**。
- [ ] **Step 7: Git atomic commit**：`git commit -m "feat(daily): 新文章7天内优先置顶今日精选位"`。

---

### Task 5: 门禁接入 CI 全链路并完成 M1 验收 [Mode: AFK] [Role: Integration Builder]

> **Task-1/Task-2 验收后追加的加固项（来自 Checker 席位的对抗性变异检查）**：
> - **YELLOW-0（真实护栏缺口，优先级最高）**：Task-2 修订轮后，「两池不退化」分支**没有可红的独立反向用例**——反向用例只断言 `check_cycle_threshold([26,26], 90)` 返回**非空**，不判内容与条数；推演证明「删掉该纯函数内的整除判定循环」后 CI **仍全绿**（`[26,26]` 靠阈值分支仍返回 1 条非空）。⇒ 本任务必须补：① 断言 `len(collapsed) == 2` 且消息文本分别包含「周期坍缩」与「同相位坍缩」；② 补一个**只触发相位分支**的判别用例 `[100, 50]`（`lcm=100 ≥ 90` 过阈值，但 `50 | 100` 必须触发同相位坍缩）；③ 顺带把该脚本 docstring 中「零 Emoji」措辞改为「站点内容零 Emoji；脚本输出沿用仓库既有 `❌`/`✅` 门禁范式」，消除自相矛盾。
> - **YELLOW-4（Task-3 验收新增 · 门禁与运行时计数口径漂移）**：`count_glossary_pool()` 当前用 `GLOSSARY_DIR.glob('*.md')`（仅顶层、不排除 `_` 前缀、不含 `.mdx`），而内容集合 loader 是 `glob({ pattern: '**/*.{md,mdx}' })` 递归加载 ⇒ 一旦 glossary 出现子目录或 `.mdx`，门禁统计的池规模将与首页实际渲染的池规模**静默脱钩**。本任务必须把文章池与词条池的计数口径**对齐**（递归 + `.md`/`.mdx` + 排除 `_` 前缀），并补一条断言：**门禁统计的池规模 == 站点实际可渲染的池规模**。
> - **YELLOW-5（Task-3 验收新增 · G2 反向用例与真实池解耦）**：Task-3 的 G2 反向用例为**硬编码** `(26,26)` 纯函数调用，与真实池脱钩；删除 G2 主断言调用后门禁对真实数据仍绿（仅靠 G3/G1 兜底）。本任务必须补一条**基于真实池的变异断言**（例如断言 `check_glossary_participation(真实池规模, 真实池规模)` 必返非空），使「假接入」防线不再依赖一次性手工验证。
> **Task-4 验收后扩充的 G8 范围（Checker 指出：原 G8 不足以封堵残留盲区）**：
> - **YELLOW-1（弱断言）**：Task-1 的门禁对 `rotation.ts` 仅做**源码 token 扫描**，空壳实现（如 `computeFingerprint` 恒返回 `""`）可骗过门禁 ⇒ 本任务必须补**行为断言**：用 `node --input-type=module -e` 载入 `rotation.ts`（Node 24 原生 TS 类型剥离），断言 `computeFingerprint(new Date('2026-01-01T00:00:00+08:00'), [26, 28])` 与手算一致、`getTodayIndex(0) === 0`、`lcm([26, 28]) === 364`。
> - **G8a（TZ 双跑一致性，必做）**：Task-4 的守门断言「函数体不得含 `getTimezoneOffset`」只是**必要非充分**条件（可被 `Intl.DateTimeFormat().resolvedOptions().timeZone` 或本地时间 getter 实现绕过）⇒ 必须在 **`TZ=UTC` 与 `TZ=Asia/Shanghai` 两种环境**下分别以 `node` 载入 `rotation.ts`，对同一批边界时刻（`2026-10-03T16:00:00Z` 前后、`2026-12-31T23:59:59Z` 跨年）断言 `beijingDayNumber` **两次运行结果完全相同**。
>   **实现提示（Task-4 实测环境坑）**：Windows 原生 `node.exe` 在 Git Bash 下**收不到含斜杠的 `TZ=` 内联前缀**（收到 `undefined`）⇒ 需改为「argv 传参 + 运行时 `process.env.TZ = ...`」，并以 `new Date().getTimezoneOffset()` 输出（`0` vs `-480`）自证时区确已切换，防止验证静默失真。
> - **G8b（`pickFreshArticle` 真行为断言，必做）**：当前 G6 的窗口边界用例是 **Python 镜像**（同构实现重写），不执行 TS ⇒ 必须用 `node` 载入 `rotation.ts`，对固定日期断言：发布第 7 天命中 / 第 8 天不命中 / 发布当天命中 / 未来日期不命中 / 多篇取最新 / 空数组返回 `null`。
> - **G8c（`_strip_ts_comments` 字面量盲区，必做）**：该函数在剥离注释时对**字符串/正则字面量内的 `//`、`/*` 不设防**（如 `href="https://…"` 或 `/https?:\/\//` 会导致整行被误截），可能造成假红或**掩盖同行真实违规**；且它被 G1 的 `quiz_keys`/`count_quiz_pool` 与 G6 的多处源码契约复用。本任务必须显式加固（剥离前先占位字符串与正则字面量），并覆盖其被复用的全部扫描路径。
> - **G6 断言窄漏绿向量加固（必做）**：`validate_g6_article_sort_descending` 仅查子串存在性 ⇒ `-(b - a)` / `(b - a) * -1`（语义为**升序**）会因降序子串命中而被误判通过。补充否定断言（拒绝一元负号/取反包裹形态），并同时接受 `-(a - b)` 等**语义等价于降序**的写法以避免误红。
> - **YELLOW-2（反向用例偏间接）**：现有反向用例只验证 Python `lcm()` 自身，未驱动门禁失败路径 ⇒ 本任务必须抽出纯函数 `check_cycle_threshold(pool_sizes: list[int], threshold: int) -> list[str]`，并断言 `check_cycle_threshold([26, 26], 90)` **返回非空错误列表**（周期坍缩 + 同相位双错误，直接证明「坏数据 ⇒ 门禁失败」）。

**Files:**
- Modify: `package.json:16`（`test:graph` 追挂 `test_daily_loop.py`）
- Modify: `scripts/test_daily_loop.py`（抽出 `check_cycle_threshold` 纯函数 + 新增 TS 行为断言组 G8）

**Interfaces:**
- Consumes: `scripts/test_daily_loop.py`
- Produces: `pnpm test` 全链路覆盖 M1 全部不变量

**Injected Instincts (Compile-Time Rule Injection):**
- [ ] `[Instinct: Fail-Fast-Order]`：新门禁脚本插在 `test_security_contracts.py` 之前、`test_tools.py` 之后，保持「结构契约 → 行为契约 → 安全契约」的既有顺序语义。
- [ ] `[Instinct: Zero-Flaky]`：新门禁不得发起任何真实网络请求（全为本地文件解析）。

**Subagent Prompt Scaffold (for /dfs-exec):**
> "Implement Task 5: 门禁接入与 M1 验收.
> Mode: AFK | Role: Integration Builder
> Goal: 把 `scripts/test_daily_loop.py` 挂进 `pnpm test:graph`，并验证 M1 全部不变量在完整 CI 链路上生效（含反向用例）。
> Target Files: Modify `package.json:16`。
> TDD Steps:
> 1. 修改 `package.json` 的 `test:graph`，在 `test_tools.py` 之后插入 `python -X utf8 scripts/test_daily_loop.py`。
> 2. 运行 `pnpm test`，确认 6 套脚本全绿 + `astro check` 零错误 + 构建页数（应为 36 页）。
> 3. 反向验证：临时把 `dailyQuiz.ts` 某条 key 删除，确认 `pnpm test` 在 G1 处 fail；恢复。
> 4. 验证 M1 验收标准：`python -X utf8 scripts/test_daily_loop.py` 输出实际周期（`lcm(文章池, 词条池) = 364` 天）、池规模与软告警状态。
> Return: 物理执行凭据（`pnpm test` 完整 stdout 尾部 + exit code 0）。"

**Step Breakdown:**
- [ ] **Step 1: Write the failing test (RED)**：先在本地跑 `pnpm test` 证明新门禁未被调用（无 `test_daily_loop` 输出）；同时新增 G8（TS 行为断言）与 `check_cycle_threshold` 断言（RED）。
- [ ] **Step 2: Verify Red**：确认 `test:graph` 输出缺少新脚本，且 G8 因 `check_cycle_threshold` 未实现而失败。
- [ ] **Step 3: Implement minimal change (GREEN)**：抽出 `check_cycle_threshold` 纯函数 + 实现 G8 的 node 行为断言 + 改 `package.json`。
- [ ] **Step 4: Run `pnpm test` and verify all green**。
- [ ] **Step 5: 反向验证（两条独立路径）**：① 删一条 quiz key ⇒ `pnpm test` 必须在 G1 fail；② 把 `rotation.ts` 的 `computeFingerprint` 改为恒返回 `''` ⇒ 必须在 G8 fail（证明行为断言不是空壳可骗）。两者均需恢复并复跑至全绿。
- [ ] **Step 6: Physical Evidence Gate**：附两条反向验证的 exit code 证据。
- [ ] **Step 7: Git atomic commit**：`git commit -m "ci: 接入每日循环门禁并补TS行为断言防空壳假绿"`。

> **M1 验收后遗留项（Checker 于 Task-5 验收时提出，非阻断；由 M2 任务顺带收口）**：
> - **L1（建议优先）**：`analyze_article_sort_primary` 仍有假降序盲区——`const d = b - a; return -d;`（中间变量再取反，语义为升序）会命中 `has_desc` 分支被放行 ⇒ 需补「对含降序子串的变量取反必须判红」的断言，或改以 node 行为级断言排序方向。**落点：Task 6 或任意触碰该文件的 M2 任务**。
> - **L2**：`content_entry_ids` 的「内部文件」判定用 `path.name`（basename），而站点页面按完整 `entry.id` 过滤 ⇒ 出现嵌套目录时会分歧（当前无嵌套，潜在）。**落点：同上**。
> - **L3（可延后）**：`_strip_ts_comments` 未解析模板串 `${...}` 插值；且 `/` 紧跟 `+`/`*`/`%` 运算符时可能被误判为正则起始。**落点：扫描目标扩展到模板插值时**。
> - **纪律项**：M2 引入 G4/G5/G7 新门禁后，必须同步更新 `scripts/test_daily_loop.py` 顶部 docstring 与 `[gate]` 横幅中「G4/G5/G7 由后续 Task 追加」的表述，避免文档漂移。

---

### Task 6: 信源清单 v2 与三模式增量发现 `discover_candidates()` [Mode: AFK] [Role: TDD Builder]

**Files:**
- Modify: `scripts/sources.json`（扩展 schema，现有 2 信源补 `discovery` 与 `admission` 字段）
- Modify: `scripts/curate_harvester.py:206-320`（`harvest_candidates` 拆出 `discover_candidates(src, seen) -> list[tuple[str, str]]`）
- Create: `scripts/fixtures/sitemap-sample.xml` / `scripts/fixtures/feed-rss-sample.xml` / `scripts/fixtures/feed-atom-sample.xml`
- Create: `scripts/test_source_discovery.py`

**Interfaces:**
- Consumes: `sources.json`、既有 `fetch_url` / `clean_title`
- Produces:
  - `def discover_candidates(src: dict, seen_urls: set[str]) -> list[tuple[str, str]]`（返回 `(url, title)`，`anchor` / `sitemap` / `feed` 三模式内部分派）
  - `def _parse_sitemap(xml_text: str, link_pattern: str, max_pages: int) -> list[str]`
  - `def _parse_feed(xml_text: str) -> list[str]`（RSS `item/link` + Atom `entry/link[@href]`）
  - `def is_source_admitted(src: dict) -> bool`（fail-closed）

**Injected Instincts (Compile-Time Rule Injection):**
- [ ] `[Instinct: Fail-Closed]`：`is_source_admitted` 返回 False 时 `discover_candidates` 必须直接返回空列表并打印跳过原因，不得「先抓后判」。
- [ ] `[Instinct: Parser-Defensive]`（vault `01-Rules/MARKDOWN-REGISTRY-VALIDATION.md §2`）：XML 解析必须容错缺失字段（无 `<loc>` / 无 `<link>` 的条目跳过而非崩溃）；fixture 自检必须先喂「空 sitemap / 单条目 sitemap」确认能解析出非 0 结果。
- [ ] `[Instinct: No-Network-In-Tests]`：`scripts/test_source_discovery.py` 只解析本地 fixture，零真实网络请求。
- [ ] `[Instinct: Stdlib-Only]`：sitemap/feed 解析只用 `xml.etree.ElementTree`，禁止引入 feedparser/bs4。

**Subagent Prompt Scaffold (for /dfs-exec):**
> "Implement Task 6: 三模式增量发现与准入 fail-closed.
> Mode: AFK | Role: TDD Builder
> Goal: 把候选发现从「入口页单页 anchor」升级为 anchor/sitemap/feed 三模式，并让未准入信源（license 为空）被硬跳过。
> Target Files: Modify `scripts/sources.json`；Modify `scripts/curate_harvester.py`；Create `scripts/fixtures/*.xml`；Create `scripts/test_source_discovery.py`。
> Injected Instincts: Fail-Closed、Parser-Defensive、No-Network-In-Tests、Stdlib-Only。
> TDD Steps:
> 1. 先写 `scripts/test_source_discovery.py`：用三个 fixture 断言 sitemap `<loc>` 提取、RSS `item/link` 提取、Atom `entry/link[@href]` 提取；断言 `link_pattern` 过滤生效；断言空 sitemap 返回 `[]` 且不抛异常；断言 `is_source_admitted` 对 `status != admitted` 或 `license == ""` 返回 False（RED）。
> 2. 运行 `python -X utf8 scripts/test_source_discovery.py` 验证失败。
> 3. 扩展 `scripts/sources.json`：为 WHO / 默沙东两条既有信源补 `discovery.mode = "anchor"`（保持原 entry_url 与 link_pattern）与 `admission`（`status: "admitted"`、`license: "link-only"`、`license_url`、`verified_at: "2026-09-27"`）；新增 1 条 sitemap 模式信源（plannedparenthood，`status: "probing"`）与 1 条 feed 模式信源（guokr，`status: "probing"`）——**probing 状态必须导致 discover 跳过**。
> 4. 在 `curate_harvester.py` 实现 `discover_candidates` / `_parse_sitemap` / `_parse_feed` / `is_source_admitted`，并让 `harvest_candidates` 改为调用 `discover_candidates`（anchor 模式行为必须与改造前逐字节等价）。
> 5. 运行 `python -X utf8 scripts/test_source_discovery.py && python -X utf8 scripts/curate_harvester.py --dry-run --limit 1` 验证全绿且既有抓取行为不变（GREEN）。
> Return: 物理执行凭据（测试 exit code + fixture 解析条数 + dry-run 输出片段）。"

**Step Breakdown:**
- [ ] **Step 1: Write the failing test (RED)**：三 fixture + 准入 fail-closed 断言。
- [ ] **Step 2: Run test and verify it fails with expected message**。
- [ ] **Step 3: Implement minimal production code (GREEN)**：schema 扩展 + 三模式解析。
- [ ] **Step 4: Run tests and verify all green**：含 `--dry-run` 兼容性回归。
- [ ] **Step 5: Refactor & Flatten with guard clauses (REFACTOR)**。
- [ ] **Step 6: Physical Evidence Gate**。
- [ ] **Step 7: Git atomic commit**：`git commit -m "feat(curate): 支持sitemap/feed/anchor三模式增量发现与信源准入fail-closed"`。

---

### Task 7: 候选池台账 v2 与幂等迁移 [Mode: AFK] [Role: TDD Builder]

**Files:**
- Modify: `scripts/curate_harvester.py`（`load_ledger` / `save_ledger` 升级 + `migrate_ledger_v1_to_v2`）
- Modify: `scripts/.curate-ledger.json`（迁移为 v2）
- Modify: `scripts/test_daily_loop.py`（G5 组断言）
- Modify: `scripts/test_source_discovery.py`（**承接 Task-6 收口项 Y3**：T5 用例除打桩 `_SITEMAP_FETCH` 外，**同时**把 `ch.fetch_url` 置为抛异常/空返回，使「测试零网络」不再依赖单一 seam）

> **Task-6 验收后承接的收口项（由 Checker 席位提出；本任务在同一批次的 `curate_harvester.py` 上顺带闭合）**：
> - **C1（阻断级，必须先处理）**：台账 v2 把 `processed_urls` 从「字符串数组」变为「对象数组」后，`harvest_candidates` 中现有的 `set(ledger.get("processed_urls", []))` 会因 **dict 不可哈希**抛 `TypeError`；`create_draft_pr` 中的台账写入同理。本任务**必须同步改造这两处**为经 `load_ledger` / `iter_pending` 的对象口径，并在 G5 加一条「v2 台账下 `harvest_candidates` 可正常调用（不抛 TypeError）」的断言。
> - **C2（误导性日志）**：sitemap **字节**体积超限分支只打印告警、**并未真正截断**，但文案声称「按 max_pages 截断处理」（与实际行为不符）；条数保护实际按 `MAX_SITEMAP_ENTRIES` 而非 `max_pages`。本任务须二选一：落实字节级截断，**或**把文案改为「字节超限，已记录告警（未截断）」。同时修正 Spec §4 中「按 `max_pages` 截断」的漂移措辞。
> - **C3（静默空结果）**：anchor 分支在信源 `keywords` 为空时会**静默产出 0 候选**；sitemap/feed 分支不做 `keywords` 过滤（与 anchor 不对称）。本任务须至少加一条「`keywords` 为空 ⇒ 打印显式告警」的守卫；相关性收敛由 Task-8 的 `rank_candidates` 承担（并在 Task-8 复核是否需为三模式统一关键词过滤）。
> - **C4（可选）**：把模块级可变 seam `_SITEMAP_FETCH` 改为 `_parse_sitemap` / `_collect_sitemap` 的**可选形参 `fetcher=`**（默认 `_default_sitemap_fetch`），消除生产模块中的测试专用全局可变状态；调用形态保持向后兼容。

**Interfaces:**
- Consumes: 既有 v1 台账（`{"version":1,"processed_urls":["url",...]}`）
- Produces:
  - `def migrate_ledger_v1_to_v2(data: dict) -> dict`（**幂等纯函数**）
  - v2 条目字段：`url / status / source_id / first_seen / last_probed / http_status`
  - `def iter_pending(ledger: dict, source_id: str | None = None) -> list[dict]`

**Injected Instincts (Compile-Time Rule Injection):**
- [ ] `[Instinct: Idempotent-Migration]`：`migrate(v1) == migrate(migrate(v1))`，重复调用结果必须逐字节一致；断言必须包含该等式。
- [ ] `[Instinct: No-Silent-Data-Loss]`：v1 中存在重复 URL 时按首次出现去重，并打印被丢弃条数（禁止静默丢弃）。
- [ ] `[Instinct: Single-Writer]`：台账读写只能经 `load_ledger` / `save_ledger`，其他函数禁止直接 `open()` 该文件。

**Subagent Prompt Scaffold (for /dfs-exec):**
> "Implement Task 7: 候选池台账 v2 与幂等迁移.
> Mode: AFK | Role: TDD Builder
> Goal: 把台账从「URL 字符串数组」升级为带状态机的候选池（pending/published/rejected + 来源 + 探活时间），并提供幂等 v1→v2 迁移。
> Target Files: Modify `scripts/curate_harvester.py`；Modify `scripts/.curate-ledger.json`；Modify `scripts/test_daily_loop.py`（G5）。
> Injected Instincts: Idempotent-Migration、No-Silent-Data-Loss、Single-Writer。
> TDD Steps:
> 1. 在 `scripts/test_daily_loop.py` 增加 G5：构造 v1 输入断言迁移输出 v2 结构；断言幂等等式；断言含重复 URL 时去重且打印丢弃数；断言现有 `scripts/.curate-ledger.json` 已是 v2 且字段完备（RED）。
> 2. 运行 `python -X utf8 scripts/test_daily_loop.py` 验证失败。
> 3. 在 `curate_harvester.py` 实现 `migrate_ledger_v1_to_v2` / `iter_pending`，并让 `load_ledger` 自动识别 v1 并迁移后写回（打印迁移条数）。
> 4. 执行一次真实迁移落盘 `scripts/.curate-ledger.json`（13 条 URL 转为 v2，`status="published"`）。
> 5. 运行 `python -X utf8 scripts/test_daily_loop.py && python -X utf8 scripts/curate_harvester.py --dry-run --limit 1` 验证全绿（GREEN）。
> Return: 物理执行凭据（迁移前后条目数 + 幂等断言输出）。"

**Step Breakdown:**
- [ ] **Step 1: Write the failing test (RED)**：G5 四组断言。
- [ ] **Step 2: Run test and verify it fails with expected message**。
- [ ] **Step 3: Implement minimal production code (GREEN)**：迁移函数 + 读写收敛。
- [ ] **Step 4: Run tests and verify all green**：含真实台账迁移。
- [ ] **Step 5: Refactor & Flatten with guard clauses (REFACTOR)**。
- [ ] **Step 6: Physical Evidence Gate**。
- [ ] **Step 7: Git atomic commit**：`git commit -m "feat(curate): 候选池台账升级v2并落地幂等迁移"`。

---

### Task 8: `curate:pool` 候选池 CLI 与分类缺口排序 [Mode: AFK] [Role: TDD Builder]

**Files:**
- Modify: `scripts/curate_harvester.py:444-489`（`main()` 新增 `--pool` 分支与 `--limit` 复用）
- Modify: `scripts/test_daily_loop.py`（G4 组：信源 schema 合法性断言）
- Modify: `package.json`（新增 `"curate:pool": "python -X utf8 scripts/curate_harvester.py --pool"`）

**Interfaces:**
- Consumes: `discover_candidates`、`sources.json`、`load_ledger`（**只读**）
- Produces:
  - `def rank_candidates(candidates: list[dict], category_counts: dict[str, int]) -> list[dict]`（四分类升序优先，同分类按首次发现升序）
  - `--pool` CLI：表格输出「标题 / 来源 / 推定分类 / 首次发现」，**不写盘**

> **Task-7 验收后钉死的两处语义（避免实现走偏）**：
> 1. **`--pool` 的数据源 = 「实时发现结果 − 台账已收录 URL」**，即以 `discover_candidates` 的本次发现为输入做差集后排序，**不是**「只读台账里 `status == "pending"` 的条目」。原因：当前**没有任何代码写入 `pending` 状态**（`iter_pending` 目前亦无生产调用方），若按后者实现，`--pool` 将永远输出空表。
> 2. **零副作用红线与 v1 陷阱**：`load_ledger()` 具备「读到 v1 时自动迁移并写回」的条件写盘行为，而 `save_ledger()` 每次都会刷新 `last_updated` ⇒ **`--pool` 路径必须只读**（不得调用 `save_ledger`），且 G4 的「台账 sha256 前后不变」断言**不得用 v1 夹具驱动**（否则会被迁移写回误判为副作用）。测试应用**已是 v2 的夹具或真实台账**驱动。`pending` 状态的写入者明确为 Task-9 的 `curate:draft`（生成骨架时把该候选登记为 `pending`），`iter_pending` 的消费者亦为 Task-9。

**Injected Instincts (Compile-Time Rule Injection):**
- [ ] `[Instinct: Dry-Run-Purity]`：`--pool` 必须为零副作用（不写台账、不写文章文件、不建分支），断言方式为「运行前后台账文件 sha256 不变」。
- [ ] `[Instinct: Actionable-Empty-State]`：候选池为空时报错并给出下一步（`请执行 curate:admit <source-id> 准入新信源`），禁止静默返回空表。
- [ ] `[Instinct: Fail-Closed]`：G4 断言 `admission.status == "admitted"` ⇒ `license` 非空；`discovery.mode` 必须在合法枚举内。

**Subagent Prompt Scaffold (for /dfs-exec):**
> "Implement Task 8: 候选池 CLI 与分类缺口排序.
> Mode: AFK | Role: TDD Builder
> Goal: 给维护者一个「我该写哪一篇」的单一入口——输出按分类缺口优先排序的候选池表格，零副作用。
> Target Files: Modify `scripts/curate_harvester.py`；Modify `scripts/test_daily_loop.py`（G4）；Modify `package.json`。
> Injected Instincts: Dry-Run-Purity、Actionable-Empty-State、Fail-Closed。
> TDD Steps:
> 1. 在 `scripts/test_daily_loop.py` 增加 G4：遍历 `sources.json` 断言 `discovery.mode` 合法、`admission.status` 合法、`admitted ⇒ license 非空`、`base_url` 为 http(s)（RED）。
> 2. 运行 `python -X utf8 scripts/test_daily_loop.py` 验证失败（当前 sources.json 尚无这些字段）。
> 3. 实现 `rank_candidates` 与 `--pool` 分支；`--pool` 只读不写。
> 4. 运行 `pnpm curate:pool --limit 40`，验证输出 ≥40 条候选且台账 sha256 前后一致。
> 5. 运行 `python -X utf8 scripts/test_daily_loop.py` 验证 G4 全绿（GREEN）。
> Return: 物理执行凭据（台账 sha256 前后值 + 候选条数 + 表格头部片段）。"

**Step Breakdown:**
- [ ] **Step 1: Write the failing test (RED)**：G4 四类断言。
- [ ] **Step 2: Run test and verify it fails with expected message**。
- [ ] **Step 3: Implement minimal production code (GREEN)**：`rank_candidates` + `--pool`。
- [ ] **Step 4: Run tests and verify all green**：含零副作用（sha256 不变）验证。
- [ ] **Step 5: Refactor & Flatten with guard clauses (REFACTOR)**。
- [ ] **Step 6: Physical Evidence Gate**。
- [ ] **Step 7: Git atomic commit**：`git commit -m "feat(curate): 新增候选池CLI与分类缺口优先排序"`。

---

### Task 9: `curate:draft`（骨架 + 速测题占位注入）与 `curate:admit` [Mode: AFK] [Role: TDD Builder]

**Files:**
- Modify: `scripts/curate_harvester.py`（新增 `--draft-url` / `--admit-source` 分支 + `inject_quiz_placeholder()`）
- Modify: `scripts/test_daily_loop.py`（新增 G7：占位注入路径断言）
- Modify: `package.json`（`curate:draft` / `curate:admit`）
- Modify: `package.json`（**Task-6 收口项**：把 Task-6 新建的 `scripts/test_source_discovery.py` 挂入 `test:graph`，位置紧接 `scripts/test_daily_loop.py` 之后——否则该门禁在 CI 中永不执行，属「写了门禁但没接线」的假安全感。**行号提示**：`curate:pool` 已于 Task-8 插入，`test:graph` 现实际位于 `package.json:17`，请按语义定位而非盲改 `:16`）

> **Task-8 验收后承接的收口项**：
> - **D1（`pending` 写入者接线，必做）**：`status="pending"` 目前**没有任何写入者**（`iter_pending` 亦无生产消费方）。本任务的 `--draft-url` 在生成骨架时**必须把该候选以 `status="pending"` 写入台账**，此次接线同时激活 `iter_pending` 的消费路径。
> - **D2（空池提示统一，必做）**：Task-8 的空池提示仍用原始 flag（`--admit-source`），且对「零个 admitted 信源」与「已准入源候选耗尽」两类原因共用同一句「候选池已耗尽」文案（后者不准确）。本任务建立 `curate:admit` npm 脚本后，须把提示统一为 `pnpm curate:admit <id>` 形式，并**按两类原因分别给出对应提示**。
> - **D3（读口径澄清，建议）**：`--pool` 的「零副作用」目前是**条件不变量**（依赖真实台账恰为规范 v2；`load_ledger` 在 `migrated != data` 时仍会条件写回）。本任务若顺带改造 `load_ledger`，建议增加 `write_back=False` 只读形参供 `--pool` 使用，使零副作用**无条件**成立（不阻塞：当前口径已被 Task-7 语义显式接受）。
> - **D4（G4 门禁与运行时契约不一致，建议）**：G4 要求 `discovery` 字段必需，而运行时 `discover_candidates` 对缺失 `discovery` 按默认 anchor 容忍。二选一并文档化（放宽门禁 or 移除兼容分支）。

**Interfaces:**
- Consumes: `compose_mdx_content`、`DAILY_QUIZZES` 文件文本
- Produces:
  - `def inject_quiz_placeholder(quiz_path: Path, slug: str) -> bool`（在 `DAILY_QUIZZES` 末尾插入占位条目，含 `// TODO` 人工补题锚点；已存在则返回 False 幂等）
  - `--draft-url <url>`：生成 MDX 骨架 + 注入速测题占位
  - `--admit-source <id>`：可达性 + 许可页抓取证据 → **打印** `admission` 草案（不自动写入）

**Injected Instincts (Compile-Time Rule Injection):**
- [ ] `[Instinct: Idempotent-Injection]`：同一 slug 重复注入必须不产生第二条占位（返回 False 且文件 sha256 不变）。
- [ ] `[Instinct: No-Auto-Approve]`：`--admit-source` **禁止**自动把 `status` 改为 `admitted` 或自动填 `license`——信任机制要求人工阅读许可页后填写（对齐项目「严禁机器自证」纪律）。
- [ ] `[Instinct: TS-Syntax-Safety]`：注入的占位条目必须是**语法合法**的 TS（否则 `pnpm check` 直接红），因此插入后必须运行 `pnpm check` 验证。

**Subagent Prompt Scaffold (for /dfs-exec):**
> "Implement Task 9: 草稿生成与信源准入 CLI.
> Mode: AFK | Role: TDD Builder
> Goal: 让「生成草稿」与「补速测题」一次完成，并把信源准入做成输出证据而不自动通过的人工闸门。
> Target Files: Modify `scripts/curate_harvester.py`；Modify `scripts/test_daily_loop.py`；Modify `package.json`。
> Injected Instincts: Idempotent-Injection、No-Auto-Approve、TS-Syntax-Safety。
> TDD Steps:
> 1. 在 `scripts/test_daily_loop.py` 增加 G7：对临时副本调用 `inject_quiz_placeholder` 两次，断言第一次返回 True、第二次返回 False 且文件 sha256 不变；断言注入后文本含 `articleId: '<slug>'` 且花括号配平。
> 2. 运行 `python -X utf8 scripts/test_daily_loop.py` 验证失败（RED）。
> 3. 实现 `inject_quiz_placeholder` / `--draft-url` / `--admit-source`。
> 4. 用 fixture URL 实跑 `pnpm curate:draft <url>`，随后运行 `pnpm check` 确认注入未破坏 TS 语法；完成后回滚临时产物。
> 5. 运行 `python -X utf8 scripts/test_daily_loop.py && pnpm check` 验证全绿（GREEN）。
> Return: 物理执行凭据（两次注入返回值 + sha256 + `pnpm check` 退出码）。"

**Step Breakdown:**
- [ ] **Step 1: Write the failing test (RED)**：G7 幂等注入断言。
- [ ] **Step 2: Run test and verify it fails with expected message**。
- [ ] **Step 3: Implement minimal production code (GREEN)**：三个 CLI 分支。
- [ ] **Step 4: Run tests and verify all green**：含 `pnpm check` 语法安全验证。
- [ ] **Step 5: Refactor & Flatten with guard clauses (REFACTOR)**。
- [ ] **Step 6: Physical Evidence Gate**。
- [ ] **Step 7: Git atomic commit**：`git commit -m "feat(curate): 草稿生成同步注入速测题占位并新增信源准入CLI"`。

> **Task-9 验收后遗留项（Checker 提出；M2 AFK 部分已完成，以下 3 项为可选加固，不阻断 Task-10 准入）**：
> - **E1（真实隐患，建议优先）**：`--draft-url` 的候选 URL **未做规范化**（发现路径 `_build_discovered` 做了 `split("#")[0].rstrip("/")`，而草稿路径 `_build_draft_candidate` 未做），且 `run_draft_url` **未比对已发布文章 URL** ⇒ 同一 URL 二次 `--draft-url` 可能：(a) 台账出现两条同 url 条目（破坏「url 全局唯一」不变量）；(b) 因 slug 重名改尾缀而**新建第二篇同源 MDX**。**落点：Task-10 准入后首次实际使用 `curate:draft` 之前，或作为独立小修**。
> - **E2（断言强度）**：G7 的「花括号配平」为**全文计数**弱断言（非字符串感知、非 TS 解析），门禁内未运行 `pnpm check` ⇒ 无法独立保证注入后 TS 语法合法。**落点：G7 加固（可断言注入点必位于 `DAILY_QUIZZES` 对象体内，或对 temp 副本做结构解析）**。
> - **E3（风格一致性）**：`run_draft_url` 新增路径仍用 `os.path.join`，而同批次新增的 `inject_quiz_placeholder` 已用 `pathlib.Path` ⇒ 与 `[Instinct: Python-Standards]` 不一致。**落点：随 E1 一并收口**。

### Task-10 第 1 步取证实录（2026-09-27，本机出口，**不可作准入证据**）

已执行 `pnpm curate:admit plannedparenthood` 与 `pnpm curate:admit guokr`（命令只读，`sources.json` 零改动，`No-Auto-Approve` 守住）：

| 信源 | `entry_url` | 许可页候选 | 判定 |
|---|---|---|---|
| `plannedparenthood` | HTTP **200**（真实页面，标题 `Sexual Health Topics`） | 5 条候选**全部 404/0**（`/copyright` 明确 404） | **未找到许可页**，需另寻真实路径 |
| `guokr` | HTTP **200** | 5 条候选**全部「✅ 可达」** | **全部为假阳性**（见 F1） |

> - **F1（真实缺陷，建议在正式准入前修复）**：`--admit-source` 的可达性探测**只判 HTTP 状态码**，不追踪重定向后的落地页。果壳对任意路径均 302/重定向回首页，实测 `https://www.guokr.com/this-path-absolutely-does-not-exist-9f3a2b/`、`/copyright`、`/about/policies/publishing/copyright` **三者均返回 200 且最终 URL 全为 `https://www.guokr.com/`、页面长度同为 100153**（即同一首页），但工具输出「✅ 可达」。**风险**：会诱导人工照着「可达」去核，实际看到的是首页而非许可条款 ⇒ **削弱 HITL 闸门有效性**。修复方向：追踪 `response.geturl()`，若最终 URL 等于站点根路径（或页面长度与首页一致）则改判「⚠️ 疑似重定向到首页（非真实许可页）」，不得判为「可达」。
> - **F2（通道缺失）**：仓库 8 个工作流**无一调用 `--admit-source`**，而 `workflow_dispatch` 要求工作流**已存在于默认分支**才能派发 ⇒ 当前**不存在获取 CI 出口证据的通道**。要取得 `verified_by_run` 的 CI run URL，需先新增一个取证工作流（如 `admit-evidence.yml`：`workflow_dispatch` + `source_id` 输入，运行 `curate:admit` 并把输出写入 `$GITHUB_STEP_SUMMARY`）**并推送至 master**。`gh` 已就绪（v2.97.0 / `ROM4n2` / `repo` scope），派发能力具备，仅缺一次推送。

#### F1 修复结果（2026-09-28，已通过独立评审 PASS）

- **根因**：`fetch_url()` 在 `with urllib.request.urlopen(...) as resp:` 内只返回 `resp.status, resp.read()`，**丢弃 `resp.geturl()`**；urllib 默认跟随重定向 ⇒ 状态码恒为落地页的 200，重定向目标被静默吞掉。
- **修法**：新增 `_http_get(url)->(status, body, final_url)` / `_url_key(url)` / `probe_page(url, site_root, root_length)->dict`；`fetch_url` 退化为**保持二元组契约**的薄包装（6 处既有解包点零漂移）；`run_admit_source` 改三态渲染（`real` / `redirect_home` / `unreachable`）；草案 `license_url` **只取首个 `real` 候选**，无 real 则置空并提示人工补充（**堵住「假 URL 进产出物」的第二处泄漏**）。
- **收口（F1b）**：评审指出「二次指纹」判据在生产态**恒不触发**（`run_admit_source` 从不传 `root_length`，仅测试激活 = 假绿）⇒ 已接线为**复用 ① 循环中 `base_url` 探测响应的 `content_length`**（**零新增网络请求**）；`redirected` 由原始字符串比较改为 `_url_key` 归一化比较；并新增**经 `run_admit_source` 端到端**的断言专防此类假绿。
- **实测**：`pnpm curate:admit guokr` ⇒ 5 候选全部「⚠️ 疑似重定向到首页（非真实许可页）」+ `落地 https://www.guokr.com/` + `len=100153`，草案 `license_url` 为空；`plannedparenthood` ⇒ 5 候选全部 `HTTP 404`，草案为空；`sources.json` 零改动。
- **已知局限（未修，非阻断）**：① **软 404 漏检**——站点把不存在路径重定向到「非站点根的统一友好页」时会误判为 `real`；② `_url_key` 未归一化默认端口（`:443`/`:80`）与 userinfo；③ **发现链路（anchor/sitemap/feed）仍全走 `fetch_url`，未接入重定向检测** ⇒ 配置的 `discovery.url` 若被重定向到首页，只会在 feed 解析失败时以「XML 解析失败」的**误导性告警**暴露（真实根因被掩盖）；④ `LICENSE_PATH_CANDIDATES` 为美国站点口径，对 PP/guokr 真实条款页覆盖不足。

#### F1 修复后对两个新信源的重新判定（**直接改变 Task-10 决策依据**）

用修复后的判定重新核查 `discovery.url`：

| 信源 | `discovery.url` | 实测 | 判定 |
|---|---|---|---|
| `guokr` | `https://www.guokr.com/feed/` | **HTTP 200 但落地 `https://www.guokr.com/`（len=100153）** | **该 feed 实际不存在**——设计阶段「`/feed/` = 200 ⇒ 适用 feed 模式」的记录**本身就是 F1 假阳性的产物**。当前配置在该模式下会抓回首页 HTML ⇒ `_parse_feed` 抛 `ParseError` ⇒ 打印「feed XML 解析失败，降级到 anchor 模式」（**有显式告警，不构成静默空结果**，但告警归因错误、掩盖真实根因）。 |
| `plannedparenthood` | `https://www.plannedparenthood.org/sitemap.xml` | **HTTP 200，`final` 即 sitemap 本身，body 以 `<?xml version="1.0"?><urlset xmlns=...` 开头** | **真实 sitemap，配置有效**（sitemap 发现模式可用）。 |

**据此对 Task-10 的建议（待用户裁决，agent 不代办）**：
- **`guokr`：不支持按现配置准入**。应置为 `rejected`，或先由人工重新定位其真实 feed/sitemap 路径后再评估；其「可达」证据来自已修的假阳性。
- **`plannedparenthood`：sitemap 有效但尚不具备准入条件**——许可页 5 个候选全 404（可能因 `LICENSE_PATH_CANDIDATES` 未覆盖其真实 Terms 路径），需人工以 CI 出口定位并阅读真实条款页后自行填 `license`/`license_url`/`status`。

---

### Task 10: 新信源准入与 M2 验收 [Mode: HITL] [Role: Integration Builder]

**Files:**
- Modify: `scripts/sources.json`（按 CI 证据填写至少 1 个新信源的 `admission`）

**Interfaces:**
- Consumes: `curate:admit` 输出、CI run URL、人工阅读许可页结论
- Produces: ≥1 个新信源 `status: "admitted"` 且 `verified_by_run` 非空

**Injected Instincts (Compile-Time Rule Injection):**
- [ ] `[Instinct: CI-Egress-Only]`：准入证据必须来自 CI run（`verified_by_run`），**本机出口结果不可用**（实测 cdc.gov 403 / unesco.org 403 / nhc.gov.cn 412 / scarleteen 与 amaze 000）。
- [ ] `[Instinct: Human-License-Reading]`：`license` 与 `license_url` 必须由人工阅读许可页后填写；无法确认许可 ⇒ 保持 `probing` 或置 `rejected`，**不得推测填值**。
- [ ] `[Instinct: Fail-Closed]`：未完成准入前该信源不得产出任何候选（由 Task 6 的 `is_source_admitted` 保证）。

**Subagent Prompt Scaffold (for /dfs-exec):**
> "Implement Task 10: 新信源准入与 M2 验收.
> Mode: HITL | Role: Integration Builder
> Goal: 至少让 1 个新信源走完准入并进入 admitted，使候选池不再只依赖 WHO 与默沙东。
> Target Files: Modify `scripts/sources.json`。
> HITL 步骤（需人工拍板，不得由 agent 代替）：
> 1. 运行 `pnpm curate:admit plannedparenthood` 与 `pnpm curate:admit guokr`，收集 CI run URL 与可达性证据（若本机执行，evidence 仅作参考，必须补一次 CI 运行）；
> 2. 人工打开许可页阅读条款，判定是否属于「允许非商业教育与链接引用」；
> 3. 由人工填写 `license` / `license_url` / `verified_at` / `verified_by_run`，并将 `status` 置为 `admitted`；
> 4. 运行 `python -X utf8 scripts/test_daily_loop.py && pnpm test` 验证 G4 与全链路全绿；
> 5. 运行 `pnpm curate:pool --limit 40` 验证候选池规模显著超过 48（验收标准）。
> Return: CI run URL + 许可页人工判读结论 + 候选池条数。"

**Step Breakdown:**
- [ ] **Step 1: 运行准入 CLI 收集证据（CI run URL）**。
- [ ] **Step 2: 人工阅读许可页并给出许可判定（HITL 闸门）**。
- [ ] **Step 3: 人工填写 admission 字段并置 admitted**。
- [ ] **Step 4: Run `pnpm test` and verify all green**。
- [ ] **Step 5: 验收候选池规模**：`pnpm curate:pool --limit 40` 输出条数 > 48。
- [ ] **Step 6: Physical Evidence Gate**：CI run URL + 候选池输出片段。
- [ ] **Step 7: Git atomic commit**：`git commit -m "chore(curate): 完成新信源准入并使候选池突破现有48篇上限"`。

---

## 🌫️ Fog of War (Not Yet Specified)

- **CI 出口的真实候选池深度**：本机出口对 cdc.gov / unesco.org / nhc.gov.cn 返回 403/412，无法判断这些权威源在 GitHub Actions 出口的可抓取性——Task 10 的 CI 实测结果才能确定。**在结果出来前不得为这些站点编写 spec 级设计。**
- **Scarleteen / AMAZE 是否可用作「愉悦」分类补源**：本机实测 `000`，无法区分「站点不可达」与「本机网络异常」——依赖 Task 10 的 CI 证据。
- **`sitemap.xml.gz` 支持**：本里程碑明确降级为 anchor 模式；是否有必要引入 gzip 解码取决于 Task 10 中实际准入的信源是否存在该形态。
- **方案 C（内容形态工厂）**：留位。触发条件 = M1/M2 落地并稳定运行后，再评估是否需要从单一知识条目派生多形态内容。

---

## 🚫 Out of Scope

- **全自动发布导读**：项目自身调研已定性为不可行（模板填充 = 信任事故）。
- **AI 自动撰写提炼要点**：人工通读原文重写是信任机制本体，不在自动化范围。
- **日更一篇新长文**：与人工提炼天花板冲突，用户已拍板放弃该新鲜度定义。
- **`sitemap.xml.gz` 解码**、**PWA / newsletter 接入**、**繁体与多语言**、**自定义域名**：均属后续里程碑。
- **引入 requests / bs4 / feedparser 等第三方抓取依赖**：违反零依赖约束。
- **重构既有 26 篇文章正文**、**改动 7 大工具组件行为**：零回归边界。

---

**下一步**：执行前需初始化 vault-exec 台账（`.vault-exec-ledger.json`，10 个 Task）。初始化后使用 `/vault-exec` 按 Frontier 顺序执行；Task 10 为 HITL，需人工闸门。
