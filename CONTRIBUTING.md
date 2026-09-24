# 贡献指南 (Contributing to know-her)

感谢你关注并愿意为 **know-her** 贡献内容！

know-her 是一个致力于打破两性伪科学与信息壁垒的每日科普分享站。为了确保全站内容的科学性、权威性与读者信任，请在提交内容前阅读以下指引。

---

## 📜 核心收录原则

1. **权威来源，拒绝二手洗稿**：
   - 优选：世界卫生组织（WHO）、联合国教科文组织（UNESCO）、默沙东诊疗手册大众版、中华医学会妇产科学分会指南、果壳、丁香医生等具有公信力的权威机构或知名科普媒体；
   - 坚决杜绝：来路不明的营销号推文、自媒体搬运、民营医院广告、带货软文。
2. **策展导读制（零版权风险）**：
   - 除非原作者采用 Creative Commons (CC) 协议授权，否则**禁止全文搬运**；
   - 采用「3~5 个核心干货要点 + 深度背景剖析 + 显式直达原出处外链」的导读形态。
3. **真实可达，零 404 硬红线**：
   - 提交的 `source_url` 必须在浏览器中真实可访问，严禁大模型凭记忆拼凑虚构 URL；
   - 提交 PR 前必须在本地运行并通过 `pnpm curate:links`。
4. **温和中立，杜绝恐吓式叙事**：
   - 使用客观、科学、去羞耻化的语言，不夸大病情，不制造容貌与身材焦虑；
   - 倡导知情同意、自主权与愉悦探索。

---

## ✍️ 提交流程

1. **Fork 本仓库** 到你的 GitHub 账号；
2. **基于 master 创建特性分支**：
   ```bash
   git checkout -b content/my-new-topic
   ```
3. **使用策展 CLI 生成新文章模板**：
   ```bash
   python scripts/curate.py new \
     --id "my-new-topic" \
     --title "文章标题" \
     --category "contraception" \
     --source-name "权威出处" \
     --source-url "https://..."
   ```
4. **撰写正文**：在 `src/content/articles/my-new-topic.mdx` 中补充核心看点与深度解读；
5. **本地完整校验**：
   ```bash
   # 1. 结构规范检查
   pnpm curate:check

   # 2. 真实外链 200 探针检查（必须全绿通过）
   pnpm curate:links

   # 3. Astro 类型与静态编译检查
   pnpm check
   pnpm build
   ```
6. **提交并推送至你的 Fork 仓库**，然后向本仓库发起 Pull Request！
   CI 门禁会自动运行全量校验，通过后维护者将尽快审阅并合并上线。
