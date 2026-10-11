# Design Specification: 深度内容扩充与现代化交互大闭环 (Content Expansion & Modern Interactive UX)

**Date**: 2026-10-10  
**Status**: APPROVED  
**Author**: know-her Architecture & Core Team  
**Target Path**: `docs/specs/2026-10-10-content-expansion-and-interactive-ux-design.md`

---

## 1. Problem Statement & User Value

- **Why build this**:
  - **内容层**：know-her 现有 26 篇文章虽建立了基础骨架，但在内分泌（PCOS、围绝经期）、月经异常点滴出血临床鉴别、棉条/月经杯卫生安全，以及深水区性心理与边界沟通（阴道痉挛、拒绝话术）上仍存在严重空白；
  - **阅读交互层**：目前 2000~4000 字长文缺少目录树导航 (TOC) 与阅读进度感知，长屏滚动极易迷失；
  - **全局检索层**：现有搜索入口分散在页面内部，缺少桌面/移动端主流的全局快捷键即时呼出能力（`Cmd+K` / `/`），查阅成本高；
  - **受众覆盖层**：作为 GitHub Pages 静态站，海外华人与港澳台群体是高价值增量受众，缺少客户端即时简繁转换；
  - **知情赋权工具层**：两性亲密探索中最大的痛点是“不敢开口提、担心被拒绝”，亟需一个纯前端保护拒绝者的“双人偏好双盲知情核对器”。

- **Target Scenario & Persona**:
  - **场景 1（临床困惑急救）**：拿到体检或内分泌激素单的女性，在手机上阅读 3000 字《多囊卵巢综合征科普》，需要通过侧边 TOC 快速直达“生活方式干预阶梯”与“就诊指标”段落；
  - **场景 2（伴侣安全探索）**：伴侣双方希望探索更丰富的性生活但担心尴尬，通过微信/Signal 发送一个加密 URL Hash，双方填写后仅展示重合愿意尝试的意向，拒绝项永久隐匿；
  - **场景 3（全站即时寻医索药）**：在任何文章详情页，按下 `/` 键秒级唤起极简纸墨搜索弹窗，精准直达相关词条与工具。

- **Cost of Doing Nothing**:
  - 内容池仅 26 篇，每日轮换周期受限；长文跳出率高；伴侣沟通诉求得不到工具支持；繁体中文读者因字符阻碍流失。

---

## 2. User Journey & Core Flow

### 2.1 长文阅读体验 (TOC & Reading Progress)
1. **进入长文** -> 顶部显示 2px 极简纸墨进度条，顶部元信息标注“预计阅读 X 分钟”；
2. **滚动阅读** -> 桌面端右侧固定显示 TOC 目录树（`sticky`），基于 `IntersectionObserver` 随视口平滑高亮当前正在阅读的 H2/H3 章节；
3. **点击定位** -> 点击目录项平滑滚动至对应小节（`scroll-mt-20`），移动端提供悬浮微型目录抽屉按钮。

### 2.2 全局即时搜索弹窗 (`Cmd+K` / `/`)
1. **触发唤起** -> 用户在全站任意页面按下 `Cmd+K`、`Ctrl+K`、`/` 键，或点击顶栏搜索放大镜图标；
2. **检索过滤** -> 弹出纸墨质感居中模态框，自动聚焦输入框，毫秒级调用 Pagefind WASM 本地全量索引展示高亮结果；
3. **键盘选中** -> 支持 `ArrowUp` / `ArrowDown` 切换候选，`Enter` 直接跳转，`Escape` 瞬间关闭。

### 2.3 伴侣双人偏好双盲知情核对器 (Intimacy Consent Blind Matching)
1. **发起方点选** -> 发起人在工具箱进入 `[09] 伴侣双盲知情核对器`，点选 20 项亲密行为（`渴望尝试` / `可以接受` / `坚决拒绝`）；
2. **密文分享** -> 点击“生成加密核对链接”，使用 Web Crypto API 本地生成对称密钥或加密 Payload，编码入 URL Hash（如 `#vault=...`），零数据上传服务器；
3. **伴侣核对并揭晓** -> 伴侣打开链接，独立勾选自己的偏好并点击“完成解密核对”：系统**仅展示双方均勾选了“渴望”或“接受”的交集项目**；若任何一方选择“坚决拒绝”，该项目直接置灰显示为“暂无交集”，绝不暴露是谁拒绝，切实保护拒绝者情感安全。

### 2.4 客户端一键简繁转换
1. **点击切换** -> 用户点击顶栏/底栏图章 `[ 繁體 ]`；
2. **即时重绘** -> 客户端动态加载轻量 `opencc-js` 字典模块，将 DOM 文本节点与 `<title>` 批量转换；
3. **状态持久化** -> 通过 `safeStorage` 记录偏好，刷新页面后自动维持繁体模式。

---

## 3. Architecture & Data Models

### 3.1 深度科普长文扩充 (6 篇 1:1 闭环)
- **文件路径**: `src/content/articles/*.mdx`
  1. `body-pcos-lifestyle-management.mdx`（多囊卵巢综合征综合管理）
  2. `body-perimenopause-hormone-fluctuation.mdx`（围绝经期雌孕激素断崖应对）
  3. `body-ovulation-bleeding-vs-implantation.mdx`（排卵期/受精着床出血鉴别）
  4. `body-tampon-menstrual-cup-tss-safety.mdx`（卫生棉条与月经杯安全使用）
  5. `pleasure-vaginismus-pelvic-floor-therapy.mdx`（阴道痉挛成因与盆底肌阶梯脱敏）
  6. `intimacy-sexual-boundary-saying-no.mdx`（亲密关系边界与体面拒绝艺术）
