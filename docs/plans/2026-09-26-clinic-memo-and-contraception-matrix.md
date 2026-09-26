# 门诊就诊沟通便签与全品类避孕决策矩阵实施计划 (Implementation Plan)

> **Goal**: 落地两大高杠杆纯前端离线医疗与健康决策工具（`ClinicMemo.astro` 与 `ContraceptionMatrix.astro`），扩充 `/tools/` 工具箱至 6 大工具矩阵，建立全自动化契约测试与外键门禁。
> **Tech Stack**: Astro 7.3.3 + TypeScript strict + Tailwind CSS v4 (`@tailwindcss/vite`) + Python 3.11+ 标准库测试脚本。
> **Spec Reference**: `docs/specs/2026-09-26-clinic-memo-and-contraception-matrix-design.md`。
> **Global Constraints**:
> 1. **零个人隐私收集**：工具完全运行于前端 DOM 交互，零服务端通信，不向 localStorage 写入敏感就诊病史；
> 2. **设计系统约束**：严格遵循 Academic Modern Editorial 纸墨调色（`#FAF8F5` 底、`#15140F` 墨、`#F43F5E` 强调），去除原生系统彩色 Emoji，使用单色语义 SVG 与文本排版符号；
> 3. **文章整洁度与外键隔离**：组件中引用的 `related_article` 必须在 `src/content/articles/*.mdx` 真实存在，受 `scripts/test_tools.py` 自动化拦截；
> 4. **无障碍与打印适配**：就诊便签必须配备标准 `@media print` 打印优化样式。

---

### Task 1: 避孕全景数据与就诊问诊知识库契约 (Data Layer & TDD Contract) [Role: TDD Builder]

**Files:**
- Create: `src/data/contraceptionMethods.ts`
- Create: `src/data/clinicQuestions.ts`
- Modify: `scripts/test_tools.py:15-30,45-65`

**Interfaces:**
- Produces:
  - `export const CONTRACEPTION_METHODS: ContraceptionMethod[]` in `src/data/contraceptionMethods.ts`
  - `export const CLINIC_SYMPTOM_CONFIGS: SymptomConfig[]` in `src/data/clinicQuestions.ts`
  - `export const RED_FLAG_SYMPTOMS: RedFlagItem[]` in `src/data/clinicQuestions.ts`
- Consumes:
  - 现存科普文章 slug：`contraception-condoms`, `contraception-oral-pills`, `contraception-iud-guide`, `contraception-emergency-pill`, `abnormal-uterine-bleeding`, `body-dysmenorrhea`, `body-bacterial-vaginosis`, `body-vaginal-yeast-infection`, `pleasure-dyspareunia-pain`

**Subagent Prompt Scaffold (for /vault-exec):**
> "Implement Task 1: 避孕全景数据与就诊问诊知识库契约.
> Goal: 建立包含 10 种现代避孕方式结构化数据与妇科 4 大主诉就诊知识库，并编写自动化测试契约.
> Target Files:
> - Modify: `scripts/test_tools.py`
> - Create: `src/data/contraceptionMethods.ts`
> - Create: `src/data/clinicQuestions.ts`
> TDD Steps:
> 1. 在 `scripts/test_tools.py` 中增加对 `contraceptionMethods.ts` 10 大避孕方式与 `clinicQuestions.ts` 4 大主诉契约的验证（RED）.
> 2. 运行 `python scripts/test_tools.py` 并确认因数据文件未创建而如期报错（Verify RED）.
> 3. 创建 `src/data/contraceptionMethods.ts` 与 `src/data/clinicQuestions.ts`，填入 WHO MEC 标准数据与外键关联（GREEN）.
> 4. 再次运行 `python scripts/test_tools.py`，确认数据结构与外键验证全部通过（Verify GREEN）.
> 5. 使用卫语句扁平化处理逻辑，保证类型定义严谨无 any（REFACTOR）.
> Return: 测试执行输出证据与数据模型导出清单."

**Step Breakdown:**
- [ ] **Step 1: Write failing test in `scripts/test_tools.py` (RED)**: 增加对两个 TS 数据文件的解析、数组长度检查（≥10 种避孕法、4 大主诉）与外键存在性校验。
- [ ] **Step 2: Run `python scripts/test_tools.py` (Verify RED)**: 验证控制台如期捕获缺失文件或未定义错误。
- [ ] **Step 3: Implement `src/data/contraceptionMethods.ts` & `src/data/clinicQuestions.ts` (GREEN)**: 编写完整 TypeScript 接口与只读常量数组。
- [ ] **Step 4: Run `python scripts/test_tools.py` (Verify GREEN)**: 验证测试全绿。
- [ ] **Step 5: Code Review & Refactor (REFACTOR)**: 确保所有字段无拼写错误，无未导出类型。
- [ ] **Step 6: Git atomic commit**: `git add scripts/test_tools.py src/data/ && git commit -m "feat(data): 落地避孕全景数据与就诊问诊知识库契约"`

