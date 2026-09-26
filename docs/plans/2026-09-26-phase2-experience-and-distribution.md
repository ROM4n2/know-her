# Phase 2: 现有体验穿透、本土化校准与视觉分发实施计划 (Implementation Plan)

> **Goal**: 针对专家蜂群审查（`vault-team`）确认的高价值 UX 痛点与本土真实语境需求，实现「决策树 ➔ 工具箱」状态无缝穿透、72h 紧急避孕本土药品可及性校准与 2h 呕吐观察计时器、纯前端原生 Canvas 纸墨长图导出、以及首页高频意图胶囊与医学专有名词轻量悬浮预览。
> **Tech Stack**: Astro 7.3.3 + TypeScript strict + Tailwind CSS v4 (`@tailwindcss/vite`) + 纯原生 HTML5 Canvas 2D API + Python 3.11+ 标准库。
> **Spec Reference**: Multi-Expert Swarm Audit Report (2026-09-26)。
> **Global Constraints**:
> 1. **零第三方重型依赖**：便签长图生成基于纯原生 Canvas 2D，拒绝引入 300KB+ 的 `html2canvas`；
> 2. **零个人隐私收集**：长图绘制完全在本地浏览器内存 Canvas 完成，零数据外发；
> 3. **设计系统铁律**：严格遵循 Academic Modern Editorial 纸墨调色板（`#FAF8F5`, `#15140F`, `#2A2620`, `rose-600`），零原生彩色 Emoji；
> 4. **代码质量与契约测试**：所有改动配备自动化断言并在 `scripts/test_tools.py` 补充契约检验，保持 `pnpm test` 100% 全绿。

---

### Task 1: 决策树与工具箱的 URL 参数状态透传与自动聚焦定位 (Cross-tool State Hand-off) [Role: TDD Builder]

**Files:**
- Modify: `src/data/decisionTree.ts`
- Modify: `src/components/DecisionGuide.astro`
- Modify: `src/pages/tools/index.astro`
- Modify: `scripts/test_tools.py`

**Interfaces:**
- Consumes: `DECISION_TREE` outcomes 数据
- Produces: `DecisionOutcome.directToolLink?: { toolId: string; urlParams: string; buttonText: string };`
- URL Protocol: `/tools/?tool=ec-countdown&hours=12`, `/tools/?tool=coc-remedy`, `/tools/?tool=clinic-memo&complaint=abnormal-uterine-bleeding`

**Subagent Prompt Scaffold (for /vault-exec):**
> "Implement Task 1: 决策树与工具箱的 URL 参数状态透传与自动聚焦定位.
> Goal: 打破决策树与工具箱之间的状态割裂，在决策树行动卡中提供一键直达对应工具的行动按钮，并在工具箱页面自动平滑滚动聚焦与预填参数.
> Target Files:
> - `src/data/decisionTree.ts`
> - `src/components/DecisionGuide.astro`
> - `src/pages/tools/index.astro`
> - `scripts/test_tools.py`
> TDD Steps:
> 1. 在 `scripts/test_tools.py` 中新增断言函数 `validate_cross_tool_handoff`：验证 `tools/index.astro` 包含 `URLSearchParams` 参数解析处理逻辑，且 `decisionTree.ts` 至少有 4 个 outcome 配置了 `directToolLink`（RED）.
> 2. 运行 `python scripts/test_tools.py` 验证失败（Verify RED）.
> 3. 修改 `src/data/decisionTree.ts`：在 `DecisionOutcome` 接口追加 `directToolLink` 可选字段，为 `outcome_ec_under_24h`、`outcome_ec_24_72h`、`outcome_ec_72_120h`、`outcome_missed_week1`、`outcome_bleeding_emergency` 等配置直达参数.
> 4. 修改 `src/components/DecisionGuide.astro`：在结果行动卡区域渲染带单色箭头的 `[ 启动工具 → ]` 直达外链按钮.
> 5. 修改 `src/pages/tools/index.astro`：在客户端 `<script>` 中解析 `new URLSearchParams(window.location.search)`，根据 `tool` 平滑滚动到对应 `#sec-*`，根据 `hours` 初始化倒计时时间，根据 `complaint` 激活门诊主诉 Tab.
> 6. 运行 `python scripts/test_tools.py` 与 `pnpm check` 验证全绿（Verify GREEN）.
> Return: 测试执行输出证据与修改总结."

