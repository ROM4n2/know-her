# know-her 权威科普候选源自动抓取与草稿 PR 流水线实现计划 (Pipeline B)

> **Goal**: 实现每日自动化权威候选源扫描与草稿 PR 流水线（Pipeline B），通过定时任务监控 WHO/默沙东/UNESCO 等权威官方信源，基于关键词匹配过滤两性与生殖健康优质内容，进行真实 200 探针校验后自动生成标准化导读草稿并提交 Draft PR，读者与维护者可在 GitHub 网页/手机端一键审阅合并，实现半自动安全扩充文章。
> **Tech Stack**: Python 3.11+ (urllib + re + json) + GitHub Actions + GitHub CLI (`gh`) + Astro Content Collection
> **Spec Reference**: `docs/adr/ADR-0002.md`（双轨策展：A 轨手工贴入 + B 轨自动化候选抓取）
> **Global Constraints**:
> - **人机协同底线（Human-in-the-loop）**：绝对禁止无人值守直接向 `master` 分支推送未审文章；所有自动化抓取成果必须以 `Draft PR` 或 `Issue` 形式落地，由维护者点击 Merge 后触发发布。
> - **零 404 硬门禁**：抓取到的外链必须通过真实 HTTP HEAD/GET 探针，只有 200 OK 且包含有效标题的页面才能进入候选池。
> - **台账去重防护（Deduplication Ledger）**：维护 `scripts/.curate-ledger.json`，已收录、已提 PR 或已拒绝的 URL 永久记录哈希，防止定时任务重复骚扰。
> - **零额外重量级依赖**：爬虫与解析器采用 Python 标准库（`urllib`, `html.parser`, `re`），无需安装大型重量级爬虫框架，保持 CI 执行秒级极速。

---

### Task 1: 权威信源定义与台账去重引擎 (`curate_harvester.py`) [Role: Data & Tooling Builder]

**Files:**
- Create: `scripts/curate_harvester.py`
- Create: `scripts/sources.json` (权威官方数据源与抓取规则配置)
- Create: `scripts/.curate-ledger.json` (去重台账初始化)

**Interfaces:**
- `class SourceHarvester`:
  - `load_sources() -> list[SourceConfig]`
  - `fetch_candidate_links(source: SourceConfig) -> list[RawCandidate]`
  - `filter_and_dedup(candidates: list[RawCandidate]) -> list[ValidCandidate]`
- `scripts/sources.json`:
  ```json
  [
    {
      "name": "世界卫生组织 (WHO) 实况报道",
      "url": "https://www.who.int/zh/news-room/fact-sheets",
      "pattern": "https://www.who.int/zh/news-room/fact-sheets/detail/[a-zA-Z0-9-]+",
      "keywords": ["避孕", "月经", "人乳头瘤", "HPV", "性传播", "宫颈", "生殖", "性健康", "高潮"],
      "default_category": "contraception"
    },
    {
      "name": "默沙东诊疗手册大众版 女性健康",
      "url": "https://www.msdmanuals.cn/home/women-s-health-issues",
      "pattern": "https://www.msdmanuals.cn/home/women-s-health-issues/[a-zA-Z0-9/-]+",
      "keywords": ["出血", "月经", "阴道", "避孕", "性交", "阴蒂", "润滑", "生殖器", "盆腔"],
      "default_category": "body"
    }
  ]
  ```

**Subagent Prompt Scaffold (for /vault-exec):**
> "在 D:\\Code\\know-her 实现权威信源抓取与去重引擎。
> 1. 创建 `scripts/sources.json`，配置 WHO 中文实况报道与默沙东大众版女性健康核心入口与关键词匹配规则；
> 2. 创建 `scripts/curate_harvester.py`：
>    - 加载本地已收录文章（扫描 `src/content/articles/*.mdx`）的 `source_url` 并预热去重池；
>    - 访问数据源入口提取匹配规则的候选文章链接；
>    - 使用标准 User-Agent 发起在线探测，确保状态码为 200 且能提取 `<title>` 和正文摘要；
>    - 过滤已有链接，输出未收录的高价值候选清单；
> 3. 本地执行 `python scripts/curate_harvester.py --dry-run` 验证抽取准确性；
> 4. git commit 'feat(curate): 实现权威信源扫描与关键词候选抽取引擎'。"

**Step Breakdown:**
- [ ] **Step 1**: 创建 `scripts/sources.json` 规则文件
- [ ] **Step 2**: 编写 `scripts/curate_harvester.py` 抓取、解析、过滤与去重逻辑
- [ ] **Step 3**: 运行 dry-run 验证能否准确命中并解析出真实 200 OK 候选条目
- [ ] **Step 4**: 提交原子 commit

---

### Task 2: 自动草稿生成与 MDX 模板合成器 [Role: Content Engineer]

**Files:**
- Modify: `scripts/curate_harvester.py`
- Modify: `scripts/curate.py`

**Interfaces:**
- `generate_draft_article(candidate: ValidCandidate) -> DraftResult`
- 功能：
  1. 将候选网页的标题、清洗后的要点摘要、权威出处机构、已验证的 `source_url` 自动合成符合 `src/content.config.ts` Schema 的 `.mdx` 文件；
  2. 自动生成候选 slug（如 `contraception-who-family-planning`）；
  3. 正文中自动生成结构化的核心看点骨架与“原文直达”引导模块；
  4. 自动匹配对应的分类标签与初始速测题雏形。

