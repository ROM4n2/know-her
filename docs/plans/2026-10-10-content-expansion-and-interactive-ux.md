# 深度内容扩充与现代化交互大闭环实施计划 (Content Expansion & Interactive UX Implementation Plan)

> **Goal**: 落地方案 B 架构规划：扩充 6 篇深度临床与两性心理循证长文（含 1:1 配套知情速测题与词典外键）、长文悬浮目录树 (TOC) 与阅读进度指示条、全局 `Cmd+K` / `/` 即时搜索模态弹窗、客户端纯静态一键简繁转换、以及第 9 大离线交互工具——伴侣双人偏好双盲知情核对器。
> **Tech Stack**: Astro 7.3.3 + TypeScript strict + Tailwind CSS v4 (`@tailwindcss/vite`) + Pagefind WASM + Web Crypto API + Python 3.11+ 标准库。
> **Spec Reference**: `docs/specs/2026-10-10-content-expansion-and-interactive-ux-design.md`
> **Global Constraints**:
> 1. **Zero-PII 铁律**：伴侣双盲核对器全流程运行在浏览器沙箱内，URL Hash 密文零服务端传输，页面刷新即焚；
> 2. **设计系统铁律**：严格遵守 Academic Modern Editorial 纸墨调色板（`#FAF8F5`、`#15140F`、`#2A2620`、`#5A5448`、rose-600/700 等），严格禁止原生彩色 Emoji，一律使用单色语义 SVG 与等宽文本图章（如 `[ 01 // 目录 ]`、`[ 渴望尝试 ]`）；
> 3. **安全规范铁律**：全站坚决遵守 **Zero innerHTML** 规范，搜索结果高亮与双盲核对视图一律采用 `createElement` / `textContent` / `replaceChildren`；
> 4. **每日循环不变量 (G1~G9)**：新增 6 篇文章必须在 `src/data/dailyQuiz.ts` 保持 1:1 双向映射，确保 `pnpm test:graph` 与 CI 100% 绿灯。

---

## 🏛️ Decisions So Far

- [ADR-0001](../adr/ADR-0001.md): 零个人隐私持久化与纯静态站点架构。
- [ADR-0002](../adr/ADR-0002.md): 循证医学科普与每日知情速测双轨制。
- [Spec-2026-10-10](../specs/2026-10-10-content-expansion-and-interactive-ux-design.md): 确认方案 B（6 篇深度内容 + TOC/进度条 + `Cmd+K` 搜索弹窗 + 纯前端简繁转换 + 伴侣双盲核对器）。

---

## 🎯 Active Frontier (Unblocked Tasks)

### Task 1: 扩充 6 篇深度循证长文与 1:1 知情速测题闭环 [Mode: AFK] [Role: TDD Builder]

**Files:**
- Create:
  - `src/content/articles/body-pcos-lifestyle-management.mdx` (多囊卵巢综合征综合管理)
  - `src/content/articles/body-perimenopause-hormone-fluctuation.mdx` (围绝经期激素断崖应对)
  - `src/content/articles/body-ovulation-bleeding-vs-implantation.mdx` (排卵期/受精着床出血鉴别)
  - `src/content/articles/body-tampon-menstrual-cup-tss-safety.mdx` (卫生棉条与月经杯安全使用)
  - `src/content/articles/pleasure-vaginismus-pelvic-floor-therapy.mdx` (阴道痉挛成因与盆底肌阶梯脱敏)
  - `src/content/articles/intimacy-sexual-boundary-saying-no.mdx` (亲密关系边界与体面拒绝艺术)
- Modify:
  - `src/data/dailyQuiz.ts` (同步追加 6 道 1:1 结构化知情速测题)
  - `src/content/glossary/*.mdx` (核验并关联新增词典外键)
- Test:
  - `scripts/test_daily_loop.py`
  - `scripts/curate.py`

