# know-her 内容建设与首批试点词条子计划

> **Goal**: 实现词条详情渲染路由与首页检索索引，交付首批 2 篇基于权威真实来源的试点词条，跑通四段审核流（3/4 达标发布 + D4 降级呈现），端到端打通 CI、Pagefind 静态检索与 RSS 发布。
> **Tech Stack**: Astro 5.x/7.x + Content Collections + Tailwind CSS + Pagefind + RSS 2.0 + Schema.org
> **Spec Reference**: `docs/adr/ADR-0001.md`（D4/D5/D6）、`docs/specs/article-writing-guide.md`、`src/content.config.ts`
> **Global Constraints**:
> - 遵循 `docs/specs/article-writing-guide.md`：禁第二人称条件句、一律第三人称枚举、急症红旗双写、权威来源严格回指。
> - 遵循 ADR-0001 D4：医学复审席位未齐前，`reviewed_medical: false`，文章必须渲染 `UnreviewedBanner` 降级横幅，绝不冒充四段全通。
> - frontmatter 严格遵循 `src/content.config.ts`，禁止自造字段（无 `title`，标题由正文 H1 提取）。
> - 零数据库、全静态输出、零个人信息收集。
> - 不做范围：补证取证（等网络）、后台管理系统、数据库、任何个人信息收集功能。

---

### Task 1: 词条详情页路由与组件装配 [Role: Frontend Builder]

**Files:**
- Create: `src/pages/articles/[id].astro`
- Modify: `src/pages/index.astro`

**Interfaces:**
- `getStaticPaths()`: 从 `getCollection('articles')` 加载并过滤非模板文件，返回 `params: { id: article.id }`
- Produces: `/articles/[id]/` 详情页，集成 `ArticleSchema` (SEO JSON-LD)、`UnreviewedBanner` (D4 降级)、`RedFlagCard` (急症红旗)、`MedicalDisclaimer`、正文 `<Content />` 与底部来源回溯/纠错外链。
- `index.astro` 增设词条列表区，展示已发布词条及审核状态徽章。

**Subagent Prompt Scaffold (for /vault-exec):**
> 「在 D:\Code\know-her 实现词条详情页路由与首页更新。
> 1. 创建 `src/pages/articles/[id].astro`：
>    - 使用 `getCollection('articles')`，过滤以 `_` 开头的私有模板文件；
>    - 使用 `render(article)` 渲染内容，提取首个 H1 作为标题，若无则回退为 `article.id`；
>    - 引入并装配 `Base.astro`、`ArticleSchema.astro`、`UnreviewedBanner.astro`、`RedFlagCard.astro`；
>    - 当 `!article.data.reviewed_medical` 时渲染 `UnreviewedBanner`；
>    - 当 `article.data.red_flags.length > 0` 时渲染 `RedFlagCard`；
>    - 页面排版采用优雅的阅读容器（Tailwind `max-w-3xl mx-auto px-4 py-8`），含元数据栏（来源、快照日期、审核状态徽章）；
>    - 页面底部提供来源直达外链（`rel="noopener noreferrer" target="_blank"`）与免个人信息纠错引导（指向 GitHub Issues）；
> 2. 更新 `src/pages/index.astro`：在搜索框下方增加「推荐词条」或「词条清单」区块，列出所有已发布条目；
> 3. `pnpm check` 0 错误通过；
> 4. `pnpm build` 编译通过；
> 5. git commit 'feat(pages): 词条详情页路由渲染与首页列表装配（D2/D4/D5）'。
> 回复：build 路由输出片段 + commit hash。」

**Step Breakdown:**
- [ ] Step 1: 编写 src/pages/articles/[id].astro 详情页组件
- [ ] Step 2: 更新 src/pages/index.astro 增加条目清单
- [ ] Step 3: pnpm check 校验类型与语法
- [ ] Step 4: pnpm build 验证路由静态编译
- [ ] Step 5: git commit 提交

---