**Step Breakdown:**
- [ ] **Step 1: Write failing test in `scripts/test_tools.py` (RED)**: 断言跨工具传参处理逻辑与数据字段.
- [ ] **Step 2: Run `python scripts/test_tools.py` (Verify RED)**: 捕获参数解析缺失.
- [ ] **Step 3: Update `src/data/decisionTree.ts` and `src/components/DecisionGuide.astro` (GREEN)**: 注入直达链接.
- [ ] **Step 4: Update `src/pages/tools/index.astro` (GREEN)**: 实现参数接收、平滑滚动与控件自动聚焦预填.
- [ ] **Step 5: Run tests (Verify GREEN)**: 契约测试与 TS 诊断通过.
- [ ] **Step 6: Git atomic commit**: `git add src/ scripts/ && git commit -m "feat(ux): 落地决策树与工具箱的跨工具URL参数透传与自动聚焦定位"`

---

### Task 2: 72h 紧急避孕本土药品指南校准与 2h 服药吸收观察计时器 (Local EC & Vomit Observation Timer) [Role: TDD Builder]

**Files:**
- Modify: `src/components/tools/EmergencyCountdown.astro`
- Modify: `scripts/test_tools.py`

**Interfaces:**
- Consumes: 本土真实医药可及性数据（左炔诺孕酮 OTC vs 乌利司他国内零售未普及现状）
- Produces: 72h/120h 卡片本土真实用药指引；2 小时服药胃部观察计时器交互模块 (`#ec-vomit-timer-container`)

**Subagent Prompt Scaffold (for /vault-exec):**
> "Implement Task 2: 72h 紧急避孕本土药品指南校准与 2h 服药吸收观察计时器.
> Goal: 校准紧急避孕国内 OTC/处方可及性，消除乌利司他买不到的恐慌，并落地 2 小时胃部观察计时器.
> Target Files:
> - `src/components/tools/EmergencyCountdown.astro`
> - `scripts/test_tools.py`
> TDD Steps:
> 1. 在 `scripts/test_tools.py` 中新增断言：检查 `EmergencyCountdown.astro` 包含 `ec-vomit-timer-container` 容器及左炔诺孕酮 OTC 本土化提示，且不鼓励盲目检索乌利司他（RED）.
> 2. 运行 `python scripts/test_tools.py` 验证失败（Verify RED）.
> 3. 更新 `EmergencyCountdown.astro` 文案：
>    - 72h 窗口：标注左炔诺孕酮为首选 OTC（1.5mg 单片装如金毓婷，或 0.75mg 双片装间隔 12h），各大药房及外卖平台 24h 随时可及；
>    - 120h 窗口：明确指出国内零售药房暂未普及醋酸乌利司他，切勿盲目检索延误黄金时效；次选为医院急诊处方低剂量米非司酮 (10mg/25mg) 或急诊放置含铜 IUD.
> 4. 在 `EmergencyCountdown.astro` 中增加「服药后 2 小时胃部吸收观察计时器」交互组件：
>    - 提供 `[ 💊 我已服药，开启 2 小时吸收观察计时 ]` 按钮；
>    - 启动后以倒计时形式展示剩余时间（120:00 -> MM:SS）；
>    - 明确循证说明：服药后 2 小时内若呕吐必须补服原剂量；超过 2 小时药物已充分吸收，无需重复补服；
>    - 提供重置按钮与到期后的安心提示.
> 5. 运行 `python scripts/test_tools.py` 与 `pnpm check` 验证全绿（Verify GREEN）.
> Return: 测试执行证据与组件截图/输出."

**Step Breakdown:**
- [ ] **Step 1: Write failing test in `scripts/test_tools.py` (RED)**: 针对计时器容器与用药文案断言.
- [ ] **Step 2: Run `python scripts/test_tools.py` (Verify RED)**: 捕获组件缺失元素.
- [ ] **Step 3: Update `EmergencyCountdown.astro` with localized advice and 2h timer (GREEN)**.
- [ ] **Step 4: Run tests (Verify GREEN)**: 契约测试通过.
- [ ] **Step 5: Code Review & Refactor**: 确保计时器使用 `setInterval` 安全管理，且无内存泄漏.
- [ ] **Step 6: Git atomic commit**: `git add src/components/tools/ scripts/test_tools.py && git commit -m "feat(tools): 落地72h紧急避孕本土药品可及性校准与2小时服药吸收观察计时器"`

