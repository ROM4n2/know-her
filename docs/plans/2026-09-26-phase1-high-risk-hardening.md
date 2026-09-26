# Phase 1: 高危止血与缺陷加固实施计划 (Implementation Plan)

> **Goal**: 针对专家蜂群审查（`vault-team`）确认的 10 项 P0/P1 高危与阻塞缺陷进行系统性加固与彻底修复，消除移动端遮挡、安全注入风险、存储崩溃与 CI/CD 冗余浪费。
> **Tech Stack**: Astro 7.3.3 + TypeScript strict + Tailwind CSS v4 (`@tailwindcss/vite`) + Python 3.11+ 标准库。
> **Spec Reference**: Multi-Expert Swarm Audit Report (2026-09-26)。
> **Global Constraints**:
> 1. **零破坏性重构**：仅修复现场缺陷，不改动业务主干逻辑；
> 2. **设计系统铁律**：严禁系统彩色 Emoji，使用单色 SVG 与学术括号排版符号；
> 3. **安全规范铁律**：彻底根绝 `innerHTML` 残留，全面采用纯 DOM 安全渲染；封堵 Zod `javascript:` 伪协议；
> 4. **测试驱动 (TDD)**：所有修复均配备自动化断言验证，全量流水线 `pnpm test` 保持 100% 全绿。

---

### Task 1: 修复移动端吸底导航遮挡悬浮对比条与触控避让 (Floating Bar Z-Index & Offset) [Role: TDD Builder]

**Files:**
- Modify: `src/components/tools/ContraceptionMatrix.astro:430-440`
- Modify: `src/components/tools/PositionAndIntimacyGuide.astro:425-435`
- Modify: `scripts/test_tools.py`

**Interfaces:**
- Consumes: `Base.astro` 移动底栏高度 (`h-[56px]`, `z-50`)
- Produces: `ContraceptionMatrix` 与 `PositionAndIntimacyGuide` 悬浮对比条移动端避让样式 `bottom-20 sm:bottom-6`

**Subagent Prompt Scaffold (for /vault-exec):**
> "Implement Task 1: 修复移动端吸底导航遮挡悬浮对比条与触控避让.
> Goal: 解决 Base.astro 移动底栏 (z-50, h-[56px]) 物理遮挡 ContraceptionMatrix 与 PositionAndIntimacyGuide 悬浮对比条 (z-40, bottom-6) 的缺陷.
> Target Files:
> - `src/components/tools/ContraceptionMatrix.astro`
> - `src/components/tools/PositionAndIntimacyGuide.astro`
> - `scripts/test_tools.py`
> TDD Steps:
> 1. 在 `scripts/test_tools.py` 中增加断言：检查上述两个组件的悬浮对比条包含 `bottom-20`（RED）.
> 2. 运行 `python scripts/test_tools.py` 验证失败（Verify RED）.
> 3. 修改两个组件，将悬浮条类名从 `bottom-6` 改为 `bottom-20 sm:bottom-6`，确保移动端悬浮在底栏上方 24px 处，并在桌面端保持原有位置（GREEN）.
> 4. 运行 `python scripts/test_tools.py` 与 `pnpm check` 验证全绿（Verify GREEN）.
> Return: 测试执行输出证据与修改总结."

**Step Breakdown:**
- [ ] **Step 1: Write failing test in `scripts/test_tools.py` (RED)**: 断言悬浮栏类名包含 `bottom-20`.
- [ ] **Step 2: Run `python scripts/test_tools.py` (Verify RED)**: 捕获类名缺失报错.
- [ ] **Step 3: Modify `ContraceptionMatrix.astro` & `PositionAndIntimacyGuide.astro` (GREEN)**: 应用 `bottom-20 sm:bottom-6`.
- [ ] **Step 4: Run tests (Verify GREEN)**: `python scripts/test_tools.py` 通过.
- [ ] **Step 5: Code Review & Refactor**: 确认桌面端与移动端断点无视觉跳变.
- [ ] **Step 6: Git atomic commit**: `git add scripts/test_tools.py src/components/tools/ && git commit -m "fix(ui): 修复移动底栏遮挡工具悬浮对比栏的层级与避让边距"`

---

