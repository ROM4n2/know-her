# 需求验证（VALIDATION.md 产出）Implementation Plan

> **Goal**: 产出 D1 要求的 `VALIDATION.md`——1 个核心用户画像 + 10~20 条真实 query 的结果页映射证据 + 缺口声明与 GO/NO-GO 裁决建议。
> **Tech Stack**: 无代码（Markdown 证据集 + 公开 SERP 人工/工具取证）。站点栈（Astro + Zod + Pagefind，ADR-0001 D2）不在本计划实施范围。
> **Spec Reference**: `docs/adr/ADR-0001.md`（D1、Q1 行、Driver「需求真伪未验证」）
> **Global Constraints**:
> - 事实红线（用户项目铁律）：query 结果、站点、数字一律不得编造；每行证据带 URL + 检索日期 + 事实摘录；推测标『假设』；拿不准的事实列「待用户拍板」清单，禁止猜。违反即整行作废。
> - 验证后下结论（vault 铁律）：裁决只能从证据推出，禁止先定结论再找证据。
> - 研究型 TDD 替代法（本子计划对 skill TDD 不变量的显式偏差，已声明）：验收标准先行（RED）→ 证据采集（GREEN）→ 交叉复核（REFACTOR）→ 原子提交。
> - 证据行沿用 claim-ledger 惯例：每条证据标来源等级（primary/secondary/community）与置信度（high/medium/low）。
> - 判据先于取证冻结：Task 3 产出的判据在 Task 5 开始前冻结为只读；取证期间修改判据 = 本计划作废重跑（防动机性推理）。
> - 执行偏差显式留痕：任何对本计划的偏离写进 work.log NOTE，不静默改计划。
> - UTF-8 无 BOM 写入；work.log 事件 ≤4KB；预提交密钥扫描兜底。
> - 取证渠道现实约束：微信搜一搜等封闭 SERP 无法稳定存证 → 主证据用可无痕复现的公开 SERP（百度/必应/Google/知乎/小红书站内搜索），渠道差异在证据表标〔限制〕。
> - **不做范围**：不做站点实现、不做内容投放测试、不做多语言、不做审核人招募、不修改 IDEA.md / ADR-0001。
> - Scope Check：本文件仅为**子计划 1**。子计划 2（D2 脚手架 + schema CI）、3（四段审核流水线）、4（分发与纠错）待本计划裁决后另行编制。

---

### Task 1: 既有供给清单 [Role: Researcher / Evidence Collector]

**Files:**
- Create: `docs/research/supply-map.md`

**Interfaces:**
- Consumes: `docs/adr/ADR-0001.md`（Drivers 已点名：丁香医生、默沙东诊疗手册大众版中文、WHO 中文、KnowSex、谈性说爱 matters.love、res.knowsex.org）
- Produces: `docs/research/supply-map.md` 供给清单表（列：名称 / URL / 形态 / 覆盖主题 / 信任与审核机制 / 版权模式 / 来源等级+置信度 / 缺口观察）

**Subagent Prompt Scaffold (for /vault-exec):**
> "Implement Task 1: 既有供给清单。
> Goal: 逐站实访核实 ADR-0001 点名的既有供给，产出证据化供给清单表。
> Target Files: Create `docs/research/supply-map.md`。
> TDD Steps:
> 1. 先写验收标准（RED）：七列齐全；每行含 URL + 访问日期 + 事实摘录 + 来源等级/置信度；缺口观察列只写观察不写结论。
> 2. 确认表为空 → 验收不通过（RED 确认）。
> 3. 逐站访问取证填表（GREEN）；禁止用记忆填充，禁止编造站点特性；站点打不开的行标『无法核实』。
> 4. 跑验收：每行证据三要素齐全（REFACTOR 前置检查）。
> 5. 交叉复核：剔除无证据断言，补『假设』标注。
> 6. 追加 work.log NOTE（≤4KB）并 git add + 原子提交。
> Return: Summary with per-row evidence (URL + date) and an explicit list of rows you could NOT verify."

**Step Breakdown:**
- [ ] **Step 1: 写验收标准（RED）**
- [ ] **Step 2: 确认验收不通过**
- [ ] **Step 3: 逐站取证填表（GREEN，≥6 站，每站一个原子动作）**
- [ ] **Step 4: 跑验收：每行 URL+日期+摘录+等级齐全**
- [ ] **Step 5: 交叉复核、剔除记忆填充（REFACTOR）**
- [ ] **Step 6: git 原子提交**