**Subagent Prompt Scaffold (for /vault-exec):**
> "在 D:\\Code\\know-her 为候选抓取器增加自动合成草稿功能。
> 1. 扩充 `scripts/curate_harvester.py` 中的 `cmd_generate_draft()`：
>    - 接收抽取到的候选对象；
>    - 生成合规的 frontmatter（`title`, `pubDate`, `summary`, `category`, `source_url`, `source_name`, `tags`）；
>    - 写入 `src/content/articles/<slug>.mdx`；
> 2. 调用已有的 `curate.py check` 与 `curate.py check-links` 验证生成的草稿百分之百符合本库契约；
> 3. git commit 'feat(curate): 实现候选词条草稿自动合成与合规校验'。"

**Step Breakdown:**
- [ ] **Step 1**: 实现根据候选数据合成规范 MDX 草稿的模板引擎
- [ ] **Step 2**: 验证生成的测试草稿通过 `pnpm curate:check` 与 `pnpm curate:links`
- [ ] **Step 3**: 提交原子 commit

---

### Task 3: 自动化 GitHub Draft PR 提交模块 [Role: DevOps / Integration]

**Files:**
- Modify: `scripts/curate_harvester.py` (增加 `--create-pr` 参数)
- Modify: `package.json` (增加 `curate:harvest` 脚本)

**Interfaces:**
- `python scripts/curate_harvester.py --create-pr [--limit 1]`：
  1. 抓取并合成 1 篇最新优质候选草稿；
  2. 使用 git 自动创建特性分支 `candidate/<slug>`；
  3. 提交代码并推送至远端分支；
  4. 调用 `gh pr create --draft --title "..." --body "..."` 发起待审草稿 PR，附带原出处验证报告；
  5. 自动打上 `daily-candidate` 标签供维护者快速识别。

**Subagent Prompt Scaffold (for /vault-exec):**
> "在 D:\\Code\\know-her 集成 GitHub CLI 自动化 PR 发起能力。
> 1. 在 `scripts/curate_harvester.py` 中增加 `--create-pr` 分支处理：
>    - 检查是否在 git 工作区干净状态下运行；
>    - 创建隔离分支 `candidate/<slug>`，commit 新生成的草稿；
>    - 使用 `gh pr create --draft` 提交 Draft PR，PR 正文中列出原文链接、自动测试结果与待审 Checklist；
>    - 恢复当前工作分支至 master；
> 2. 在 `package.json` 注册快捷脚本 `"curate:harvest": "python scripts/curate_harvester.py"`；
> 3. 本地测试命令行参数与边界条件；
> 4. git commit 'feat(cli): 集成自动化特性分支创建与 GitHub Draft PR 发起流程'。"

**Step Breakdown:**
- [ ] **Step 1**: 编写基于 `gh` CLI 的分支创建与 Draft PR 提交逻辑
- [ ] **Step 2**: 配置 PR 模板与审核 Check-list
- [ ] **Step 3**: 本地 dry-run 验证分支与命令流
- [ ] **Step 4**: 提交原子 commit

---

### Task 4: GitHub Actions 每日自动化候选抓取与发 PR 工作流 [Role: SRE / CI Builder]

**Files:**
- Create: `.github/workflows/harvest-candidates.yml`
- Modify: `README.md` (增加流水线与维护说明)

**Workflow Schedule & Automation:**
- 触发方式：`schedule: - cron: '30 0 * * *'`（每天北京时间 08:30，在每日巡检之后执行）+ `workflow_dispatch`（支持手动一键运行）。
- 工作流权限：`contents: write`, `pull-requests: write`, `issues: write`。
- 执行流程：
  1. 检出代码，安装环境；
  2. 执行 `python scripts/curate_harvester.py --create-pr --limit 1`；
  3. 若当天探测到高质量新篇目，自动向仓库提交 1 篇 Draft PR；
  4. 若当天无新篇目或全部已收录，安静退出并输出报告至 Step Summary；
  5. PR 创建后，GitHub 移动端与网页端即时收到提醒，维护者点击 `Merge` 即可一键上线。

**Subagent Prompt Scaffold (for /vault-exec):**
> "在 D:\\Code\\know-her 创建每日自动化候选抓取 GitHub Actions 工作流。
> 1. 编写 `.github/workflows/harvest-candidates.yml`；
> 2. 配置工作流权限与定时 cron；
> 3. 使用 `GITHUB_TOKEN` 执行 `gh pr create`；
> 4. 运行本地 yaml 语法校验；
> 5. 更新 `README.md` 记录 Pipeline B 自动化机制；
> 6. git commit 'ci: 配置每日 08:30 自动化信源扫描与待审 Draft PR 提交工作流'。"

**Step Breakdown:**
- [ ] **Step 1**: 编写 `.github/workflows/harvest-candidates.yml`
- [ ] **Step 2**: 本地 yaml 语法检查
- [ ] **Step 3**: 更新 `README.md` 完善双轨维护文档
- [ ] **Step 4**: 提交原子 commit

---

### Task 5: 端到端联调与闭环发布 [Role: Lead Maintainer]

**Files:**
- 全链路验证

**Verification Criteria:**
1. 本地执行 `pnpm curate:harvest --dry-run` 成功展示抓取到的候选篇目；
2. 触发一次手动 `workflow_dispatch` 或本地模拟，成功生成规范的 Draft PR；
3. Draft PR 包含的 `.mdx` 自动通过 CI 中的 `pnpm check` 与 `pnpm curate:links`（零 404）；
4. 模拟合并该 PR，触发 `deploy.yml` 成功部署上线；
5. 更新 `WORKMEMORY/PROJECT_OVERVIEW.md` 归档。

**Step Breakdown:**
- [ ] **Step 1**: 运行本地抓取与草稿生成冒烟测试
- [ ] **Step 2**: 推送代码至 GitHub master
- [ ] **Step 3**: 触发 `workflow_dispatch` 测试远端 Draft PR 创建流程
- [ ] **Step 4**: 刷新项目概览并完成结项
