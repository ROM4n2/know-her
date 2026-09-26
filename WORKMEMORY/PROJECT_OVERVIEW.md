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

- **当前状态（2026-09-26 方案 C 落地后）**：
  - **科普长文库**：25 篇精选权威科普导读（覆盖避孕、愉悦、身体、亲密四大领域，新增女上位深度控制与深部痛防护、侧卧匙羹与剪刀式力学低耗能、后入位入径力学与子宫后位撞击痛避坑）；
  - **两性医学词典**：28 个高频词条（新增《子宫后位》、《深部性交痛》、《解剖进入角度》）；
  - **每日 30 秒速测**：25 道循证知情题 1:1 闭环覆盖全库 25 篇文章；
  - **纯前端离线实用工具箱（/tools/）扩充至 7 大工具**：
    1. 紧急避孕 72h / 120h 黄金窗口倒计时（`EmergencyCountdown`）
    2. 短效口服避孕药 (COC) 漏服分周补救计算器（`CocRemedyCalculator`）
    3. 月经四大指标与经量自测评估（`CycleAssessment`）
    4. 性唤起“油门与刹车”双重控制模型自测盘点器（`ArousalBrakesChecklist`）
    5. 体位生理力学矩阵与伴侣探索知情清单（`PositionAndIntimacyGuide`）
    6. 全品类现代避孕知情选择与对比矩阵（`ContraceptionMatrix`）
    7. 门诊就诊沟通备忘录小抄生成器（`ClinicMemo`）
  - **全站静态路由**：35 个静态页面 + Pagefind 本地全文检索 100% 成功生成，全链路测试门禁（`pnpm test`）零错误零警告。

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
  15. 全站去 Emoji 严肃社论视觉重塑（遵循 `frontend-design`）：
     - 彻底清除导航、工具箱、应急决策树、词典、隐私声明与信源准则中的所有彩色原生系统 Emoji；
     - 替换为 Academic Modern Editorial 纸张墨水风格的专业排版与排版符号（单色 SVG 图标、`[ 准入清单 ]` 紧凑微标签、`01 // PRINCIPLE` 结构化编号与专业提示点）；
     - 全量 19 篇 MDX 词条标题统一去除装饰性 Emoji（`💡`、`📖`、`🚨`、`🩺`、`🔗` 等），全面回归出版级严肃循证质感；
     - 清理代码内未引用变量，全站编译零错误、零警告。
  16. 落地 `artifact`（极光帘幕 Aurora Veil）设计语言（方案 A + B）：
     - 提取 `artifact/` 中工业级微排版与 WebGL2 实时光幕渲染思路；
     - 开发 `src/components/AmbientHero.astro`，构建适配 `#FAF8F5` 温润纸底的柔粉珊瑚-暖桃-琥珀金三层呼吸有机光幕，支持光标与触控微摆动（Sway the veil）；
     - 落地大尺度字重对比（`KNOW HER`<br>`<span class="font-light">两性健康与自主愉悦探索</span>`）；
     - 引入宽字间距（`tracking-[0.28em]`）、荧光微光斑指示点（`shadow-[0_0_10px_rgba(244,63,94,0.7)]`）与毛玻璃半透徽标（`backdrop-blur-md`）；
     - 完善无障碍体验：响应 `prefers-reduced-motion`，支持 `IntersectionObserver` 离屏静默零 CPU 浪费。
  17. 愉悦探索与性爱技巧循证体系扩容（方案 C 落地）：
     - 突破单一插入迷思，扩容 3 篇性生理学与现代性心理学核心词条：
       • 《为什么女性需要更长时间？性唤起的时间生理学、帐篷效应与充分预热黄金期》（`pleasure-arousal-time-physiology`）；
       • 《打破单一插入迷思：CAT协调对位法与消除高潮鸿沟的解剖学技巧》（`pleasure-cat-technique-alignment`）；
       • 《我不是性冷淡，只是被动唤起：自发性 vs 响应性欲望与双重控制模型》（`pleasure-responsive-desire-dual-control`）；
     - 词典库同步扩容至 25 个医学词条（新增 `帐篷效应 (Tenting Effect)`、`CAT对位法 (Coital Alignment Technique)`、`双重控制模型 (Dual Control Model)`）；
     - 每日速测题库同步扩容 3 道知情题至 22 题闭环；
     - 上线第 4 大纯前端离线工具 `ArousalBrakesChecklist.astro`（性唤起“油门与刹车”自测盘点器，支持一键生成不伤人的伴侣沟通便签）。
     - 全站静态页面扩充至 32 个路由，测试门禁全部通过。
  18. 实用工具箱扩展至 6 大离线工具与 3 大场景分区（方案 A 落地）：
     - 建立 `src/data/contraceptionMethods.ts`（10 大现代避孕法）与 `src/data/clinicQuestions.ts`（4 大门诊主诉问诊逻辑与急腹症红旗预警）结构化数据集契约；
     - 落地 `ClinicMemo.astro`（门诊就医沟通备忘录小抄生成器）：支持 SOAP 格式一句话主诉生成、LMP 智能天数推算、医生追问清单、一键复制与 `@media print` 纸质打印；
     - 落地 `ContraceptionMatrix.astro`（全品类现代避孕知情选择与对比矩阵）：集成 6 维多标签即时筛选、珍珠指数典型/完美年失败率柱状对比、双选 PK 浮动条与侧边横向对比抽屉（零 innerHTML 严防 XSS）；
     - 重构 `src/pages/tools/index.astro` 为 3 大临床与生活场景分区（场景一：突发意外与黄金救援窗口、场景二：日常生理与身体自主管理、场景三：知情决策与门诊就医沟通）及 `[01]`~`[06]` 微导航定位；
     - 扩展 `scripts/test_tools.py` 自动化门禁，全站通过 `pnpm test` 全链路回归。
  19. 性生理力学与伴侣探索知情清单落地（方案 C 落地）：
     - 突破单一插入迷思与网络低俗姿势误导，扩容 3 篇性生理力学深度长文（女上位掌控度与深部痛防护、侧卧匙羹力学与低耗能、后入位曲度与子宫后位避坑）；
     - 词典库同步扩容至 28 个医学词条（新增子宫后位、深部性交痛、解剖进入角度），每日速测题库扩充至 25 题 100% 覆盖；
     - 建立 `positionMatrix.ts`（8 种循证体位、3 维力学条形指标）与 `intimacyChecklist.ts`（5 大脱敏分类 16 项点选与非暴力沟通话术）；
     - 落地第 7 大纯前端离线交互工具 `PositionAndIntimacyGuide.astro`，支持体位 6 维标签即时筛选、双选横向 PK 对比抽屉、Yes/No/Maybe 亲密沟通便签实时生成、一键复制与纸质打印；
     - 全站静态页面扩充至 35 个路由。
  20. 蜂群审查全景高危与阻塞缺陷系统性加固（Phase 1 落地）：
     - 修复移动端吸底导航遮挡悬浮对比条：`ContraceptionMatrix` 与 `PositionAndIntimacyGuide` 悬浮条调整为 `bottom-20 sm:bottom-6`，彻底避开 56px 底栏；`scripts/test_tools.py` 新增自动化断言；
     - 根除 4 处 `innerHTML` 残留：重构 `CycleAssessment`、`ArousalBrakesChecklist`、`DecisionGuide` 与 `DailyCard` 为纯 DOM 安全构建（`replaceChildren` / `createElement`），并在 `scripts/test_article_hygiene.py` 新增全组件零 innerHTML 静态门禁；
     - 修复 `curate.py` 403 异常漏报漏洞与 Zod `source_url` 协议校验：阻断 `javascript:` 等伪协议注入，403 重试遇 404/网络中断正确返回 False 阻断；编写 `scripts/test_security_contracts.py` 接入全量测试；
     - 本地存储异常防护与排版净化：`DailyCard` 增加 `safeGetItem` / `safeSetItem` 的 `try...catch` 降级容灾（防御 Safari 无痕模式崩溃）；净化 `AgePreferenceBanner` 中彩色 Emoji ⏰ 为单色学术印章 `[ 年龄确认 ]`；统一跨端积日模运算公式 `(day - 1) % totalCount` 与稳定排序；
     - CI/CD 拓扑优化与客户端 CSP 注入：`ci.yml` 忽略 master 分支避免双重构建，为 `deploy.yml` 与 `daily-routine.yml` 增加 `timeout-minutes: 10` 硬熔断，在 `Base.astro` 注入兼顾 Pagefind WASM 的客户端 CSP 与 Referrer-Policy 标头。

