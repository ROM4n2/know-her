# 架构设计规格书：就医沟通便签生成器与全品类避孕矩阵筛选器

- **文档状态**：Draft（等待用户最终审批）
- **日期**：2026-09-26
- **架构方案**：方案 A（极简实用主义 · 临床与避孕场景闭环）
- **对应目标**：在 `src/components/tools/` 落地两大高杠杆纯前端离线交互工具，扩充 `/tools/` 静态路由功能矩阵，闭环“科普导读 ➔ 应急自查 ➔ 就诊沟通 / 避孕选型”的完整行动链条。

---

## 1. Problem Statement & User Value（问题陈述与用户价值）

### 1.1 痛点一：门诊就医恐慌与信息失真（Clinic Visit Friction）
- **现实场景**：
  公立医院妇科门诊平均单次面诊时间仅 3~5 分钟。年轻女性或伴侣在突发异常出血、持续痛经、排卵期剧痛或性交疼痛时，往往处于高度焦虑状态。
- **核心摩擦**：
  1. **关键病史遗漏**：紧张之下经常忘记末次月经时间（LMP）、忘记交代正在服用的避孕药（COC/紧急药）或宫内节育器类型；
  2. **描述主观模糊**：无法清晰量化疼痛级别（NRS 1-10）、出血与周期的相对时间（经期延长 vs 排卵期突破性出血）；
  3. **病耻感与医患沟通摩擦**：面对敏感问题（同房史、近期无保护接触）不敢开口，导致医生无法获取第一手诊断依据，甚至漏做关键检查（如 HCG 验孕或阴道超声）。
- **用户价值**：
  提供零门槛交互小工具，用户在候诊或家中的 1 分钟内，通过点选结构化症状，即可生成一张严谨、专业、去污名化的《就医沟通备忘录便签》，支持一键纯文本复制到备忘录或直接打印/给医生查看。

### 1.2 痛点二：避孕方式碎片化与认知偏差（Contraception Choice Fog）
- **现实场景**：
  绝大多数读者对避孕的认知局限于“男用安全套”与“事后紧急避孕药”，对长效可逆避孕（LARC，如曼月乐左炔诺孕酮节育系统、皮下埋植剂、含铜IUD）存在严重误区（例如恐惧“上环烂肉”谣言、混淆短效与紧急避孕药）。
- **核心摩擦**：
  1. **珍珠指数认知缺失**：不知道典型使用下安全套年失败率高达 13%，而皮埋与曼月乐失败率仅 <0.1%~0.2%；
  2. **个体禁忌不透明**：如先兆偏头痛或重度吸烟者不宜使用复方雌孕激素（COC），但适用单纯孕激素或含铜IUD；
  3. **月经改善收益未被知晓**：不知晓曼月乐是治疗月经过多（AUB-HMB）的一线推荐方案。
- **用户价值**：
  基于 WHO《避孕方法选用的医学资格标准》（MEC）建立包含 10 种主流现代避孕手段的结构化数据字典，提供即时多维筛选（防 STI、长效省心、无激素、改善月经痛量等）与双向横向对比能力。

---

## 2. User Journey & Core Flow（用户旅程与核心交互）

### 2.1 工具一：《就诊沟通备忘录小抄生成器》(ClinicMemo.astro)
```
[ 选择主要主诉 ] ➔ [ 勾选发作时长与痛感/出血特征 ] ➔ [ 录入月经与避孕用药史 ] ➔ [ 实时生成便签卡 ] ➔ [ 复制/打印/查看关联深度科普 ]
```
1. **Step 1: 主诉分类选择 (Tabs / Radios)**
   - 🩸 异常阴道出血（经期延长 / 两次月经间出血 / 同房后接触性出血 / 绝经后出血）
   - ⚡ 盆腔与下腹疼痛（进行性重度痛经 / 同房疼痛与痉挛 / 排卵期一侧突发下腹痛 / 非经期隐痛坠胀）
   - 🔬 异常白带与瘙痒（豆腐渣样凝乳白带 / 鱼腥味稀薄灰白 / 黄绿泡沫状 / 伴排尿灼痛）
   - 🛡️ 避孕与常规查体咨询（长效避孕咨询 / 避孕药不良反应评估 / 宫颈 HPV/TCT 筛查咨询）
2. **Step 2: 核心体征与既往史快填 (Quick Taps)**
   - 末次月经日期（LMP）：日期选择器 + 周期天数输入（默认约 28-30 天）；
   - 近期避孕与性行为：无保护 / 全程安全套 / 规律服用短效COC / 带有节育器(IUD) / 近期服用紧急避孕药；
   - 验孕排查情况：未测 / 尿早孕试纸阴性 / 尿早孕试纸阳性；
   - 严重伴随症状红旗预警（多选）：体温≥38.5℃ / 突发晕厥或冷汗 / 剧烈撕裂样剧痛 / 1小时浸透2片卫生巾连续2小时（若勾选则高亮显示【🚨 急诊红旗提示】）。