---

### Task 2: 核心用户画像草案 + 用户拍板 [Role: Researcher] 〔含 Human Gate〕

**Files:**
- Create: `docs/research/persona.md`

**Interfaces:**
- Consumes: `IDEA.md`（受众描述）、`docs/adr/ADR-0001.md`（product-ux P0#1 的四类候选用户）
- Produces: `docs/research/persona.md` = 1 个画像（人口学与情境字段全部『假设』标注）+ 信息行为矩阵（渠道/搜索语言/设备/信任锚点）+ **待用户拍板问题清单（3~5 条）**

**Subagent Prompt Scaffold (for /vault-exec):**
> "Implement Task 2: 核心用户画像草案。
> Goal: 基于 IDEA.md 与 ADR-0001 的候选用户类型，产出 1 个核心画像草案与信息行为矩阵，并列出需要用户拍板的事实问题。
> Target Files: Create `docs/research/persona.md`。
> TDD Steps:
> 1. 先写验收标准（RED）：单画像；每个事实字段非『假设』即证据；信息行为矩阵含渠道/搜索语言/设备/信任锚点四维；待拍板清单 3~5 条且每条给 2~4 个候选选项。
> 2. 确认文件为空 → 验收不通过。
> 3. 起草画像与矩阵（GREEN）；候选选项只从 IDEA.md/ADR-0001 的四类候选用户推演，不得引入新的编造设定。
> 4. 跑验收并逐字段检查『假设』标注。
> 5. 复核：删除一切无法标注出处的断言（REFACTOR）。
> 6. 追加 work.log NOTE 并 git 原子提交。你无法向用户提问——把待拍板清单留在文件里，由编排者转交用户。
> Return: Summary + the exact 待拍板 questions (they will be relayed to the human)."

**Step Breakdown:**
- [ ] **Step 1: 写验收标准（RED）**
- [ ] **Step 2: 确认验收不通过**
- [ ] **Step 3: 起草单画像 + 信息行为矩阵（GREEN）**
- [ ] **Step 4: 跑验收：逐字段『假设』/证据检查**
- [ ] **Step 5: 复核剔除无出处断言（REFACTOR）**
- [ ] **Step 6: git 原子提交**
- [ ] **Step 7〔Human Gate〕: 待拍板清单交用户拍板 → 回填定稿版**（拍板前 Task 3 可并行起草、Task 5 不得开始）

---

### Task 3: 判据预注册（GO/NO-GO 阈值冻结）[Role: Analyst] 〔冻结点〕

**Files:**
- Create: `docs/research/gap-criteria.md`

**Interfaces:**
- Consumes: `docs/research/persona.md`（拍板版或草案版标明状态）、`docs/research/supply-map.md`
- Produces: `docs/research/gap-criteria.md` = 缺口成立判据 + 裁决矩阵（GO / 有条件 GO / NO-GO 三态定义）+ 冻结声明（冻结时间戳 + sha256，取证开始后只读）

**Subagent Prompt Scaffold (for /vault-exec):**
> "Implement Task 3: 判据预注册。
> Goal: 在任何取证之前冻结『缺口成立』判据，防动机性推理。
> Target Files: Create `docs/research/gap-criteria.md`。
> TDD Steps:
> 1. 先写验收标准（RED）：判据可逐条勾稽（对每条 query 的结果页能机械判定满足/不满足）；三态裁决矩阵互斥完备；含冻结声明区块。
> 2. 确认文件为空 → 验收不通过。
> 3. 起草判据（GREEN）。默认建议阈值（用户可在冻结前调整）：≥60% 的 query，其结果页前两屏无任何同时满足【来源可追溯 + 审核透明 + 非营销导流】三要件的供给，且 supply-map 中无可迁移填补渠道 → 缺口成立（GO）；介于中间 → 有条件 GO（限定主题/人群切入）；否则 NO-GO（转 D1 退出路线：供稿策展）。
> 4. 跑验收：任取 2 条示例 query 空跑勾稽流程确认可机械判定。
> 5. 复核三态互斥完备（REFACTOR），写入冻结声明（时间戳 + 文件 sha256）。
> 6. 追加 work.log DECISION 事件记录阈值冻结并 git 原子提交。冻结后本文件只读。
> Return: Summary + the frozen criteria verbatim."

