# 性生理力学矩阵、伴侣知情清单与深度科普体系 (方案 C) 实施计划

> **Goal**: 落地 3 篇性生理学科普长文、3 个医学词典词条、扩充 3 道每日速测题、并在 `/tools/` 落地第 7 大纯前端离线工具《体位生理力学矩阵与伴侣探索知情清单》(PositionAndIntimacyGuide.astro)，全链路通过 `pnpm test` 门禁。
> **Tech Stack**: Astro 7.3.3, TypeScript 5.8.3, Tailwind CSS v4, Python 3.11+ 标准库测试套件。
> **Spec Reference**: `docs/specs/2026-09-26-sexual-positions-and-intimacy-checklist-design.md`
> **Global Constraints**:
> - 严格遵从 Academic Modern Editorial 纸墨美学，全站禁止彩色原生 Emoji（单色 SVG 与文本印章 `[ 01 // STEP ]` 替代）。
> - 纯前端离线运行，零 `localStorage` / 零接口回传，无任何隐私外泄。
> - 客户端动态 DOM 更新严格采用 `createElement` / `textContent` / `replaceChildren()`，**Zero innerHTML**。
> - Python 测试脚本仅使用标准库。
> - 执行模式：严格遵循 `/vault-exec` 派发子代理（TDD Builder + Reviewer Maker-Checker）。

---

### Task 1: 3 篇深度科普长文、3 大医学词典词条与速测题库扩充 (Content & Glossary Layer) [Role: TDD Builder]

**Files:**
- Create:
  - `src/content/articles/pleasure-woman-on-top-mechanics.mdx`
  - `src/content/articles/pleasure-side-lying-spooning.mdx`
  - `src/content/articles/pleasure-rear-entry-angles.mdx`
  - `src/content/glossary/retroverted-uterus.md`
  - `src/content/glossary/deep-dyspareunia.md`
  - `src/content/glossary/coital-angle.md`
- Modify:
  - `src/data/dailyQuiz.ts` (扩充 3 道与新文章关联的 30 秒知情速测题)

**Interfaces:**
- Consumes: `src/content.config.ts` (articles & glossary zod collections), `scripts/curate.py check`, `scripts/test_glossary.py`
- Produces: 3 篇完整 Frontmatter MDX、3 篇词典 Markdown，25 篇文章/28 个词条/25 道速测题。

**Subagent Prompt Scaffold (for /vault-exec):**
> "Implement Task 1: 3 篇深度科普长文、3 大医学词典词条与速测题库扩充.
> Goal: 编写 3 篇严肃循证性生理学科普文章、3 个词典词条，并向 dailyQuiz 扩充 3 道知情题。
> Target Files:
> - `src/content/articles/pleasure-woman-on-top-mechanics.mdx` (女上位掌控度、深度控制与深部痛防护，信源默沙东大众版)
> - `src/content/articles/pleasure-side-lying-spooning.mdx` (侧卧匙羹与剪刀式，低耗能与盆底肌放松，信源梅奥诊所)
> - `src/content/articles/pleasure-rear-entry-angles.mdx` (后入位角度力学与子宫后位撞击痛避坑，信源默沙东/梅奥)
> - `src/content/glossary/retroverted-uterus.md` (子宫后位)
> - `src/content/glossary/deep-dyspareunia.md` (深部性交痛)
> - `src/content/glossary/coital-angle.md` (解剖进入角度)
> - `src/data/dailyQuiz.ts` (增加 3 道与上述 3 篇文章关联的速测题)
> Steps:
> 1. 创建 3 篇 MDX 文章与 3 篇词典文件，严格遵从 Frontmatter 格式，不嵌入全局布局组件，不使用彩色 Emoji。
> 2. 更新 `src/data/dailyQuiz.ts` 增加对应题目。
> 3. 运行 `python scripts/curate.py check` 和 `python scripts/test_glossary.py` 验证全绿。
> 4. 运行 `pnpm check` 验证 TS 诊断无错误。
> Return: Summary with test execution evidence. Do NOT run git commit."

