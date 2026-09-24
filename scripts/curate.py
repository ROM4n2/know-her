#!/usr/bin/env python3
"""
curate.py — know-her 日常科普策展与内容管理辅助工具 (ADR-0002)

用法：
  1. 列出当前收录的所有词条：
     python scripts/curate.py list

  2. 极简交互/命令行创建新词条草稿：
     python scripts/curate.py new --id "contraception-iud-basics" \
       --title "一文搞懂宫内节育器(IUD)：曼月乐与含铜节育环怎么选？" \
       --category "contraception" \
       --source-name "丁香医生" \
       --source-url "https://dxy.com/article/12345"

  3. 校验所有文章 frontmatter 合规性：
     python scripts/curate.py check

  4. 严格在线探测所有文章原出处外链可达性（杜绝 404）：
     python scripts/curate.py check-links
"""

import os
import sys
import re
import argparse
import datetime
import urllib.request
import urllib.error

ARTICLES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src", "content", "articles")
VALID_CATEGORIES = ["contraception", "pleasure", "body", "intimacy"]

CATEGORY_NAMES = {
    "contraception": "安全避孕",
    "pleasure": "愉悦探索",
    "body": "身体机制",
    "intimacy": "亲密沟通",
}

DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def parse_frontmatter(content: str):
    match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n(.*)$", content, re.DOTALL)
    if not match:
        return {}, content
    yaml_text = match.group(1)
    body = match.group(2)
    meta = {}
    for line in yaml_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            k, v = line.split(":", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            meta[k] = v
    return meta, body

def cmd_list(args):
    files = [f for f in os.listdir(ARTICLES_DIR) if f.endswith(".mdx") and not f.startswith("_")]
    print(f"📖 know-her 当前收录文章列表（共 {len(files)} 篇）：\n")
    print(f"{'分类':<10} {'发布日期':<12} {'来源':<20} {'标题'}")
    print("-" * 80)
    for fname in sorted(files):
        fpath = os.path.join(ARTICLES_DIR, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            meta, _ = parse_frontmatter(f.read())
        cat = CATEGORY_NAMES.get(meta.get("category", ""), meta.get("category", "未知"))
        date = meta.get("pubDate", "----")
        src = meta.get("source_name", "未知")
        title = meta.get("title", fname)
        print(f"[{cat}] {date:<12} {src:<20} {title}")
    print()

def cmd_check(args):
    files = [f for f in os.listdir(ARTICLES_DIR) if f.endswith(".mdx") and not f.startswith("_")]
    errors = 0
    print(f"🔍 检查 {len(files)} 篇文章的 frontmatter 契约...\n")
    for fname in sorted(files):
        fpath = os.path.join(ARTICLES_DIR, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            meta, body = parse_frontmatter(f.read())
        
        required_fields = ["title", "pubDate", "summary", "category", "source_url", "source_name"]
        missing = [rf for rf in required_fields if rf not in meta or not meta[rf]]
        if missing:
            print(f"❌ {fname}: 缺少必填字段: {missing}")
            errors += 1
            continue

        cat = meta.get("category")
        if cat not in VALID_CATEGORIES:
            print(f"❌ {fname}: 非法分类 '{cat}'，允许值: {VALID_CATEGORIES}")
            errors += 1
            continue

        url = meta.get("source_url", "")
        if not (url.startswith("http://") or url.startswith("https://")):
            print(f"❌ {fname}: source_url 必须是合法的 http/https URL: {url}")
            errors += 1
            continue

        print(f"✅ {fname} ({CATEGORY_NAMES.get(cat)}) 格式规范")

    if errors == 0:
        print(f"\n🎉 全部 {len(files)} 篇文章通过结构校验，无格式错误！")
    else:
        print(f"\n⚠️ 发现 {errors} 处错误，请及时修复。")
        sys.exit(1)

def cmd_check_links(args):
    files = [f for f in os.listdir(ARTICLES_DIR) if f.endswith(".mdx") and not f.startswith("_")]
    errors = 0
    print(f"🌐 在线探测 {len(files)} 篇词条的原出处外链可达性（杜绝 404）...\n")
    for fname in sorted(files):
        fpath = os.path.join(ARTICLES_DIR, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            meta, _ = parse_frontmatter(f.read())
        
        url = meta.get("source_url", "")
        src_name = meta.get("source_name", "未知")
        if not url:
            print(f"❌ {fname}: 无 source_url")
            errors += 1
            continue

        req = urllib.request.Request(url, headers={"User-Agent": DEFAULT_USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                code = resp.status
                if 200 <= code < 400:
                    print(f"✅ [{code} OK] {fname}")
                    print(f"   机构: {src_name}")
                    print(f"   链接: {url}")
                else:
                    print(f"❌ [{code} FAIL] {fname} ({src_name}) -> {url}")
                    errors += 1
        except urllib.error.HTTPError as e:
            print(f"❌ [{e.code} HTTP Error] {fname} ({src_name}) -> {url}")
            errors += 1
        except Exception as e:
            print(f"❌ [网络错误: {e}] {fname} ({src_name}) -> {url}")
            errors += 1

    if errors == 0:
        print(f"\n🎉 完美！全部 {len(files)} 篇词条原文外链均返回 200 OK，零 404！")
    else:
        print(f"\n⚠️ 发现 {errors} 处无效或 404 外链，请按照真实出处修复后再发布。")
        sys.exit(1)

def cmd_new(args):
    slug = args.id
    if not slug.endswith(".mdx"):
        filename = f"{slug}.mdx"
    else:
        filename = slug

    target_path = os.path.join(ARTICLES_DIR, filename)
    if os.path.exists(target_path):
        print(f"❌ 文件已存在：{target_path}")
        sys.exit(1)

    today = datetime.date.today().isoformat()
    cat = args.category if args.category in VALID_CATEGORIES else "body"

    template = f"""---
title: "{args.title}"
pubDate: {today}
summary: "{args.summary or '请在此处填写入库推荐理由与 1~2 句话核心看点。'}"
category: "{cat}"
tags:
  - {CATEGORY_NAMES.get(cat, '科普')}
  - 性健康
source_url: "{args.source_url}"
source_name: "{args.source_name}"
author: "{args.author or args.source_name}"
is_full_text: false
---

## 💡 核心看点速览

- 核心要点 1：提炼原文章最核心、最有颠覆性或最实用的结论；
- 核心要点 2：指出常见认知误区或临床指引；
- 核心要点 3：给出行动建议或安全警示。

## 📖 深度解读与精彩摘录

在此补充 2~3 段对原文精华观点的转述与背景梳理，保留原作者权威观点，避免主观臆断。

> 权威观点引用摘录（可选）

## 🔗 原文直达

本篇导读基于 {args.source_name} 发布的科普内容精编。查阅完整深度报告与实验数据，请访问出处：
"""

    with open(target_path, "w", encoding="utf-8") as f:
        f.write(template)

    print(f"✅ 成功创建新词条模板：src/content/articles/{filename}")
    print(f"   标题: {args.title}")
    print(f"   分类: [{CATEGORY_NAMES.get(cat)}] {cat}")
    print(f"   出处: {args.source_name} ({args.source_url})")

def main():
    parser = argparse.ArgumentParser(description="know-her 日常策展管理工具")
    subparsers = parser.add_subparsers(dest="command")

    # list
    subparsers.add_parser("list", help="列出所有已收录科普文章")

    # check
    subparsers.add_parser("check", help="校验文章格式合规性")

    # check-links
    subparsers.add_parser("check-links", help="在线探测所有词条原出处外链可达性")

    # new
    new_p = subparsers.add_parser("new", help="创建新文章草稿模板")
    new_p.add_argument("--id", required=True, help="文件 slug（如 contraception-iud-basics）")
    new_p.add_argument("--title", required=True, help="文章标题")
    new_p.add_argument("--category", choices=VALID_CATEGORIES, default="body", help="分类")
    new_p.add_argument("--source-name", required=True, help="出处机构/博主名")
    new_p.add_argument("--source-url", required=True, help="出处原链接")
    new_p.add_argument("--summary", default="", help="一句话导读看点")
    new_p.add_argument("--author", default="", help="原作者（选填）")

    args = parser.parse_args()
    if args.command == "list":
        cmd_list(args)
    elif args.command == "check":
        cmd_check(args)
    elif args.command == "check-links":
        cmd_check_links(args)
    elif args.command == "new":
        cmd_new(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