**Interfaces:**
- Consumes: `QuizItem` from `src/data/dailyQuiz.ts`, Article Zod Schema from `src/content.config.ts`
- Produces: 6 篇符合 A/B 级循证规范的 MDX 深度长文，6 道 1:1 对应的 `DAILY_QUIZZES` 测题，满足 G1 门禁（32 篇 : 32 题）

**Injected Instincts (Compile-Time Rule Injection):**
- [ ] `[Instinct: G1-Symmetry]`: 文章文件名必须与 `dailyQuiz.ts` 的 `articleId` 键 100% 精确一致。
- [ ] `[Instinct: Anti-Slop]`: 正文禁止模板套话，严格提供可操作临床/心理指引与权威公立医学出处。
- [ ] `[Instinct: Zero-Emoji]`: 正文与速测题中严格不得出现任何原生彩色 Emoji。

**Subagent Prompt Scaffold (for /dfs-exec):**
> "Implement Task 1: 扩充 6 篇深度循证长文与 1:1 知情速测题闭环.
> Mode: AFK | Role: TDD Builder
> Goal: 按照规范创建 6 篇深度科普长文，并在 `src/data/dailyQuiz.ts` 中配置对应的 6 道知情速测题，确保 G1 门禁 1:1 闭环并通过格式校验.
> Target Files:
> - Create:
>   `src/content/articles/body-pcos-lifestyle-management.mdx`
>   `src/content/articles/body-perimenopause-hormone-fluctuation.mdx`
>   `src/content/articles/body-ovulation-bleeding-vs-implantation.mdx`
>   `src/content/articles/body-tampon-menstrual-cup-tss-safety.mdx`
>   `src/content/articles/pleasure-vaginismus-pelvic-floor-therapy.mdx`
>   `src/content/articles/intimacy-sexual-boundary-saying-no.mdx`
> - Modify: `src/data/dailyQuiz.ts`
> TDD Steps:
> 1. 先创建 6 篇 MDX 文章骨架（包含严格合规的 frontmatter，合规分类 category: body / pleasure / intimacy，真实权威 source_url，合规 evidence_tier）；
> 2. 运行 `python -X utf8 scripts/test_daily_loop.py` 验证因速测题未匹配而报错（RED 确认）；
> 3. 在 `src/data/dailyQuiz.ts` 中针对这 6 篇新增文章配置 6 道高质量临床/心理知情速测题（GREEN）；
> 4. 运行 `python -X utf8 scripts/curate.py check` 与 `python -X utf8 scripts/test_daily_loop.py` 验证全绿（Verify GREEN）；
> 5. 运行 `pnpm check` 验证无类型报错.
> Return: Summary with MANDATORY Physical Execution Receipt (exit code + stdout snippet). Do NOT run git commit."

**Step Breakdown:**
- [ ] **Step 1: Write 6 new MDX articles in `src/content/articles/`**
- [ ] **Step 2: Run `python -X utf8 scripts/test_daily_loop.py` (Verify RED - G1 detects 6 missing quizzes)**
- [ ] **Step 3: Implement 6 matching quiz items in `src/data/dailyQuiz.ts` (GREEN)**
- [ ] **Step 4: Run `python -X utf8 scripts/test_daily_loop.py` & `curate.py check` (Verify GREEN - 32:32 passing)**
- [ ] **Step 5: Code Review & Zero-Emoji verification**
- [ ] **Step 6: Physical Evidence Gate**: `pnpm check` + terminal test output receipt
- [ ] **Step 7: Git atomic commit**

---

### Task 2: 长文阅读体验升级 —— 悬浮目录树与阅读进度条 [Mode: AFK] [Role: TDD Builder]

**Files:**
- Create:
  - `src/components/TableOfContents.astro` (侧边悬浮章节目录树)
  - `src/components/ReadingProgress.astro` (顶部 2px 极简纸墨阅读进度条)
  - `scripts/test_reading_ux.py` (阅读体验契约门禁)
- Modify:
  - `src/pages/articles/[id].astro` (引入并挂载 TOC 与进度条)
  - `package.json` (将 `test_reading_ux.py` 纳入 `test:graph`)