3. **Step 3: 实时渲染结果卡片 (Editorial Note Card)**
   - 呈现结构化排版：
     - `01 // 门诊主诉陈述`（一句话标准医学描述模版）
     - `02 // 关键病史速览`（LMP、避孕用药、验孕情况、特征量化）
     - `03 // 我想向医生重点确认的 3 个问题`（自动匹配针对性专业问题，例如：“是否需要安排经阴道/经腹部妇科超声？”、“是否需要查血 HCG 排除异位妊娠？”、“目前症状是否需要处方止血/消炎药物？”）
   - 操作按钮：`[ 📋 复制就医小抄 ]`、`[ 🖨️ 打印便签 ]`、`[ 🧹 重置 ]`。

### 2.2 工具二：《全品类避孕知情选择矩阵》(ContraceptionMatrix.astro)
```
[ 状态总览/指标筛选 ] ➔ [ 矩阵卡片网格响应式呈现 ] ➔ [ 点击卡片展开深度禁忌与月经影响 ] ➔ [ 勾选两项进行横向 PK 对比 ]
```
1. **多维即时筛选器（Tag Filters）**：
   - `[ 全部收录 (10) ]`
   - `[ 🛡️ 能预防性传播疾病 (STI) ]`
   - `[ ⏱️ 长效可逆省心 (≥3年) ]`
   - `[ 🌿 不含任何激素 (Non-hormonal) ]`
   - `[ 🩸 适合经量过多/严重痛经 ]`
   - `[ 🚀 突发事后紧急补救 ]`
2. **矩阵卡片核心信息规整**：
   - 名称与别名（如：曼月乐 LNG-IUS）
   - 有效期与使用频次（5年 / 每次同房 / 每日固定时间）
   - **有效率双轨展示**：完美使用（<0.2%）vs 典型使用（<0.2%），并与安全套（典型 13%）形成直观视觉比对
   - 核心机制徽标：`[ 宫内局部孕激素 ]`、`[ 物理屏障 ]`、`[ 抑制排卵 ]`
   - 月经影响标签：`[ 经量显著减少/痛经缓解 ]`、`[ 可能出现点滴出血 ]`
3. **双选横向对比面板（Head-to-Head Compare Modal / Drawer）**：
   - 支持同时勾选任意 2 种避孕方式（如“复方短效口服避孕药” vs “曼月乐节育系统”），弹出横向对比表格：失败率对比、忘服/移位容错度、价格与可及性、生育力恢复时间、禁忌人群。

---

## 3. Architecture & Data Models（架构与数据模型）

### 3.1 目录结构与组件拓扑
```
src/
├── data/
│   ├── contraceptionMethods.ts         # 10 大避孕方式静态全景数据集
│   └── clinicQuestions.ts              # 就诊小抄主诉映射表与智能追问知识库
├── components/
│   └── tools/
│       ├── ClinicMemo.astro            # 就诊沟通备忘录小抄生成器组件
│       ├── ContraceptionMatrix.astro   # 全品类避孕知情选择矩阵组件
│       ├── EmergencyCountdown.astro    # 已有：紧急避孕 72h 倒计时
│       ├── CocRemedyCalculator.astro   # 已有：COC 漏服补救计算器
│       ├── CycleAssessment.astro       # 已有：月经指标自测
│       └── ArousalBrakesChecklist.astro# 已有：油门刹车盘点
└── pages/
    └── tools/
        └── index.astro                 # 工具箱聚合页（统一排版导航）
```

### 3.2 避孕方式数据模型契约 (`src/data/contraceptionMethods.ts`)
```typescript
export interface ContraceptionMethod {
  id: string;
  name: string;
  en_name: string;
  category: 'barrier' | 'hormonal_short' | 'hormonal_long' | 'non_hormonal_long' | 'emergency' | 'permanent';
  /** 珍珠指数典型使用年失败率 (例如 "13%") */
  failure_rate_typical: string;
  /** 珍珠指数完美使用年失败率 (例如 "2%") */
  failure_rate_perfect: string;
  /** 有效持续时间 / 频次描述 */
  duration: string;
  /** 是否能阻断 HIV / STIs */
  protects_sti: boolean;
  /** 激素类型 */
  hormone_type: 'none' | 'combined' | 'progestin_only';
  /** 生育力恢复速度 */
  fertility_return: '立即' | '数天内' | '取出后迅速' | '永久不可逆';
  /** 对月经量的预期改变 */
  menses_effect: string;
  /** 核心优势点 */
  pros: string[];
  /** 常见不良反应与适应期 */
  cons: string[];
  /** 典型绝对/相对禁忌症（WHO MEC 标准） */
  contraindications: string[];
  /** 关联本站深度循证科普 slug（用于外键连通性门禁） */
  related_article: string;
}
```

