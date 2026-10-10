# 妇科检查报告通俗解码台与 PWA 离线防窥急救包实施计划 (Implementation Plan)

> **Goal**: 落地两大高价值战略能力——「妇科检查报告通俗解码台」（狙击“宫颈糜烂/积液/转阴”过度治疗与医源性恐慌）与「PWA 离线急救包与防窥一键伪装」（弱网秒开离线急救、桌面独立沙箱与双击 Esc 瞬时工作备忘录伪装），建立全自动化契约测试与安全门禁。
> **Tech Stack**: Astro 7.3.3 + TypeScript strict + Tailwind CSS v4 (`@tailwindcss/vite`) + 原生 Service Worker & Web App Manifest + Python 3.11+ 标准库。
> **Spec Reference**: Multi-Expert Swarm Audit Report (方向 2 & 3)。
> **Global Constraints**:
> 1. **零个人隐私收集**：检查报告解码完全在前端 DOM 与内存中点选运行，零化验单数据上传，无服务端接口，页面刷新即焚；
> 2. **设计系统铁律**：严格遵循 Academic Modern Editorial 纸墨调色（`#FAF8F5` 纸底、`#15140F` 墨黑、`rose-600` 重点、`#5A5448` 辅助），严禁原生系统彩色 Emoji，使用单色语义 SVG 与文本排版印章 `[ 01 // PRINCIPLE ]`；
> 3. **安全规范铁律**：严格遵守 **Zero innerHTML** 规范，客户端 DOM 动态渲染一律采用 `createElement` / `textContent` / `replaceChildren`，杜绝 XSS；
> 4. **零新增第三方依赖**：Service Worker 与 Manifest 采用原生 Web API，不引入 Workbox 或第三方重型 runtime；
> 5. **测试驱动 (TDD)**：所有功能配备自动化 Python 测试契约，全量流水线 `pnpm test` 保持 100% 全绿。

---

### Task 1: 妇科检查报告通俗解码数据集与测试契约 (Data Layer & TDD Contract) [Role: TDD Builder]

**Files:**
- Create: `src/data/labReportDecoder.ts`
- Modify: `scripts/test_tools.py`

**Interfaces:**
- Produces:
  - `export interface LabReportItem`: 包含 `id`, `name`, `en_name`, `category`, `clinical_definition`, `plain_language_meaning`, `management_tier` (`normal_physiologic` | `routine_monitoring` | `specialist_consult`), `overtreatment_redflags` (过度治疗避坑提示), `doctor_questions` (就诊追问清单), `related_article`
  - `export interface LabCategoryConfig`: 包含 `id`, `name`, `badge`, `description`, `items`
  - `export const LAB_REPORT_CATEGORIES: LabCategoryConfig[]` in `src/data/labReportDecoder.ts`
- Consumes:
  - 现存科普文章 slug：`body-bacterial-vaginosis`, `body-vaginal-yeast-infection`, `abnormal-uterine-bleeding`, `normal-menstrual-cycle`, `body-hpv-vaccine-screening`, `body-endometriosis`

**Subagent Prompt Scaffold (for /dfs-exec):**
> "Implement Task 1: 妇科检查报告通俗解码数据集与测试契约.
> Goal: 建立涵盖白带常规与微生态、妇科超声、宫颈癌筛查 TCT+HPV、早孕与内分泌四大维度的结构化检查指标数据集，并编写自动化测试契约.
> Target Files:
> - Create `src/data/labReportDecoder.ts`
> - Modify `scripts/test_tools.py`
> TDD Steps:
> 1. 在 `scripts/test_tools.py` 中新增 `validate_lab_report_data` 函数：验证 `labReportDecoder.ts` 导出 `LAB_REPORT_CATEGORIES`，涵盖 4 大检查分类与至少 12 个指标条目，断言必填字段（`id`, `name`, `plain_language_meaning`, `management_tier`, `overtreatment_redflags`, `doctor_questions`, `related_article`），并核验所有 `related_article` 在 `src/content/articles/*.mdx` 真实存在（RED）.
> 2. 运行 `python -X utf8 scripts/test_tools.py` 验证因文件缺失报错（Verify RED）.
> 3. 创建 `src/data/labReportDecoder.ts`，严格按照 FIGO / ACOG / 默沙东大众版标准录入 4 大分类 14 个核心检查指标，特别注重狙击「宫颈糜烂做物理微波/激光手术」、「盆腔积液消炎吊水」、「HPV 昂贵转阴贴片」等过度治疗骗局（GREEN）.
> 4. 运行 `python -X utf8 scripts/test_tools.py` 与 `pnpm check` 验证全绿（Verify GREEN）.
> Return: 测试执行输出证据与数据模型导出清单. Do NOT run git commit."

