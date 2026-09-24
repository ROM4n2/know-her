# 🌸 know-her · 每日性健康科普与愉悦分享

<div align="center">

[![CI](https://github.com/ROM4n2/know-her/actions/workflows/ci.yml/badge.svg)](https://github.com/ROM4n2/know-her/actions/workflows/ci.yml)
[![Deploy to GitHub Pages](https://github.com/ROM4n2/know-her/actions/workflows/deploy.yml/badge.svg)](https://github.com/ROM4n2/know-her/actions/workflows/deploy.yml)
[![Daily Routine](https://github.com/ROM4n2/know-her/actions/workflows/daily-routine.yml/badge.svg)](https://github.com/ROM4n2/know-her/actions/workflows/daily-routine.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-rose.svg)](LICENSE)
[![Astro](https://img.shields.io/badge/Astro-7.x-BC52EE.svg)](https://astro.build)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-v4-06B6D4.svg)](https://tailwindcss.com)

**倡导科学 · 自主知情 · 愉悦探索 · 零伪科学**

[🌐 访问线上主站](https://rom4n2.github.io/know-her/) · [📡 订阅 RSS 2.0](https://rom4n2.github.io/know-her/rss.xml) · [📖 参与策展指南](CONTRIBUTING.md)

</div>

---

## 💡 为什么做 know-her？

在中文互联网上，搜索两性知识与妇科健康常常充斥着两极分化：要么是莆田系医院的恐吓式广告与营销软文，要么是冷冰冰、晦涩难懂且充满教条的诊疗手册。

**know-her** 致力于成为一个温暖、现代、科学的每日性健康与愉悦探索分享站。我们不试图成为严肃的就医问诊工具，而是专注在日常生活中，为读者提供：
- 🛡️ **安全避孕**：破除避孕套双层摩擦破裂等致命误区，科学指导紧急与短效避孕药服用；
- 🌸 **愉悦探索**：从现代解剖学认识阴蒂的“隐藏冰山”，打破单一插入迷思，科普润滑剂选型与女性自慰脱敏；
- 🩸 **身体机制**：客观看待月经周期的四大健康指标（24~38天允许波动），科学识别排卵期出血与 HPV 疫苗常识；
- 💬 **亲密沟通**：深入践行联合国全面性教育倡导的 FRIES 知情同意法则，建立平等尊重的亲密边界。

---

## ✨ 核心特性

- 📅 **今日精选 & 每日 30 秒速测**：首页置顶每日推荐科普，基于当前公历日期确定性轮换；内嵌趣味速测题与即时权威医学原理解析，支持客户端连续打卡天数记录（纯 `localStorage` 存储，零个人隐私收集）。
- 💡 **精选策展导读 + 权威出处直达（ADR-0002 架构）**：每篇文章提供“核心要点导读速览 + 深度剖析 + 醒目原文直达外链”，彻底杜绝版权争议与二手洗稿。
- 🛡️ **100% 真实外链，CI 自动化零 404 硬门禁**：所有收录出处均经过真机 HTTP 探针严格校验（引自 WHO、联合国教科文组织、默沙东大众版等）；GitHub Actions 在每次构建与部署前自动扫描，任何 404 死链均会被秒级拦截。
- 🔍 **本地分词静态全文搜索**：集成 Pagefind 静态搜索引擎，零外部服务器依赖，毫秒级快速匹配站内科普内容。
- 📡 **开放生态**：原生支持全站 RSS 2.0 订阅与 Schema.org `Article` 语义化结构化数据，方便各类阅读器分发。

---

## 📚 当前收录分类

| 分类 | 涵盖核心议题 | 样例词条 |
| :--- | :--- | :--- |
| **安全避孕** (`contraception`) | 避孕套使用误区、紧急避孕药黄金窗口、短效口服避孕药(COC)漏服补救 | 《避孕套使用的 5 个常见致命误区》、《短效避孕药规律服用与漏服应对》 |
| **愉悦探索** (`pleasure`) | 阴蒂立体解剖、女性高潮机制、人体润滑剂选型、女性自慰脱敏与心理 | 《重新认识阴蒂：解构女性愉悦的隐藏冰山》、《告别自慰耻感：医学视角的自我探索》 |
| **身体机制** (`body`) | 正常月经四大参数(FIGO)、异常出血剖析、HPV 疫苗与宫颈癌联合筛查 | 《正常月经周期的四大客观指标》、《人乳头瘤病毒(HPV)与宫颈癌防治》 |
| **亲密沟通** (`intimacy`) | 知情同意 FRIES 法则、亲密关系边界沟通、性安全与自主权 | 《亲密关系中的‘知情同意’不仅是说声好：全面拆解 FRIES 黄金法则》 |

---

## 🛠️ 本地开发与管理指南

### 1. 环境准备
- Node.js >= 22.0.0 (推荐 Node 24)
- pnpm >= 10.0.0
- Python 3.9+ (用于运行策展辅助脚本)

```bash
# 克隆仓库
git clone https://github.com/ROM4n2/know-her.git
cd know-her

# 安装依赖
pnpm install
```

### 2. 启动本地开发服务
```bash
# 启动热重载开发服务器 (默认端口 4321)
pnpm dev

# 执行静态构建与本地检索索引生成
pnpm build

# 预览生产构建产物
pnpm preview
```

### 3. 策展 CLI 常用命令 (`scripts/curate.py`)
我们在项目中内置了轻量内容管理工具，帮助维护者规范收录：

```bash
# 列出当前所有已收录的词条
pnpm curate:list

# 校验所有词条 frontmatter 结构合规性
pnpm curate:check

# 在线真实探测全站外链可达性（杜绝 404）
pnpm curate:links

# 查看今日精选排期与今日速测题目
pnpm curate:today

# 快速创建一篇新词条草稿模板
python scripts/curate.py new \
  --id "contraception-iud-basics" \
  --title "一文搞懂宫内节育器(IUD)：曼月乐与含铜节育环怎么选？" \
  --category "contraception" \
  --source-name "世界卫生组织 (WHO)" \
  --source-url "https://www.who.int/zh/..."
```

---

## 🤝 参与贡献

我们非常欢迎更多关注两性健康与性科普的伙伴一同参与策展！

- **提交优质出处或勘误**：欢迎通过 [GitHub Issues](https://github.com/ROM4n2/know-her/issues) 提交权威科普线索或错漏指正；
- **提交新词条**：请参阅 [CONTRIBUTING.md](CONTRIBUTING.md) 了解文章编写与合规标准，提交 PR。

---

## 📄 免责声明

know-her 刊载的内容为健康科普与生活常识分享，不能替代执业医师的面诊与临床诊疗。涉及严重身体不适、妇科异常病变或处方药物使用，请务必前往正规医疗机构就诊。

---

## 📜 开源协议

本项目基于 [MIT License](LICENSE) 开源发布。
各词条引用的第三方权威文献版权归原出处机构所有，本站严格遵循合理使用原则进行摘要导读与原文回溯。