### 3.3 就诊沟通数据契约 (`src/data/clinicQuestions.ts`)
```typescript
export interface SymptomConfig {
  id: string;
  title: string;
  chiefComplaintTemplate: (ctx: ClinicContext) => string;
  recommendedQuestions: string[];
  relatedArticle: string;
}
```

### 3.4 纯前端无状态与无埋点保证
- **数据持久化原则**：零服务端接口，零 Cookie，零 Analytics 跟踪。
- 用户输入状态仅在浏览器内存（DOM 元素 value）中实时计算；页面刷新或点击 `[ 重置 ]` 立即彻底销毁，不向 localStorage 写入任何可能泄露个人隐私的就诊病史。

---

## 4. Edge Cases & Resilience（边缘情况与韧性设计）

1. **红旗体征急腹症拦截**：
   - 若用户勾选了突发撕裂样剧痛、晕厥冷汗或大出血，系统在便签顶部以强制高危卡片阻断（`🚨 急诊红旗提示：这可能提示宫外孕破裂、黄体破裂或急性盆腔感染，不可等待常规预约，请立即前往附近医院急诊！`），并锁定醒目字色。
2. **未成年人与非婚就医法律/关怀提示**：
   - 便签注明“医生负有法定隐私保密义务，如实告知末次月经与性接触史是排除宫外孕等致命急症的医学前提”。
3. **输入边界防御**：
   - 月经周期天数限制 15~100 天，越界时自动友好提示；未选日期时生成相对描述（“末次月经时间不详”）。
4. **移动端与纸张打印适配**：
   - 打印样式注入 `@media print` 规则：隐藏所有网页导航、返回按钮、Tab 标签与页脚，只留下干净整洁的单页就诊便签，方便随身携带或直接递交医生。

---

## 5. Test Strategy & Quality Gates（测试策略与质量门禁）

### 5.1 自动化测试扩展 (`scripts/test_tools.py`)
更新测试脚本，在 `REQUIRED_COMPONENTS` 数组中追加两个新组件：
```python
REQUIRED_COMPONENTS = [
    ("EmergencyCountdown.astro", ["ec-datetime-input", "ec-progress-bar", "contraception-emergency-pill"]),
    ("CocRemedyCalculator.astro", ["coc-pack-type", "coc-week-phase", "contraception-oral-pills"]),
    ("CycleAssessment.astro", ["cycle-len-input", "period-days-input", "normal-menstrual-cycle"]),
    ("ArousalBrakesChecklist.astro", ["brakes-calc-container", "brakes-copy-btn", "pleasure-responsive-desire-dual-control"]),
    # 新增验证项：
    ("ClinicMemo.astro", ["clinic-memo-container", "clinic-copy-btn", "abnormal-uterine-bleeding"]),
    ("ContraceptionMatrix.astro", ["matrix-filter-container", "matrix-card", "contraception-condoms"]),
]
```
- **外键核验**：自动化扫描 `contraceptionMethods.ts` 与 `clinicQuestions.ts` 中引用的每一个 `related_article`，强制要求在 `src/content/articles/*.mdx` 中 100% 存在，一旦出现死链或拼写错误直接中断 CI 构建。
- **全链路门禁**：通过 `pnpm check && pnpm test:graph && pnpm curate:check && pnpm build` 保证 0 错误、0 警告。

### 5.2 视觉与排版合规
- 遵守 Academic Modern Editorial 规范，全站严格无彩色原生系统 Emoji，使用专业单色 SVG 图标与文本排版符号（`01 // STEP`，`[ 珍珠指数 ]`）。
- 维持温润纸墨底色（`#FAF8F5`、`#15140F`）与物理墨线阴影（`shadow-[2px_2px_0_rgba(21,20,15,1)]`）。

---

## 6. Self-Review Checklist（规格书自检）
- [x] **无 TODO/TBD**：所有核心数据结构、算法逻辑、外键关联均有明确定义。
- [x] **零范畴漂移 (No Scope Creep)**：不引入新数据库、不新增重量级 npm 依赖，完全复用现有 Astro + Tailwind v4 架构。
- [x] **零隐私收集保证**：就诊数据完全留在本地单次操作生命周期中。
- [x] **医学准确性背书**：避孕数据基于 WHO MEC 与 CDC 避孕有效率金标准，就诊问诊基于妇产科 SOAP 问诊规范。
