#!/usr/bin/env python3
"""
curate_harvester.py — know-her 权威科普候选源自动抓取与草稿合成引擎 (Pipeline B)
用于自动化监控 WHO、默沙东大众版等官方权威信源，提取两性健康与生理机制优质文章，
经过 200 OK 探针过滤与去重后合成合规导读草稿，支持发起 Draft PR 进行人工审阅上线。
"""

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from html import unescape

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
ARTICLES_DIR = os.path.join(ROOT_DIR, "src", "content", "articles")
SOURCES_FILE = os.path.join(SCRIPT_DIR, "sources.json")
LEDGER_FILE = os.path.join(SCRIPT_DIR, ".curate-ledger.json")

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"


def load_ledger() -> dict:
    if os.path.exists(LEDGER_FILE):
        try:
            with open(LEDGER_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"version": 1, "last_updated": "", "processed_urls": [], "rejected_urls": []}


def save_ledger(ledger: dict):
    ledger["last_updated"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with open(LEDGER_FILE, "w", encoding="utf-8") as f:
        json.dump(ledger, f, indent=2, ensure_ascii=False)


def get_existing_article_urls() -> set:
    urls = set()
    if not os.path.exists(ARTICLES_DIR):
        return urls
    for f in os.listdir(ARTICLES_DIR):
        if f.endswith(".mdx"):
            path = os.path.join(ARTICLES_DIR, f)
            try:
                content = open(path, "r", encoding="utf-8").read()
                m = re.search(r"source_url:\s*\"([^\"]+)\"", content)
                if m:
                    urls.add(m.group(1).strip())
            except Exception:
                pass
    return urls


def fetch_url(url: str, timeout: int = 15) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", errors="ignore")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception:
        return 0, ""


def clean_title(raw_title: str) -> str:
    t = unescape(raw_title).strip()
    t = re.sub(r"\s*-\s*《?默沙东诊疗手册大众版》?.*$", "", t)
    t = re.sub(r"\s*-\s*女性健康.*$", "", t)
    t = re.sub(r"\s*-\s*世界卫生组织.*$", "", t)
    t = re.sub(r"\s*-\s*WHO.*$", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s*\|\s*WHO.*$", "", t, flags=re.IGNORECASE)
    return t.strip()


def extract_metadata(html: str) -> tuple[str, str]:
    title_m = re.search(r"<title>(.*?)</title>", html, re.DOTALL | re.IGNORECASE)
    raw_title = title_m.group(1).strip() if title_m else ""
    title = clean_title(raw_title)

    desc_m = re.search(r"<meta\s+name=[\"\']description[\"\']\s+content=[\"\'](.*?)[\"\']", html, re.IGNORECASE)
    if not desc_m:
        desc_m = re.search(r"<meta\s+property=[\"\']og:description[\"\']\s+content=[\"\'](.*?)[\"\']", html, re.IGNORECASE)
    desc = unescape(desc_m.group(1).strip()) if desc_m else ""
    # 去除多余换行与空白
    desc = re.sub(r"\s+", " ", desc)

    # 兜底：若 meta description 过短或缺乏有效中文，自动提取正文首个高质量段落
    has_cjk = bool(re.search(r"[\u4e00-\u9fff]", desc))
    if len(desc) < 20 or not has_cjk:
        ps = re.findall(r"<p[^>]*>(.*?)</p>", html, re.DOTALL)
        for p in ps:
            clean_p = unescape(re.sub(r"<[^>]+>", "", p)).strip()
            clean_p = re.sub(r"\s+", " ", clean_p)
            if len(clean_p) >= 25 and re.search(r"[\u4e00-\u9fff]", clean_p):
                desc = clean_p
                break

    if len(title) <= 4 and re.search(r"[\u4e00-\u9fff]", title):
        title = f"{title}：权威医学实况与科学指导"

    return title, desc


def determine_category_and_tags(title: str, desc: str, source_cfg: dict) -> tuple[str, list[str]]:
    combined = title + " " + desc
    cat_map = source_cfg.get("category_map", {})
    category = source_cfg.get("default_category", "body")

    matched_kw = []
    for kw, cat in cat_map.items():
        if kw in combined:
            category = cat
            matched_kw.append(kw)
            break

    tags = []
    if category == "contraception":
        tags.extend(["安全避孕", "避孕科普"])
    elif category == "pleasure":
        tags.extend(["愉悦探索", "性心理"])
    elif category == "body":
        tags.extend(["身体机制", "生殖健康"])
    elif category == "intimacy":
        tags.extend(["亲密沟通", "知情同意"])

    for kw in ["避孕", "月经", "阴道", "阴蒂", "HPV", "性传播", "润滑", "痛经", "子宫"]:
        if kw in combined and kw not in tags:
            tags.append(kw)

    return category, tags[:4]


def generate_slug(category: str, source_id: str, candidate_url: str) -> str:
    path_part = candidate_url.rstrip("/").split("/")[-1]
    # 清洗非字母数字字符
    clean_part = re.sub(r"[^a-zA-Z0-9-]", "", path_part).lower()
    if len(clean_part) < 3:
        clean_part = "topic-" + datetime.datetime.now().strftime("%m%d%H%M")
    return f"{category}-{clean_part[:30]}"


def compose_mdx_content(candidate: dict) -> str:
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    tags_yaml = "\n".join([f"  - {t}" for t in candidate["tags"]])
    
    summary = candidate["summary"]
    if not summary:
        summary = f"权威科普解析：全面了解{candidate['title']}的核心医学常识与科学应对建议。"
    elif len(summary) > 160:
        summary = summary[:157] + "..."

    evidence_tier = candidate.get("evidence_tier", "A")

    mdx = f"""---
title: "{candidate['title']}"
pubDate: {today_str}
summary: "{summary}"
category: "{candidate['category']}"
tags:
{tags_yaml}
evidence_tier: "{evidence_tier}"
source_url: "{candidate['source_url']}"
source_name: "{candidate['source_name']}"
author: "{candidate['source_name']}"
reviewed_by: ""
last_verified_at: {today_str}
is_full_text: false
---

## 为什么收录这篇？

两性与生殖健康需要建立在严谨客观的现代医学认知之上。本导读精选自**{candidate['source_name']}**官方发布的权威指引，帮助读者破除恐吓式营销与网络谣言，获取科学、去羞耻化的第一手常识。

## 🔍 核心要点导读速览（待维护者人工提炼）

<!-- ⚠️ 待审必读：合并前请维护者通读原文，提炼 3~4 条真正有医学增量的核心干货，切勿使用套话 -->
1. **核心机制与客观认知**：<!-- 请在此填入提炼要点 1 -->
2. **日常自我关注与防范**：<!-- 请在此填入提炼要点 2 -->
3. **常见误区与就医时机**：<!-- 请在此填入提炼要点 3 -->

## 📖 候选摘录背景

{candidate.get('raw_desc', '')}

在面对相关生理状况时，保持客观平实的心态尤为关键。不随意盲目自我用药或轻信虚假宣传，如有明确身体不适，应前往正规公立医院专科就医。

## 🔗 推荐阅读与原出处直达

想要查阅原文献、临床试验数据与官方防控建议，欢迎点击下方按钮直达官方权威页面：
"""
    return mdx


def harvest_candidates(limit: int = 1, source_id: str | None = None) -> list[dict]:
    if not os.path.exists(SOURCES_FILE):
        print(f"❌ 找不到数据源配置文件: {SOURCES_FILE}")
        return []

    with open(SOURCES_FILE, "r", encoding="utf-8") as f:
        sources = json.load(f)

    ledger = load_ledger()
    processed_urls = set(ledger.get("processed_urls", []))
    rejected_urls = set(ledger.get("rejected_urls", []))
    existing_urls = get_existing_article_urls()
    all_seen_urls = processed_urls | rejected_urls | existing_urls

    candidates = []

    for src in sources:
        if source_id and src.get("id") != source_id:
            continue

        print(f"\n🔍 正在扫描信源: {src['name']} ({src['entry_url']})")
        status, html = fetch_url(src["entry_url"])
        if status != 200 or not html:
            print(f"  ⚠️ 入口请求失败 (HTTP {status})，跳过")
            continue

        # 从入口页面提取带有锚文本的链接: <a href="...">text</a>
        pattern = src["link_pattern"]
        link_regex = re.compile(
            r"<a[^>]+href=[\"\'](" + pattern + r")[\"\'][^>]*>(.*?)</a>",
            re.DOTALL | re.IGNORECASE,
        )
        found_anchors = link_regex.findall(html)
        print(f"  ✓ 匹配到 {len(found_anchors)} 个链接条目")

        base_url = src.get("base_url", "")
        keywords = src.get("keywords", [])

        # 预过滤出符合关键词且未曾处理过的条目
        filtered_items = []
        seen_in_batch = set()

        for item in found_anchors:
            rel_url = item[0]
            raw_text = item[-1]
            # 清理 anchor 文本作为初步标题
            anchor_title = unescape(re.sub(r"<[^>]+>", "", raw_text)).strip()
            anchor_title = clean_title(anchor_title)

            # 组装完整 URL
            if rel_url.startswith("http"):
                full_url = rel_url
            elif rel_url.startswith("/"):
                full_url = base_url + rel_url
            else:
                full_url = base_url + "/" + rel_url

            full_url = full_url.split("#")[0].rstrip("/")

            if full_url in all_seen_urls or full_url in seen_in_batch:
                continue

            # 关键词初筛（标题或链接本身包含关键词）
            has_kw = any(kw in anchor_title for kw in keywords) or any(kw in rel_url for kw in keywords)
            if not has_kw:
                continue

            seen_in_batch.add(full_url)
            filtered_items.append((full_url, anchor_title))

        print(f"  🎯 初筛命中 {len(filtered_items)} 篇未收录相关候选")

        # 仅对初筛命中的候选发起真实探测
        for full_url, anchor_title in filtered_items:
            if len(candidates) >= limit:
                break

            p_status, p_html = fetch_url(full_url, timeout=10)
            if p_status != 200 or not p_html:
                all_seen_urls.add(full_url)
                continue

            page_title, desc = extract_metadata(p_html)
            final_title = page_title if (page_title and len(page_title) >= len(anchor_title)) else anchor_title
            final_title = clean_title(final_title)

            category, tags = determine_category_and_tags(final_title, desc, src)
            slug = generate_slug(category, src["id"], full_url)

            # 检查本地是否有重名 slug
            target_path = os.path.join(ARTICLES_DIR, f"{slug}.mdx")
            if os.path.exists(target_path):
                slug = f"{slug}-{int(datetime.datetime.now().timestamp()) % 1000}"

            candidate = {
                "title": final_title,
                "summary": desc,
                "raw_desc": desc,
                "category": category,
                "tags": tags,
                "source_url": full_url,
                "source_name": src["name"],
                "slug": slug,
                "source_id": src["id"],
            }
            candidates.append(candidate)
            all_seen_urls.add(full_url)
            print(f"  ✨ 成功捕获并验证候选: [{category}] {final_title}")
            print(f"     🔗 {full_url}")

        if len(candidates) >= limit:
            break

    return candidates


def create_draft_pr(candidate: dict) -> bool:
    slug = candidate["slug"]
    branch_name = f"candidate/{slug}"
    target_file = os.path.join(ARTICLES_DIR, f"{slug}.mdx")

    # 1. 检查 git 状态
    st = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
    if st.stdout.strip():
        print("❌ 当前 Git 工作区存在未提交变更，请先保存后再发起 Draft PR")
        return False

    current_branch = subprocess.run(
        ["git", "branch", "--show-current"], capture_output=True, text=True
    ).stdout.strip()

    print(f"\n🚀 开始自动化 PR 流程: {branch_name}")
    try:
        # 防重复守卫：该候选分支若已有待审 PR，直接跳过，避免每日重复刷 PR
        dup = subprocess.run(
            ["gh", "pr", "list", "--head", branch_name, "--state", "open", "--json", "number"],
            capture_output=True,
            text=True,
        )
        if dup.returncode == 0 and dup.stdout.strip() not in ("", "[]"):
            print(f"  ⏭️ 分支 {branch_name} 已存在待审 PR，跳过本次候选生成")
            return True

        # 创建分支
        subprocess.run(["git", "checkout", "-b", branch_name], check=True)

        # 写入 MDX
        mdx_content = compose_mdx_content(candidate)
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(mdx_content)
        print(f"  ✓ 已生成草稿文件: {target_file}")

        # 更新台账
        ledger = load_ledger()
        if candidate["source_url"] not in ledger.get("processed_urls", []):
            ledger.setdefault("processed_urls", []).append(candidate["source_url"])
        save_ledger(ledger)
        print(f"  ✓ 已更新台账: {LEDGER_FILE}")

        # 验证合规性
        chk = subprocess.run(["python", os.path.join(SCRIPT_DIR, "curate.py"), "check"], capture_output=True, text=True)
        if chk.returncode != 0:
            print(f"❌ 草稿结构校验失败:\n{chk.stdout}\n{chk.stderr}")
            raise RuntimeError("curate check failed")

        # Git commit
        subprocess.run(["git", "add", target_file, LEDGER_FILE], check=True)
        commit_msg = f"feat(curate): 自动生成候选导读草稿《{candidate['title']}》"
        subprocess.run(["git", "commit", "-m", commit_msg], check=True)

        # Git push (带重试机制，防止网络抖动)
        # --force-with-lease：候选分支为机器生成的临时草稿分支，上次运行若在 PR 创建前中断，
        # 远端会残留陈旧分支导致常规 push non-fast-forward 永久卡死流水线
        print(f"  ⬆️ 正在推送分支 {branch_name} 至远端 GitHub...")
        pushed = False
        for attempt in range(1, 4):
            try:
                subprocess.run(
                    ["git", "push", "--force-with-lease", "-u", "origin", branch_name],
                    check=True,
                )
                pushed = True
                break
            except subprocess.CalledProcessError:
                print(f"  ⚠️ git push 第 {attempt} 次失败，等待重试...")
                import time
                time.sleep(2)

        if not pushed:
            raise RuntimeError("git push failed after 3 attempts")

        # PR Body
        pr_body = f"""## 🌸 每日自动化候选导读草稿提交 (Pipeline B)

**原标题**：{candidate['title']}
**收录分类**：`{candidate['category']}`
**权威信源**：{candidate['source_name']}
**原出处链接**：{candidate['source_url']}

### 🔍 自动化探活与静态校验
- [x] **真实外链探针**：HTTP 200 OK 确认可达
- [x] **Schema 结构化检查**：符合 `src/content.config.ts` 规范

### ✍️ 维护者人工审阅 Checklist（严禁机器自打勾，合并前必须由人核实）
- [ ] **原文核实**：点击上述出处链接，确认内容与本篇主题完全匹配；
- [ ] **人工撰写导读**：已在 Files changed 中填入 3~4 点人工提炼的核心要点，清除了占位提示；
- [ ] **版权合规核验**：遵循 ADR-0002 双轨制（精炼导读 + 原文直达链接，无侵权搬运）；
- [ ] **CI 门禁全绿**：Astro 编译与外链真实探测均 PASS。
"""

        # gh pr create
        print(f"  📋 正在创建 GitHub Draft PR...")
        pr_cmd = [
            "gh", "pr", "create",
            "--draft",
            "--title", f"📝 [候选导读] {candidate['title']}",
            "--body", pr_body,
            "--label", "daily-candidate",
            "--base", "master",
            "--head", branch_name
        ]
        res = subprocess.run(pr_cmd, capture_output=True, text=True)
        if res.returncode == 0:
            pr_url = res.stdout.strip()
            print(f"  🎉 Draft PR 创建成功: {pr_url}")
            return True
        else:
            print(f"❌ gh pr create 失败: {res.stderr}")
            return False

    except Exception as e:
        print(f"❌ 流程异常: {e}")
        return False
    finally:
        # 无论成功失败，恢复原分支
        subprocess.run(["git", "checkout", current_branch], check=False)


def main():
    parser = argparse.ArgumentParser(description="know-her 权威科普候选源自动抓取与草稿合成引擎")
    parser.add_argument("--dry-run", action="store_true", help="仅抓取并展示候选，不写文件不提 PR")
    parser.add_argument("--limit", type=int, default=1, help="每次抓取并生成的候选数量（默认 1）")
    parser.add_argument("--source-id", help="限定仅扫描指定信源 ID (who-fact-sheets / msd-women-health)")
    parser.add_argument("--save-draft", action="store_true", help="直接在当前分支保存 .mdx 草稿文件")
    parser.add_argument("--create-pr", action="store_true", help="自动建立特性分支并提交 GitHub Draft PR")

    args = parser.parse_args()

    candidates = harvest_candidates(limit=args.limit, source_id=args.source_id)
    if not candidates:
        print("\n✨ 今日无新增待收录候选或全部候选均已在台账中。")
        return

    print(f"\n📊 共发现 {len(candidates)} 篇高价值候选：")
    for idx, c in enumerate(candidates, 1):
        print(f"{idx}. [{c['category']}] {c['title']}")
        print(f"   来源: {c['source_name']}")
        print(f"   外链: {c['source_url']}")
        print(f"   摘要: {c['summary'][:80]}...")

    if args.dry_run:
        print("\n[Dry Run 模式] 演示生成 MDX 格式：")
        print("--------------------------------------------------")
        print(compose_mdx_content(candidates[0]))
        print("--------------------------------------------------")
        return

    if args.save_draft:
        for c in candidates:
            target_path = os.path.join(ARTICLES_DIR, f"{c['slug']}.mdx")
            mdx = compose_mdx_content(c)
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(mdx)
            print(f"💾 已保存草稿: {target_path}")

    if args.create_pr:
        for c in candidates:
            success = create_draft_pr(c)
            if not success:
                sys.exit(1)


if __name__ == "__main__":
    main()
