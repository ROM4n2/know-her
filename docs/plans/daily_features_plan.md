# know-her 每日科普与任务闭环实现计划 (Daily Features Plan)

> **Goal**: 落地 know-her「每日科普与任务闭环体系」，涵盖前端「今日精选科普 + 每日知情速测卡片（打卡互动）」与工程端「每日 GitHub Actions 定时巡检 + 自动化候选推送工作流」，彻底激活“每日性知识分享站”的生命力。
> **Tech Stack**: Astro 7.3.3 + TypeScript strict + Tailwind CSS v4 + Zod + LocalStorage + GitHub Actions Cron
> **Spec Reference**: `docs/adr/ADR-0002.md`（双轨策展与每日分享机制）
> **Global Constraints**:
> - 零服务端依赖：打卡天数与做题记录纯本地客户端存储（`localStorage`），零个人隐私收集。
> - 零 404 硬门禁：任何每日推荐与新增外链必须经由 `pnpm curate:links` 真实探测 200 OK。
> - 遵循无依赖与确定性原则：今日精选推荐算法按公历日期（Day of Year）在全库 200 验证文章中确定性轮换，刷新页面不抖动。

---

### Task 1: 每日速测数据契约与题库映射 [Role: Data Architect]

**Files:**
- Create: `src/data/dailyQuiz.ts`
- Modify: `src/content.config.ts` (可选扩充或保持解耦)
- Test: `tests/dailyQuiz.test.ts` 或 CLI 验证

**Interfaces:**
- `DailyQuizItem`: `{ articleId: string, question: string, options: string[], correctIndex: number, explanation: string }`
- 导出 `getTodayPick(articles, date?: Date)`: 根据公历年份第几天（Day of Year）对文章列表做确定性模运算，返回今日主推词条及关联速测题。

**Subagent Prompt Scaffold (for /vault-exec):**
> "在 D:\\Code\\know-her 实现每日速测题库与确定性轮换计算器。
> 1. 创建 `src/data/dailyQuiz.ts`，为当前 10 篇精选词条各配置 1 道极具启发性与趣味性的单选题（例如避孕套误区、润滑剂油基禁忌、月经天数允许波动、FRIES知情同意等）；
> 2. 实现 `getTodayIndex(totalCount: number, now?: Date): number`，以当前北京时间日期的 UTC+8 积日进行取模，确保当天全站读者看到一致的今日精选；
> 3. 运行 node/pnpm 测试验证算法在跨天与边界条件下的稳定性；
> 4. git commit 'feat(data): 建立每日科普速测题库与确定性推荐计算模块'。"

**Step Breakdown:**
- [ ] **Step 1**: 编写 `src/data/dailyQuiz.ts`，定义数据接口并灌入当前 10 篇核心词条的高质量速测题
- [ ] **Step 2**: 实现 `getTodayIndex` 与 `getTodayFeatured` 辅助函数
- [ ] **Step 3**: 运行自动化单测/脚本验证返回值合法性与确定性
- [ ] **Step 4**: 提交原子 commit

---

### Task 2: 首页「今日精选 & 每日一答打卡」交互组件 [Role: Frontend Builder]

**Files:**
- Create: `src/components/DailyCard.astro`
- Modify: `src/pages/index.astro`

**Interfaces:**
- `DailyCard.astro`: 置顶渲染于首页 Hero 与分类条之间。
- 交互能力：
  1. 展示今日精选科普推荐卡（带日期、分类徽章、核心导读）；
  2. 嵌入「每日 30 秒知情速测」：2~3 个可点击选项，用户点击后即时反馈对错、展开权威医学解释与“阅读完整导读”按钮；
  3. 「今日打卡」状态与连续阅读天数计数（基于 `localStorage.getItem('know_her_streak')`）。

**Subagent Prompt Scaffold (for /vault-exec):**
> "在 D:\\Code\\know-her 开发首页今日精选与速测打卡组件 `src/components/DailyCard.astro`。
> 1. 采用 Tailwind CSS 卡片设计，背景渐变（如 rose-50/blue-50），带有精致的每日日历徽章；
> 2. 包含两段式交互：
>    - 左侧/上方：今日主推文章一览与直达；
>    - 右侧/下方：交互式每日一问，点击选项即时高亮正确/错误，展示简短解析；
> 3. 客户端脚本记录答题打卡天数（以 `know_her_last_checkin` 记录 YYYY-MM-DD，连续递增 `know_her_streak`）；
> 4. 将其引入并装配至 `src/pages/index.astro`；
> 5. `pnpm check && pnpm build` 编译通过；
> 6. git commit 'feat(ui): 首页新增今日精选卡片与每日速测打卡组件'。"

