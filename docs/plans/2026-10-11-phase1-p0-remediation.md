# P0 高危缺陷与交互阻断系统性加固实施计划 (Phase 1 P0 Remediation Plan)

> **Goal**: 依据蜂群审查共识报告，系统性修复 5 大已确认的 P0 核心缺陷（移动端双指缩放劫持、悬浮对比栏遮挡、外网探测阻断生产部署、SW 预缓存离线白屏、漏服短效药决策树与计算器临床指引矛盾）与 2 项核心 P1（隐私记录清除修复、全站零 innerHTML 与零 Emoji 测试门禁全覆盖）。
> **Tech Stack**: Astro 7.3.3 + TypeScript strict + Tailwind CSS v4 + Python 3.11 标准库 + GitHub Actions。
> **Spec Reference**: `docs/audit/` 蜂群审查全景报告与反证核验确认清单。
> **Global Constraints**:
> 1. **Zero-PII & Zero-Breakage**：所有修复必须通过全量测试套件 `pnpm test`（类型检查 + 9 套契约门禁 + 策展校验 + 静态编译）；
> 2. **设计系统铁律**：Academic Modern Editorial 纸墨调色板（`#FAF8F5`, `#15140F`），坚决杜绝原生彩色 Emoji 与 `innerHTML`；
> 3. **Maker-Checker 铁律**：主线程仅负责状态机与提交，代码修改经由隔离子代理与独立 Reviewer 审核合入。

---

## 🏛️ Decisions So Far

- [D40]: 废除 `PanicExit.astro` 中粗暴的全局双指触碰 `touchstart` 劫持，改用双击悬浮按钮或专用 3 指特定手势，无障碍保留原生双指缩放。
- [D41]: `ContraceptionMatrix.astro` 移动端悬浮条由 `bottom-20` 上移至 `bottom-24`（或防窥按钮上浮），彻底消除与对比按钮的点击穿透重叠。
- [D42]: `.github/workflows/deploy.yml` 剥离实时外部网络探针 `curate:links`，或配置软失败容错，将实时外网健康度监控收敛至定时巡检 `daily-routine.yml` 与 PR 门禁。
- [D43]: 优化 `sw.js` 离线急救资源策略，构建时或请求拦截中稳健兜底离线 CSS/JS 资源，并在离线导航降级时明确展示离线急救横幅。
- [D44]: `CocRemedyCalculator.astro` 细化漏服天数维度（区分漏服 1 天 vs 漏服 >=2 天），与 `decisionTree.ts` 临床结论完全对齐。
- [D45]: `privacy.astro` 遍历 `localStorage` 动态清洗 `know_her_last_date` 与 `know_her_last_quiz_*` 全量历史打卡键。
- [D46]: `test_article_hygiene.py` 门禁范围扩展至 `src/pages/**/*.astro`、`src/layouts/**/*.astro` 与 `src/content/articles/*.mdx` 全量 Emoji 扫描。

---

## 🎯 Active Frontier (Unblocked Tasks)

### Task 1: 移动端手势冲突与悬浮对比栏物理遮挡修复 [Mode: AFK] [Role: TDD Builder]

**Files:**
- Modify:
  - `src/components/PanicExit.astro:315-322` (移除或替换双指 touchstart 监听)
  - `src/components/tools/ContraceptionMatrix.astro:434` (调整悬浮 bar 位置)
  - `scripts/test_tools.py` (增加防遮挡与手势安全测试断言)

**Interfaces:**
- Consumes: `PanicExit` touch event handler, `ContraceptionMatrix` floating bar layout
- Produces: 允许移动端原生双指自由缩放，悬浮对比按钮在移动端 100% 可正常点击且不被遮挡

**Subagent Prompt Scaffold (for /dfs-exec):**
> "Implement Task 1: 移动端手势冲突与悬浮对比栏物理遮挡修复.
> Mode: AFK | Role: TDD Builder
> Goal: 修复 P0-1（双指缩放误触防窥）与 P0-2（防窥按钮遮挡对比栏）.
> Target Files:
> - Modify `src/components/PanicExit.astro`
> - Modify `src/components/tools/ContraceptionMatrix.astro`
> - Modify `scripts/test_tools.py`
> Steps:
> 1. 在 `scripts/test_tools.py` 中增加断言：确保 `PanicExit.astro` 不存在粗暴的 `e.touches.length >= 2` 无位移监听，确保 `ContraceptionMatrix.astro` 的 floating bar 类名避开 `bottom-20`（调整为 `bottom-24` 或自适应偏移）；
> 2. 运行 `python -X utf8 scripts/test_tools.py` 验证因未修改而报错（RED）；
> 3. 在 `src/components/PanicExit.astro` 中：移除双指 `touchstart` 劫持代码，仅保留双击 `Esc` 键、反引号键以及点击悬浮按钮唤起防窥；
> 4. 在 `src/components/tools/ContraceptionMatrix.astro` 中：将 `.matrix-floating-bar` 调整为 `bottom-24 sm:bottom-6`，彻底避开右下角 `bottom-20` 处的防窥按钮；
> 5. 运行 `python -X utf8 scripts/test_tools.py` 与 `pnpm check` 验证全绿（GREEN）.
> Return: Summary with MANDATORY Physical Execution Receipt. Do NOT run git commit."