**Interfaces:**
- Consumes: `headings` from `await render(entry)` in `[id].astro` (`{ depth: number, slug: string, text: string }[]`)
- Produces: 
  - `<TableOfContents headings={headings} />` 响应式目录树组件（桌面端 `sticky` 侧边栏，移动端折叠抽屉）；
  - `<ReadingProgress />` 顶层纸墨色条，支持 `requestAnimationFrame` 滚动监听与百分比宽度更新；
  - 自动化测试脚本 `scripts/test_reading_ux.py`。

**Injected Instincts (Compile-Time Rule Injection):**
- [ ] `[Instinct: Minimal-Surface]`: 纯原生 HTML5/Web API 实现（`IntersectionObserver` + CSS `position: sticky`），零外部滚动依赖。
- [ ] `[Instinct: Zero-Emoji]`: 目录树标记使用单色几何符号或等宽文本，严禁彩色 Emoji。
- [ ] `[Instinct: Performance]`: 滚动事件使用 `requestAnimationFrame` 或纯 CSS 动画，避免重排抖动 (Layout Thrashing)。

**Subagent Prompt Scaffold (for /dfs-exec):**
> "Implement Task 2: 长文阅读体验升级 —— 悬浮目录树与阅读进度条.
> Mode: AFK | Role: TDD Builder
> Goal: 开发 `TableOfContents.astro` 与 `ReadingProgress.astro`，挂载至 `src/pages/articles/[id].astro`，并编写自动化测试契约.
> Target Files:
> - Create `scripts/test_reading_ux.py`
> - Create `src/components/TableOfContents.astro`
> - Create `src/components/ReadingProgress.astro`
> - Modify `src/pages/articles/[id].astro`
> - Modify `package.json`
> TDD Steps:
> 1. 编写 `scripts/test_reading_ux.py`：断言 `TableOfContents.astro` 与 `ReadingProgress.astro` 存在；断言 `[id].astro` 提取并传递 `headings`；断言包含 `#table-of-contents` 与 `#reading-progress-bar`；断言目录树包含 `IntersectionObserver` 滚动高亮脚本；并在 `package.json` 的 `test:graph` 中注册本测试脚本（RED）；
> 2. 运行 `python -X utf8 scripts/test_reading_ux.py` 验证因文件缺失报错（Verify RED）；
> 3. 实现 `src/components/ReadingProgress.astro`：顶部固定 2px 极简玫瑰/墨色进度条，平滑反映阅读进度，展示阅读时长标签；
> 4. 实现 `src/components/TableOfContents.astro`：解析 H2/H3 标题树，桌面端显示在正文右侧 `sticky top-24` 区域，移动端提供微型折叠按钮；点击平滑滚动并自动更新 URL Hash；
> 5. 在 `src/pages/articles/[id].astro` 解构 `const { Content, headings } = await render(entry);` 并挂载组件；
> 6. 运行 `python -X utf8 scripts/test_reading_ux.py` 与 `pnpm check` 验证全绿（Verify GREEN）.
> Return: Summary with MANDATORY Physical Execution Receipt (exit code + stdout snippet). Do NOT run git commit."

**Step Breakdown:**
- [ ] **Step 1: Write failing test in `scripts/test_reading_ux.py` (RED)**
- [ ] **Step 2: Run test and verify failure**
- [ ] **Step 3: Implement `ReadingProgress.astro` & `TableOfContents.astro` (GREEN)**
- [ ] **Step 4: Mount into `src/pages/articles/[id].astro` & update `package.json`**
- [ ] **Step 5: Run tests and verify all green**
- [ ] **Step 6: Physical Evidence Gate**: Raw execution receipt
- [ ] **Step 7: Git atomic commit**

---

### Task 3: 全局即时搜索模态弹窗与键盘快捷键接入 [Mode: AFK] [Role: TDD Builder]

**Files:**
- Create:
  - `src/components/SearchModal.astro` (全局即时检索模态弹窗)
