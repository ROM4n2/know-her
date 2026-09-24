# PROJECT_OVERVIEW — know-her

> 60 秒项目 primer。新 agent 的第二读（读完 work.log 事件流之前先建立全局认知）。
> 维护规则：bootstrap 时由 agent 从代码库提炼生成初稿；此后每次 WORK_END / 交接后刷新。

## 这是什么项目

know-her —— 一个现代、温暖、科学的**每日两性健康科普与愉悦探索分享站**（2026-09-24 ADR-0002 确立最新定位）。

**核心理念**：
- **生活化与常态化**：从严肃的疾病自诊就医手册，转向日常两性健康、安全避孕、愉悦探索、身体生理机制与亲密关系沟通；
- **权威策展与零侵权**：无需人工医学专家交叉审核，以全网权威来源（WHO、果壳、谈性说爱、默沙东、丁香等）为基准，采用“**精选要点导读 + 权威出处直达外链**”的双轨模式（开放 CC 内容支持全文收录）；
- **隐私与轻量**：全静态站点，零数据库，零个人隐私收集。

**技术栈实现**：Astro 7.3.3 + TypeScript strict + Tailwind CSS v4 (`@tailwindcss/vite`) + Zod 轻量 Content Collection Schema + Pagefind 本地静态全文搜索 + RSS 2.0 订阅 + Schema.org Article 结构化数据 + GitHub Actions CI + GitHub Pages 自动化部署体系。

## 当前状态

- **最新架构决策（ADR-0002）已全面落地**：
  1. `src/content.config.ts`：彻底解除四段医学审核与强门禁，确立包含四大分类（`contraception` 避孕、`pleasure` 愉悦、`body` 身体、`intimacy` 亲密）的现代化轻量博客 Schema；
  2. 页面交互全面升级：首页精致卡片流（分类筛选、一句话导读速览、外链直达提示），文章详情页增加醒目的“前往原出处查阅原文”外链与核心看点 Callout；
  3. 首批 4 篇精选科普导读入库并全链路编译成功：
     - `contraception-condom-myths.mdx`（避孕套使用中的 5 个常见致命误区，引 WHO）
     - `female-pleasure-clitoris.mdx`（重新认识阴蒂：解构女性愉悦的隐藏冰山与高潮机制，引 果壳网）
     - `normal-menstrual-cycle.mdx`（正常月经周期的四大客观指标，引 FIGO / WHO）
     - `abnormal-uterine-bleeding.mdx`（异常出血速查：常见诱因剖析，引 默沙东大众版）
  4. 全链路校验通过：`pnpm check` 0 errors，`pnpm build` 成功生成 6 个静态路由，Pagefind 静态索引覆盖 5 个页面，RSS 2.0（`dist/rss.xml`）收录完整。

## 高频坑（踩过的雷区）

- 现象：Astro 5/7 与 Tailwind v4 不兼容 → 根因：`@astrojs/tailwind` 不支持 Tailwind v4 → 解法：改用 `@tailwindcss/vite` Vite 插件接入。
- 现象：TypeScript 7.0 破坏 `@astrojs/check` → 根因：TS 7 移除了 programmatic API → 解法：固定安装 `typescript@5.8.3`。
- 现象：Astro 7 内容集合必须放在 `src/content.config.ts` 并配合 `glob` loader。
- 现象：文章标签在 TS strict 下报 `implicitly has any type` → 解法：在模板 `.map((tag: string) => ...)` 中显式类型声明。
- 现象：版权侵权与搬运风险 → 根因：第三方权威文章多为保留版权 → 解法：ADR-0002 确立“策展导读（核心干货提炼 + 原文直达链接）”，合法引用零侵权。
