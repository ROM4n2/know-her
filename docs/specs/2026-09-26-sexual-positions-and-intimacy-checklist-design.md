# 架构设计规格书：性生理力学矩阵、伴侣知情清单与深度科普体系 (方案 C)

- **文档状态**：Draft（等待用户最终审批）
- **日期**：2026-09-26
- **架构方案**：方案 C（Extensible: 深度科普系列 + 词典 + 体位生理矩阵 + 伴侣私密探索 Yes/No/Maybe 清单）
- **对应目标**：在全站科普库扩充 3 篇性生理学与体位力学核心文章、3 个医学词典词条，并在 `/tools/` 落地第 7 大纯前端离线交互工具《体位生理力学矩阵与伴侣探索知情清单》，彻底打破网络低俗杂技式姿势误导，建立去污名化、以女性解剖学与舒适度为基准的循证探索指南。

---

## 1. Problem Statement & User Value（问题陈述与用户价值）

### 1.1 痛点一：网络姿势猎奇化与女性生理脱节
- **现实场景**：
  网络流传的“姿势大全”大多源自色情片或追求杂技式高难度动作，充斥男性中心视角与表演性质。
- **核心摩擦**：
  1. **忽视阴蒂解剖**：70%~80% 的女性无法单纯通过抽插达到高潮，而绝大多数流行体位几乎完全避开了阴蒂头与前庭球的持续接触；
  2. **忽视深部碰撞痛与子宫解剖**：约 20% 的女性为子宫后位（Retroverted Uterus），或在排卵期/经前期存在黄体囊肿或盆腔充血。在后入位或深部插入时极易发生宫颈强力顶撞，引发撕裂样下腹剧痛（深部性交痛 Deep Dyspareunia），却常被误解为“娇气”或“性冷淡”；
  3. **体能透支与肌肉紧张**：许多体位需要过度消耗下肢与腰部核心力量，导致盆底肌反射性收紧痉挛，进一步破坏唤起过程。

### 1.2 痛点二：伴侣探索沟通壁垒与“拒斥焦虑”
- **现实场景**：
  在亲密关系中，无论是想尝试新动作、垫枕头调整角度，还是明确拒绝某种让自己疼痛的不适体位，双方往往难以启齿。
- **核心摩擦**：
  1. **开口尴尬**：担心提出调整会被对方误认为“嫌弃技巧”或“索求无度”；
  2. **拒绝愧疚**：不适时不敢喊停，长期忍受不适导致性厌恶；
  3. **缺少去情绪化的沟通载体**：国际性治疗临床中成熟的 **“Yes / No / Maybe” 知情清单** 能够去人格化地表达边界与偏好，但国内几乎没有中立、严谨、零隐私风险的中文工具。

### 1.3 用户价值
1. **解剖学知情平权**：将体位从“技巧杂耍”回归到“骨盆倾角、重心错位、阴蒂可达度与耗能等级”的生理物理学；
2. **零隐私泄露的探索便签**：提供纯前端单人自评或沟通清单生成器，一键导出体贴、积极、不伤自尊的《探索沟通小抄》。

---

## 2. User Journey & Core Flow（用户旅程与核心交互）

### 2.1 模块一：体位生理力学与知情选择矩阵 (Position Matrix)
```
[ 筛选偏好标签 (如防撞击/高阴蒂贴合) ] ➔ [ 8 大循证体位卡片网格 ] ➔ [ 展开生理受力/禁忌与改良建议 ] ➔ [ 双选横向 PK 对比 ]
```
1. **多维即时筛选器**：
   - `[ 全部收录 (8) ]`
   - `[ 阴蒂高频贴合 (Clitoral Contact) ]`
   - `[ 女性自主主导深度 (Female Control) ]`
   - `[ 低体能消耗/放松 (Low Energy) ]`
   - `[ 避免深部撞击痛 (Prevent Deep Pain) ]`
   - `[ 枕头硬垫辅助推荐 (Pillow Support) ]`
2. **卡片结构 (Academic Modern Editorial)**：
   - 姿势名称与解剖学别名（如：正向女上位 / 屈膝对位式）；
   - 三重核心参数条（阴蒂可达度指数、宫颈碰撞风险、体能消耗等级）；
   - 核心力学机制：进入轴线（Coital Angle）、骨盆支撑点；
   - 展开面板：核心优势 (PROS)、潜在弊端与适应 (CONS)、改良支点方案（如“臀下垫 10cm 硬枕”）；
   - 深度科普文章跳转（如 `pleasure-woman-on-top-mechanics`）；
   - 加入双项横向对比 (Head-to-Head PK)。

### 2.2 模块二：伴侣知情探索 Yes/No/Maybe 清单 (Intimacy Checklist)
```
[ 浏览 5 大类脱敏项目 ] ➔ [ 勾选 YES / MAYBE / NO ] ➔ [ 实时生成温和便签卡片 ] ➔ [ 一键复制/打印/重置 ]
```
1. **5 大类脱敏知情探索题库**（共 15~18 个结构化选项）：
   - `01 // 体位微调与角度`（如：骨盆下垫硬枕、CAT 贴合微磨、侧卧慢速深拥）
   - `02 // 预热与唤起时间`（如：15~20分钟纯外围预热、温水沐浴放松、全身肌肉抚触）
   - `03 // 辅助润滑与道具`（如：足量水基润滑剂补给、外用震动器协同刺激）
   - `04 // 节奏与深度界限`（如：女性主导进入速度、严禁突击性深插、设置随时可叫停的安全词）
   - `05 // 环境与感官调适`（如：柔和暖光昏暗环境、背景轻音乐、结束后温热毛巾与紧拥）
