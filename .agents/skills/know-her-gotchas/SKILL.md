---
name: know-her-gotchas
description: know-her 项目踩坑与安全铁律。改动本站 Astro 组件、链接、本地存储或发布流水线时触发。
metadata:
  version: 0.1.0
  platforms: linux, macos, windows
  hermes:
    tags:
      - astro
      - security
      - xss
      - base-url
      - mobile
      - release-pipeline
---

# know-her 项目踩坑与安全铁律

本技能是 `D:\Code\know-her`（Astro 7 静态科普站，`base: '/know-her'`）的**项目级避坑真值源**。
以下每条均为**实际踩过并修复**的缺陷，非推测。

> 全局编码规范仍以 `D:\Obsidian\Coding\01-Rules\` 为准；本文件只钉住 know-her 特有约束。

---

## 1. Base URL 与动态链接 (MUST)

站点部署在 GitHub Pages 子路径，硬编码 `/xxx` 会 404。

- **单一真值源**：客户端动态生成的链接 **MUST** 读根容器的 `data-base-url` 属性，或构建期 `import.meta.env.BASE_URL`。
- **禁止启发式猜测**：**MUST NOT** 通过查询任意 `<nav a[href]>` 反推 base 路径——嵌套子路由的链接会被误采，导致路径拼接错位。

```js
// ✅ 正确
const base = document.querySelector('[data-base-url]').dataset.baseUrl;
// ❌ 反例：可能取到 /know-her/categories/contraception 这类子路由链接
const base = document.querySelector('nav a[href]').getAttribute('href');
```

**完成判据**：`pnpm run build` 后，产物中所有内部锚点/资源链接均以 `/know-her/` 开头。

---

## 2. 安全铁律 (MUST)

| 铁律 | 要求 | 理由 |
|---|---|---|
| **Zero-innerHTML** | 禁用 `innerHTML`；用 `textContent` 或 DOM API | XSS 防线 |
| **URL 协议白名单** | Zod 校验 URL 时 **MUST** 追加协议 refine | `z.string().url()` 符合 RFC 3986，**放行 `javascript:`** |
| **Zero-Emoji** | 用单色 SVG 与括号标签 `[ 01 // PRINCIPLE ]` | 学术编辑风格 |
| **零本地持久化** | 敏感门诊健康输入 **MUST NOT** 写 localStorage | 纯静态站零隐私收集定位 |

```ts
// ✅ 必须追加的协议 refine（防存储型 XSS）
z.string().url().refine(u => /^https?:\/\//i.test(u))
```

---

## 3. 移动端布局 (MUST)

- **底部导航遮挡**：吸底导航栏（`h-14`/`h-16`，`z-50`）会盖住浮动操作栏；浮动栏 **MUST** 留出移动端净空（如 `bottom-20 sm:bottom-6`）。
- **手势冲突**：**MUST NOT** 在 `touchstart` 上直接绑定 `e.touches.length >= 2` 做「恐慌快捷键」——会劫持移动端原生双指缩放，破坏图表/表格可读性。改用专用点击目标或明确的多击阈值。

---

## 4. 存储 API 容错 (MUST)

Safari 隐私浏览下 `localStorage` 抛 `SecurityError`。任何存取 **MUST** 包 try-catch 并带降级路径，否则该浏览器整页白屏。

---

## 5. 发布流水线策略 (MUST)

`deploy.yml` 中的**外链探活**（`curate:links`）**MUST** 软失败（`continue-on-error: true`）——第三方站点宕机不得阻断本站发布。

硬门禁 **SHOULD** 只保留本地可判定的 schema/元数据校验（`curate:check`）。

---

## 6. Astro 作用域事实

Astro 组件 `<style>` 默认带 `[data-astro-cid-...]` 作用域，`body *` 这类选择器**不会**泄漏到兄弟组件。排查样式串扰时不必先怀疑此处。

---

## 7. 内容池与门禁的联动约束 (MUST)

- **扩文章必须同步扩词典**：`test_daily_loop.py` 的 G3 判定 `lcm(文章池, 词典池) >= 90` 且两池互不整除。文章池 32→42 后若词典停在 28，`lcm(42,28)=84` 直接判红「周期坍缩」。扩文章前先算 `lcm(新文章数, 现词典数)`，不达标就在同一次改动里把词典扩到互不整除的规模（如 33 ⇒ lcm=462）。
- **候选 PR 分支的 `dailyQuiz.ts` 必然冲突**：harvester 生成的分支在 `DAILY_QUIZZES` 尾部追加带 `TODO(human)` 的占位条目，合 master 时与主分支新增键冲突。固定解法：`git checkout --theirs src/data/dailyQuiz.ts`（取 master 版）→ 在对象尾部插入本条真实条目 → 删掉分支占位条目，切勿保留占位文字（`curate:check` 的 `PLACEHOLDER_MARKERS` 与 G1 都会判红）。
- **每篇新文章必须配速测题**：G1 强制文章 slug 与 `DAILY_QUIZZES` 键双向 1:1，新增 `.mdx` 而漏题即红；题目里的占位文本（`待人工补题`）同样判红。
- **占位扫描是全库的**：`curate:check` 与 CI 对全量文章扫描 `待人工提炼` / `待人工补题` / `待维护者人工提炼` / `TODO(human)`，同一分支里遗留任何一处都会阻断发布。
- **截断 slug 撞名与重复 PR 查重**：`curate_harvester.generate_slug` 仅截取 URL 末段前 30 字符，长 URL（如儿童版对比成人版）会与已有文章撞名并触发时间戳后缀（`-222`/`-795`），绕过分支去重而连续多天开出同源重复 PR。处理积压 PR 前**MUST**先按 `source_url` 查重（关闭多余重复单并删远端分支），策展时将截断或带随机后缀的文件名规范化为完整语义 slug 并同步速测题键。

## 8. 关联

- 项目工程上下文：`D:\Code\know-her\.agent-context.md`（测试基线、符号地图、红线）
- 全局编码规范：`D:\Obsidian\Coding\01-Rules\CODING-UNIVERSAL.md`
