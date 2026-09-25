#!/usr/bin/env python3
"""
test_glossary.py — 验证两性医学词典库的数据契约与关联文章外键完整性
"""

import os
import sys
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
GLOSSARY_DIR = os.path.join(ROOT_DIR, "src", "content", "glossary")
ARTICLES_DIR = os.path.join(ROOT_DIR, "src", "content", "articles")


def parse_frontmatter(content: str) -> dict:
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not m:
        return {}
    fm_raw = m.group(1)
    data = {}
    for line in fm_raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line and not line.startswith("-"):
            key, val = line.split(":", 1)
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            data[key] = val
    return data


def run_tests():
    if not os.path.exists(GLOSSARY_DIR):
        print(f"❌ 词典目录不存在: {GLOSSARY_DIR}")
        sys.exit(1)

    files = [f for f in os.listdir(GLOSSARY_DIR) if f.endswith(".md") or f.endswith(".mdx")]
    print(f"📚 正在检测两性医学词典库 ({len(files)} 个词条)...")

    assert len(files) >= 15, f"词典词条数量应至少包含 15 个，当前为 {len(files)}"

    errors = []
    categories = {"contraception", "pleasure", "body", "intimacy"}

    for fname in files:
        fpath = os.path.join(GLOSSARY_DIR, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()

        fm = parse_frontmatter(content)
        if not fm:
            errors.append(f"{fname}: 缺少或无法解析 YAML frontmatter")
            continue

        # 检查必需字段
        for req in ["term", "letter", "definition", "category", "source"]:
            if req not in fm or not fm[req]:
                errors.append(f"{fname}: 缺少必需字段 '{req}'")

        # 检查分类有效性
        cat = fm.get("category")
        if cat not in categories:
            errors.append(f"{fname}: 非法分类 '{cat}'，允许: {categories}")

        # 检查字母大写
        letter = fm.get("letter", "")
        if len(letter) != 1 or not letter.isalpha() or not letter.isupper():
            errors.append(f"{fname}: letter 必须是单个大写字母，当前为 '{letter}'")

        # 检查关联文章存在性
        rel = fm.get("related_article")
        if rel:
            rel_path = os.path.join(ARTICLES_DIR, f"{rel}.mdx")
            if not os.path.exists(rel_path):
                errors.append(f"{fname}: 关联的科普文章不存在: {rel}.mdx")

    if errors:
        print(f"\n❌ 发现 {len(errors)} 个词典校验错误：")
        for err in errors:
            print(f"  • {err}")
        sys.exit(1)

    print(f"🎉 词典库测试通过！全量 {len(files)} 个医学词条字段规范，关联文章外键 100% 存在！")


if __name__ == "__main__":
    run_tests()