2. **三态选择（无感快速点选）**：
   - `[ 愿尝试 (YES) ]`：非常有兴趣，希望优先探索；
   - `[ 视情况 (MAYBE) ]`：条件成熟/沟通好前提下可以考虑；
   - `[ 明确不接受 (NO) ]`：当前红线，请勿施加压力。
3. **实时生成的《伴侣探索沟通便签》**：
   - 采用非暴力沟通 (NVC) 模板：“在我们的亲密时光里，我很期待尝试……同时目前希望避免……这能让我们更放松安全”；
   - 零隐私留存，支持一键纯文本复制、纸质打印、一键清空。

---

## 3. Architecture & Data Models（架构与数据模型）

### 3.1 目录结构与组件拓扑
```
src/
├── content/
│   ├── articles/
│   │   ├── pleasure-woman-on-top-mechanics.mdx   # 新增：女上位掌控度与深部痛防护
│   │   ├── pleasure-side-lying-spooning.mdx      # 新增：侧卧匙羹与剪刀式力学
│   │   └── pleasure-rear-entry-angles.mdx        # 新增：后入位入径与子宫后位避坑
│   └── glossary/
│       ├── retroverted-uterus.md                 # 新增词条：子宫后位
│       ├── deep-dyspareunia.md                   # 新增词条：深部性交痛
│       └── coital-angle.md                       # 新增词条：解剖进入角度
├── data/
│   ├── positionMatrix.ts                         # 8 大循证体位力学数据集
│   ├── intimacyChecklist.ts                      # Yes/No/Maybe 脱敏知情题库
│   └── dailyQuiz.ts                              # 扩充 3 道每日速测知情题
├── components/
│   └── tools/
│       ├── PositionAndIntimacyGuide.astro        # 体位力学矩阵与探索清单复合组件
│       └── ... (原有 6 大工具)
└── pages/
    └── tools/
        └── index.astro                           # 挂载第 7 大工具，更新微导航与场景描述
```

### 3.2 数据模型契约

#### 1) 体位力学数据集契约 (`src/data/positionMatrix.ts`)
```typescript
export interface SexualPosition {
  id: string;
  name: string;
  en_name: string;
  category: 'female_control' | 'intimacy_close' | 'low_energy' | 'deep_penetration';
  clitoral_access: 'high' | 'moderate' | 'low';
  cervical_collision_risk: 'low' | 'moderate' | 'high';
  energy_expenditure: 'low' | 'moderate' | 'high';
  pelvic_support_advice: string;
  coital_angle_desc: string;
  pros: string[];
  cons: string[];
  communication_tip: string;
  related_article: string; // 外键映射至 src/content/articles/*.mdx
}
```

#### 2) 伴侣探索题库契约 (`src/data/intimacyChecklist.ts`)
```typescript
export interface ChecklistCategory {
  id: string;
  name: string;
  description: string;
  items: ChecklistItem[];
}

export interface ChecklistItem {
  id: string;
  title: string;
  physiological_reason: string;
  suggestion_text: string;
}
```

---

## 4. Edge Cases & Resilience（边界情况与韧性）

1. **零隐私泄露与无状态原则**：
   - 用户的选项与表单状态**仅存在于当前浏览器的 DOM/内存闭包**中；
   - 严禁向 `localStorage`、URL Hash、Cookie 或第三方接口回传任何勾选项，刷新页面即物理销毁。
2. **防 XSS 攻击**：
   - 动态便签与对比抽屉渲染一律使用 `textContent`、`createElement`、`replaceChildren()`，严格禁止 `innerHTML`。
3. **学术严肃排版与去低俗化**：
   - 严禁彩色图符与系统原生 Emoji（`🔞`、`👉` 等全部禁止）；
   - 一律采用单色矢量 SVG、`[ 01 // STEP ]` 经典印章标签与 Paper & Ink 色板。
4. **外键连通性**：
   - 8 种体位的所有 `related_article` 必须指向真实存在的 MDX 文件；
   - 自动化测试脚本严格保障 100% 连通。

---

## 5. Test Strategy & Verification Gate（测试策略与质量门禁）

1. **测试脚本扩展 (`scripts/test_tools.py`)**：
   - 验证 `src/data/positionMatrix.ts` 导出 ≥8 种姿势，各字段类型完备，`related_article` 全量存在；
   - 验证 `src/data/intimacyChecklist.ts` 导出 5 大分类与 ≥15 个选项；
   - 验证 `PositionAndIntimacyGuide.astro` 挂载点与关键 DOM 类名契约。
2. **词典与图谱测试 (`scripts/test_glossary.py` & `scripts/test_decision_tree.py`)**：
   - 验证新增 3 个词条（子宫后位、深部性交痛、解剖进入角度）格式严谨且外键关联有效。
3. **全链路 CI 验收 (`pnpm test`)**：
   - `astro check`：0 错误、0 警告；
   - `test:graph`：全图连通测试全绿；
   - `curate:check`：25 篇（22+3）科普导读元数据契约全部通过；
   - `astro build`：全量静态路由打包与 Pagefind 索引成功（预计由 32 扩增至 35+ 页面）。