- Modify:
  - `src/layouts/Base.astro` (全局引入并挂载 `<SearchModal />`，并在顶栏导航增加 `[ 搜索 ]` 快捷键胶囊)
  - `scripts/test_reading_ux.py` (补充 SearchModal 契约断言)

**Interfaces:**
- Consumes: Pagefind WASM 客户端 API (`/know-her/pagefind/pagefind.js`)
- Produces: 
  - 全局键盘监听器（`Cmd+K` / `Ctrl+K` / `/` 呼出，`Escape` 关闭，`ArrowUp`/`ArrowDown` 导航，`Enter` 直达）；
  - 纸墨质感居中模态弹窗（带焦点捕获 Focus Trap、无障碍 ARIA 属性、零 `innerHTML` 高亮结果渲染）。

**Injected Instincts (Compile-Time Rule Injection):**
- [ ] `[Instinct: Zero-innerHTML]`: Pagefind 返回的结果摘录与高亮标记，严禁直接使用 `innerHTML` 插入；必须使用安全文本节点与 `createElement('mark')` 拼装！
- [ ] `[Instinct: Safe-Keyboard]`: 监听输入法状态与当前激活元素（如当前用户已在 `<input>` 或 `<textarea>` 中打字时，按 `/` 键不得拦截呼出搜索）。
- [ ] `[Instinct: Zero-Emoji]`: 弹窗 UI 采用 Academic Editorial 调色，使用单色 SVG 放大镜与快捷键徽标 `[ ⌘K ]`。

**Subagent Prompt Scaffold (for /dfs-exec):**
> "Implement Task 3: 全局即时搜索模态弹窗与键盘快捷键接入.
> Mode: AFK | Role: TDD Builder
> Goal: 开发 `SearchModal.astro` 模态弹窗并在 `src/layouts/Base.astro` 中全局挂载，支持 `Cmd+K` / `Ctrl+K` / `/` 毫秒级唤起并调用 Pagefind 搜索.
> Target Files:
> - Create `src/components/SearchModal.astro`
> - Modify `src/layouts/Base.astro`
> - Modify `scripts/test_reading_ux.py`
> TDD Steps:
> 1. 在 `scripts/test_reading_ux.py` 中增加 `validate_search_modal_contract`：断言 `SearchModal.astro` 存在并在 `Base.astro` 中挂载；断言包含快捷键监听 (`k`, `KeyK`, `/`, `Slash`)、模态容器 `#search-modal-container`、输入框 `#search-modal-input`、结果容器 `#search-modal-results`，断言零 `innerHTML` 漏洞（RED）；
> 2. 运行 `python -X utf8 scripts/test_reading_ux.py` 验证因组件缺失报错（Verify RED）；
> 3. 实现 `src/components/SearchModal.astro`：
>    - 悬浮半透纸墨遮罩层；
>    - 搜索输入框（自动聚焦，支持清空，带 `[ ⌘K / ESC ]` 提示）；
>    - Pagefind WASM 懒加载与输入防抖查询（150ms）；
>    - 纯安全 DOM 节点渲染（`createElement`, `textContent`, `replaceChildren`）；
>    - 键盘上下选择与回车跳转；
> 4. 在 `src/layouts/Base.astro` 引入 `<SearchModal />`，并在桌面端顶栏导航增加微型快捷搜索按钮；
> 5. 运行 `python -X utf8 scripts/test_reading_ux.py` 与 `pnpm check` 验证全绿（Verify GREEN）.
> Return: Summary with MANDATORY Physical Execution Receipt (exit code + stdout snippet). Do NOT run git commit."

**Step Breakdown:**
- [ ] **Step 1: Write failing test in `scripts/test_reading_ux.py` (RED)**
- [ ] **Step 2: Run test and verify failure**
- [ ] **Step 3: Implement `SearchModal.astro` (GREEN)**
- [ ] **Step 4: Mount into `src/layouts/Base.astro`**
- [ ] **Step 5: Run tests and verify all green**
- [ ] **Step 6: Physical Evidence Gate**: Raw execution receipt
- [ ] **Step 7: Git atomic commit**

---