---

### Task 3: 纯前端零依赖 Canvas 纸墨质感便签长图导出器 (Editorial Canvas Memo Exporter) [Role: TDD Builder]

**Files:**
- Create: `src/lib/ui/memoImageExporter.ts`
- Modify: `src/components/tools/ClinicMemo.astro`
- Modify: `src/components/tools/PositionAndIntimacyGuide.astro`
- Modify: `scripts/test_tools.py`

**Interfaces:**
- Produces: `export function exportMemoAsImage(options: MemoExportOptions): Promise<void>` in `src/lib/ui/memoImageExporter.ts`
- Consumes: SOAP 格式门诊主诉数据、Yes/No/Maybe 亲密沟通便签数据

**Subagent Prompt Scaffold (for /vault-exec):**
> "Implement Task 3: 纯前端零依赖 Canvas 纸墨质感便签长图导出器.
> Goal: 解决移动端微信无法调用 window.print() 及长文本复制格式碎裂的问题，纯前端通过原生 Canvas 2D 导出 Academic Modern Editorial 纸墨风格高质感长图卡片.
> Target Files:
> - `src/lib/ui/memoImageExporter.ts` (新建)
> - `src/components/tools/ClinicMemo.astro`
> - `src/components/tools/PositionAndIntimacyGuide.astro`
> - `scripts/test_tools.py`
> TDD Steps:
> 1. 在 `scripts/test_tools.py` 中新增断言：检查 `memoImageExporter.ts` 存在并导出 `exportMemoAsImage`，且 `ClinicMemo.astro` 与 `PositionAndIntimacyGuide.astro` 均包含保存长图按钮 `memo-export-image-btn`（RED）.
> 2. 运行 `python scripts/test_tools.py` 验证失败（Verify RED）.
> 3. 创建 `src/lib/ui/memoImageExporter.ts`：
>    - 使用纯原生 Canvas 2D API 动态排版文本行（实现自动折行计算与多段间距）；
>    - 绘制温润纸白背景 `#FAF8F5`、实体墨框 `#15140F` (2px)、顶部双线印章徽标 `[ know-her · 离线健康决策便签 ]`；
>    - 绘制结构化栏目标题（rose-600）与正文内容（#2A2620），底部绘制免责声明标牌与生成时间戳；
>    - DPR 设为 2.0 保证高清视网膜显示；
>    - 调用 `canvas.toBlob('image/png')`，支持触发下载或弹层长按保存.
> 4. 在 `ClinicMemo.astro` 和 `PositionAndIntimacyGuide.astro` 底部操作栏接入 `[ 🖼️ 保存便签长图 ]` 按钮，绑定导出逻辑.
> 5. 运行 `python scripts/test_tools.py` 与 `pnpm check` 验证全绿（Verify GREEN）.
> Return: 测试执行证据与导出器实现清单."

**Step Breakdown:**
- [ ] **Step 1: Write failing test in `scripts/test_tools.py` (RED)**.
- [ ] **Step 2: Run `python scripts/test_tools.py` (Verify RED)**.
- [ ] **Step 3: Implement `src/lib/ui/memoImageExporter.ts` (GREEN)**.
- [ ] **Step 4: Integrate export buttons into `ClinicMemo.astro` and `PositionAndIntimacyGuide.astro` (GREEN)**.
- [ ] **Step 5: Run tests (Verify GREEN)**.
- [ ] **Step 6: Git atomic commit**: `git add src/ scripts/ && git commit -m "feat(ui): 落地纯前端原生Canvas纸墨风格就诊与伴侣便签长图导出器"`

---

### Task 4: 首页突发场景意图搜索胶囊与长文医学名词 In-situ Tooltip 悬浮预览 (Search Intent Pills & Glossary Popover) [Role: TDD Builder]

**Files:**
- Modify: `src/components/Search.astro`
- Modify: `src/pages/articles/[id].astro`
- Modify: `scripts/test_tools.py`

**Interfaces:**
- Consumes: 突发场景关键词、`glossary` 医学词典数据
- Produces: 首页 6 大高频意图胶囊；长文详情页顶部医学名词速查徽章与原地极简定义预览

