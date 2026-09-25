# PROJECT_OVERVIEW — know-her

> 60 秒项目 primer。新 agent 的第二读（读完 work.log 事件流之前先建立全局认知）。
> 维护规则：bootstrap 时由 agent 从代码库提炼生成初稿；此后每次 WORK_END / 交接后刷新。

## 这是什么项目

know-her —— 一个现代、温暖、科学的**每日两性健康科普与愉悦探索分享站**（2026-09-24 ADR-0002 确立最新定位）。

- **公开仓库**：`https://github.com/ROM4n2/know-her`
- **线上发布**：`https://rom4n2.github.io/know-her/`

**核心理念**：
- **生活化与常态化**：从严肃的疾病自诊就医手册，转向日常两性健康、安全避孕、愉悦探索、身体生理机制与亲密关系沟通；
- **权威策展与零侵权**：无需人工医学专家交叉审核，以全网权威来源（WHO、果壳、谈性说爱、默沙东、联合国教科文组织等）为基准，采用“**精选要点导读 + 权威出处直达外链**”的双轨模式（开放 CC 内容支持全文收录）；
- **隐私与轻量**：全静态站点，零数据库，零个人隐私收集。

**技术栈实现**：Astro 7.3.3 + TypeScript strict + Tailwind CSS v4 (`@tailwindcss/vite`) + Zod 轻量 Content Collection Schema + Pagefind 本地静态全文搜索 + RSS 2.0 订阅 + Schema.org Article 结构化数据 + GitHub Actions CI + GitHub Pages 自动化部署体系。

## 当前状态