**Step Breakdown:**
- [ ] **Step 1: Write failing test in `scripts/test_tools.py` (RED)**: 增加对 `labReportDecoder.ts` 的结构与外键验证.
- [ ] **Step 2: Run `python -X utf8 scripts/test_tools.py` (Verify RED)**: 捕获文件缺失报错.
- [ ] **Step 3: Implement `src/data/labReportDecoder.ts` (GREEN)**: 编写完整 TypeScript 接口与只读数据.
- [ ] **Step 4: Run tests (Verify GREEN)**: 验证契约全绿通过.
- [ ] **Step 5: Code Review & Refactor**: 确保类型严谨无 `any`，无原生彩色 Emoji.
- [ ] **Step 6: Git atomic commit**: `git add src/data/ scripts/test_tools.py && git commit -m "feat(data): 落地妇科检查报告通俗解码数据集与测试契约"`

---

### Task 2: 妇科检查报告通俗解码台交互组件开发 (ReportDecoder.astro) [Role: TDD Builder]

**Files:**
- Create: `src/components/tools/ReportDecoder.astro`
- Modify: `src/pages/tools/index.astro`
- Modify: `scripts/test_tools.py`

**Interfaces:**
- Consumes: `LAB_REPORT_CATEGORIES` from `../../data/labReportDecoder`
- Produces: 离线交互组件 `<ReportDecoder />`，挂载至 `src/pages/tools/index.astro`，支持四大分类切换、常见指标点选人话速解、三级处置警报标尺、过度治疗红旗提示、医患沟通提问清单，以及便签长图导出接入

**Subagent Prompt Scaffold (for /dfs-exec):**
> "Implement Task 2: 妇科检查报告通俗解码台交互组件开发.
> Goal: 开发 ReportDecoder.astro 交互组件并挂载到工具箱页面，提供直观、免恐慌的化验单人话解码与防坑指南.
> Target Files:
> - Create `src/components/tools/ReportDecoder.astro`
> - Modify `src/pages/tools/index.astro`
> - Modify `scripts/test_tools.py`
> TDD Steps:
> 1. 在 `scripts/test_tools.py` 的 `REQUIRED_COMPONENTS` 注册 `("ReportDecoder.astro", ["decoder-category-tab", "decoder-item-card", "abnormal-uterine-bleeding"])`，断言组件在 `tools/index.astro` 中被引用（RED）.
> 2. 运行 `python -X utf8 scripts/test_tools.py` 验证因组件缺失报错（Verify RED）.
> 3. 实现 `src/components/tools/ReportDecoder.astro`：
>    - 包含分类 Tab 切换 (`decoder-category-tab`)；
>    - 指标卡片网格 (`decoder-item-card`)，点击可查看指标深度人话解析；
>    - 核心诊断面板：包含三级处理建议微徽章（`[ 正常生理现象 ]` / `[ 建议择期复查 ]` / `[ 建议公立专科规范诊疗 ]`）；
>    - 医疗过度治疗避坑警示栏（用醒目墨线框标出常见过度治疗与私立忽悠陷阱）；
>    - 建议与医生确认的问题卡；
>    - 接入长图导出按钮，关联科普文章外链；
>    - 纯 DOM 安全构建（Zero innerHTML），严格无彩色 Emoji.
> 4. 在 `src/pages/tools/index.astro` 挂载组件并增加微导航 `[08]` 锚点 `#sec-report-decoder`.
> 5. 运行 `python -X utf8 scripts/test_tools.py` 与 `pnpm check` 验证全绿（Verify GREEN）.
> Return: 变更摘要与测试输出. Do NOT run git commit."

**Step Breakdown:**
- [ ] **Step 1: Write failing test in `scripts/test_tools.py` (RED)**: 注册 `ReportDecoder.astro` 契约.
- [ ] **Step 2: Run `python -X utf8 scripts/test_tools.py` (Verify RED)**: 捕获组件缺失报错.
- [ ] **Step 3: Implement `ReportDecoder.astro` (GREEN)**: 编写自包含交互组件.
- [ ] **Step 4: Mount into `src/pages/tools/index.astro` (GREEN)**: 挂载到场景三并更新导航.
- [ ] **Step 5: Run tests (Verify GREEN)**: 验证组件契约通过.
- [ ] **Step 6: Git atomic commit**: `git add src/ scripts/ && git commit -m "feat(tools): 落地妇科检查报告通俗解码台组件与防过度治疗指南"`

