#!/usr/bin/env python3
"""
scripts/test_reading_ux.py — 长文阅读体验与目录导视契约测试

覆盖契约：
1. 组件物理存在性：
   - src/components/TableOfContents.astro 存在
   - src/components/ReadingProgress.astro 存在
2. 详情页 src/pages/articles/[id].astro 契约：
   - 调用 render(entry) 解构提取 headings: const { Content, headings } = await render(entry);
   - 引用并渲染 <ReadingProgress />
   - 引用并渲染 <TableOfContents headings={headings} />
3. 阅读进度条 src/components/ReadingProgress.astro 规范：
   - 包含 #reading-progress-bar
   - 使用 window.addEventListener('scroll', ...) 并配合 requestAnimationFrame 优化性能
   - 零 emoji 纯净风格
4. 目录树 src/components/TableOfContents.astro 规范：
   - 包含 #table-of-contents
   - 过滤 depth 2 与 depth 3 (H2/H3) 标题
   - 包含 IntersectionObserver 实现滚动高亮当前章节 (包含 .toc-link 与 active 类)
   - 采用 Academic Modern Editorial 设计系统配色 (#15140F, #FAF8F5, #5A5448, rose-600)
   - 零 emoji 纯净风格
5. 构建与自动化回归门禁 (package.json):
   - test:graph 中包含 python -X utf8 scripts/test_reading_ux.py
"""

import json
import os
import re
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOC_FILE = os.path.join(PROJECT_ROOT, "src", "components", "TableOfContents.astro")
PROGRESS_FILE = os.path.join(PROJECT_ROOT, "src", "components", "ReadingProgress.astro")
ARTICLE_PAGE_FILE = os.path.join(PROJECT_ROOT, "src", "pages", "articles", "[id].astro")
PACKAGE_JSON_FILE = os.path.join(PROJECT_ROOT, "package.json")

EMOJI_PATTERN = re.compile(
    r"[\U0001F600-\U0001F64F"  # emoticons
    r"\U0001F300-\U0001F5FF"  # symbols & pictographs
    r"\U0001F680-\U0001F6FF"  # transport & map symbols
    r"\U0001F700-\U0001F77F"  # alchemical symbols
    r"\U0001F780-\U0001F7FF"  # geometric shapes extended
    r"\U0001F800-\U0001F8FF"  # supplemental arrows-c
    r"\U0001F900-\U0001F9FF"  # supplemental symbols and pictographs
    r"\U0001FA00-\U0001FA6F"  # chess symbols
    r"\U0001FA70-\U0001FAFF"  # symbols and pictographs extended-a
    r"\U00002702-\U000027B0"  # dingbats
    r"]",
    flags=re.UNICODE
)

def test_components_exist():
    print("📁 [1/5] 检验阅读体验核心组件物理存在性...")
    errors = []
    if not os.path.isfile(PROGRESS_FILE):
        errors.append(f"缺失 ReadingProgress 组件: {PROGRESS_FILE}")
    if not os.path.isfile(TOC_FILE):
        errors.append(f"缺失 TableOfContents 组件: {TOC_FILE}")
    if not errors:
        print("   ✅ TableOfContents.astro 与 ReadingProgress.astro 均已创建")
    return errors

