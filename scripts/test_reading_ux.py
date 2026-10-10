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
SEARCH_MODAL_FILE = os.path.join(PROJECT_ROOT, "src", "components", "SearchModal.astro")
BASE_LAYOUT_FILE = os.path.join(PROJECT_ROOT, "src", "layouts", "Base.astro")
PACKAGE_JSON_FILE = os.path.join(PROJECT_ROOT, "package.json")
LANG_CONVERTER_FILE = os.path.join(PROJECT_ROOT, "src", "lib", "ui", "langConverter.ts")
LANG_SWITCHER_FILE = os.path.join(PROJECT_ROOT, "src", "components", "LangSwitcher.astro")

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

def validate_search_modal_contract(errors: list) -> list:
    print("🔍 [6/6] 检验全局即时搜索模态弹窗与快捷键契约 (SearchModal)...")
    if not os.path.isfile(SEARCH_MODAL_FILE):
        errors.append(f"缺失 SearchModal 组件: {SEARCH_MODAL_FILE}")
        return errors

    if not os.path.isfile(BASE_LAYOUT_FILE):
        errors.append(f"缺失 Base 布局文件: {BASE_LAYOUT_FILE}")
        return errors

    # 1. 检验 Base.astro 导入与渲染
    with open(BASE_LAYOUT_FILE, "r", encoding="utf-8") as f:
        base_content = f.read()

    clean_base = re.sub(r"\{\/\*[\s\S]*?\*\/\}", "", base_content)
    clean_base = re.sub(r"<!--[\s\S]*?-->", "", clean_base)

    if "SearchModal" not in clean_base or ("import SearchModal" not in base_content and "import SearchModal from" not in base_content):
        errors.append("Base.astro 必须引入 SearchModal 组件")
    if not re.search(r"<SearchModal\s*/>", clean_base) and not re.search(r"<SearchModal\s*>", clean_base):
        errors.append("Base.astro 必须挂载并渲染 <SearchModal />")
    if 'id="nav-search-trigger"' not in base_content and 'id="global-search-btn"' not in base_content and "id='nav-search-trigger'" not in base_content and "id='global-search-btn'" not in base_content:
        errors.append("Base.astro 必须提供快速搜索触发按钮 (#nav-search-trigger 或 #global-search-btn)")

    # 2. 检验 SearchModal.astro 组件内容与契约
    with open(SEARCH_MODAL_FILE, "r", encoding="utf-8") as f:
        modal_content = f.read()

    # Modal container
    if 'id="search-modal-container"' not in modal_content and "id='search-modal-container'" not in modal_content:
        errors.append("SearchModal.astro 必须包含 id=\"search-modal-container\"")

    # Backdrop
    if 'id="search-modal-backdrop"' not in modal_content and "id='search-modal-backdrop'" not in modal_content:
        errors.append("SearchModal.astro 必须包含 id=\"search-modal-backdrop\"")

    # Input field
    if 'id="search-modal-input"' not in modal_content and "id='search-modal-input'" not in modal_content:
        errors.append("SearchModal.astro 必须包含 id=\"search-modal-input\"")

    # Results list
    if 'id="search-modal-results"' not in modal_content and "id='search-modal-results'" not in modal_content:
        errors.append("SearchModal.astro 必须包含 id=\"search-modal-results\"")

    # Keyboard event handlers: check for key === 'k' || key === 'K' (with metaKey or ctrlKey), and key === '/'
    has_k_shortcut = ("'k'" in modal_content or '"k"' in modal_content) and ("metaKey" in modal_content or "ctrlKey" in modal_content)
    if not has_k_shortcut:
        errors.append("SearchModal.astro 必须监听 ⌘K / Ctrl+K 全局快捷键")

    if "'/'" not in modal_content and '"/"' not in modal_content:
        errors.append("SearchModal.astro 必须监听 '/' 全局搜索快捷键")

    # Safe input check: ignore shortcut if user is already typing in INPUT, TEXTAREA, SELECT, or isContentEditable
    for tag in ["INPUT", "TEXTAREA", "SELECT", "isContentEditable"]:
        if tag not in modal_content:
            errors.append(f"SearchModal.astro 快捷键处理必须规避用户输入态: 缺少对 {tag} 的判断")

    # Escape close check
    if "Escape" not in modal_content:
        errors.append("SearchModal.astro 必须支持 Escape 键关闭弹窗")

    # Focus management: focuses search-modal-input on open
    if "focus()" not in modal_content or "search-modal-input" not in modal_content:
        errors.append("SearchModal.astro 唤起时必须自动聚焦 search-modal-input 输入框")

    # Zero innerHTML violation
    clean_modal_js = re.sub(r"<!--[\s\S]*?-->", "", modal_content)
    clean_modal_js = re.sub(r"//.*", "", clean_modal_js)
    clean_modal_js = re.sub(r"/\*[\s\S]*?\*/", "", clean_modal_js)
    if ".innerHTML" in clean_modal_js:
        errors.append("SearchModal.astro 严禁使用 innerHTML (存在 XSS 风险)，必须严格使用 createElement/textContent/replaceChildren")

    for method in ["createElement", "textContent", "replaceChildren"]:
        if method not in modal_content:
            errors.append(f"SearchModal.astro 动态渲染必须使用安全 DOM API: 缺少 {method}")

    # Zero native colored emoji
    emojis = EMOJI_PATTERN.findall(modal_content)
    if emojis:
        errors.append(f"SearchModal.astro 存在违规 emoji 字符: {emojis}，必须保持纯净学术编辑排版")

    if not errors:
        print("   ✅ SearchModal.astro 模态弹窗、快捷键、DOM 安全 API 与零 emoji 规范合规")
    return errors