### Task 2: 首批试点词条 1 — 异常子宫出血的识别与就医时机 [Role: Content Specialist]

**Files:**
- Create: `src/content/articles/abnormal-uterine-bleeding.mdx`

**Domain / Context:**
- 对应核心画像需求（验证 Query #1「月经完了又出了一点点血 正常吗」与 Query #4「月经拖尾 咖啡色 一直不干净」）。
- 权威来源：默沙东诊疗手册大众版（中文）《异常子宫出血 (AUB)》 / FIGO 异常子宫出血分类体系。
- 来源 URL: `https://www.msdmanuals.cn/home/women-s-health-issues/symptoms-of-gynecologic-disorders/abnormal-uterine-bleeding`
- 快照日期: `2026-09-23`

**Content Invariants:**
- frontmatter 严格遵循 `src/content.config.ts`：
  - `source_url: 'https://www.msdmanuals.cn/home/women-s-health-issues/symptoms-of-gynecologic-disorders/abnormal-uterine-bleeding'`
  - `source_snapshot_date: '2026-09-23'`
  - `review_status: 'published'`
  - `review_interval_months: 12`
  - `reviewed_source: true`
  - `reviewed_copyright: true`
  - `reviewed_medical: false` (遵循 D4，未就位如实标 false)
  - `reviewed_sensitivity: true`
  - `has_individual_advice: false`
  - `lang: 'zh-CN'`
  - `red_flags`: 包含 2 条权威急症指征（WHO / ACOG / 中华妇产科共识来源）
- 正文严格遵循 `docs/specs/article-writing-guide.md`：
  - 正文首行 H1 标题
  - 来源摘要区（来源主张与本站判定分列，逐句可回溯）
  - 医学说明区（**严禁第二人称条件句**，全部采用第三人称人群枚举：适用人群 / 不适用人群 / 需医生评估人群，收口于医生判定）
  - 急症红旗区（与 `red_flags` 数组严格 1:1 双写对应）

**Subagent Prompt Scaffold (for /vault-exec):**
> 「在 D:\Code\know-her 编写首篇试点词条 `src/content/articles/abnormal-uterine-bleeding.mdx`。
> 1. frontmatter 必须通过 Zod strict 验证，字段符合 Task 2 规定；
> 2. `reviewed_medical: false`，遵循 D4 降级规范；
> 3. 正文通篇禁止出现「你 / 您」引导的条件行动指令，严格使用第三人称人群枚举；
> 4. `red_flags` 数组与正文急症红旗区块严格 1:1 双写；
> 5. `pnpm check` 验证零错误（Zod 验证通过）；
> 6. git commit 'content: 首篇试点词条-异常子宫出血的识别与就医时机（D4/D5）'。
> 回复：frontmatter 摘要 + check 验证结果 + commit hash。」

**Step Breakdown:**
- [ ] Step 1: 编写 abnormal-uterine-bleeding.mdx frontmatter 与正文
- [ ] Step 2: 依据 writing-guide 进行第二人称条件句自查与红旗双写校验
- [ ] Step 3: pnpm check 校验 Zod 与 Astro 类型
- [ ] Step 4: git commit 提交

---

### Task 3: 首批试点词条 2 — 正常月经周期的四大客观指标 [Role: Content Specialist]

**Files:**
- Create: `src/content/articles/normal-menstrual-cycle.mdx`

**Domain / Context:**
- 对应常识科普痛点（验证 Query #6「正常月经一般来几天算正常」）。
- 权威来源：FIGO 正常月经参数标准 (2018) / 中华医学会妇产科学分会妇科内分泌学组相关共识。
- 来源 URL: `https://www.who.int/zh` (或 FIGO 官方指南可溯源 URL)
- 快照日期: `2026-09-23`

**Content Invariants:**
- frontmatter 严格遵循 `src/content.config.ts`：
  - `review_status: 'published'`
  - `reviewed_source: true`
  - `reviewed_copyright: true`
  - `reviewed_medical: false` (遵循 D4，未就位如实标 false)
  - `reviewed_sensitivity: true`
  - `has_individual_advice: false`
  - `lang: 'zh-CN'`
  - `red_flags`: 包含至少 1 条周期极端异常的急症就医指征