---

### Task 3: PWA 规范基建与轻量 Service Worker 离线急救缓存系统 [Role: TDD Builder]

**Files:**
- Create: `public/manifest.webmanifest`
- Create: `public/sw.js`
- Create: `scripts/test_pwa_contracts.py`
- Modify: `src/layouts/Base.astro`
- Modify: `package.json`

**Interfaces:**
- Produces: Web App Manifest 配置、Service Worker 离线急救缓存核心、PWA 契约自动化测试套件
- Consumes: 纯原生浏览器 Web API (CacheStorage, ServiceWorker)

**Subagent Prompt Scaffold (for /dfs-exec):**
> "Implement Task 3: PWA 规范基建与轻量 Service Worker 离线急救缓存系统.
> Goal: 配置 PWA manifest 与轻量 Service Worker，实现弱网/无网断网环境下 7 大工具秒级启动与离线运行，同时为私密使用提供桌面独立沙箱环境.
> Target Files:
> - Create `public/manifest.webmanifest`
> - Create `public/sw.js`
> - Create `scripts/test_pwa_contracts.py`
> - Modify `src/layouts/Base.astro`
> - Modify `package.json`
> TDD Steps:
> 1. 创建 `scripts/test_pwa_contracts.py`：断言 `manifest.webmanifest` 存在且包含合规字段（`name`, `short_name`, `start_url`, `display: standalone`, `theme_color`, `icons`），断言 `sw.js` 存在且包含 `CACHE_NAME`、`install`、`activate`、`fetch` 事件监听与核心预缓存路径（`/tools/`, `/guide/decision-tree/`），断言 `Base.astro` 包含 manifest link 与 SW 注册代码（RED）.
> 2. 运行 `python -X utf8 scripts/test_pwa_contracts.py` 验证因文件缺失报错（Verify RED）.
> 3. 创建 `public/manifest.webmanifest`：配置 Academic Modern Editorial 纸墨配色（`#FAF8F5`）与独立沙箱窗口（`standalone`）.
> 4. 创建 `public/sw.js`：实现轻量 Service Worker（Cache-First 核心骨架，Stale-While-Revalidate 科普词条，自动清理旧缓存）.
> 5. 在 `src/layouts/Base.astro` 的 `<head>` 注入 `<link rel=\"manifest\" ...>`，并在 `<body>` 尾部注入安全的 SW 注册脚本（生产环境生效，带安全 try-catch）.
> 6. 在 `package.json` 的 `test:graph` 接入 `python -X utf8 scripts/test_pwa_contracts.py`.
> 7. 运行 `pnpm test:graph` 与 `pnpm check` 验证全绿（Verify GREEN）.
> Return: 测试执行输出证据. Do NOT run git commit."

**Step Breakdown:**
- [ ] **Step 1: Write test script `scripts/test_pwa_contracts.py` (RED)**: 断言 PWA 规范与 SW 缓存契约.
- [ ] **Step 2: Run test (Verify RED)**: 捕获缺失文件.
- [ ] **Step 3: Implement `manifest.webmanifest` & `sw.js` (GREEN)**: 编写原生 PWA 资产与缓存策略.
- [ ] **Step 4: Update `Base.astro` and `package.json` (GREEN)**: 挂载清单与注册脚本.
- [ ] **Step 5: Run tests (Verify GREEN)**: 契约测试通过.
- [ ] **Step 6: Git atomic commit**: `git add public/ src/ scripts/ package.json && git commit -m "feat(pwa): 落地Web App Manifest与轻量Service Worker离线急救缓存系统"`

---

### Task 4: 全局防窥一键伪装避险组件开发 (PanicExit.astro) [Role: TDD Builder]

**Files:**
- Create: `src/components/PanicExit.astro`
- Modify: `src/layouts/Base.astro`
- Modify: `scripts/test_tools.py`

**Interfaces:**
- Produces: 全局防窥避险组件 `<PanicExit />`
- Triggers: 连按两次 `Esc` 键、双指快速轻触屏幕、或点击右下角极简图章 `[ 离线便签模式 ]`
- Action: 页面瞬时重绘为极简黑白「工作备忘录/每日待办清单」，标题替换为「工作备忘录 - 每日待办事项」，清除 URL 敏感参数，双击便签标题或按 `Esc` 解锁恢复