### Task 2: 根除 4 处 `innerHTML` 残留，切换为纯 DOM 安全构建 (Zero-innerHTML Enforcement) [Role: TDD Builder]

**Files:**
- Modify: `src/components/tools/CycleAssessment.astro:260-275`
- Modify: `src/components/tools/ArousalBrakesChecklist.astro:220-245`
- Modify: `src/components/DecisionGuide.astro:240-255,325-350`
- Modify: `src/components/DailyCard.astro:230-250`
- Modify: `scripts/test_article_hygiene.py`

**Interfaces:**
- Consumes: 原有 HTML 字符串拼接
- Produces: 安全纯 DOM 操作 (`createElement`, `textContent`, `replaceChildren`)，彻底杜绝客户端 XSS

**Subagent Prompt Scaffold (for /vault-exec):**
> "Implement Task 2: 根除 4 处 innerHTML 残留，切换为纯 DOM 安全构建.
> Goal: 根治审计发现的 4 处 innerHTML 破例代码，并在测试脚本中增加全局零 innerHTML 静态门禁.
> Target Files:
> - `src/components/tools/CycleAssessment.astro`
> - `src/components/tools/ArousalBrakesChecklist.astro`
> - `src/components/DecisionGuide.astro`
> - `src/components/DailyCard.astro`
> - `scripts/test_article_hygiene.py`
> TDD Steps:
> 1. 在 `scripts/test_article_hygiene.py` 中增加断言函数 `verify_zero_inner_html()`，扫描 `src/components/` 下所有 `.astro` 文件，若包含 `.innerHTML` 则报错（RED）.
> 2. 运行 `python scripts/test_article_hygiene.py` 验证因 4 处残留如期报错（Verify RED）.
> 3. 重构 4 个文件：
>    - `CycleAssessment.astro`: 用 `replaceChildren()` 和遍历创建带 `class` 的文本节点代替 `notes.join('<br>')`.
>    - `ArousalBrakesChecklist.astro`: 用 `textContent` 与 `createElement('strong')` 重构诊断结论.
>    - `DecisionGuide.astro`: 用 `createElement('span')` 构建序号与步骤.
>    - `DailyCard.astro`: 用 `createElement('span')` 构建 `[ 回答正确 ]` 徽标.
> 4. 运行 `python scripts/test_article_hygiene.py` 与 `pnpm check` 验证全绿（Verify GREEN）.
> Return: 扫描全绿输出证据与安全 DOM 重构代码."

**Step Breakdown:**
- [ ] **Step 1: Write failing test in `scripts/test_article_hygiene.py` (RED)**: 注入 `verify_zero_inner_html` 规则.
- [ ] **Step 2: Run `python scripts/test_article_hygiene.py` (Verify RED)**: 确认准确检出 4 个违规文件.
- [ ] **Step 3: Refactor 4 components with safe DOM APIs (GREEN)**: 消除所有 `.innerHTML` 赋值.
- [ ] **Step 4: Run tests (Verify GREEN)**: 静态卫生检查全绿.
- [ ] **Step 5: Code Review & Refactor**: 确认动态渲染文本在各分辨率下表现无退化.
- [ ] **Step 6: Git atomic commit**: `git add scripts/test_article_hygiene.py src/components/ && git commit -m "fix(security): 根除所有 innerHTML 残留并新增全组件零注入门禁"`

---

### Task 3: 修复 `curate.py` 403 异常漏报 Bug 与 Zod 协议校验 (Link Probe & URL Protocol Hardening) [Role: TDD Builder]

**Files:**
- Modify: `scripts/curate.py:145-160`
- Modify: `src/content.config.ts:15-25`
- Modify: `scripts/test_glossary.py` (或新增 `scripts/test_security_contracts.py`)

**Interfaces:**
- Consumes: Zod schema, `check_single_url()`
- Produces: 拦截 `javascript:` 伪协议的严密 Zod URL 校验；403 降级重试后若遇 404/410/网络断开正确返回 `False`

