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
  3. 已上线 11 篇精选权威科普导读（涵盖避孕套误区、紧急避孕药、短效口服避孕药COC、安全套权威指南、阴蒂解剖与愉悦冰山、人体润滑剂选型、女性自慰与性心理、月经四大客观指标、异常出血诱因、HPV疫苗与宫颈筛查、FRIES知情同意法则）；所有外链 100% 在线探测 200 OK；
  4. 生产流水线打通：GitHub Actions CI 校验通过，Deploy to GitHub Pages 自动化发布通过，线上 `https://rom4n2.github.io/know-her/` 实测 200 OK，CSS/JS 资源与 Pagefind 索引正常；
  5. 每日任务与互动闭环上线：首页置顶「今日精选科普 + 每日一答 30 秒速测」组件（确定性积日轮换、localStorage 连续打卡记天数）；配置 `.github/workflows/daily-routine.yml` 每天北京时间 08:00 定时全库外链 200 探针巡检并播报；CLI 支持 `pnpm curate:today` 查看每日排期；
  6. 开源规范达标：建立高标准 `README.md`、MIT `LICENSE`、`CONTRIBUTING.md` 与 `CODE_OF_CONDUCT.md`，GitHub 社区健康度跃升至 85%+；
  7. Pipeline B 每日自动化扩充工作流打通：开发 `scripts/curate_harvester.py`、`scripts/sources.json` 与 `.github/workflows/harvest-candidates.yml`，每日 08:30 自动扫描 WHO/默沙东权威入口并提交待审 Draft PR，杜绝 404 与凭空捏造，首篇候选 PR #1 已成功合并上线；
  8. 社交分享与交互体验升级：全站集成 Open Graph 与 Twitter Card 预览卡片（`public/og-card.svg`）；四大分类拥有独立静态路由（`/categories/[category]/`）；文章详情页新增“⏱️ 导读时长预估”与“📋 一键复制精炼要点卡片”；首页新增“🎲 随便逛逛”灵感漫游。

## 高频坑（踩过的雷区）

- 现象：Astro 5/7 与 Tailwind v4 不兼容 → 根因：`@astrojs/tailwind` 不支持 Tailwind v4 → 解法：改用 `@tailwindcss/vite` Vite 插件接入。
- 现象：TypeScript 7.0 破坏 `@astrojs/check` → 根因：TS 7 移除了 programmatic API → 解法：固定安装 `typescript@5.8.3`。
- 现象：Astro 7 内容集合必须放在 `src/content.config.ts` 并配合 `glob` loader。
- 现象：文章标签在 TS strict 下报 `implicitly has any type` → 解法：在模板 `.map((tag: string) => ...)` 中显式类型声明。
- 现象：版权侵权与搬运风险 → 根因：第三方权威文章多为保留版权 → 解法：ADR-0002 确立“策展导读（核心干货提炼 + 原文直达链接）”，合法引用零侵权。
- 现象：GitHub Pages 项目页样式丢失与链接 404 → 根因：默认根路径 `/` 在项目站点下未对齐二级目录 `/know-her/` → 解法：`astro.config.mjs` 配置 `site: 'https://rom4n2.github.io'` 与 `base: '/know-her'`，内部路由均走 `${import.meta.env.BASE_URL}`。
- 现象：外链原文 404 或内容不符 → 根因：大模型凭记忆捏造/脑补第三方文章 URL ID（如果壳文章编号、联合国未发布的 path）未在线探测 → 解法：全面换成默沙东/WHO/UNESCO 实测 200 OK 真实链接，`scripts/curate.py` 增加 `check-links` 在线探测，并在 `ci.yml` 和 `deploy.yml` 注入零 404 阻断门禁。