- **最新架构决策（ADR-0002）已全面落地并成功上线**：
  1. `src/content.config.ts`：轻量科普博客 Schema（`contraception` 避孕、`pleasure` 愉悦、`body` 身体、`intimacy` 亲密四大主题）；
  2. 交互升级：首页分类实时客户端筛选、一句话导读卡片流、文章详情页醒目原出处直达跳转；
  3. 已上线 19 篇精选权威科普导读（涵盖安全套误区、紧急避孕药、短效口服药、安全套指南、宫内节育器IUD选型、阴蒂解剖与愉悦、润滑剂渗透压选型、女性自慰心理、性交疼痛/阴道痉挛、月经四大指标、异常出血诱因、HPV与宫颈筛查、痛经前列腺素机制、细菌性阴道病BV、假丝酵母菌/霉菌性阴道炎、子宫内膜异位症与腺肌病、FRIES知情同意、STIs性传播感染防治、亲密伴侣暴力与控制边界）；所有 19 篇外链 100% 在线探测 200 OK；
  4. 生产流水线打通：GitHub Actions CI 校验通过，Deploy to GitHub Pages 自动化发布通过，线上 `https://rom4n2.github.io/know-her/` 实测 200 OK，CSS/JS 资源与 Pagefind 索引正常；
  5. 每日任务与互动闭环上线：首页置顶「今日精选科普 + 每日一答 30 秒速测」组件（确定性积日轮换、localStorage 连续打卡记天数）；配置 `.github/workflows/daily-routine.yml` 每天北京时间 08:00 定时全库外链 200 探针巡检并播报；CLI 支持 `pnpm curate:today` 查看每日排期；
  6. 开源规范达标：建立高标准 `README.md`、MIT `LICENSE`、`CONTRIBUTING.md` 与 `CODE_OF_CONDUCT.md`，GitHub 社区健康度跃升至 85%+；
  7. Pipeline B 每日自动化扩充工作流打通：开发 `scripts/curate_harvester.py`、`scripts/sources.json` 与 `.github/workflows/harvest-candidates.yml`，每日 08:30 自动扫描 WHO/默沙东权威入口并提交待审 Draft PR，杜绝 404 与凭空捏造，首篇候选 PR #1 已成功合并上线；
  8. 社交分享与交互体验升级：全站集成 Open Graph 与 Twitter Card 预览卡片（`public/og-card.svg`）；四大分类拥有独立静态路由（`/categories/[category]/`）；文章详情页新增“⏱️ 导读时长预估”与“📋 一键复制精炼要点卡片”；首页新增“🎲 随便逛逛”灵感漫游；
  9. 信任基建与循证分级升级（全面吸纳 2026-09-25 竞品调研与可行性审计）：
     - 清除 Harvester 模板套话病句，彻底重写《安全套科学选用指南》，确立机器探活+人工深读边界；
     - PR 模板去机器自打勾；清理废弃死代码 `UnreviewedBanner.astro`；
     - 升级 Schema 支持 `evidence_tier`（Tier A/B/C）、`reviewed_by` 与 `last_verified_at`，全库 11 篇完成严谨分级与复审标注；
     - 上线「信任两页」：`/how-we-source/`（信源准入清单与循证定义）与 `/privacy/`（零收集三段论与本机打卡记录一键清空）；
     - SEO 与协议合规：集成 `@astrojs/sitemap` 生成 `sitemap-index.xml` + `robots.txt`，设定 GitHub 仓库 topics 与 homepage，归档 `CONTENT-LICENSE.md`（代码 MIT / 导读 CC BY-SA 4.0 分立）；
     - 外链探针降频分级：晨检仅探测今日精选（<1秒），新增 `.github/workflows/weekly-full-audit.yml` 每周日五态全量体检；
     - 文章详情页新增预填 GitHub Issue 勘误闭环通道；
  10. 紧急状况交互决策树上线（路线 2->1 第一阶段）：
     - 依据 WHO、FIGO 与默沙东临床指南编制 `src/data/decisionTree.ts` 题库与状态图；
     - 编写纯前端无埋点离线交互组件 `src/components/DecisionGuide.astro` 与独立路由 `/guide/decision-tree/`；
     - 覆盖三大高频意外：避孕套破裂滑脱（<24h, 24-72h, 72-120h, >120h）、短效口服避孕药连续漏服分周抢救、突发异常出血生理鉴别与急腹症红旗警报；
     - 配备《行动方案卡》一键复制、关键验孕复查时间表与站内深度词条锚定；
     - 编写 `scripts/test_decision_tree.py` 自动化图遍历测试，确立 100% 全连通零死胡同门禁；
  11. 两性健康与医学术语词典库上线（路线 2->1 第二阶段）：
     - 在 `src/content.config.ts` 增加 `glossary` collection，首批收录 16 个高频医学专有名词（涵盖左炔诺孕酮、含铜IUD、COC、储精囊、渗透压、阴蒂解剖、FIGO标准、PALM-COEIN等）；
     - 建立独立静态词典路由 `/glossary/`，集成实时关键词搜索、四大主题分类与 A-Z 首字母快速定位索引；
     - 文章详情页自动关联渲染「本文涉及的医学专有名词速查」卡片，降低专业阅读摩擦；
     - 编写 `scripts/test_glossary.py` 确保 100% 格式合规与外键文章存在性，并集成到 CI `pnpm test` 门禁中；
  12. 词条库大扩充（11 篇 ➔ 19 篇）与题库/词典联动：
     - 新增 8 篇高频痛点词条：痛经前列腺素机制、细菌性阴道病BV、外阴阴道假丝酵母菌病、宫内节育器IUD指南、性传播感染STIs防治、同房疼痛与阴道痉挛GPPPD、亲密关系暴力与控制边界、子宫内膜异位症与腺肌病；
     - 8 篇全部实测 WHO / 默沙东大众版 200 OK 真实链接，全库 19 篇 100% 探活全绿；
     - `src/data/dailyQuiz.ts` 题库同步扩容 8 道 30 秒速测知情题，覆盖全库 19 篇词条；
     - `src/content/glossary/` 同步扩充 6 个高频名词至 22 词条；
     - 静态构建产物扩充至 28 个路由页面。
  13. 落地知识库 `FRONTEND-DESIGN-PATTERNS` 规范（UI/UX 质感重塑）：
     - 注入 Paper & Ink Design Tokens（`--paper: #FAF8F5`, `--paper-card: #FFFFFF`, `--ink: #15140F`, `--ink-soft: #2A2620`），彻底告别廉价灰阶与冰冷模板感；
     - 移动端人体工学优化：部署 44px 黄金触控区移动端吸底操作栏（`Mobile Bottom Bar`：首页/应急速查/知识词典/随机漫游）；
     - 实体物理触感（Tactile Feedback）：卡片与按钮统一采用 `shadow-[2px_2px_0_rgba(21,20,15,...)]` 实体墨线与 `:active:translate` 微按压动效；
     - 文章详情页沉浸式长文阅读升级：新增顶部动态阅读进度条、1.85 黄金行距、柔墨黑（`#2A2620`）抗疲劳排版与表格/引用块美化。
  14. 落地纯前端离线实用健康工具箱（`/tools/`）：
     - 紧急避孕 72h / 120h 黄金窗口倒计时（左炔诺孕酮口服药 72h 递减区间 vs 医院急诊含铜IUD 120h 终极拦截）；
     - 短效口服避孕药 (COC) 漏服分周补救计算器（区分 21/28 片制、第 1/2/3 周漏服、跳过 7 天停药期核心规则与紧急避孕联动）；
     - 月经四大指标与经量自测评估（周期长度、持续天数、波动幅度、经量过多 AUB-HMB 判定与就医沟通小抄）；
     - 编写自动化验证门禁 `scripts/test_tools.py` 并接入 `pnpm test`，全站静态路由扩至 29 个页面。