### Task 4: 客户端纯静态一键简繁转换能力 [Mode: AFK] [Role: TDD Builder]

**Files:**
- Create:
  - `src/lib/ui/langConverter.ts` (基于 opencc-js 的轻量客户端简繁转换器)
  - `src/components/LangSwitcher.astro` (极简纸墨风格简繁切换图章)
- Modify:
  - `package.json` (引入轻量依赖 `opencc-js`)
  - `src/layouts/Base.astro` (顶栏挂载 `<LangSwitcher />`)
  - `scripts/test_reading_ux.py` (补充简繁转换契约断言)

**Interfaces:**
- Consumes: `opencc-js` (`Converter({ from: 'cn', to: 'tw' })`)
- Produces: 
  - `initLangConverter(): void`：自动检查 `localStorage` 语言偏好，若为繁体模式则遍历 DOM 文本节点动态转换；
  - `toggleLanguage(): 'cn' | 'tw'`：切换当前语言模式并持久化存储（带 Safari 无痕降级防护）。

**Injected Instincts (Compile-Time Rule Injection):**
- [ ] `[Instinct: DOM-Safety]`: 仅转换文本节点 (`Node.TEXT_NODE`) 与 `<title>`、`placeholder`，跳过 `<script>`、`<style>`、`<code>` 块。
- [ ] `[Instinct: Storage-Resilience]`: `localStorage` 访问必须封装在 `try...catch` 中，避免无痕模式抛出 `SecurityError`。
- [ ] `[Instinct: Dynamic-Import]`: `opencc-js` 仅在用户实际点击切换为繁体时按需动态 `import()` 加载，确保简体用户首屏 0KB 额外体积负担。

**Subagent Prompt Scaffold (for /dfs-exec):**
> "Implement Task 4: 客户端纯静态一键简繁转换能力.
> Mode: AFK | Role: TDD Builder
> Goal: 安装 `opencc-js`，开发 `langConverter.ts` 与 `LangSwitcher.astro`，在 `Base.astro` 顶栏挂载一键简繁切换图章.
> Target Files:
> - Create `src/lib/ui/langConverter.ts`
> - Create `src/components/LangSwitcher.astro`
> - Modify `package.json`
> - Modify `src/layouts/Base.astro`
> - Modify `scripts/test_reading_ux.py`
> TDD Steps:
> 1. 在 `scripts/test_reading_ux.py` 中增加 `validate_lang_converter_contract`：断言 `opencc-js` 存在于 `package.json`，断言 `langConverter.ts` 与 `LangSwitcher.astro` 存在，断言 `Base.astro` 挂载了简繁切换按钮，断言包含动态 import 与 storage 安全容灾（RED）；
> 2. 运行 `python -X utf8 scripts/test_reading_ux.py` 验证因缺失报错（Verify RED）；
> 3. 安装依赖 `pnpm add opencc-js`；
> 4. 实现 `src/lib/ui/langConverter.ts`：封装动态 import 机制、DOM 文本递归遍历替换逻辑、`document.title` 同步转换、以及带 fallback 的持久化状态管理；
> 5. 实现 `src/components/LangSwitcher.astro`：极简纸墨印章外观 `[ 繁體 ]` / `[ 简体 ]`，挂载在 `src/layouts/Base.astro` 顶栏导航区；
> 6. 运行 `python -X utf8 scripts/test_reading_ux.py` 与 `pnpm check` 验证全绿（Verify GREEN）.
> Return: Summary with MANDATORY Physical Execution Receipt (exit code + stdout snippet). Do NOT run git commit."

**Step Breakdown:**
- [ ] **Step 1: Write failing test in `scripts/test_reading_ux.py` (RED)**
- [ ] **Step 2: Run test and verify failure**
- [ ] **Step 3: Add `opencc-js` & implement `langConverter.ts` + `LangSwitcher.astro` (GREEN)**
- [ ] **Step 4: Mount into `src/layouts/Base.astro`**
- [ ] **Step 5: Run tests and verify all green**
- [ ] **Step 6: Physical Evidence Gate**: Raw execution receipt
- [ ] **Step 7: Git atomic commit**