**Subagent Prompt Scaffold (for /vault-exec):**
> "Implement Task 3: 修复 curate.py 403 异常漏报 Bug 与 Zod 协议校验.
> Goal: 封堵死链借 403 异常静默穿透门禁的漏洞，并封锁 Zod source_url 的 javascript: 伪协议注入风险.
> Target Files:
> - `scripts/curate.py`
> - `src/content.config.ts`
> - `scripts/test_security_contracts.py` (新建自动化测试契约)
> TDD Steps:
> 1. 新建 `scripts/test_security_contracts.py`:
>    - 导入并测试 `src/content.config.ts` 的 schema，断言 `javascript:alert(1)` 必须校验失败（RED）.
>    - 测试 `curate.py` 的 `check_single_url` 逻辑，断言在 403 后若二次探测遇到 404 必须返回 `False`（RED）.
> 2. 运行 `python scripts/test_security_contracts.py` 验证失败（Verify RED）.
> 3. 修改 `src/content.config.ts`:
>    - `source_url: z.string().url().refine(u => /^https?:\\/\\//i.test(u), { message: '仅支持 http 或 https 协议' })`.
> 4. 修改 `scripts/curate.py`:
>    - 在 403 异常重试块中，针对 `urllib.error.HTTPError as e2`，若 `e2.code in (404, 410)` 坚决返回 `False`；对其它不可判定的异常标记警告并如实返回 `False` 或受控的警告状态，不再静默 `return True`.
> 5. 运行 `python scripts/test_security_contracts.py` 与 `pnpm check` 验证全绿（Verify GREEN）.
> Return: 契约测试与安全逻辑修复证据."

**Step Breakdown:**
- [ ] **Step 1: Write test script `scripts/test_security_contracts.py` (RED)**: 断言协议阻断与 404 绝不穿透.
- [ ] **Step 2: Run test (Verify RED)**: 捕获 Zod 放行伪协议与 403 静默放行.
- [ ] **Step 3: Modify `content.config.ts` and `curate.py` (GREEN)**: 实施安全防御.
- [ ] **Step 4: Run tests (Verify GREEN)**: 契约测试通过.
- [ ] **Step 5: Code Review & Refactor**: 在 `package.json` 的 `test:graph` 接入 `test_security_contracts.py`.
- [ ] **Step 6: Git atomic commit**: `git add src/content.config.ts scripts/ package.json && git commit -m "fix(security): 封堵 URL 伪协议注入并修复外链探测 403 漏报漏洞"`

---

### Task 4: 补齐 `DailyCard` 存储异常防护与净化 `AgePreferenceBanner` 彩色 Emoji (Storage Resilience & Editorial Purity) [Role: TDD Builder]

**Files:**
- Modify: `src/components/DailyCard.astro:165-215`
- Modify: `src/components/AgePreferenceBanner.astro:1-20`
- Modify: `src/data/dailyQuiz.ts:335-345`
- Modify: `scripts/curate.py:185-195,235-245`

**Interfaces:**
- Consumes: `localStorage`, 系统 Unicode 符号
- Produces: `safeGetStorage` / `safeSetStorage` 容灾调用；单色线框 SVG 时钟与学术印章；统一的积日模运算公式 `(day_of_year - 1) % count`

**Subagent Prompt Scaffold (for /vault-exec):**
> "Implement Task 4: 补齐 DailyCard 存储异常防护、净化 AgePreferenceBanner 彩色 Emoji 并统一积日算法.
> Goal: 解决 DailyCard 在无痕模式下抛出 SecurityError 崩溃的问题，替换 AgePreferenceBanner 中彩色 Emoji ⏰，并统一下标对齐.
> Target Files:
> - `src/components/DailyCard.astro`
> - `src/components/AgePreferenceBanner.astro`
> - `src/data/dailyQuiz.ts`
> - `scripts/curate.py`
> TDD Steps:
> 1. 检查 `src/components/AgePreferenceBanner.astro` 中的 `⏰` 符号，替换为内联单色 SVG 时钟图标或学术方括号 `[ 年龄确认 ]`.
> 2. 在 `DailyCard.astro` 客户端脚本中实现安全存储访问包装函数 `safeGet(key, defaultVal)` 与 `safeSet(key, val)`，使用 `try...catch` 兜底任何 `DOMException`/`SecurityError`，并在存储不可用时降级为内存变量.
> 3. 校准 `dailyQuiz.ts` 与 `curate.py` 的积日计算公式，统一使用 `(day_of_year - 1) % total`，并对文章列表增加稳定的 `id` 排序键（`a.id.localeCompare(b.id)` / Python `sort(key=lambda x: (x.date, x.id))`），消除跨 OS 排序不一致.
> 4. 运行 `pnpm check` 与 `pnpm test` 验证全绿（Verify GREEN）.
> Return: 变更摘要与测试输出."

