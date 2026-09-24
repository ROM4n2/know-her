# PROJECT_OVERVIEW — know-her

> 60 秒项目 primer。新 agent 的第二读（读完 work.log 事件流之前先建立全局认知）。
> 维护规则：bootstrap 时由 agent 从代码库提炼生成初稿；此后每次 WORK_END / 交接后刷新。

## 这是什么项目

know-her —— 一个依托 GitHub 开放协作的**妇科与性健康科普知识库**。核心原则（来自 IDEA.md，2026-09-22 版）：不转载全文，默认外链+短摘要，权威来源优先，来源/许可/审核人/审核日期/更新状态透明可追溯；GitHub Actions 自动任务只做发现和整理候选，**不经人工审核不发布**（审核链：来源核验 → 版权检查 → 医学准确性审核 → 敏感度审核）；社区可提交资料/纠错/翻译，但必须审核后才进正式内容；只做科普，不做诊断、处方或个体化医疗建议，敏感内容带年龄提示、免责声明、紧急就医提示；隐私优先，不收集病例或可识别个人信息；**静态站点部署，无后端数据库**；内容定期复审标过期。定位：可信、开放、尊重多元文化的中文/多语言健康知识库。

**技术栈实现**：Astro 7.3.3 + TypeScript strict + Tailwind CSS v4 (`@tailwindcss/vite`) + Zod v4 Content Collections Schema (`superRefine` 机器强制不变式) + Pagefind 本地静态全文搜索 + RSS 2.0 + Schema.org `MedicalWebPage` JSON-LD 结构化数据 + GitHub Actions CI (check + build 双阻断门禁) + lychee 外链巡检。

## 当前状态

- **方向已锁定**：2026-09-22 双镜共识 ADR-0001 (D1–D7) 全部落地。
- **子计划 1（需求验证）8/8 完成**：产出 `docs/VALIDATION.md`，用户拍板 D11=有条件 GO + 补证计划（敏感性口径 5/5 有效观察缺口成立，10 行受出口限制挂起等待网络就绪后补证）。
- **子计划 2（架构与工程准备）7/7 完成**：Astro 静态站骨架、Zod `.strict()` schema 校验、4 核心合规组件（免责声明/降级横幅/红旗卡/年龄偏好确认）、Pagefind 检索、CI 双 workflow、零个人信息 Issue 模板及四段审核 PR 模板全量上线。
- **子计划 3（内容建设与首批试点）4/4 完成**：
  - `/articles/[id]/` 动态路由渲染与首页列表装配就绪。
  - 首批 2 篇试点词条入库并发布：
    1. `abnormal-uterine-bleeding.mdx`（异常子宫出血：成因、表现与就医指征，引 MSD / ACOG / 中华医学会共识）
    2. `normal-menstrual-cycle.mdx`（正常月经周期四大客观指标，引 FIGO / WHO）
  - 严格执行 D4 降级标记（`reviewed_medical: false` + 正文警示横幅，不冒充医学复审）、禁止第二人称条件句（全部第三人称枚举）、急症红旗双写 1:1 严格对齐。
  - 全链路端到端验收 ALL PASS：`pnpm check` 0 errors，`pnpm build` 生成 4 个静态页面/路由，`dist/rss.xml` 包含 2 个条目，Pagefind 静态索引覆盖 3 页。
- **后续待办**：
  1. 远端仓库关联与 GitHub Pages / Cloudflare Pages 静态部署；
  2. 医学专业审核人招募（就位后可摘除 D4 降级横幅）；
  3. 网络就绪后按 `docs/VALIDATION.md` §⑤.5 执行 10 行 SERP 补证并重推档位。

## 高频坑（踩过的雷区）

- 现象：Astro 5/7 与 Tailwind v4 不兼容 → 根因：`@astrojs/tailwind` 不支持 Tailwind v4 → 解法：改用 `@tailwindcss/vite` Vite 插件接入。
- 现象：TypeScript 7.0 破坏 `@astrojs/check` → 根因：TS 7 移除了 programmatic API → 解法：固定安装 `typescript@5.8.3`。
- 现象：Astro 7 内容集合报找不到 config → 根因：Astro 7 弃用 `src/content/config.ts`，改为根下 `src/content.config.ts` + `glob` loader。
- 现象：`astro:content` 导出的 `z` 报 TS 弃用 → 根因：Astro 内置 z 是 zod v3 → 解法：独立引入 `zod` v4 包并使用 `z.ZodIssueCode.custom`。
- 现象：frontmatter 自造字段导致 build 失败 → 根因：schema 启用了 `.strict()` → 解法：词条标题写在正文首个 `# H1`，frontmatter 不得加 `title` 字段。
- 现象：出第二人称条件句（如「如果你...就...」）→ 根因：易滑向个体化诊疗建议（违反 `has_individual_advice: false`）→ 解法：一律改用第三人称人群枚举（「适用人群 A / 需医生评估人群 B」），结论收口于医生判定。