---

### Task 2: 门诊就诊沟通备忘录小抄生成器组件 (ClinicMemo.astro) [Role: TDD Builder]

**Files:**
- Create: `src/components/tools/ClinicMemo.astro`
- Modify: `scripts/test_tools.py:15-25`

**Interfaces:**
- Consumes:
  - `src/data/clinicQuestions.ts` (`CLINIC_SYMPTOM_CONFIGS`, `RED_FLAG_SYMPTOMS`)
  - `src/styles/global.css` (Paper & Ink tokens)
- Produces:
  - `<ClinicMemo />` Astro 自包含交互组件，包含客户端表单、急腹症拦截、响应式排版小抄卡、一键纯文本复制、`@media print` 样式。

**Subagent Prompt Scaffold (for /vault-exec):**
> "Implement Task 2: 门诊就诊沟通备忘录小抄生成器组件 (ClinicMemo.astro).
> Goal: 开发纯前端无状态就医沟通便签小抄生成器，支持 4 大主诉切换、经期避孕史快填、急腹症红旗预警与便签复制/打印.
> Target Files:
> - Modify: `scripts/test_tools.py` (加入 REQUIRED_COMPONENTS: 'ClinicMemo.astro' 与关键 DOM token)
> - Create: `src/components/tools/ClinicMemo.astro`
> TDD Steps:
> 1. 在 `scripts/test_tools.py` 的 REQUIRED_COMPONENTS 中追加 `('ClinicMemo.astro', ['clinic-memo-container', 'clinic-copy-btn', 'abnormal-uterine-bleeding'])` (RED).
> 2. 运行 `python scripts/test_tools.py`，确认报错提示 `组件缺失: ClinicMemo.astro` (Verify RED).
> 3. 实现 `src/components/tools/ClinicMemo.astro`，完成 DOM 结构、原生轻量交互 JS、急腹症红旗拦截、复制功能与打印专用 CSS (GREEN).
> 4. 运行 `python scripts/test_tools.py`，验证通过 (Verify GREEN).
> 5. 检查 UI 规范：全站无彩色 Emoji，纯单色 SVG 图标，实体墨线阴影与按压效果 (REFACTOR).
> Return: 组件实现说明与 `test_tools.py` 通过日志."

**Step Breakdown:**
- [ ] **Step 1: Update `scripts/test_tools.py` contract for ClinicMemo (RED)**: 追加组件存在性与标识 token 门禁要求。
- [ ] **Step 2: Run `python scripts/test_tools.py` (Verify RED)**: 确认组件缺失失败信息。
- [ ] **Step 3: Implement `src/components/tools/ClinicMemo.astro` (GREEN)**:
  - 编写主诉单选卡、末次月经/避孕药具输入框、急腹症多选预警框；
  - 编写实时渲染的 Editorial Note 便签模板；
  - 注入客户端 JS 监听 input/change 事件，实现 0 延迟实时内容响应；
  - 注入 navigator.clipboard 一键复制与 window.print 打印样式。
- [ ] **Step 4: Run `python scripts/test_tools.py` (Verify GREEN)**: 验证通过。
- [ ] **Step 5: Visual & Editorial Refactor (REFACTOR)**: 确认排版符合 Academic Modern Editorial 纸墨美学。
- [ ] **Step 6: Git atomic commit**: `git add scripts/test_tools.py src/components/tools/ClinicMemo.astro && git commit -m "feat(tools): 落地门诊就诊沟通备忘录小抄生成器 (ClinicMemo)"`

---

### Task 3: 全品类现代避孕知情选择与对比矩阵组件 (ContraceptionMatrix.astro) [Role: TDD Builder]

**Files:**
- Create: `src/components/tools/ContraceptionMatrix.astro`
- Modify: `scripts/test_tools.py:15-25`

**Interfaces:**
- Consumes:
  - `src/data/contraceptionMethods.ts` (`CONTRACEPTION_METHODS`)
- Produces:
  - `<ContraceptionMatrix />` Astro 自包含交互组件，包含多维即时筛选、珍珠指数比对卡片网格、双向横向 PK 对比抽屉。