**Subagent Prompt Scaffold (for /vault-exec):**
> "Implement Task 4: 首页突发场景意图搜索胶囊与长文医学名词 In-situ Tooltip 悬浮预览.
> Goal: 降低口语化突发恐慌用户的搜索摩擦，并在文章阅读心流中提供无需跳出的医学术语即时释义.
> Target Files:
> - `src/components/Search.astro`
> - `src/pages/articles/[id].astro`
> - `scripts/test_tools.py`
> TDD Steps:
> 1. 在 `scripts/test_tools.py` 中新增断言：检查 `Search.astro` 包含高频场景胶囊容器 `search-intent-pills`，且 `articles/[id].astro` 包含术语速查微标签（RED）.
> 2. 运行 `python scripts/test_tools.py` 验证失败（Verify RED）.
> 3. 在 `src/components/Search.astro` 搜索框下方新增一组高频突发场景意图胶囊：
>    - `[ 避孕套滑脱破损 ]` (直达决策树)
>    - `[ 紧急避孕72h倒计时 ]` (直达工具箱)
>    - `[ 漏服短效口服药 ]` (直达工具箱)
>    - `[ 异常褐血与月经紊乱 ]` (直达自测工具)
>    - `[ 同房疼痛与痉挛 ]` (直达科普词条)
>    - `[ 怎么跟医生讲主诉 ]` (直达问诊小抄)
> 4. 在 `src/pages/articles/[id].astro` 顶部元数据区下方，渲染关联医学名词的速查微胶囊，鼠标悬浮（或轻触）通过标准 HTML `title` 属性或轻量 CSS 原生 Popover 展现 80 字内纯净定义与出处，不打断阅读心流.
> 5. 运行 `python scripts/test_tools.py` 与 `pnpm check` 验证全绿（Verify GREEN）.
> Return: 变更摘要与测试输出."

**Step Breakdown:**
- [ ] **Step 1: Write failing test in `scripts/test_tools.py` (RED)**.
- [ ] **Step 2: Run `python scripts/test_tools.py` (Verify RED)**.
- [ ] **Step 3: Update `Search.astro` with intent pills (GREEN)**.
- [ ] **Step 4: Update `articles/[id].astro` with inline glossary popovers (GREEN)**.
- [ ] **Step 5: Run tests (Verify GREEN)**.
- [ ] **Step 6: Git atomic commit**: `git add src/ scripts/ && git commit -m "feat(ux): 落地首页突发场景意图胶囊与科普详情页医学术语悬浮速查"`

---

### Task 5: 实用工具箱与全站全流水线回归核验 (Full Regression & Gate Verification) [Role: Integration Builder]

**Files:**
- Test all: `pnpm check && pnpm test:graph && pnpm curate:check && pnpm build`

**Interfaces:**
- Consumes: 全站 35 个静态路由、7 大交互工具、决策树与词典
- Produces: 100% 通过的 CI 全链路门禁报告与 Pagefind 索引更新

**Subagent Prompt Scaffold (for /vault-exec):**
> "Implement Task 5: 实用工具箱与全站全流水线回归核验.
> Goal: 验证 Phase 2 所有 4 大任务改动无任何回归缺陷，全站静态生成无报错，零 Emoji 违规，零 innerHTML 违规.
> Target: 执行全套验证套件并生成审计总结.
> 验证命令：
> 1. `python scripts/test_decision_tree.py`
> 2. `python scripts/test_glossary.py`
> 3. `python scripts/test_tools.py`
> 4. `python scripts/test_article_hygiene.py`
> 5. `python scripts/test_security_contracts.py`
> 6. `pnpm check`
> 7. `pnpm curate:check`
> 8. `pnpm build`
> 9. `pnpm test`
> Return: 完整流水线测试执行证据与 35 个页面打包凭据."

**Step Breakdown:**
- [ ] **Step 1: Run all Python contract tests (Verify GREEN)**.
- [ ] **Step 2: Run Astro type check `pnpm check` (Verify GREEN)**.
- [ ] **Step 3: Run curate schema check `pnpm curate:check` (Verify GREEN)**.
- [ ] **Step 4: Run full static build `pnpm build` (Verify GREEN)**.
- [ ] **Step 5: Run complete CI command `pnpm test` (Verify GREEN)**.
- [ ] **Step 6: Git summary & finalize ledger**.

---