**Step Breakdown:**
- [ ] **Step 1: 创建 3 篇严肃性生理学科普 MDX 文章**
- [ ] **Step 2: 创建 3 个医学专有词条并关联对应文章**
- [ ] **Step 3: 扩充 dailyQuiz.ts 题库至 25 题**
- [ ] **Step 4: 运行 curate.py check 与 test_glossary.py 验证通过**
- [ ] **Step 5: 运行 pnpm check 验证零 TS 错误**

---

### Task 2: 体位力学全景数据集与伴侣知情题库契约 (Data Layer & TDD Contract) [Role: TDD Builder]

**Files:**
- Create:
  - `src/data/positionMatrix.ts`
  - `src/data/intimacyChecklist.ts`
- Modify:
  - `scripts/test_tools.py` (新增对 positionMatrix 与 intimacyChecklist 的结构/外键断言)

**Interfaces:**
- Consumes: `src/data/positionMatrix.ts`, `src/data/intimacyChecklist.ts`
- Produces: `POSITION_METHODS: SexualPosition[]` (8 种姿势), `INTIMACY_CHECKLIST_CONFIGS: ChecklistCategory[]` (5 大分类 16 项), `scripts/test_tools.py` 门禁函数 `validate_position_data` 与 `validate_checklist_data`。

**Subagent Prompt Scaffold (for /vault-exec):**
> "Implement Task 2: 体位力学全景数据集与伴侣知情题库契约.
> Goal: 在 `scripts/test_tools.py` 新增契约门禁，并创建 `positionMatrix.ts` 与 `intimacyChecklist.ts`。
> Steps:
> 1. 在 `scripts/test_tools.py` 添加 `validate_position_data`（断言 positionMatrix 包含 ≥8 种体位，校验 id, name, category, clitoral_access, cervical_collision_risk, energy_expenditure, related_article 外键存在性）和 `validate_checklist_data`（断言 intimacyChecklist 包含 5 大类且 ≥15 个选项）。
> 2. 运行 `python scripts/test_tools.py` 验证 RED 失败。
> 3. 创建 `src/data/positionMatrix.ts`（收录 8 大体位：正向女上位、反向女上位、侧卧匙羹式、侧卧剪刀式、经典改良男上位、骨盆垫枕高迎角式、立姿支撑式、改良屈膝后入式，所有 related_article 映射到真实文章）。
> 4. 创建 `src/data/intimacyChecklist.ts`（收录 5 大类 16 项 Yes/No/Maybe 探索项与非暴力沟通建议文案）。
> 5. 运行 `python scripts/test_tools.py` 验证 GREEN 通过。
> 6. 运行 `pnpm check` 验证 0 错误。
> Return: Summary with test execution evidence. Do NOT run git commit."

**Step Breakdown:**
- [ ] **Step 1: 在 scripts/test_tools.py 添加数据集契约断言 (RED)**
- [ ] **Step 2: 运行测试并捕获失败**
- [ ] **Step 3: 落地 src/data/positionMatrix.ts 与 src/data/intimacyChecklist.ts (GREEN)**
- [ ] **Step 4: 运行 scripts/test_tools.py 验证通过**
- [ ] **Step 5: 运行 pnpm check 确保 TS 0 错误**

---

### Task 3: 体位生理力学矩阵与知情探索清单复合组件 (PositionAndIntimacyGuide.astro) [Role: TDD Builder]

**Files:**
- Create:
  - `src/components/tools/PositionAndIntimacyGuide.astro`
- Modify:
  - `scripts/test_tools.py` (在 REQUIRED_COMPONENTS 添加 PositionAndIntimacyGuide.astro 及关键类名)

**Interfaces:**
- Consumes: `CONTRACEPTION_METHODS`, `POSITION_METHODS`, `INTIMACY_CHECKLIST_CONFIGS`
- Produces: 自包含复合交互组件，包含 Tab 1 (体位矩阵与双向 PK 抽屉) 与 Tab 2 (Yes/No/Maybe 亲密沟通便签生成器)。