**Subagent Prompt Scaffold (for /vault-exec):**
> "Implement Task 3: 全品类现代避孕知情选择与对比矩阵组件 (ContraceptionMatrix.astro).
> Goal: 开发现代避孕知情选择矩阵，支持 10 种避孕方式珍珠指数对比、标签即时筛选与双选横向 PK 抽屉.
> Target Files:
> - Modify: `scripts/test_tools.py` (加入 REQUIRED_COMPONENTS: 'ContraceptionMatrix.astro' 与关键 DOM token)
> - Create: `src/components/tools/ContraceptionMatrix.astro`
> TDD Steps:
> 1. 在 `scripts/test_tools.py` 的 REQUIRED_COMPONENTS 中追加 `('ContraceptionMatrix.astro', ['matrix-filter-container', 'matrix-card', 'contraception-condoms'])` (RED).
> 2. 运行 `python scripts/test_tools.py`，确认报错提示 `组件缺失: ContraceptionMatrix.astro` (Verify RED).
> 3. 实现 `src/components/tools/ContraceptionMatrix.astro`，完成多维筛选器、卡片网格、典型 vs 完美失败率进度条展示、双选对比弹窗 (GREEN).
> 4. 运行 `python scripts/test_tools.py`，验证通过 (Verify GREEN).
> 5. 校验微交互与移动端触控，确保无原生 Emoji (REFACTOR).
> Return: 组件实现说明与自动化测试输出."

**Step Breakdown:**
- [ ] **Step 1: Update `scripts/test_tools.py` contract for ContraceptionMatrix (RED)**: 追加矩阵组件断言。
- [ ] **Step 2: Run `python scripts/test_tools.py` (Verify RED)**: 确认组件缺失失败信息。
- [ ] **Step 3: Implement `src/components/tools/ContraceptionMatrix.astro` (GREEN)**:
  - 编写顶部多维筛选标签栏（全部/防STI/长效/无激素/改善月经/紧急补救）；
  - 渲染 10 大避孕方式卡片，突出典型年失败率对比与 WHO MEC 核心要点；
  - 编写纯原生客户端 JS 筛选与两两对比（Head-to-head Compare）面板。
- [ ] **Step 4: Run `python scripts/test_tools.py` (Verify GREEN)**: 验证通过。
- [ ] **Step 5: Code Review & Polish (REFACTOR)**: 确认移动端响应式布局流畅。
- [ ] **Step 6: Git atomic commit**: `git add scripts/test_tools.py src/components/tools/ContraceptionMatrix.astro && git commit -m "feat(tools): 落地全品类现代避孕知情选择与对比矩阵 (ContraceptionMatrix)"`

---

### Task 4: 工具箱聚合页集成与流水线全绿核验 (Integration & Gate Verification) [Role: Integration Builder]

**Files:**
- Modify: `src/pages/tools/index.astro:20-100`
- Test: 全量流水线 `pnpm test`

**Interfaces:**
- Consumes:
  - `<ClinicMemo />`, `<ContraceptionMatrix />`, `<EmergencyCountdown />`, `<CocRemedyCalculator />`, `<CycleAssessment />`, `<ArousalBrakesChecklist />`
- Produces:
  - 升级后的 `/tools/` 页面，包含 3 大场景分段（【突发应急与黄金窗口】/【日常周期与生理管理】/【知情决策与门诊就诊】）与平滑锚点导航。

**Subagent Prompt Scaffold (for /vault-exec):**
> "Implement Task 4: 工具箱聚合页集成与流水线全绿核验.
> Goal: 在 `src/pages/tools/index.astro` 挂载 ClinicMemo 和 ContraceptionMatrix，组织三大板块清晰层级，并确保全站构建与测试 100% 通过.
> Target Files:
> - Modify: `src/pages/tools/index.astro`
> TDD Steps:
> 1. 修改 `src/pages/tools/index.astro` 导入并挂载两大组件，增加顶部微导航锚点.
> 2. 运行 `pnpm test:graph` 确保决策树、词典、工具箱与文章整洁度四维测试全绿.
> 3. 运行 `pnpm check` 确保 TypeScript 与 Astro 诊断 0 错误 0 警告.
> 4. 运行 `pnpm curate:check` 确保科普库契约完整.
> 5. 运行 `pnpm build` 确保全站静态构建成功且 Pagefind 全文索引更新.
> Return: 全套测试套件运行通过截图/日志证明与构建产物统计."

**Step Breakdown:**
- [ ] **Step 1: Refactor `src/pages/tools/index.astro`**:
  - 引入新组件；
  - 建立三段式版块架构；
  - 配备紧凑目录微导航（Paper & Ink 风格徽标）。
- [ ] **Step 2: Run `python scripts/test_tools.py`**: 验证工具箱聚合页面与全部 6 大组件 100% 连通。
- [ ] **Step 3: Run `pnpm test` (Full Suite)**: 验证 TypeScript 类型检查、所有图谱与整洁度脚本、文章规范与最终 Astro 构建。
- [ ] **Step 4: Update Documentation & Work Memory**: 更新 `WORKMEMORY/work.log` 与 `WORKMEMORY/PROJECT_OVERVIEW.md`。
- [ ] **Step 5: Git atomic commit**: `git add src/pages/tools/index.astro WORKMEMORY/ && git commit -m "feat(tools): 聚合工具箱升级为 6 大工具矩阵并全线验证通过"`

---

## Downstream Dispatch

Plan generated with subagent prompt scaffolds. Initialize ledger and execute with /vault-exec?
