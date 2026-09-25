# 紧急状况交互决策树设计规格书 (Emergency Decision Guide Design Spec)

> **文档标识**：`docs/specs/2026-09-25-emergency-decision-guide-design.md`  
> **演化阶段**：路线 `2 -> 1` 第一阶段（方向二：紧急状况交互决策树；后续串联方向一：医学术语词典库）  
> **参考对标**：`canihavesex.today`（极简问答行动卡）与 `HowToLiveBetter`（循证处置要点）  
> **技术栈**：Astro 7 + TypeScript Strict + Tailwind CSS v4 + 纯客户端离线状态机  

---

## 1. Problem Statement & User Value (问题定义与用户价值)

### 1.1 现实痛点与目标场景
在两性与生殖健康领域，用户最紧急、搜索意图最强烈、恐慌感最高的时刻，往往是发生意外的瞬间：
1. **避孕突发事故**：避孕套滑脱、破裂、射精后留在体内、中途未全程佩戴；
2. **常规避孕脱漏**：短效口服避孕药（COC）漏服 1 天或连续漏服 2 天以上；
3. **突发身体信号**：月经干净后又见咖啡色分泌物、两次经期正中间微量点滴出血、同房后接触性出血。

在上述场景中，用户处于极度焦虑与内疚状态，**根本没有耐心和心力去通读几千字长篇大论或翻阅教科书**。现存商业搜索通常充斥着莆田系民营医院的“不孕不育/宫颈糜烂恐吓”或母婴论坛七嘴八舌的玄学谣言。

### 1.2 核心价值与成功指标
- **极速触达行动方案 (Time-to-Action <= 3 步)**：用户只需按顺序回答 2~3 个选择题，即可在 15 秒内获得清晰、明确、符合 WHO 与 FIGO 指南的处置指令；
- **消除信息差与恐吓**：明确告知紧急避孕药的真实有效窗口（24h > 48h > 72h）、含铜节育环 120 小时终极备选、漏服补救原则以及排卵期出血的生理性本质；
- **医疗红旗硬预警**：对伴随剧烈腹痛、高热、撕裂样疼痛等急性体征，给出最高优先级的“立即前往公立医院急诊”红旗警示；
- **零隐私泄露底线**：决策树全部逻辑在用户浏览器本地离线运行，不向任何服务端发送请求，不留任何敏感记录。

---

## 2. User Journey & Core Flow (用户旅程与核心流)

```
[首页顶栏 / 导航入口 / Direct URL: /guide/decision-tree/]
                           │
                           ▼
            【第一步：选择当前的突发紧急状况】
 ┌─────────────────────────┼─────────────────────────┐
 ▼                         ▼                         ▼
【A. 避孕套破损/脱落】   【B. 短效避孕药漏服】     【C. 突发非经期出血】
 │                         │                         │
 Q1: 距同房过去了多久？   Q1: 漏服了几天？         Q1: 处于月经什么时期？
 (<24h / 24-72h / >72h)    (1天 / 连续>=2天)        (两次中间/经期拖尾/临近)
 │                         │                         │
 Q2: 处于月经周期的哪段？  Q2: 处于药板的哪一周？   Q2: 是否伴有剧烈腹痛/发热？
 (易孕排卵期 / 安全期 / 不清) (第1周 / 第2周 / 第3周)   (是红旗 / 否)
 └─────────────────────────┼─────────────────────────┘
                           │
                           ▼
            【第三步：即时生成《行动处置决策卡》】
 ┌────────────────────────────────────────────────────────┐
 │ • 状态指示：🟢 安全无虞 / 🟡 需尽快补救 / 🔴 警惕就医   │
 │ • 核心行动指令（1-2-3 步优先级排列）                  │
 │ • 关键时间窗口与成功率说明                            │
 │ • 验孕复核时间点（如同房后 14 天晨尿）                │
 │ • 关联权威科普词条直达（可点击展开深读）              │
 └────────────────────────────────────────────────────────┘
```

### 2.1 页面交互规范
- **单选推进**：每个问题仅提供 2~4 个互斥选项，点击选项后以平滑动画自动切入下一步；
- **无障碍回退**：每一步均提供“← 上一步”与“↺ 重新选择”按钮，支持修改前序选项；
- **一键分享与保存**：卡片右上方提供“📋 复制本条行动方案”按钮，方便发给伴侣或自存备忘。

---

## 3. Architecture & Data Models (架构设计与数据模型)

### 3.1 数据契约 (`src/data/decisionTree.ts`)

