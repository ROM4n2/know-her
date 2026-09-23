# know-her 架构与工程准备子计划

> **Goal**: 在无任何业务医学内容的前提下，将 ADR-0001 D2–D7 的架构决策完整落成可运行、CI 强制的静态站骨架。
> **Tech Stack**: Astro 5 + TypeScript strict + Zod `.strict()` + Tailwind CSS + Pagefind + GitHub Actions
> **Spec Reference**: `docs/adr/ADR-0001.md`（D2–D7）、`IDEA.md`
> **Global Constraints**:
> - 零后端数据库；全静态输出（`output: 'static'`）
> - 不收集个人信息；analytics 仅聚合统计（Plausible/CF Analytics）
> - fork PR 不得接触 secrets；门禁 check 无 `paths:` 过滤、始终运行
> - 不做范围：补证取证、医学内容录入、newsletter 实际接入、DB

---

### Task 1: Astro 5 + TypeScript 项目初始化 [Role: Scaffolder]

**Files:**
- Create: `package.json`、`astro.config.mjs`、`tsconfig.json`、`.gitignore`（更新）
- Create: `src/` 目录骨架（`content/`、`layouts/`、`pages/`、`components/`）

**Interfaces:**
- Produces: `pnpm dev` 可运行的 Astro 5 静态站骨架（homepage 空白占位）

**Subagent Prompt Scaffold (for /vault-exec):**
> 「在 D:\Code\know-her 根目录初始化 Astro 5 + TypeScript + Tailwind 静态站。
> 1. `pnpm create astro@latest . --template minimal --typescript strict --install`（若已有 package.json 则 `pnpm add astro @astrojs/ts-plugin @astrojs/tailwind tailwindcss`）
> 2. 设 `astro.config.mjs` output 为 'static'，site 为占位符 `https://know-her.pages.dev`
> 3. 创建 `src/pages/index.astro` 空白占位首页（只输出 `<html lang="zh-CN">` + 声明横幅）
> 4. `pnpm astro check` 零错误通过
> 5. `pnpm build`（`dist/` 产出，verify index.html 存在）
> 6. git commit "feat: Astro 5 静态站初始化（TypeScript strict + Tailwind）"
> 回复：build 输出片段 + astro check 结果。」

**Step Breakdown:**
- [ ] Step 1: pnpm 安装 Astro 5 + 依赖
- [ ] Step 2: 配置 astro.config.mjs（output static + site）
- [ ] Step 3: tsconfig.json strict 模式
- [ ] Step 4: 首页占位 + astro check 通过
- [ ] Step 5: pnpm build 通过，dist/index.html 存在
- [ ] Step 6: git atomic commit

---

### Task 2: Zod Content Schema（内容契约）[Role: Schema Architect] 〔核心门禁〕

**Files:**
- Create: `src/content/config.ts`（Zod `.strict()` Schema + `superRefine` 不变式）
- Create: `src/content/articles/.gitkeep`（目录占位）

**Interfaces:**
- Produces: `defineCollection` 导出，`astro check` 对格式不合规 frontmatter 报错

**字段规范（全必填除标注外）:**
```typescript
// 来源与溯源
source_url: z.string().url()           // 来源 URL（必须可访问）
source_snapshot_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/)  // 取证日期 YYYY-MM-DD
source_snapshot_hash: z.string().optional()  // 页面快照哈希（选填）

// 审核状态机：draft → in_review → published → stale
review_status: z.enum(['draft','in_review','published','stale'])
review_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/).optional()  // 最近审核日期
review_interval_months: z.number().int().min(6).max(24).default(12)  // 复审周期
// review_due 为派生值（review_date + review_interval_months），不允许手填

// 四段审核（均必须明确填写，不可留空字符串）
reviewed_source: z.boolean()           // 来源核验 ✓/✗
reviewed_copyright: z.boolean()        // 版权检查 ✓/✗
reviewed_medical: z.boolean()          // 医学准确性 ✓/✗（D4：未就位时填 false）
reviewed_sensitivity: z.boolean()      // 敏感度 ✓/✗

// 敏感内容（D5）
red_flags: z.array(z.string())         // 急症红旗清单（允许空数组，但字段必填）
has_individual_advice: z.literal(false) // 禁止个体化建议，只能为 false

// 多语言（D6）
lang: z.enum(['zh-CN','en']).default('zh-CN')
translation_of: z.string().optional()  // 指向源条目 slug（译文才填）
```

