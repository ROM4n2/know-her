#!/usr/bin/env python3
"""
scripts/test_article_hygiene.py — 文章 MDX 正文整洁度与布局隔离守则门禁
确保文章 MDX 纯粹作为内容存在，不违规内嵌全局布局组件（如 MedicalDisclaimer, Base, Footer 等）。
全站组件、页面与核心库零 innerHTML (XSS 防御) 及零原生彩色 Emoji 门禁。
"""
import glob
import os
import re
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARTICLES_DIR = os.path.join(PROJECT_ROOT, "src", "content", "articles")
GLOSSARY_DIR = os.path.join(PROJECT_ROOT, "src", "content", "glossary")
COMPONENTS_DIR = os.path.join(PROJECT_ROOT, "src", "components")
PAGES_DIR = os.path.join(PROJECT_ROOT, "src", "pages")
LAYOUTS_DIR = os.path.join(PROJECT_ROOT, "src", "layouts")
LIB_DIR = os.path.join(PROJECT_ROOT, "src", "lib")

FORBIDDEN_PATTERNS = [
    ("MedicalDisclaimer", "全局页脚免责声明由 Base.astro 统一挂载，严禁在 MDX 文章正文中重复引用或渲染"),
    ("<Base", "文章正文严禁内嵌全局 Base 布局"),
    ("MobileBottomBar", "移动端底栏由 Base.astro 统一管理"),
]

INNER_HTML_PATTERN = re.compile(r"\.innerHTML|\[\s*['\"]innerHTML['\"]\s*\]")
EMOJI_PATTERN = re.compile(
    r"[\U0001F300-\U0001F64F\U0001F680-\U0001F6FF\U0001F900-\U0001F9FF\U0001FA70-\U0001FAFF\U00002702-\U000027B0\U0001F1E0-\U0001F1FF]"
)


def verify_zero_inner_html():
    print("🛡️ 正在扫描全站组件、页面与核心库防范 innerHTML XSS 漏洞...")
    patterns = [
        os.path.join(COMPONENTS_DIR, "**", "*.astro"),
        os.path.join(PAGES_DIR, "**", "*.astro"),
        os.path.join(LAYOUTS_DIR, "**", "*.astro"),
        os.path.join(LIB_DIR, "**", "*.ts"),
        os.path.join(LIB_DIR, "**", "*.js"),
    ]
    files = []
    for pattern in patterns:
        files.extend(glob.glob(pattern, recursive=True))
    files = sorted(set(files))

    errors = []
    for fpath in files:
        rel_path = os.path.relpath(fpath, PROJECT_ROOT).replace("\\", "/")
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()

        if INNER_HTML_PATTERN.search(content):
            lines = content.splitlines()
            matched_lines = [
                i + 1 for i, l in enumerate(lines) if INNER_HTML_PATTERN.search(l)
            ]
            errors.append(
                f"文件 {rel_path} (行 {matched_lines}) 包含违规属性 innerHTML，严禁使用 innerHTML 防范 XSS 漏洞，请使用 safe DOM API (createElement/textContent/replaceChildren)"
            )
    return errors


def verify_zero_emoji_content():
    print("🎨 正在扫描所有文章、词条及全站组件防范原生彩色 Emoji 违规...")
    patterns = [
        os.path.join(ARTICLES_DIR, "*.mdx"),
        os.path.join(ARTICLES_DIR, "*.md"),
        os.path.join(GLOSSARY_DIR, "*.md"),
        os.path.join(GLOSSARY_DIR, "*.mdx"),
        os.path.join(PAGES_DIR, "**", "*.astro"),
        os.path.join(LAYOUTS_DIR, "**", "*.astro"),
        os.path.join(COMPONENTS_DIR, "**", "*.astro"),
    ]
    files = []
    for pattern in patterns:
        files.extend(glob.glob(pattern, recursive=True))
    files = sorted(set(files))

    errors = []
    for fpath in files:
        rel_path = os.path.relpath(fpath, PROJECT_ROOT).replace("\\", "/")
        with open(fpath, "r", encoding="utf-8") as f:
            lines = f.readlines()

        file_violations = []
        for line_idx, line in enumerate(lines, start=1):
            matches = EMOJI_PATTERN.findall(line)
            if matches:
                file_violations.append((line_idx, matches))

        if file_violations:
            detail = ", ".join(
                f"行 {idx}: {' '.join(m)}" for idx, m in file_violations[:5]
            )
            if len(file_violations) > 5:
                detail += f" ...共 {len(file_violations)} 处"
            errors.append(
                f"文件 {rel_path} 发现原生 Emoji 违规字符 ({detail})，全站严禁使用原生 Emoji，必须使用 SVG 图标或纯文字"
            )
    return errors


def run_hygiene_check():
    print("🧹 正在检测文章 MDX 正文整洁度与布局组件隔离...")
    files = glob.glob(os.path.join(ARTICLES_DIR, "*.mdx")) + glob.glob(
        os.path.join(ARTICLES_DIR, "*.md")
    )

    if not files:
        print("❌ 未找到任何文章文件！")
        sys.exit(1)

    errors = []

    for fpath in sorted(files):
        fname = os.path.basename(fpath)
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()

        for pattern, reason in FORBIDDEN_PATTERNS:
            if pattern in content:
                # 定位行号
                lines = content.splitlines()
                matched_lines = [i + 1 for i, l in enumerate(lines) if pattern in l]
                errors.append(
                    f"{fname} (行 {matched_lines}): 命中违规项 '{pattern}' -> {reason}"
                )

    errors.extend(verify_zero_inner_html())
    errors.extend(verify_zero_emoji_content())

    if errors:
        print(f"❌ 整洁度与安全检查未通过，发现 {len(errors)} 个违规项:")
        for err in errors:
            print(f"   • {err}")
        sys.exit(1)

    print("🎉 卫生与安全检查全绿！所有文章、词条及全站组件零 innerHTML 且零原生 Emoji 违规！")


def main():
    run_hygiene_check()


if __name__ == "__main__":
    main()