---

### Task 5: 伴侣双人偏好双盲知情核对器 (IntimacyBlindMatch.astro) [Mode: AFK] [Role: TDD Builder]

**Files:**
- Create:
  - `src/data/intimacyPreferences.ts` (20 项亲密行为探索与沟通条目数据契约)
  - `src/components/tools/IntimacyBlindMatch.astro` (伴侣双盲知情核对器交互组件)
- Modify:
  - `src/pages/tools/index.astro` (挂载为场景三第 9 大实用工具 `#sec-blind-match`，导航胶囊 `[09]`)
  - `scripts/test_tools.py` (补充工具 9 契约断言)

**Interfaces:**
- Consumes: `INTIMACY_PREFERENCE_ITEMS` from `../../data/intimacyPreferences`
- Produces: 
  - `<IntimacyBlindMatch />` 离线交互组件；
  - 纯前端 Web Crypto / Base64 URL Hash 密文生成与解析引擎；
  - 双人偏好交集计算（仅揭晓双方共同接受项，拒绝项永久保护不暴露）；
  - 一键生成双人探索知情长图（联动 `memoImageExporter.ts`）。

**Injected Instincts (Compile-Time Rule Injection):**
- [ ] `[Instinct: Zero-PII]`: 绝对零网络请求。数据仅存在于 URL Hash（`#vault=...`），HTTP 请求中绝不携带 Hash 串，保护双方极致隐私。
- [ ] `[Instinct: Zero-innerHTML]`: 选项列表与交集结果卡片必须全部使用 `createElement` / `textContent` / `replaceChildren` 构建。
- [ ] `[Instinct: Zero-Emoji]`: 偏好状态标尺严格采用文本与单色矢量符号（`[ 渴望尝试 ]`、`[ 可以接受 ]`、`[ 坚决拒绝 ]`、`[ 双方交集 ]`）。

**Subagent Prompt Scaffold (for /dfs-exec):**
> "Implement Task 5: 伴侣双人偏好双盲知情核对器 (IntimacyBlindMatch.astro).
> Mode: AFK | Role: TDD Builder
> Goal: 建立 `intimacyPreferences.ts` 数据集，开发 `IntimacyBlindMatch.astro` 组件并挂载至 `tools/index.astro` 场景三，作为工具箱第 9 大工具.
> Target Files:
> - Create `src/data/intimacyPreferences.ts`
> - Create `src/components/tools/IntimacyBlindMatch.astro`
> - Modify `src/pages/tools/index.astro`
> - Modify `scripts/test_tools.py`
> TDD Steps:
> 1. 在 `scripts/test_tools.py` 的 `REQUIRED_COMPONENTS` 注册 `("IntimacyBlindMatch.astro", ["blind-match-container", "blind-match-share-btn", "pleasure-responsive-desire-dual-control"])`，断言 `tools/index.astro` 挂载 `#sec-blind-match` 与导航胶囊 `[09] 伴侣双盲知情核对器`，断言支持 URL Hash 加密解析（RED）；
> 2. 运行 `python -X utf8 scripts/test_tools.py` 验证因文件缺失报错（Verify RED）；
> 3. 创建 `src/data/intimacyPreferences.ts`：定义 20 项涵盖前戏、体位、环境、沟通与事后温存的结构化条目；
> 4. 实现 `src/components/tools/IntimacyBlindMatch.astro`：
>    - 发起方模式：点选 20 项偏好，生成带 URL Hash 的无害分享链接；
>    - 伴侣应答模式：从 Hash 解析出加密载荷，伴侣填写自身偏好并点击比对；
>    - 结果呈现：仅揭示重合的“渴望尝试”与“可以接受”项，任何一方选“拒绝”的项目统统置灰隐藏，绝对不透露具体是谁拒绝；
>    - 支持导出纸墨对比便签（联动 `memoImageExporter`）；
>    - 纯安全 DOM 操作（Zero innerHTML），严格无原生彩色 Emoji；
> 5. 在 `src/pages/tools/index.astro` 挂载组件并更新导航与映射；
> 6. 运行 `python -X utf8 scripts/test_tools.py` 与 `pnpm check` 验证全绿（Verify GREEN）.
> Return: Summary with MANDATORY Physical Execution Receipt (exit code + stdout snippet). Do NOT run git commit."