**Subagent Prompt Scaffold (for /dfs-exec):**
> "Implement Task 4: 全局防窥一键伪装避险组件开发.
> Goal: 为在工位、地铁、寝室查阅私密健康的用户提供秒级防窥伪装功能，瞬间化身为中立的每日待办工作便签.
> Target Files:
> - Create `src/components/PanicExit.astro`
> - Modify `src/layouts/Base.astro`
> - Modify `scripts/test_tools.py`
> TDD Steps:
> 1. 在 `scripts/test_tools.py` 中新增 `validate_panic_exit_contract` 函数：断言 `PanicExit.astro` 存在并在 `Base.astro` 中被引入，断言包含快捷键 Escape 监听、伪装标题 `工作备忘录`、以及待办事项渲染容器 `panic-disguise-container`（RED）.
> 2. 运行 `python -X utf8 scripts/test_tools.py` 验证失败（Verify RED）.
> 3. 实现 `src/components/PanicExit.astro`：
>    - 悬浮在页面右下角极低权重的极简图章按钮 `[ 便签模式 ]`；
>    - 客户端脚本监听双击 `Esc` 键与双指快速触控；
>    - 触发后显示全屏极简黑白伪装层（模拟原生记事本/Todo List，内置可交互勾选的“今日工作待办”）；
>    - 修改 `document.title = '工作备忘录 - 每日待办事项'`；
>    - 使用 `history.replaceState` 清空 URL 上的敏感参数；
>    - 再次按 `Esc` 或双击便签顶栏可无痕解锁恢复；
>    - 纯 DOM 安全构建（Zero innerHTML），严格无彩色 Emoji.
> 4. 在 `src/layouts/Base.astro` 引入并挂载 `<PanicExit />`.
> 5. 运行 `python -X utf8 scripts/test_tools.py` 与 `pnpm check` 验证全绿（Verify GREEN）.
> Return: 变更摘要与测试输出. Do NOT run git commit."

**Step Breakdown:**
- [ ] **Step 1: Write failing test in `scripts/test_tools.py` (RED)**: 注入 `validate_panic_exit_contract`.
- [ ] **Step 2: Run `python -X utf8 scripts/test_tools.py` (Verify RED)**: 捕获组件缺失.
- [ ] **Step 3: Implement `PanicExit.astro` (GREEN)**: 编写防窥避险组件与待办伪装层.
- [ ] **Step 4: Mount into `Base.astro` (GREEN)**: 全局集成.
- [ ] **Step 5: Run tests (Verify GREEN)**: 契约测试全绿.
- [ ] **Step 6: Git atomic commit**: `git add src/ scripts/ && git commit -m "feat(privacy): 落地全局防窥一键伪装避险组件与工作备忘录重绘模式"`

---

### Task 5: 全站全流水线回归核验与文档更新 (Full Regression & Milestone Close) [Role: Integration Builder]

**Files:**
- Modify: `WORKMEMORY/PROJECT_OVERVIEW.md`
- Modify: `WORKMEMORY/work.log`
- Modify: `.vault-exec-ledger.json`

**Interfaces:**
- Consumes: 36 个静态页面、8 大交互工具、PWA 基础设施与防窥组件
- Produces: 100% 通过的 CI 全链路门禁报告、Pagefind 索引更新与工作记忆固化

**Subagent Prompt Scaffold (for /dfs-exec):**
> "Implement Task 5: 全站全流水线回归核验与文档更新.
> Goal: 验证报告通俗解码台与 PWA 防窥离线急救包的所有改动无任何回归缺陷，全站静态生成无报错，零 Emoji 违规，零 innerHTML 违规，并更新项目工作记忆.
> Target: 执行全套验证套件并生成结项报告.
> 验证命令：
> 1. `pnpm check` (Astro & TS 诊断)
> 2. `pnpm test:graph` (全套 6 个契约测试脚本)
> 3. `pnpm curate:check` (文章元数据契约)
> 4. `pnpm build` (静态打包与 Pagefind 索引)
> 5. `pnpm test` (完整 CI 脚本)
> Return: 完整流水线测试执行证据与静态打包凭据."

**Step Breakdown:**
- [ ] **Step 1: Run full CI regression `pnpm test` (Verify GREEN)**.
- [ ] **Step 2: Update `WORKMEMORY/PROJECT_OVERVIEW.md` with new capabilities**.
- [ ] **Step 3: Append `WORK_END` event to `WORKMEMORY/work.log`**.
- [ ] **Step 4: Finalize ledger `.vault-exec-ledger.json` to 5/5 completed**.
- [ ] **Step 5: Git atomic commit**: `git add WORKMEMORY/ .vault-exec-ledger.json docs/ && git commit -m "docs(workmemory): 登记报告解码台与PWA防窥急救包落地事件并刷新项目概览"`