**Step Breakdown:**
- [ ] **Step 1: 写验收标准（RED）**
- [ ] **Step 2: 确认验收不通过**
- [ ] **Step 3: 起草判据与三态矩阵（GREEN，默认阈值可被用户在冻结前改）**
- [ ] **Step 4: 空跑勾稽验证可机械判定**
- [ ] **Step 5: 写冻结声明：时间戳 + sha256（REFACTOR）**
- [ ] **Step 6: work.log DECISION + git 原子提交 → 文件转只读**

---

### Task 4: query 清单设计（10–20 条）[Role: Researcher]

**Files:**
- Create: `docs/research/query-list.md`

**Interfaces:**
- Consumes: `docs/research/persona.md`（信息行为矩阵）、`docs/research/supply-map.md`、`docs/research/gap-criteria.md`（只读）
- Produces: `docs/research/query-list.md` query 表（列：# / query 原文 / 语言 / 意图类型（症状问诊/知识科普/求助支持）/ 敏感度（高/低）/ 检索渠道 / 设计理由 / 来源等级+置信度）

**Subagent Prompt Scaffold (for /vault-exec):**
> "Implement Task 4: query 清单设计。
> Goal: 设计 10–20 条将用于取证的 query，覆盖画像信息行为的意图×敏感度组合。
> Target Files: Create `docs/research/query-list.md`。
> TDD Steps:
> 1. 先写验收标准（RED）：10–20 行；三类意图均有覆盖且各 ≥2 条；敏感/低敏感混合；每行有设计理由与来源标注『画像推演』——禁止声称『用户真实搜索』。
> 2. 确认表为空 → 验收不通过。
> 3. 设计 query 表（GREEN）：用词必须像真实的人会打的字（口语、错词容忍），query 渠道与画像矩阵一致。
> 4. 跑验收：意图×敏感度矩阵覆盖检查。
> 5. 复核：删掉只有行业黑话不像真人打的 query（REFACTOR）。
> 6. 追加 work.log NOTE 并 git 原子提交。
> Return: Summary + full query table."

**Step Breakdown:**
- [ ] **Step 1: 写验收标准（RED）**
- [ ] **Step 2: 确认验收不通过**
- [ ] **Step 3: 设计 10–20 条 query 表（GREEN）**
- [ ] **Step 4: 意图×敏感度覆盖验收**
- [ ] **Step 5: 去黑话化复核（REFACTOR）**
- [ ] **Step 6: git 原子提交**

---

### Task 5: SERP 取证组 A（query #1–⌈N/3⌉）[Role: Researcher / Evidence Collector] 〔与 Task 6/7 并行安全〕

**Files:**
- Create: `docs/research/serp-evidence-1.md`

**Interfaces:**
- Consumes: `docs/research/query-list.md`（组 A 行）、`docs/research/gap-criteria.md`（**只读**，冻结版）
- Produces: `docs/research/serp-evidence-1.md`——每 query 一节：检索渠道 + 检索日期 + 完整 query 字符串 + 前 5 结果（标题/URL/站点类型）+ 结果页观察（权威源占比 / 疑似仿冒或 SEO 农场 / 营销导流迹象）+ 三要件逐项判定 +〔限制〕+ 来源等级/置信度

**Subagent Prompt Scaffold (for /vault-exec):**
> "Implement Task 5: SERP 取证组 A。
> Goal: 对组 A 的 query 逐条取证今天的结果页，证据格式可机械勾稽 gap-criteria。
> Target Files: Create `docs/research/serp-evidence-1.md`。
> TDD Steps:
> 1. 先写验收标准（RED）：每 query 一节七要素齐全（渠道/日期/原文/前5结果/观察/三要件判定/限制）；三要件判定只允许『满足/不满足/无法判定』三值。
> 2. 确认文件为空 → 验收不通过。
> 3. 逐 query 取证（GREEN，每条一个原子动作）：无痕、不登录、记录完整 query 字符串；禁止因判据难满足而调整检索姿势。
> 4. 跑验收：逐节七要素检查。
> 5. 交叉复核（REFACTOR）：每条判定回勾 gap-criteria 原文条款号；无出处的『疑似仿冒』判断降级为『无法判定』。
> 6. 追加 work.log NOTE 并 git 原子提交。
> Return: Summary + per-query one-line result and any 无法核实 rows."