## 高频坑（踩过的雷区）

- 现象：Zod 原生 `z.string().url()` 放行 `javascript:alert(1)` → 根因：RFC 3986 规范视其为合法 URL 方案 → 解法：必须链式追加 `.refine(u => /^https?:\/\//i.test(u))` 限制仅放行 http/https 协议。
- 现象：Safari 无痕浏览模式或限制性 iframe 下访问 `localStorage` 抛出 `SecurityError` 导致整页脚本崩溃中断 → 根因：浏览器隐私沙盒直接禁止访问 Storage API → 解法：必须使用 `try...catch` 包裹所有 `getItem` / `setItem` 操作，并在失败时优雅降级为内存变量。
- 现象：悬浮组件在移动端被吸底导航栏覆盖无法点击 → 根因：全局移动底栏占据 `h-[56px] z-50`，而悬浮组件类名为 `bottom-6 z-40` → 解法：移动端断点追加 `bottom-20`（80px），桌面端恢复 `sm:bottom-6`。
- 现象：外链探测遇到 403 封锁时死链被误判为 200 通过 → 根因：重试逻辑中宽泛的 `except Exception:` 直接 `return True` 吞掉了 404/网络错误 → 解法：精确区分 HTTP 状态码，重试遇 404/410/500/网络中断坚决返回 `False`，仅二次确认 403 放行。
- 现象：GitHub Actions 中 `setup-python@v5` 配置 `cache: "pip"` 导致 Action 启动即挂（exit 1） → 根因：仓库内仅使用 Python 标准库而未提供 `requirements.txt` 或 `pyproject.toml`，pip 缓存插件探测失败直接抛错中断 → 解法：移除 `cache: "pip"`，全标准库轻量运行零外部下载。
- 现象：Pipeline B 自动合成导读产生机械模板病句与假自证 → 根因：大模型盲目将标题插值进固定句式，PR 脚本自己替人勾选版权合规 → 解法：机器只抓取真实候选与元数据生成 TODO 草稿骨架，核心导读由人工通读原文提炼，PR Checklist 默认未勾选强制人工核验。
- 现象：外链探针频繁扫描导致告警噪音 → 根因：push/daily/weekly 三通道全量重扫 → 解法：分层降频——晨检仅测今日精选，PR 仅测变更文件，全库深度体检降为周度任务，支持 1in7 风格的五态判定。