**superRefine 不变式:**
- `reviewed_medical === true` 时 `review_date` 必须存在
- `translation_of` 存在时 `lang` 不得为 `'zh-CN'`（源语言不填该字段）
- `review_status === 'published'` 时 `reviewed_source && reviewed_copyright && reviewed_sensitivity` 必须全为 true

**Subagent Prompt Scaffold (for /vault-exec):**
> 「在 D:\Code\know-her/src/content/config.ts 实现 Zod `.strict()` Content Collection Schema（字段见计划 Task 2 规范）。
> 1. `pnpm add zod`（若未安装）
> 2. 实现 `defineCollection` + 上述所有字段 + 三条 superRefine 不变式
> 3. 写两个测试 frontmatter YAML fixture：一个合规（GREEN）、一个违反不变式（RED，review_status=published 但 reviewed_source=false）
> 4. `pnpm astro check` 对合规 fixture 零错误，对不合规 fixture 报 ZodError
> 5. git commit "feat(schema): Zod content schema + superRefine 不变式（D2 D5 D6）"
> 回复：两个 fixture 的 check 输出截取。」

**Step Breakdown:**
- [ ] Step 1: 编写 src/content/config.ts 完整 Zod Schema
- [ ] Step 2: 三条 superRefine 不变式
- [ ] Step 3: GREEN fixture（合规）通过 astro check
- [ ] Step 4: RED fixture（违反不变式）astro check 报 ZodError
- [ ] Step 5: git commit

---

### Task 3: 核心 UI 组件（免责声明、降级横幅、红旗卡）[Role: Frontend Builder] 〔D2 D4 D5〕

**Files:**
- Create: `src/components/MedicalDisclaimer.astro`（页脚全局免责声明）
- Create: `src/components/UnreviewedBanner.astro`（D4 未获医学复审降级横幅）
- Create: `src/components/RedFlagCard.astro`（急症红旗警示卡）
- Create: `src/components/AgePreferenceBanner.astro`（年龄提示，localStorage 一次性）
- Modify: `src/layouts/Base.astro`（植入 MedicalDisclaimer + AgePreferenceBanner）

**约束:**
- 纯 Astro 组件（零 JS 框架依赖）；AgePreferenceBanner 使用内联 `<script>`（只读写 localStorage）
- 无任何 `fetch`、API 调用、个人数据采集
- Tailwind 样式，红旗卡用警示色（red-600/amber-500）

**Subagent Prompt Scaffold (for /vault-exec):**
> 「在 D:\Code\know-her 实现四个 Astro 核心 UI 组件（见计划 Task 3 规范），并植入 Base.astro 布局。
> 1. MedicalDisclaimer：静态文字，声明非医疗建议、急症请拨 120
> 2. UnreviewedBanner：接受 prop `medicalReviewed: boolean`，false 时显示橙色横幅「本文尚未获得医学专业人士复审」
> 3. RedFlagCard：接受 prop `flags: string[]`，非空时渲染红色警示卡列表
> 4. AgePreferenceBanner：localStorage 'know_her_age_confirmed' 不存在时显示提示，用户点击后写 localStorage 并隐藏
> 5. 写 Base.astro，在 <body> 顶部放 AgePreferenceBanner，底部放 MedicalDisclaimer
> 6. pnpm build 通过
> 7. git commit "feat(ui): 核心合规组件（D2/D4/D5）"
> 回复：各组件行数 + build 通过证明。」

**Step Breakdown:**
- [ ] Step 1: MedicalDisclaimer.astro
- [ ] Step 2: UnreviewedBanner.astro（带 prop）
- [ ] Step 3: RedFlagCard.astro（带 prop）
- [ ] Step 4: AgePreferenceBanner.astro（localStorage，内联 script）
- [ ] Step 5: Base.astro 布局植入
- [ ] Step 6: pnpm build 通过
- [ ] Step 7: git commit