---

### Task 2: 解耦生产部署与外部第三方网络依赖 [Mode: AFK] [Role: TDD Builder]

**Files:**
- Modify:
  - `.github/workflows/deploy.yml` (解除外部不可控网络对生产部署的硬阻断)
  - `scripts/test_security_contracts.py` (断言 deploy.yml 的发布弹性契约)

**Interfaces:**
- Consumes: GitHub Actions runner lifecycle
- Produces: 允许生产部署流程在外部医学门户宕机时依然平稳上线本地静态产物与安全补丁

**Subagent Prompt Scaffold (for /dfs-exec):**
> "Implement Task 2: 解耦生产部署与外部第三方网络依赖.
> Mode: AFK | Role: TDD Builder
> Goal: 修复 P0-3（外部网络故障阻塞发布）.
> Target Files:
> - Modify `.github/workflows/deploy.yml`
> - Modify `scripts/test_security_contracts.py`
> Steps:
> 1. 在 `scripts/test_security_contracts.py` 中增加断言：确保 `deploy.yml` 中的外链巡检步骤具备 `continue-on-error: true` 或分离至 CI 异步检测，确保生产构建部署不会因外部网络抖动中断；
> 2. 运行 `python -X utf8 scripts/test_security_contracts.py` 验证断言（RED）；
> 3. 修改 `.github/workflows/deploy.yml`：保留 `pnpm curate:check`（本地 frontmatter 语法格式强校验），为 `pnpm curate:links` 步骤配置 `continue-on-error: true`（或仅在 CI/daily 中做阻断），并输出警告日志；
> 4. 运行 `python -X utf8 scripts/test_security_contracts.py` 验证全绿（GREEN）.
> Return: Summary with MANDATORY Physical Execution Receipt. Do NOT run git commit."

---

### Task 3: 消除短效药漏服决策树与计算器的临床指引矛盾 [Mode: AFK] [Role: TDD Builder]

**Files:**
- Modify:
  - `src/components/tools/CocRemedyCalculator.astro` (重构漏服时间/片数选择与医学建议)
  - `src/data/decisionTree.ts` (核对与对齐选项文案与跳转参数)
  - `scripts/test_tools.py` (增加临床建议一致性测试)

**Interfaces:**
- Consumes: WHO MEC / CDC SPR 短效药漏服处置标准
- Produces: 漏服 1 天（漏服 1 片）明确输出“立即补服，避孕效果依然可靠，无需额外戴套 7 天”，漏服 >=2 天输出“补服+严格戴套 7 天+评估紧急避孕”，彻底消灭两个急救入口的矛盾冲突

**Subagent Prompt Scaffold (for /dfs-exec):**
> "Implement Task 3: 消除短效药漏服决策树与计算器的临床指引矛盾.
> Mode: AFK | Role: TDD Builder
> Goal: 修复 P0-5（临床处置指引矛盾）.
> Target Files:
> - Modify `src/components/tools/CocRemedyCalculator.astro`
> - Modify `scripts/test_tools.py`
> Steps:
> 1. 在 `scripts/test_tools.py` 中增加断言：确保 `CocRemedyCalculator.astro` 包含针对“仅漏服 1 片（<24h 或漏服 1 天）”的专门选项与指引，且其建议明确标注“常规无需额外加用避孕套”；
> 2. 运行 `python -X utf8 scripts/test_tools.py` 确认失败（RED）；
> 3. 重构 `CocRemedyCalculator.astro` 的选项：将“超过 12 小时”拆分为“漏服 1 天（1 片，延迟 12~24 小时）”与“连续漏服 2 天或以上（>=2 片）”，在第一周仅漏服 1 片时与决策树完全对齐（立即补服，无需慌张，避孕效果依然可靠）；
> 4. 运行 `python -X utf8 scripts/test_tools.py` 与 `pnpm check` 验证全绿（GREEN）.
> Return: Summary with MANDATORY Physical Execution Receipt. Do NOT run git commit."