def validate_lang_converter_contract(errors: list) -> list:
    print("🔤 [7/7] 检验客户端纯静态一键简繁转换契约 (LangSwitcher & langConverter)...")
    # 1. 检验 opencc-js 依赖注册
    if os.path.isfile(PACKAGE_JSON_FILE):
        with open(PACKAGE_JSON_FILE, "r", encoding="utf-8") as f:
            pkg = json.load(f)
        deps = pkg.get("dependencies", {})
        if "opencc-js" not in deps:
            errors.append("package.json dependencies 必须包含 'opencc-js'")
    else:
        errors.append(f"package.json 文件不存在: {PACKAGE_JSON_FILE}")

    # 2. 检验文件物理存在性
    if not os.path.isfile(LANG_CONVERTER_FILE):
        errors.append(f"缺失简繁转换核心模块: {LANG_CONVERTER_FILE}")
    if not os.path.isfile(LANG_SWITCHER_FILE):
        errors.append(f"缺失简繁切换组件: {LANG_SWITCHER_FILE}")

    # 3. 检验 Base.astro 导入与渲染
    if os.path.isfile(BASE_LAYOUT_FILE):
        with open(BASE_LAYOUT_FILE, "r", encoding="utf-8") as f:
            base_content = f.read()
        clean_base = re.sub(r"\{\/\*[\s\S]*?\*\/\}", "", base_content)
        clean_base = re.sub(r"<!--[\s\S]*?-->", "", clean_base)
        if "LangSwitcher" not in clean_base or ("import LangSwitcher" not in base_content and "import LangSwitcher from" not in base_content):
            errors.append("Base.astro 必须引入 LangSwitcher 组件")
        if not re.search(r"<LangSwitcher\s*/>", clean_base) and not re.search(r"<LangSwitcher\s*>", clean_base):
            errors.append("Base.astro 必须挂载并渲染 <LangSwitcher />")
    else:
        errors.append(f"缺失 Base 布局文件: {BASE_LAYOUT_FILE}")

    # 4. 检验 langConverter.ts 契约
    if os.path.isfile(LANG_CONVERTER_FILE):
        with open(LANG_CONVERTER_FILE, "r", encoding="utf-8") as f:
            converter_content = f.read()

        # 动态加载 opencc-js
        if "import('opencc-js')" not in converter_content and 'import("opencc-js")' not in converter_content:
            errors.append("langConverter.ts 必须使用动态 import('opencc-js')，确保简体用户初次加载零额外开销")

        # DOM 递归遍历与 Node.TEXT_NODE === 3
        if "3" not in converter_content or ("TEXT_NODE" not in converter_content and "nodeType" not in converter_content):
            errors.append("langConverter.ts 必须递归遍历 DOM 文本节点 (Node.TEXT_NODE === 3)")

        # 跳过 SCRIPT, STYLE, CODE, PRE
        for tag in ["SCRIPT", "STYLE", "CODE", "PRE"]:
            if tag not in converter_content:
                errors.append(f"langConverter.ts DOM 遍历必须跳过 {tag} 标签")

        # document.title 转换
        if "document.title" not in converter_content:
            errors.append("langConverter.ts 必须转换 document.title")

        # safeGet 与 safeSet 封装
        if "safeGet" not in converter_content or "safeSet" not in converter_content:
            errors.append("langConverter.ts 必须包含 safeGet 与 safeSet 封装（try...catch 避免 Safari 隐身模式报错）")
        if "try" not in converter_content or "catch" not in converter_content:
            errors.append("langConverter.ts 必须包含 try...catch 存储异常防护")

        # 暴露 initLangConverter 与 toggleLanguage
        if "initLangConverter" not in converter_content or "toggleLanguage" not in converter_content:
            errors.append("langConverter.ts 必须暴露 initLangConverter 与 toggleLanguage 方法")

    # 5. 检验 LangSwitcher.astro 契约
    if os.path.isfile(LANG_SWITCHER_FILE):
        with open(LANG_SWITCHER_FILE, "r", encoding="utf-8") as f:
            switcher_content = f.read()

        if 'id="lang-switch-btn"' not in switcher_content and "id='lang-switch-btn'" not in switcher_content:
            errors.append("LangSwitcher.astro 必须包含 id=\"lang-switch-btn\"")

        # 括号排版字符
        has_bracket = any(term in switcher_content for term in ["[ 繁體 ]", "[ 简体 ]", "[ 繁 / 简 ]", "[繁體]", "[简体]"])
        if not has_bracket:
            errors.append("LangSwitcher.astro 必须使用括号学术排版字符 (如 [ 繁體 ] / [ 简体 ] / [ 繁 / 简 ])")

        # 零 emoji
        emojis = EMOJI_PATTERN.findall(switcher_content)
        if emojis:
            errors.append(f"LangSwitcher.astro 存在违规 emoji 字符: {emojis}，必须保持纯净学术编辑排版")

    if not any(e for e in errors if "LangSwitcher" in e or "langConverter" in e or "opencc-js" in e):
        print("   ✅ LangSwitcher.astro 与 langConverter.ts 动态加载、DOM遍历、安全存储与排版契约合规")

    return errors

def run_tests() -> list:
    all_errors = []
    all_errors.extend(test_components_exist())
    all_errors.extend(test_article_page_contract())
    all_errors.extend(test_reading_progress_contract())
    all_errors.extend(test_table_of_contents_contract())
    all_errors.extend(test_package_json_registration())
    validate_search_modal_contract(all_errors)
    validate_lang_converter_contract(all_errors)
    return all_errors

def main():
    print("=" * 60)
    print("🚀 开始执行 know-her 长文阅读体验升级与搜索模态契约检验")
    print("=" * 60)

    all_errors = run_tests()

    print("=" * 60)
    if all_errors:
        print(f"❌ 体验契约检验未通过，共发现 {len(all_errors)} 处违规：")
        for err in all_errors:
            print(f"   • {err}")
        sys.exit(1)

    print("🎉 全部长文阅读体验与搜索模态契约通过！")
    print("=" * 60)

if __name__ == "__main__":
    main()