**Step Breakdown:**
- [ ] **Step 1: Write failing test in `scripts/test_tools.py` (RED)**
- [ ] **Step 2: Run test and verify failure**
- [ ] **Step 3: Implement `intimacyPreferences.ts` & `IntimacyBlindMatch.astro` (GREEN)**
- [ ] **Step 4: Mount into `src/pages/tools/index.astro`**
- [ ] **Step 5: Run tests and verify all green**
- [ ] **Step 6: Physical Evidence Gate**: Raw execution receipt
- [ ] **Step 7: Git atomic commit**

---

### Task 6: 全链路流水线全绿回归与里程碑结项 [Mode: HITL] [Role: Integration Builder]

**Files:**
- Modify: `WORKMEMORY/PROJECT_OVERVIEW.md`
- Modify: `WORKMEMORY/work.log`
- Modify: `.vault-exec-ledger.json`

**Interfaces:**
- Consumes: 全站 32 篇科普文章、32 道速测题、9 大离线交互工具、TOC/阅读进度条、全局搜索弹窗与简繁转换模块
- Produces: 100% 通过的 CI 全链路构建产物与更新后的工作记忆

**Subagent Prompt Scaffold (for /dfs-exec):**
> "Implement Task 6: 全链路流水线全绿回归与里程碑结项.
> Mode: HITL | Role: Integration Builder
> Goal: 执行全量自动化测试与全站打包编译，确保 0 报错、0 警告、0 Emoji 违规、0 innerHTML 违规，更新台账与工作记忆.
> Steps:
> 1. 运行 `pnpm check` (Astro & TypeScript 严格类型检查)；
> 2. 运行 `pnpm test:graph` (全量 9 套测试契约门禁)；
> 3. 运行 `pnpm curate:check` (32 篇文章 frontmatter 契约校验)；
> 4. 运行 `pnpm build` (全站静态 HTML 页面打包与 Pagefind 索引生成)；
> 5. 运行 `pnpm test` (CI 全量流水线)；
> 6. 刷新 `WORKMEMORY/PROJECT_OVERVIEW.md` 与 `work.log`；
> 7. 更新 `.vault-exec-ledger.json` 状态至 100% COMPLETED.
> Return: 全量流水线实测输出证据与静态生成摘要."

**Step Breakdown:**
- [ ] **Step 1: Run full CI regression `pnpm test` (Verify GREEN)**
- [ ] **Step 2: Update `WORKMEMORY/PROJECT_OVERVIEW.md`**
- [ ] **Step 3: Append `WORK_END` event to `WORKMEMORY/work.log`**
- [ ] **Step 4: Finalize ledger `.vault-exec-ledger.json` to 6/6 completed**
- [ ] **Step 5: Git atomic commit & push**

---

## 🌫️ Fog of War (Not Yet Specified)

- **[Unknown 1]**: `opencc-js` 客户端完整字典包体积（若大于 1.5MB，将在 Task 4 中裁剪为仅含常用字与现代性健康医学词汇的轻量分支）。
- **[Unknown 2]**: 移动端微信内置浏览器中 URL Hash 长链接的截断风险（在 Task 5 中设计 Base64 字典位掩码紧凑编码，将 20 项偏好压缩在 30 字符以内）。

---

## 🚫 Out of Scope

- 不引入服务端数据库、API 服务或登录账户系统（维持零成本纯静态架构）。
- 不引入重型多语言路径拆分（不拆 `/zh-cn/`、`/zh-tw/` 路由，保持单一物理 URL）。
- 不自动对外部第三方来源进行全量爬取（维持人工深读策展与信源准入规则）。