- 正文严格遵循 `docs/specs/article-writing-guide.md`：
  - H1 标题
  - 阐明四大指标：周期长度（24–38天）、经期持续（≤8天）、经期规律性（周期差异 ≤7–9天）、失血量自评
  - 医学说明区（第三人称人群枚举，严禁「如果你...就...」）
  - 急症红旗区（与 `red_flags` 1:1 双写）

**Subagent Prompt Scaffold (for /vault-exec):**
> 「在 D:\Code\know-her 编写第二篇试点词条 `src/content/articles/normal-menstrual-cycle.mdx`。
> 1. frontmatter 必须通过 Zod strict 验证，字段符合 Task 3 规定；
> 2. `reviewed_medical: false`，遵循 D4 降级规范；
> 3. 正文通篇禁止出现第二人称条件句，严格使用第三人称人群枚举；
> 4. `red_flags` 数组与正文急症红旗区块严格 1:1 双写；
> 5. `pnpm check` 验证零错误；
> 6. git commit 'content: 第二篇试点词条-正常月经周期的四大客观指标（D4/D5）'。
> 回复：frontmatter 摘要 + check 验证结果 + commit hash。」

**Step Breakdown:**
- [ ] Step 1: 编写 normal-menstrual-cycle.mdx frontmatter 与正文
- [ ] Step 2: 依据 writing-guide 进行规范自查
- [ ] Step 3: pnpm check 校验通过
- [ ] Step 4: git commit 提交

---

### Task 4: 全链路端到端构建、静态检索与 RSS 综合验收 [Role: QA & Integrator]

**Files:**
- Verify: `dist/index.html`
- Verify: `dist/articles/abnormal-uterine-bleeding/index.html`
- Verify: `dist/articles/normal-menstrual-cycle/index.html`
- Verify: `dist/pagefind/`
- Verify: `dist/rss.xml`

**Acceptance Criteria:**
1. `pnpm check` 零错误；
2. `pnpm build` 成功执行：
   - 详情路由 `/articles/abnormal-uterine-bleeding/` 与 `/articles/normal-menstrual-cycle/` 成功静态生成；
   - 编译后的详情页 HTML 包含 `UnreviewedBanner`、`RedFlagCard`、`MedicalDisclaimer` 及 `ArticleSchema` JSON-LD；
   - Pagefind 索引页面数由 1 页增加至 3 页，索引覆盖新词条；
   - `dist/rss.xml` 正确包含两篇 published 词条的 `<item>`（含 link、title、description、guid）；
3. 仓库 git 状态 clean，台账更新为 100%。

**Subagent Prompt Scaffold (for /vault-exec):**
> 「在 D:\Code\know-her 执行全链路综合验收与构建检查。
> 1. 执行 `pnpm check` 并记录诊断日志；
> 2. 执行 `pnpm build` 并检查路由生成列表；
> 3. 抽查生成的 HTML 文件（检查 UnreviewedBanner、RedFlagCard、MedicalWebPage JSON-LD 标签真实存在）；
> 4. 检查 `dist/rss.xml` 确认已收录 2 篇条目；
> 5. 检查 `dist/pagefind/` 确认索引页面数为 3；
> 6. git status 确认工作树状态；
> 7. git commit 'test: 全链路构建、Pagefind 索引与 RSS 发布验收通过'（如有必要微调或格式整理）。
> 回复：验收核验报告各项证据。」

**Step Breakdown:**
- [ ] Step 1: 运行 pnpm check 确保全站类型与 schema 校验通过
- [ ] Step 2: 运行 pnpm build 静态编译全站
- [ ] Step 3: 产物机械校验（HTML / Pagefind / RSS / Schema）
- [ ] Step 4: 台账 4/4 标记完成与 WORKMEMORY 结项