- **数据契约与门禁**:
  - `src/data/dailyQuiz.ts` 对应新增 6 道题，满足 G1 门禁（文章数:速测题数 = 32:32 强约束）；
  - `src/content/glossary/*.mdx` 新增关联词条（`pcos`、`perimenopause`、`vaginismus`）。

### 3.2 核心组件与模块设计

| 组件 / 模块 | 职责与技术边界 |
| :--- | :--- |
| `src/components/TableOfContents.astro` | 解析 Astro MDX 导出的 `headings`，构建双层 H2/H3 目录树；基于 `IntersectionObserver` 驱动当前视口高亮；纯 CSS + 极简原生 JS。 |
| `src/components/ReadingProgress.astro` | 监听 `scroll` 事件（`requestAnimationFrame` 节流），驱动页面顶层 2px 极简进度条宽度百分比；计算预计阅读时长。 |
| `src/components/SearchModal.astro` | 全局模态弹窗，监听 `keydown` 全局事件；封装 Pagefind WASM 调用接口；键盘焦点陷阱 (Focus Trap) 与无障碍 ARIA 属性。 |
| `src/lib/ui/langConverter.ts` | 动态加载 `opencc-js` 客户端模块；遍历 DOM 文本节点替换字符；持久化存储适配 Safari 无痕降级。 |
| `src/components/tools/IntimacyBlindMatch.astro` | 挂载于 `src/pages/tools/index.astro` 场景三（`#sec-blind-match`，导航 `[09]`）；管理 20 项两性探索条目；Web Crypto 加密与 URL Hash 编解码。 |

### 3.3 数据类型契约 (TypeScript)

```typescript
// 伴侣双盲偏好项数据结构
export type PreferenceLevel = 'desire' | 'willing' | 'reject';

export interface IntimacyItem {
  id: string;
  category: 'emotional' | 'foreplay' | 'positions' | 'novelty' | 'aftercare';
  title: string;
  description: string;
  levelGuidance: string;
}

// 加密 Payload 结构 (经过 AES-GCM 或压缩 Base64 存储于 URL Hash)
export interface BlindMatchPayload {
  v: number; // 协议版本号
  t: number; // 时间戳
  p: Record<string, PreferenceLevel>; // 匿名选择项字典
}
```

---

## 4. Edge Cases & Resilience

1. **零服务端与无痕隐私 (Privacy-First)**:
   - 双盲核对器全流程运行在浏览器沙箱中，URL Hash 不会随 HTTP 请求发送到服务器，服务端完全无法感知用户填写的亲密偏好；
2. **Safari 无痕模式与 Storage 异常**:
   - `langConverter` 与 `BlindMatch` 状态读取全部经由 `try...catch` 安全包装，在 `localStorage` 被禁用时优雅降级为内存会话状态；
3. **Pagefind 搜索冷启动与资源加载**:
   - 快捷键唤醒弹窗时采用骨架屏与懒加载，若 Pagefind WASM 尚未就绪，展示 `[ 正在初始化本地离线索引... ]` 提示，杜绝白屏与未捕获 Promise 异常；
4. **长文标题锚点重复与特殊字符**:
   - `TableOfContents` 锚点对齐 Astro 原生 slug 生成规则，自动过滤特殊符号，确保与 HTML `id` 100% 连通；
5. **Zero-innerHTML & Zero-Emoji 全局防线**:
   - 搜索高亮与双盲核对器视图全部使用 `document.createElement` / `textContent` / `replaceChildren` 构建，杜绝 XSS；
   - 界面一律使用单色 SVG 与等宽文本图章，严格无原生彩色 Emoji。

---

## 5. Test Strategy & Verification Commands

1. **内容不变量门禁 (`test_daily_loop.py` & G1-G9)**:
   - 验证文章数 = 32，速测题数 = 32，1:1 闭环，缺失数 = 0；
   - 验证轮换周期 `lcm(32, 28) = 224 天` 满足大于 90 天约束。
2. **实用工具箱契约 (`test_tools.py`)**:
   - 注册并断言 `IntimacyBlindMatch.astro` 存在；
   - 断言 `tools/index.astro` 正确挂载锚点 `#sec-blind-match` 与微导航 `[09] 伴侣双盲知情核对器`；
   - 断言双盲核对器包含 20 项探索条目、交集计算逻辑与加密协议。
3. **文章卫生与安全门禁 (`test_article_hygiene.py`)**:
   - 扫描新增的 6 篇 MDX 文章正文纯净度，确保全站所有 Astro 组件 **零 innerHTML 违规**。
4. **静态构建与类型验证**:
   - `pnpm check`（0 errors, 0 warnings）；
   - `pnpm test:graph`（9 套测试全绿）；
   - `pnpm build`（全量 42+ 个静态页面顺利编译，Pagefind 全文检索索引 100% 成功）。

---

## 6. Fog of War & Scope Boundaries

- **Fog of War (显式范围划定)**:
  - 简繁转换默认仅转换页面主体文本，代码块与专有名词英文缩写（如 COC、IUD、HPV）保持原样不转换；
  - 伴侣双盲核对器采用 URL Hash 纯客户端解密，不依赖外部扫码中继服务，在跨设备复制链接时保证安全无残留。
- **Out of Scope (本里程碑非目标)**:
  - 不引入服务端数据库或用户登录系统（坚守零 PII 静态站架构）；
  - 不引入重型多语言国际化路由拆分（保持单一路由结构，通过客户端动态转换满足繁体受众）。

---

## Self-Review Checklist
- [x] 零 "TODO" / "TBD" 占位符。
- [x] 符合 Fog of War 阶段性演进，无隐含膨胀范围。
- [x] 遵循 Ladder of Reuse：优先原生 Web API、Astro Headings、Pagefind 与纯前端 Web Crypto。
