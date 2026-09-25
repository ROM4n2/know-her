# 紧急状况交互决策树实现计划 (Emergency Decision Guide Implementation Plan)

> **Goal**: 落地 know-her「“我该怎么办？”紧急状况交互决策树与速查行动指南」，帮助面临避孕事故、漏服药物或异常出血恐慌的用户在 3 步内获得明确的循证处置指令与红旗就医预警。  
> **Tech Stack**: Astro 7 + TypeScript Strict + Tailwind CSS v4 + 客户端离线状态机 + Python 图结构断言测试  
> **Spec Reference**: `docs/specs/2026-09-25-emergency-decision-guide-design.md`  
> **Global Constraints**:  
> - **纯前端离线运行**：零服务端依赖，零数据收集（完全契合 `privacy.astro` 声明）；  
> - **图连通性强校验**：决策树所有边和结果节点必须经 Python 测试脚本 100% 验证无死胡同、无孤岛节点；  
> - **人机协同与主线程直接执行**：全流程在主线程内完成，不派发子代理。  

---

### Task 1: 决策树数据模型与图结构数据契约 (`src/data/decisionTree.ts`) [Role: Data Architect]

**Files:**
- Create: `src/data/decisionTree.ts`
- Create: `scripts/test_decision_tree.py` (自动化图连通性与节点完整性测试)

**Interfaces:**
- `export interface DecisionTreeData` (含 `initialCategories`, `nodes`, `outcomes`)
- `export const DECISION_TREE: DecisionTreeData`
- 覆盖三大核心分支：
  1. `contraception_accident`（避孕套破损/滑脱/中途才戴：<24h, 24-72h, 72-120h, >120h）
  2. `missed_pill`（短效COC漏服：漏服1天、连续漏服2天以上第1周/第2周/第3周）
  3. `abnormal_bleeding`（非经期出血：排卵期生理点滴、经期拖尾咖啡色、剧痛红旗警报）

**Step Breakdown:**
- [ ] **Step 1**: 编写图完整性测试脚本 `scripts/test_decision_tree.py`（RED：文件尚不存在）
- [ ] **Step 2**: 编写 `src/data/decisionTree.ts` 完整类型定义与节点图数据
- [ ] **Step 3**: 运行 `python scripts/test_decision_tree.py` 验证图遍历 100% 连通（GREEN）
- [ ] **Step 4**: 提交原子 commit

---

### Task 2: 交互式决策树组件实现 (`src/components/DecisionGuide.astro`) [Role: Frontend Engineer]

**Files:**
- Create: `src/components/DecisionGuide.astro`

**Interfaces:**
- 接收初始分类并维护本地选项路径栈 (`history: string[]`)；
- 支持单选平滑切题、无障碍“上一步”回退与“重选”；
- 结果态渲染：
  - 紧急度状态徽章（🟢 正常安心 / 🟡 尽快补救 / 🔴 警惕就医）；
  - 1-2-3 优先级处置清单；
  - 关键时间窗口与有效率说明；
  - 验孕复查时间提醒；
  - 一键复制行动方案卡片；
  - 对应站内深度科普词条直达外链。

**Step Breakdown:**
- [ ] **Step 1**: 编写 `DecisionGuide.astro` 结构与样式
- [ ] **Step 2**: 编写客户端轻量状态机 JS 逻辑（支持 history 栈与剪贴板复制）
- [ ] **Step 3**: 验证各分支状态切换与回退无抖动

---

### Task 3: 独立路由页与全站导航入口整合 [Role: Integration Engineer]

**Files:**
- Create: `src/pages/guide/decision-tree.astro`
- Modify: `src/layouts/Base.astro` (顶栏加入“⚡ 应急速查”导航)
- Modify: `src/pages/index.astro` (首页检索区加入“⚡ 紧急状况速查”直达按钮)

**Interfaces:**
- 独立 URL：`/guide/decision-tree/`
- 支持 URL Hash 快速直达特定分类（如 `#condom`, `#missed-pill`, `#bleeding`）
- 完备的 SEO、Open Graph 与社交分享卡片配置

**Step Breakdown:**
- [ ] **Step 1**: 编写 `src/pages/guide/decision-tree.astro` 页面
- [ ] **Step 2**: 在 `Base.astro` 顶栏增加直达链接
- [ ] **Step 3**: 在 `index.astro` 首页增加显式应急按钮
- [ ] **Step 4**: 提交原子 commit

---

### Task 4: 端到端静态编译、图测试与外链巡检门禁 [Role: QA / Lead]

**Files:**
- Verification only

**Step Breakdown:**
- [ ] **Step 1**: 运行 `python scripts/test_decision_tree.py`
- [ ] **Step 2**: 运行 `pnpm curate:check && pnpm curate:links`
- [ ] **Step 3**: 运行 `pnpm check && pnpm build` 确认 19+ 静态页面全绿编译并被 Pagefind 索引覆盖

---

### Task 5: 推送远端、CI/Pages 验证与工作记忆归档 [Role: Lead Maintainer]

**Files:**
- Modify: `WORKMEMORY/PROJECT_OVERVIEW.md`

**Step Breakdown:**
- [ ] **Step 1**: Git commit 并推送到远端 master
- [ ] **Step 2**: 监控 GitHub Actions 确认 CI 与 Pages 自动化部署成功
- [ ] **Step 3**: 真机 curl 验证线上站点 `/guide/decision-tree/` 返回 HTTP 200 OK
- [ ] **Step 4**: 刷新工作记忆文档