- 现象：Astro 5/7 与 Tailwind v4 不兼容 → 根因：`@astrojs/tailwind` 不支持 Tailwind v4 → 解法：改用 `@tailwindcss/vite` Vite 插件接入。
- 现象：TypeScript 7.0 破坏 `@astrojs/check` → 根因：TS 7 移除了 programmatic API → 解法：固定安装 `typescript@5.8.3`。
- 现象：部分文章正文前出现全站页脚文字（应急决策树、实用工具箱、声明等） → 根因：`curate_harvester.py` 模板误写了 `import MedicalDisclaimer` 与 `<MedicalDisclaimer />`，该组件本身为全站 `<footer>`，导致正文顶部重复渲染全站页脚打乱 DOM 流 → 解法：移除 MDX 中的多余组件，修正模板，落地 `scripts/test_article_hygiene.py` 自动化门禁拦截。
- 现象：Astro 7 内容集合必须放在 `src/content.config.ts` 并配合 `glob` loader。
- 现象：文章标签在 TS strict 下报 `implicitly has any type` → 解法：在模板 `.map((tag: string) => ...)` 中显式类型声明。
- 现象：版权侵权与搬运风险 → 根因：第三方权威文章多为保留版权 → 解法：ADR-0002 确立“策展导读（核心干货提炼 + 原文直达链接）”，合法引用零侵权。
- 现象：GitHub Pages 项目页样式丢失与链接 404 → 根因：默认根路径 `/` 在项目站点下未对齐二级目录 `/know-her/` → 解法：`astro.config.mjs` 配置 `site: 'https://rom4n2.github.io'` 与 `base: '/know-her'`，内部路由均走 `${import.meta.env.BASE_URL}`。
- 现象：外链原文 404 或内容不符 → 根因：大模型凭记忆捏造/脑补第三方文章 URL ID（如果壳文章编号、联合国未发布的 path）未在线探测 → 解法：全面换成默沙东/WHO/UNESCO 实测 200 OK 真实链接，`scripts/curate.py` 增加 `check-links` 在线探测，并在 `ci.yml` 和 `deploy.yml` 注入零 404 阻断门禁。