---

### Task 4: Pagefind 静态搜索集成 [Role: Search Integrator] 〔D2 D3〕

**Files:**
- Modify: `astro.config.mjs`（集成 `@pagefind/plugin-astro` 或 build hook）
- Create: `src/components/Search.astro`（搜索框 + Pagefind UI 初始化）
- Modify: `src/pages/index.astro`（植入搜索框）

**Subagent Prompt Scaffold (for /vault-exec):**
> 「在 D:\Code\know-her 集成 Pagefind 静态搜索。
> 1. `pnpm add @pagefind/plugin-astro`（或 `astro-pagefind`）并配置 astro.config.mjs
> 2. 创建 Search.astro 组件，引入 Pagefind UI（内联 script + link 指向 pagefind/pagefind-ui.js）
> 3. 在 index.astro 植入 <Search />
> 4. pnpm build（dist/ 下出现 pagefind/ 目录）
> 5. git commit "feat(search): Pagefind 静态搜索集成（D3）"
> 回复：dist/pagefind/ 目录 ls 输出。」

**Step Breakdown:**
- [ ] Step 1: 安装 Pagefind 插件
- [ ] Step 2: Search.astro 组件
- [ ] Step 3: index.astro 植入
- [ ] Step 4: build 验证（pagefind/ 目录存在）
- [ ] Step 5: git commit

---

### Task 5: 词条内容模板（标准骨架）[Role: Content Architect] 〔D4 D5〕

**Files:**
- Create: `src/content/articles/_template.mdx`（带注释的完整 frontmatter 骨架）
- Create: `docs/specs/article-writing-guide.md`（写作规范：第三人称枚举、禁第二人称条件句、红旗写法）

**约束:** 模板本身通过 Zod 校验（GREEN fixture）

**Subagent Prompt Scaffold (for /vault-exec):**
> 「在 D:\Code\know-her 创建标准词条模板与写作规范。
> 1. `src/content/articles/_template.mdx`：包含所有 Task 2 定义的 frontmatter 字段（用合规占位值），正文含三个注释区块：来源摘要区、医学说明区（第三人称枚举模板）、急症红旗区
> 2. `docs/specs/article-writing-guide.md`：写作规范文档（禁第二人称条件句→第三人称枚举、红旗清单格式、急症指征来源（WHO/ACOG/中华妇产科指南））
> 3. pnpm astro check（template.mdx frontmatter 合规，零 ZodError）
> 4. git commit "docs(spec): 词条模板 + 写作规范（D4/D5）"
> 回复：模板 frontmatter 字段列表 + astro check 通过证明。」

**Step Breakdown:**
- [ ] Step 1: _template.mdx（完整 frontmatter + 正文骨架）
- [ ] Step 2: article-writing-guide.md（写作规范）
- [ ] Step 3: astro check 校验 template.mdx 合规
- [ ] Step 4: git commit

---

### Task 6: GitHub Actions CI（门禁 + 链检）[Role: DevOps Engineer] 〔D2 D7〕

**Files:**
- Create: `.github/workflows/ci.yml`（`astro check` + `astro build` 全程阻断）
- Create: `.github/workflows/lychee.yml`（定时 + PR 外链有效性巡检）
- Create: `.github/ISSUE_TEMPLATE/correction.yml`（纠错模板，零个人信息字段）
- Create: `.github/ISSUE_TEMPLATE/new-source.yml`（来源提交模板）
- Create: `.github/pull_request_template.md`（PR 清单，含四段审核自查项）

**CI 约束（ADR-0001）:**
- `ci.yml` 无 `paths:` 过滤（始终运行）
- `pull_request_target` 仅打 label，绝不 checkout PR 代码
- fork PR 无 secrets 原则（ci.yml 不引用任何 secret）
- lychee.yml 用 `actions/cache` 缓存链检结果；PR 只查 diff，schedule 全量

