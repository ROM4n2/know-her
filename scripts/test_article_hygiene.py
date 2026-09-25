#!/usr/bin/env python3
"""
scripts/test_article_hygiene.py — 文章 MDX 正文整洁度与布局隔离守则门禁
确保文章 MDX 纯粹作为内容存在，不违规内嵌全局布局组件（如 MedicalDisclaimer, Base, Footer 等）。
"""
import glob
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARTICLES_DIR = os.path.join(PROJECT_ROOT, "src", "content", "articles")

FORBIDDEN_PATTERNS = [
    ("MedicalDisclaimer", "全局页脚免责声明由 Base.astro 统一挂载，严禁在 MDX 文章正文中重复引用或渲染"),
    ("<Base", "文章正文严禁内嵌全局 Base 布局"),
    ("MobileBottomBar", "移动端底栏由 Base.astro 统一管理"),
]

def run_hygiene_check():
    print("🧹 正在检测文章 MDX 正文整洁度与布局组件隔离...")
    files = glob.glob(os.path.join(ARTICLES_DIR, "*.mdx")) + glob.glob(os.path.join(ARTICLES_DIR, "*.md"))
    
    if not files:
        print("❌ 未找到任何文章文件！")
        sys.exit(1)

    errors = []

    for fpath in files:
        fname = os.path.basename(fpath)
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()

        for pattern, reason in FORBIDDEN_PATTERNS:
            if pattern in content:
                # 定位行号
                lines = content.splitlines()
                matched_lines = [i + 1 for i, l in enumerate(lines) if pattern in l]
                errors.append(f"{fname} (行 {matched_lines}): 命中违规项 '{pattern}' -> {reason}")

    if errors:
        print(f"❌ 文章整洁度检查未通过，发现 {len(errors)} 个违规项:")
        for err in errors:
            print(f"   • {err}")
        sys.exit(1)

    print(f"🎉 文章整洁度检查全绿！{len(files)} 篇文章纯净合规，零非法布局组件内嵌！")

if __name__ == "__main__":
    run_hygiene_check()