## 高频坑（踩过的雷区）

- 现象：GitHub Actions 中 `setup-python@v5` 配置 `cache: "pip"` 导致 Action 启动即挂（exit 1） → 根因：仓库内仅使用 Python 标准库而未提供 `requirements.txt` 或 `pyproject.toml`，pip 缓存插件探测失败直接抛错中断 → 解法：移除 `cache: "pip"`，全标准库轻量运行零外部下载。
- 现象：Pipeline B 自动合成导读产生机械模板病句与假自证 → 根因：大模型盲目将标题插值进固定句式，PR 脚本自己替人勾选版权合规 → 解法：机器只抓取真实候选与元数据生成 TODO 草稿骨架，核心导读由人工通读原文提炼，PR Checklist 默认未勾选强制人工核验。
- 现象：外链探针频繁扫描导致告警噪音 → 根因：push/daily/weekly 三通道全量重扫 → 解法：分层降频——晨检仅测今日精选，PR 仅测变更文件，全库深度体检降为周度任务，支持 1in7 风格的五态判定。

- 现象：Astro 5/7 与 Tailwind v4 不兼容 → 根因：`@astrojs/tailwind` 不支持 Tailwind v4 → 解法：改用 `@tailwindcss/vite` Vite 插件接入。
- 现象：TypeScript 7.0 破坏 `@astrojs/check` → 根因：TS 7 移除了 programmatic API → 解法：固定安装 `typescript@5.8.3`。
- 现象：Astro 7 内容集合必须放在 `src/content.config.ts` 并配合 `glob` loader。
- 现象：文章标签在 TS strict 下报 `implicitly has any type` → 解法：在模板 `.map((tag: string) => ...)` 中显式类型声明。
- 现象：版权侵权与搬运风险 → 根因：第三方权威文章多为保留版权 → 解法：ADR-0002 确立“策展导读（核心干货提炼 + 原文直达链接）”，合法引用零侵权。
- 现象：GitHub Pages 项目页样式丢失与链接 404 → 根因：默认根路径 `/` 在项目站点下未对齐二级目录 `/know-her/` → 解法：`astro.config.mjs` 配置 `site: 'https://rom4n2.github.io'` 与 `base: '/know-her'`，内部路由均走 `${import.meta.env.BASE_URL}`。
- 现象：外链原文 404 或内容不符 → 根因：大模型凭记忆捏造/脑补第三方文章 URL ID（如果壳文章编号、联合国未发布的 path）未在线探测 → 解法：全面换成默沙东/WHO/UNESCO 实测 200 OK 真实链接，`scripts/curate.py` 增加 `check-links` 在线探测，并在 `ci.yml` 和 `deploy.yml` 注入零 404 阻断门禁。