**Subagent Prompt Scaffold (for /vault-exec):**
> "Implement Task 3: 体位生理力学矩阵与知情探索清单复合组件.
> Goal: 落地 `PositionAndIntimacyGuide.astro` 复合组件及客户端无状态交互脚本。
> Steps:
> 1. 在 `scripts/test_tools.py` 的 REQUIRED_COMPONENTS 追加 `("PositionAndIntimacyGuide.astro", ["position-filter-container", "position-card", "intimacy-checklist-root", "pleasure-woman-on-top-mechanics"])`。
> 2. 运行 `python scripts/test_tools.py` 验证 RED 失败。
> 3. 实现 `src/components/tools/PositionAndIntimacyGuide.astro`：
>    - 顶部 Tab 切换：`[ 姿势生理力学知情选择矩阵 ]` 与 `[ 伴侣私密探索知情清单 (Yes/No/Maybe) ]`；
>    - Tab 1: 6 维多标签即时筛选、8 大姿势卡片网格（阴蒂可达度/宫颈碰撞/体能条形指示）、双选 PK 浮动栏与侧边抽屉对比台账（零 innerHTML）；
>    - Tab 2: 5 大类 16 项点选卡片、实时渲染《伴侣探索沟通便签》、一键复制、纸质打印 (@media print)、重置；
>    - 严格遵循 Academic Modern Editorial 纸墨规范，无彩色 Emoji。
> 4. 运行 `python scripts/test_tools.py` 验证 GREEN。
> 5. 运行 `pnpm check` 验证 0 错误。
> Return: Summary with test execution evidence. Do NOT run git commit."

**Step Breakdown:**
- [ ] **Step 1: 在 scripts/test_tools.py 增加组件契约 (RED)**
- [ ] **Step 2: 编写 src/components/tools/PositionAndIntimacyGuide.astro (GREEN)**
- [ ] **Step 3: 运行 scripts/test_tools.py 验证通过**
- [ ] **Step 4: 运行 pnpm check 确保 0 错误**

---

### Task 4: 工具箱聚合页挂载与全站全流水线回归验证 (Integration & Gate Verification) [Role: Integration Builder]

**Files:**
- Modify:
  - `src/pages/tools/index.astro` (在场景二日常生理与身体自主管理下挂载 PositionAndIntimacyGuide，顶部扩充 `[07]` 锚点)

**Interfaces:**
- Consumes: 全站 25 篇文章、28 个词条、7 大工具组件、35+ 个静态页面
- Produces: 完整构建的 `dist/`，全部 CI 脚本通过。

**Subagent Prompt Scaffold (for /vault-exec):**
> "Implement Task 4: 工具箱聚合页挂载与全站全流水线回归验证.
> Goal: 在 `src/pages/tools/index.astro` 挂载第 7 大工具，更新微导航与场景描述，并执行全链路测试套件。
> Steps:
> 1. 更新 `src/pages/tools/index.astro`：
>    - 顶部微导航新增 `[07] 体位力学矩阵与探索清单` 锚点；
>    - 场景二（日常生理与身体自主管理）挂载 `<PositionAndIntimacyGuide />`；
>    - 确保无彩色原生 Emoji。
> 2. 依次运行全量流水线：
>    - `python scripts/test_tools.py`
>    - `pnpm test:graph`
>    - `pnpm check`
>    - `pnpm curate:check`
>    - `pnpm build`
>    - `pnpm test`
> 3. 验证生成 35 个静态路由并完成 Pagefind 全文索引。
> Return: Summary with full test execution evidence. Do NOT run git commit."

**Step Breakdown:**
- [ ] **Step 1: 修改 src/pages/tools/index.astro 挂载组件与微导航**
- [ ] **Step 2: 运行全量测试流水线 (pnpm test)**
- [ ] **Step 3: 验证 Pagefind 索引与 35 个静态页面无误**