**Step Breakdown:**
- [ ] **Step 1: 写验收标准（RED）**
- [ ] **Step 2: 确认验收不通过**
- [ ] **Step 3: 逐 query 取证（每条一个原子动作，GREEN）**
- [ ] **Step 4: 逐节七要素验收**
- [ ] **Step 5: 判定回勾判据条款号（REFACTOR）**
- [ ] **Step 6: git 原子提交**

---

### Task 6: SERP 取证组 B（query ⌈N/3⌉+1–⌈2N/3⌉）[Role: Researcher / Evidence Collector] 〔与 Task 5/7 并行安全〕

**Files:**
- Create: `docs/research/serp-evidence-2.md`

**Interfaces / Subagent Prompt Scaffold / Step Breakdown:**
- 与 Task 5 完全同构，目标文件换 `docs/research/serp-evidence-2.md`，取证范围为组 B 行；同样的七要素、三值判定、判据回勾与禁止调整检索姿势约束。

---

### Task 7: SERP 取证组 C（query ⌈2N/3⌉+1–N）[Role: Researcher / Evidence Collector] 〔与 Task 5/6 并行安全〕

**Files:**
- Create: `docs/research/serp-evidence-3.md`

**Interfaces / Subagent Prompt Scaffold / Step Breakdown:**
- 与 Task 5 完全同构，目标文件换 `docs/research/serp-evidence-3.md`，取证范围为组 C 行。

---

### Task 8: 缺口声明与裁决汇总（VALIDATION.md）[Role: Analyst / Integrator] 〔含 Human Gate〕

**Files:**
- Create: `VALIDATION.md`（仓库根，D1 点名交付物）

**Interfaces:**
- Consumes: `docs/research/persona.md`（拍板版）、`docs/research/query-list.md`、`docs/research/serp-evidence-1..3.md`、`docs/research/gap-criteria.md`（冻结版）、`docs/research/supply-map.md`
- Produces: `VALIDATION.md` = ① 画像摘要（1 段）② 10–20 条 query 映射表（query / 结果页主要站点 / 三要件满足情况 / 证据链接）③ 缺口声明（对冻结判据逐条勾稽）④ 裁决建议（GO / 有条件 GO / NO-GO 三选一）⑤ 开放问题与〔限制〕汇总

**Subagent Prompt Scaffold (for /vault-exec):**
> "Implement Task 8: 缺口声明与裁决汇总。
> Goal: 把五份证据文件汇总为 D1 要求的 VALIDATION.md，按冻结判据给出三选一裁决建议。
> Target Files: Create `VALIDATION.md`。
> TDD Steps:
> 1. 先写验收标准（RED）：映射表行数 = query-list 行数；每行证据链接可达；判据逐条给出勾稽结果；裁决建议三选一且每条判据都指向证据行；无任何新增断言（只汇编既有证据）。
> 2. 确认文件为空 → 验收不通过。
> 3. 汇编写入（GREEN）：严格从证据文件汇编，缺口声明逐条引用判据条款号 + 证据文件行号。
> 4. 跑验收：行数、链接、勾稽完整性机械检查。
> 5. 复核（REFACTOR）：全文扫描确保无编造数字/站名/引语；『假设』与〔限制〕集中一节。
> 6. 追加 work.log WORK_END（含回写检查）+ 刷新 WORKMEMORY/PROJECT_OVERVIEW.md 当前状态 + git 原子提交。
> Return: Summary + the verbatim 裁决建议 (it will be put to the human for final decision)."

**Step Breakdown:**
- [ ] **Step 1: 写验收标准（RED）**
- [ ] **Step 2: 确认验收不通过**
- [ ] **Step 3: 汇编 VALIDATION.md（GREEN）**
- [ ] **Step 4: 机械验收：行数/链接/勾稽**
- [ ] **Step 5: 全文反编造复核（REFACTOR）**
- [ ] **Step 6: work.log WORK_END + PROJECT_OVERVIEW 刷新 + git 原子提交**
- [ ] **Step 7〔Human Gate〕: 裁决建议交用户拍板**（GO → 编制子计划 2；有条件 GO → 收窄后编制子计划 2；NO-GO → 执行 D1 退出路线，转供稿策展）

---

## 依赖图

```
Task 1 ──┐
Task 2 ──┼──> Task 3（冻结判据）──> Task 4 ──> Task 5/6/7（并行）──> Task 8 ──> 〔用户拍板〕
         │                                （Task 5 不得早于 Task 3 冻结）
（Task 2 拍板可与 Task 3 起草并行，Task 8 汇编须用拍板版）
```