**Step Breakdown:**
- [ ] **Step 1: Replace colored emoji with monochrome SVG in `AgePreferenceBanner.astro` (GREEN)**.
- [ ] **Step 2: Add `try...catch` storage wrapper in `DailyCard.astro` (GREEN)**.
- [ ] **Step 3: Synchronize day-of-year modulo and sort tie-breaker in `dailyQuiz.ts` and `curate.py` (GREEN)**.
- [ ] **Step 4: Run `pnpm check` & `pnpm test:graph` (Verify GREEN)**.
- [ ] **Step 5: Code Review & Refactor**: 确保 Unicode 表情扫描 0 检出.
- [ ] **Step 6: Git atomic commit**: `git add src/ scripts/ && git commit -m "fix(resilience): 增加本地存储异常降级容灾并统一确定性排序与排版符号"`

---

### Task 5: 优化 CI/CD 流水线，消除 master 分支双重构建与死锁风险 (CI/CD Pipeline Optimization) [Role: Integration Builder]

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `.github/workflows/deploy.yml`
- Modify: `.github/workflows/daily-routine.yml`
- Modify: `src/layouts/Base.astro:15-35` (注入静态 CSP 与 Referrer-Policy Meta 头)

**Interfaces:**
- Consumes: GitHub Actions triggers
- Produces: 互斥不重复的 CI 与 Deploy 流水线，带 `timeout-minutes: 10` 硬熔断约束；基础静态安全 CSP Meta 注入

**Subagent Prompt Scaffold (for /vault-exec):**
> "Implement Task 5: 优化 CI/CD 流水线，消除 master 分支双重构建与死锁风险，并注入 CSP Meta 头.
> Goal: 重构 ci.yml 与 deploy.yml 触发关系，避免 master push 双重触发导致资源浪费与重复外链扫描；补充超时限制；在 Base.astro 注入客户端 CSP.
> Target Files:
> - `.github/workflows/ci.yml`
> - `.github/workflows/deploy.yml`
> - `.github/workflows/daily-routine.yml`
> - `src/layouts/Base.astro`
> TDD Steps:
> 1. 在 `ci.yml` 中配置 `push: branches-ignore: [ master ]`，master 推送完全交由 `deploy.yml` 执行，避免双重运行.
> 2. 为 `deploy.yml`（build/deploy 两个 job）与 `daily-routine.yml` 显式设置 `timeout-minutes: 10`，杜绝悬挂 6 小时风险.
> 3. 在 `src/layouts/Base.astro` 的 `<head>` 区域注入符合 Pagefind WASM 规范的 `<meta http-equiv=\"Content-Security-Policy\" ...>` 与 `strict-origin-when-cross-origin`.
> 4. 执行全套回归验证：`pnpm check && pnpm test:graph && pnpm curate:check && pnpm build` 确认 35 个页面全量生成且 Pagefind 索引正常.
> Return: 完整流水线测试执行证据."

**Step Breakdown:**
- [ ] **Step 1: Update `.github/workflows/ci.yml` to ignore master on push (GREEN)**.
- [ ] **Step 2: Add `timeout-minutes: 10` to `deploy.yml` and `daily-routine.yml` (GREEN)**.
- [ ] **Step 3: Inject CSP meta tags into `src/layouts/Base.astro` (GREEN)**.
- [ ] **Step 4: Run full regression `pnpm test` (Verify GREEN)**.
- [ ] **Step 5: Code Review & Refactor**: 确认 Actions YAML 语法安全有效.
- [ ] **Step 6: Git atomic commit**: `git add .github/workflows/ src/layouts/Base.astro && git commit -m "ci(sre): 优化构建流水线触发拓扑、增加硬熔断超时并注入客户端安全标头"`

---