**Subagent Prompt Scaffold (for /vault-exec):**
> 「在 D:\Code\know-her 创建 GitHub Actions CI 工作流与 Issue/PR 模板（见 Task 6 规范）。
> 1. .github/workflows/ci.yml：trigger on push+PR（无 paths 过滤）；jobs: astro-check（pnpm astro check）+ build（pnpm build）；零 secrets 引用
> 2. .github/workflows/lychee.yml：schedule 每周日 + on pull_request；PR job 只检 changed files；使用 actions/cache 缓存 .lycheecache
> 3. 纠错 Issue 模板：字段只有「问题描述」「来源 URL」「改进建议」（无姓名/邮件字段）
> 4. PR 模板：包含四段审核自查 checkbox（来源核验/版权/医学/敏感度）
> 5. yaml lint 无报错（python -c "import yaml; yaml.safe_load(open(...))"）
> 6. git commit "ci: GitHub Actions CI + 链检 + Issue/PR 模板（D2/D7）"
> 回复：ci.yml jobs 列表 + yaml lint 输出。」

**Step Breakdown:**
- [ ] Step 1: ci.yml（astro check + build，无 secrets，无 paths 过滤）
- [ ] Step 2: lychee.yml（schedule + PR diff 模式 + cache）
- [ ] Step 3: correction.yml Issue 模板（零个人信息）
- [ ] Step 4: new-source.yml Issue 模板
- [ ] Step 5: pull_request_template.md（四段审核 checkbox）
- [ ] Step 6: yaml lint 通过
- [ ] Step 7: git commit

---

### Task 7: RSS + Schema.org 分发标注 [Role: Distribution Engineer] 〔D3〕

**Files:**
- Create: `src/pages/rss.xml.ts`（Astro RSS endpoint）
- Modify: `src/layouts/Base.astro`（植入 `<link rel="alternate" type="application/rss+xml">`）
- Create: `src/components/ArticleSchema.astro`（`MedicalWebPage` + `fact-checked` Schema.org 标注）

**Subagent Prompt Scaffold (for /vault-exec):**
> 「在 D:\Code\know-her 实现 RSS feed + Schema.org MedicalWebPage 标注。
> 1. pnpm add @astrojs/rss
> 2. src/pages/rss.xml.ts：从 content collection 读取 published 状态词条输出 RSS 2.0
> 3. Base.astro 植入 <link rel="alternate" ...> 指向 /rss.xml
> 4. ArticleSchema.astro：输出 <script type="application/ld+json"> MedicalWebPage + ClaimReview（fact-checked）Schema
> 5. pnpm build（dist/rss.xml 存在）
> 6. git commit "feat(dist): RSS feed + Schema.org MedicalWebPage（D3）"
> 回复：dist/rss.xml 前 20 行 + ArticleSchema 输出结构。」

**Step Breakdown:**
- [ ] Step 1: @astrojs/rss 安装 + rss.xml.ts
- [ ] Step 2: Base.astro 植入 RSS link
- [ ] Step 3: ArticleSchema.astro（MedicalWebPage JSON-LD）
- [ ] Step 4: pnpm build（rss.xml 存在）
- [ ] Step 5: git commit

---

## 执行顺序与依赖关系

```
Task 1（Astro 初始化）
  ↓
Task 2（Zod Schema）←── 其他所有任务的基础
  ↓              ↓
Task 3（UI 组件） Task 5（词条模板）
  ↓
Task 4（Pagefind）
  ↓
Task 6（CI）←── 所有组件就绪后才有意义
  ↓
Task 7（RSS + Schema.org）
```

Task 1 → Task 2 严格串行；Task 3/4/5 可在 Task 2 完成后并行；Task 6/7 在 Task 3/4/5 完成后执行。

---

## 验收基线（全局 DONE 条件）

- `pnpm astro check` 零错误
- `pnpm build` 产出 `dist/`，含 `index.html`、`pagefind/`、`rss.xml`
- 不合规 frontmatter（违反任一 superRefine 不变式）触发 `astro check` 报错
- `ci.yml` yaml lint 通过，无 secrets 引用，无 paths 过滤
- 工作树 clean，所有文件入库，无临时 debug 代码