**Step Breakdown:**
- [ ] **Step 1**: 编写 `src/components/DailyCard.astro`
- [ ] **Step 2**: 在 `src/pages/index.astro` 引入并装配至首屏推荐区
- [ ] **Step 3**: 验证响应式布局（手机端与桌面端自适应）
- [ ] **Step 4**: `pnpm check` 与 `pnpm build` 校验
- [ ] **Step 5**: 提交原子 commit

---

### Task 3: 策展 CLI 增加每日任务与预览支持 [Role: Tooling Engineer]

**Files:**
- Modify: `scripts/curate.py`
- Modify: `package.json`

**Interfaces:**
- `python scripts/curate.py daily [--date YYYY-MM-DD]`：
  1. 输出今日推荐的文章信息、对应速测题目及解析；
  2. 验证该文章外链是否为 200 OK；
  3. 若指定日期，可预览未来任何一天的排期轮换情况。
- `package.json` 注册快捷命令 `"curate:today": "python scripts/curate.py daily"`。

**Subagent Prompt Scaffold (for /vault-exec):**
> "在 D:\\Code\\know-her 增强 `scripts/curate.py`。
> 1. 新增 `daily` 子命令：
>    - 计算并展示指定日期（默认当天）的主推词条、作者与来源；
>    - 对今日主推词条的外链发起即时可达性探测；
> 2. 在 `package.json` 增加 `curate:today`；
> 3. 运行 `pnpm curate:today` 验证输出格式；
> 4. git commit 'feat(cli): curate.py 增加 daily 每日排期查看与巡检子命令'。"

**Step Breakdown:**
- [ ] **Step 1**: 修改 `scripts/curate.py` 增加 `daily` 逻辑
- [ ] **Step 2**: `package.json` 注入 `curate:today` 脚本
- [ ] **Step 3**: 本地执行验证输出
- [ ] **Step 4**: 提交原子 commit

---

### Task 4: GitHub Actions 每日自动化巡检与候选工作流 [Role: SRE / DevOps]

**Files:**
- Create: `.github/workflows/daily-routine.yml`
- Create: `.github/ISSUE_TEMPLATE/daily-candidate.md` (候选模版)

**Workflow Schedule & Actions:**
- 定时：每天 UTC 00:00（北京时间早上 08:00）。
- 自动化作业内容：
  1. 运行 `pnpm curate:check` + `pnpm curate:links`，执行全库 200 OK 探针巡检；
  2. 运行 `pnpm curate:today`，将今日推荐词条与健康状态自动输出至 GitHub Actions Step Summary；
  3. 若外链巡检失败，自动创建/更新名为 `🚨 外链告警：发现失效死链` 的 Issue 提醒管理员维护。

**Subagent Prompt Scaffold (for /vault-exec):**
> "在 D:\\Code\\know-her 创建每日自动化巡检工作流 `.github/workflows/daily-routine.yml`。
> 1. 触发条件：`schedule: - cron: '0 0 * * *'` + `workflow_dispatch`；
> 2. 配置 pnpm 环境与 Node.js 24；
> 3. 步骤：
>    - 检出代码并安装依赖；
>    - 执行 `pnpm curate:check`；
>    - 执行 `pnpm curate:links` 进行全网真实 200 探针；
>    - 执行 `pnpm curate:today` 并将结果追加至 `$GITHUB_STEP_SUMMARY`；
>    - 若失败则通过 gh issue create 或 action 提告警 Issue；
> 4. 使用 yaml 校验器验证工作流语法；
> 5. git commit 'ci: 配置每日晨间 08:00 定时巡检与健康播报工作流'。"

**Step Breakdown:**
- [ ] **Step 1**: 编写 `.github/workflows/daily-routine.yml`
- [ ] **Step 2**: 本地 yaml 语法检查
- [ ] **Step 3**: 提交原子 commit

---

### Task 5: 全链路构建、真机端到端验收与发布 [Role: Lead Maintainer]

**Files:**
- 全局联动校验

**Verification Criteria:**
1. `pnpm curate:check` 100% 格式合规；
2. `pnpm curate:links` 10 篇词条原文外链实测 200 OK；
3. `pnpm curate:today` 成功打印今日排期与速测题；
4. `pnpm check` 0 errors, 0 warnings；
5. `pnpm build` 100% 编译成功；
6. push 至 GitHub，触发 CI 与 Pages 部署，线上页面确认「今日精选 & 每日一答」渲染正常。

**Step Breakdown:**
- [ ] **Step 1**: 本地全量测试命令串行跑通
- [ ] **Step 2**: 推送远程分支触发 GitHub Actions
- [ ] **Step 3**: curl 验证线上渲染与功能完整性
- [ ] **Step 4**: 刷新 `WORKMEMORY/PROJECT_OVERVIEW.md` 归档结项