---

### Task 4: 修复隐私协议页本地做题打卡记录清除漏洞 [Mode: AFK] [Role: TDD Builder]

**Files:**
- Modify:
  - `src/pages/privacy.astro` (完善本地 localStorage 遍历与清除)
  - `scripts/test_security_contracts.py` (增加隐私清除契约断言)

**Interfaces:**
- Consumes: `DailyCard.astro` localStorage 命名规范 (`know_her_last_date`, `know_her_last_quiz_*`, `know_her_streak`)
- Produces: 点击清除按钮后 100% 抹除真实打卡状态与做题记录

**Subagent Prompt Scaffold (for /dfs-exec):**
> "Implement Task 4: 修复隐私协议页本地做题打卡记录清除漏洞.
> Mode: AFK | Role: TDD Builder
> Goal: 修复 P1-1（隐私记录清除失效）.
> Target Files:
> - Modify `src/pages/privacy.astro`
> - Modify `scripts/test_security_contracts.py`
> Steps:
> 1. 在 `scripts/test_security_contracts.py` 中增加断言：检验 `privacy.astro` 脚本是否正确清除了 `know_her_last_date`、`know_her_streak`、以及通过循环/正则清除所有以 `know_her_last_quiz_` 开头的键；
> 2. 运行 `python -X utf8 scripts/test_security_contracts.py` 验证失败（RED）；
> 3. 修改 `src/pages/privacy.astro` 中的清除逻辑，动态遍历 `Object.keys(localStorage)`，清除所有包含 `know_her_` 前缀的打卡、速测与偏好键名；
> 4. 运行 `python -X utf8 scripts/test_security_contracts.py` 与 `pnpm check` 验证全绿（GREEN）.
> Return: Summary with MANDATORY Physical Execution Receipt. Do NOT run git commit."

---

### Task 5: 全站零 innerHTML 与零 Emoji 测试门禁覆盖加固 [Mode: AFK] [Role: TDD Builder]

**Files:**
- Modify:
  - `scripts/test_article_hygiene.py` (全量扫描 pages/layouts 及 articles/*.mdx)

**Interfaces:**
- Consumes: 全站代码库与文章内容
- Produces: 自动化防线杜绝未来任何在 pages/layouts 中的 innerHTML 违规，以及 articles 正文中的 Emoji 渗入

**Subagent Prompt Scaffold (for /dfs-exec):**
> "Implement Task 5: 全站零 innerHTML 与零 Emoji 测试门禁覆盖加固.
> Mode: AFK | Role: TDD Builder
> Goal: 修复 P1-3（门禁盲区）.
> Target Files:
> - Modify `scripts/test_article_hygiene.py`
> Steps:
> 1. 扩展 `verify_zero_inner_html()`：扫描范围由 `src/components/` 扩展至 `src/**/*.{astro,ts,js}`，同时匹配 `.innerHTML` 与 `['innerHTML']` / `[\"innerHTML\"]`；
> 2. 新增 `verify_zero_emoji_content()`：对全量 `src/content/articles/*.mdx` 和 `src/content/glossary/*.md` 实施 `EMOJI_PATTERN` 扫描，一旦发现原生彩色 Emoji 立即报错并点名文件与行号；
> 3. 运行 `python -X utf8 scripts/test_article_hygiene.py` 验证全绿（GREEN）；
> 4. 验证全站现有 32 篇文章与所有页面零违规.
> Return: Summary with MANDATORY Physical Execution Receipt. Do NOT run git commit."

---

### Task 6: P0/P1 加固里程碑全量回归与工作记忆结项 [Mode: HITL] [Role: Integration Builder]

**Files:**
- Modify: `WORKMEMORY/PROJECT_OVERVIEW.md`
- Modify: `WORKMEMORY/work.log`
- Modify: `.vault-exec-ledger.json`

**Interfaces:**
- Consumes: 修复后的全站交互组件、部署配置与自动化测试套件
- Produces: 100% 通过的 CI 全量构建产物与更新后的工作记忆

**Step Breakdown:**
- [ ] **Step 1: Run full CI regression `pnpm test` (Verify GREEN)**
- [ ] **Step 2: Update `WORKMEMORY/PROJECT_OVERVIEW.md`**
- [ ] **Step 3: Append `WORK_END` event to `WORKMEMORY/work.log`**
- [ ] **Step 4: Finalize ledger `.vault-exec-ledger.json` to 6/6 completed**
- [ ] **Step 5: Git atomic commit & push**