```typescript
export type DecisionUrgency = 'emergency' | 'warning' | 'info' | 'reassurance';

export interface DecisionOption {
  label: string;
  desc?: string;
  nextNodeId?: string;
  outcomeId?: string;
}

export interface DecisionNode {
  id: string;
  category: 'contraception_accident' | 'missed_pill' | 'abnormal_bleeding';
  question: string;
  hint?: string;
  options: DecisionOption[];
}

export interface DecisionOutcome {
  id: string;
  category: 'contraception_accident' | 'missed_pill' | 'abnormal_bleeding';
  urgency: DecisionUrgency;
  title: string;
  headline: string;
  actionItems: string[];
  timelineGuide?: string;
  redFlags?: string[];
  reassuranceNote?: string;
  relatedArticleSlug?: string;
  sourceAuthority: string;
}

export interface DecisionTreeData {
  initialCategories: Array<{
    id: string;
    title: string;
    icon: string;
    desc: string;
    startNodeId: string;
  }>;
  nodes: Record<string, DecisionNode>;
  outcomes: Record<string, DecisionOutcome>;
}
```

### 3.2 初始涵盖的核心决策分支（全量循证对齐 WHO / FIGO）

#### 分支 1：避孕套破损/滑脱/中途未戴 (Contraception Accident)
- **Outcome A1 (72h 黄金抢救)**：距离事故发生 <72 小时。推荐单剂左炔诺孕酮（1.5mg）或乌利司他。越早服用成功率越高（前 24h 高达 95%）。告知轻度恶心或点滴出血属正常药物反应。
- **Outcome A2 (120h 终极备选)**：距离事故发生 72~120 小时（3~5天）。普通口服紧急避孕药有效率骤降；推荐前往正规妇产科就诊放置含铜宫内节育器（Copper IUD），有效率仍超 99%。
- **Outcome A3 (>120h 随访监测)**：已错过紧急避孕窗口。切勿滥用大剂量药物；指导在事故发生后满 14 天使用晨尿验孕棒或前往医院查血 HCG。

#### 分支 2：短效口服避孕药 (COC) 漏服处置
- **Outcome B1 (漏服 1 片)**：立即补服漏服的药片（即便同一天服用 2 片），随后按原计划服药。无需额外防护，避孕效果依然受保护。
- **Outcome B2 (连续漏服 2 片以上 · 第 1 周)**：立即补服最近 1 片，后续常规服药，且未来 7 天内性行为**必须全程加用避孕套**；若过去 5 天内有无保护同房，需加服紧急避孕药。
- **Outcome B3 (连续漏服 2 片以上 · 第 2 周)**：补服最近 1 片，未来 7 天加用避孕套防护。
- **Outcome B4 (连续漏服 2 片以上 · 第 3 周)**：服完当前药板有效药后不进入停药期（或跳过安慰剂），直接开始下一板。

#### 分支 3：非经期或异常出血 (Abnormal Bleeding)
- **Outcome C1 (排卵期生理性点滴)**：两次月经正中间（第 12~16 天），无剧痛，持续 1~3 天。属于雌激素短暂波动内膜少量脱落，无需特殊用药，观察即可。
- **Outcome C2 (经期拖尾咖啡色)**：经期第 6~8 天咖啡色分泌物，为陈旧性氧化出血，属常见生理现象。
- **Outcome C3 (红旗警报 · 急诊/专科就诊)**：伴随剧烈撕裂样下腹痛、冷汗、异味脓性白带或同房剧痛。强警示排查黄体破裂、宫外孕或急性盆腔炎，建议立即挂公立医院急诊。

---

## 4. Edge Cases & Resilience (边界情况与韧性设计)

1. **用户中途返回与分支跳跃**：通过栈结构记录用户的路径历史 `history: string[]`，点击“返回上一步”严格逆向回退，状态无错乱。
2. **离线与断网可用性**：所有题库与判定逻辑内嵌在静态 JS 中，零异步 fetch，断网状态下决策树百分之百流畅运转。
3. **免责与知情提醒**：卡片底部恒常展示“本工具为循证常识速查，不能替代急诊或专科医师现场面诊”提示。
4. **URL Hash 定向直达**：支持带 Hash 直接定位（如 `/guide/decision-tree/#missed-pill`），方便文章详情页内链精准直达。

---

## 5. Test Strategy (验证与测试策略)

1. **状态机全连通性静态测试**：
   - 编写 `scripts/test_decision_tree.py`，遍历决策树所有 node 与 option，断言：
     - 每一个 `nextNodeId` 必须存在于 `nodes` 中；
     - 每一个 `outcomeId` 必须存在于 `outcomes` 中；
     - 不存在无法抵达的孤立节点（Orphan Nodes）与死胡同选项（Dead Ends）；
2. **类型检查**：`pnpm check`（Astro strict TS 校验 0 error）；
3. **构建产物验证**：`pnpm build` 确认静态页面顺利生成并被 Pagefind 索引覆盖。

---

## 6. 与方向一（医学术语词典库）的串联规划

完成方向二后，决策树中涉及的专业名词（如“左炔诺孕酮”、“含铜IUD”、“黄体期”、“PALM-COEIN”、“紧急避孕窗口”）将直接与方向一的 **Glossary 词典**实现联动锚定，形成完整的“速查 ➔ 行动 ➔ 词典深度研读”知识闭环。