def test_article_page_contract():
    print("📄 [2/5] 检验 articles/[id].astro 导视与进度条挂载契约...")
    if not os.path.isfile(ARTICLE_PAGE_FILE):
        return [f"缺失文章详情页文件: {ARTICLE_PAGE_FILE}"]

    with open(ARTICLE_PAGE_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    errors = []
    # 剔除 JSX 与 HTML 注释，防止注释内的占位假绿
    clean_content = re.sub(r"\{\/\*[\s\S]*?\*\/\}", "", content)
    clean_content = re.sub(r"<!--[\s\S]*?-->", "", clean_content)

    # 1. 检验 render(entry) 中提取 headings
    if not re.search(r"\{\s*Content\s*,\s*headings\s*\}\s*=\s*await\s+render\s*\(\s*entry\s*\)", clean_content) and not re.search(r"\{\s*headings\s*,\s*Content\s*\}\s*=\s*await\s+render\s*\(\s*entry\s*\)", clean_content):
        errors.append("articles/[id].astro 必须调用 const { Content, headings } = await render(entry); 提取标题大纲")

    # 2. 检验组件导入
    if "ReadingProgress" not in clean_content:
        errors.append("articles/[id].astro 必须引入 ReadingProgress 组件")
    if "TableOfContents" not in clean_content:
        errors.append("articles/[id].astro 必须引入 TableOfContents 组件")

    # 3. 检验组件渲染挂载
    if not re.search(r"<ReadingProgress\s*/>", clean_content) and not re.search(r"<ReadingProgress\s*>", clean_content):
        errors.append("articles/[id].astro 必须渲染 <ReadingProgress />")

    if not re.search(r"<TableOfContents\s+headings=\{headings\}", clean_content):
        errors.append("articles/[id].astro 必须渲染 <TableOfContents headings={headings} />")

    if not errors:
        print("   ✅ articles/[id].astro 成功提取 headings 并挂载 ReadingProgress 与 TableOfContents")
    return errors

def test_reading_progress_contract():
    print("📏 [3/5] 检验 ReadingProgress.astro 规范与滚动动效契约...")
    if not os.path.isfile(PROGRESS_FILE):
        return [f"ReadingProgress.astro 文件不存在: {PROGRESS_FILE}"]

    with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    errors = []
    # 1. 包含 #reading-progress-bar
    if 'id="reading-progress-bar"' not in content and "id='reading-progress-bar'" not in content:
        errors.append("ReadingProgress.astro 必须包含 id=\"reading-progress-bar\"")

    # 2. 包含 scroll 监听与 requestAnimationFrame 性能优化
    if "scroll" not in content or "addEventListener" not in content:
        errors.append("ReadingProgress.astro 必须监听 window 滚动事件 (scroll)")
    if "requestAnimationFrame" not in content:
        errors.append("ReadingProgress.astro 必须使用 requestAnimationFrame 进行滚动帧率节流优化")

    # 3. 零 emoji
    emojis = EMOJI_PATTERN.findall(content)
    if emojis:
        errors.append(f"ReadingProgress.astro 存在违规 emoji 字符: {emojis}，必须保持纯净学术编辑排版")

    if not errors:
        print("   ✅ ReadingProgress.astro 进度条 ID、scroll/requestAnimationFrame 监听与零 emoji 规范合规")
    return errors

def test_table_of_contents_contract():
    print("📑 [4/5] 检验 TableOfContents.astro 目录树与高亮观察器契约...")
    if not os.path.isfile(TOC_FILE):
        return [f"TableOfContents.astro 文件不存在: {TOC_FILE}"]

    with open(TOC_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    errors = []
    # 1. 包含 #table-of-contents
    if 'id="table-of-contents"' not in content and "id='table-of-contents'" not in content:
        errors.append("TableOfContents.astro 必须包含 id=\"table-of-contents\"")

    # 2. 过滤 depth 2 与 depth 3 标题
    if not (("depth === 2" in content or "depth == 2" in content or "h.depth === 2" in content or "h.depth == 2" in content) and
            ("depth === 3" in content or "depth == 3" in content or "h.depth === 3" in content or "h.depth == 3" in content)):
        errors.append("TableOfContents.astro 必须过滤深度为 depth === 2 || depth === 3 (H2 与 H3) 的标题")

    # 3. 包含 IntersectionObserver
    if "IntersectionObserver" not in content:
        errors.append("TableOfContents.astro 客户端脚本必须使用 IntersectionObserver 监听并高亮当前阅读章节")

    # 4. 包含 .toc-link 与 active 高亮标识
    if "toc-link" not in content:
        errors.append("TableOfContents.astro 目录链接需标记 class 包含 'toc-link'")
    if "active-toc-link" not in content and "active" not in content:
        errors.append("TableOfContents.astro 必须提供高亮激活样式类 (如 active-toc-link)")

    # 5. Academic Modern Editorial 配色规范检查 (#15140F, #FAF8F5, #5A5448, rose-600)
    for color in ["#15140F", "#FAF8F5", "#5A5448", "rose-600"]:
        if color.lower() not in content.lower():
            errors.append(f"TableOfContents.astro 缺少 Academic Modern Editorial 标志性配色 '{color}'")

    # 6. 零 emoji
    emojis = EMOJI_PATTERN.findall(content)
    if emojis:
        errors.append(f"TableOfContents.astro 存在违规 emoji 字符: {emojis}，必须保持纯净学术编辑排版")

    if not errors:
        print("   ✅ TableOfContents.astro 目录 ID、深度过滤、IntersectionObserver 与学术配色合规")
    return errors

def test_package_json_registration():
    print("📦 [5/5] 检验 package.json test:graph 回归链路契约...")
    if not os.path.isfile(PACKAGE_JSON_FILE):
        return [f"package.json 文件不存在: {PACKAGE_JSON_FILE}"]

    with open(PACKAGE_JSON_FILE, "r", encoding="utf-8") as f:
        pkg = json.load(f)

    test_graph = pkg.get("scripts", {}).get("test:graph", "")
    if "scripts/test_reading_ux.py" not in test_graph and "test_reading_ux.py" not in test_graph:
        return ["package.json 的 test:graph 脚本未包含 test_reading_ux.py 执行命令"]

    print("   ✅ package.json 成功注册 test_reading_ux.py 到自动化测试链路")
    return []

def main():
    print("=" * 60)
    print("🚀 开始执行 know-her 长文阅读体验升级 (TOC 与进度条) 契约检验")
    print("=" * 60)

    all_errors = []
    all_errors.extend(test_components_exist())
    all_errors.extend(test_article_page_contract())
    all_errors.extend(test_reading_progress_contract())
    all_errors.extend(test_table_of_contents_contract())
    all_errors.extend(test_package_json_registration())

    print("=" * 60)
    if all_errors:
        print(f"❌ 长文阅读体验契约检验未通过，共发现 {len(all_errors)} 处违规：")
        for err in all_errors:
            print(f"   • {err}")
        sys.exit(1)

    print("🎉 全部长文阅读体验契约通过！TOC 悬浮目录树与 ReadingProgress 表现合规！")
    print("=" * 60)

if __name__ == "__main__":
    main()
