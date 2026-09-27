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
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from html import unescape
from pathlib import Path

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
ARTICLES_DIR = os.path.join(ROOT_DIR, "src", "content", "articles")
SOURCES_FILE = os.path.join(SCRIPT_DIR, "sources.json")
LEDGER_FILE = os.path.join(SCRIPT_DIR, ".curate-ledger.json")
QUIZ_FILE = os.path.join(ROOT_DIR, "src", "data", "dailyQuiz.ts")

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"


# ---------------------------------------------------------------------------
# M2：候选池台账 v2（带状态机）与幂等 v1 -> v2 迁移
# ---------------------------------------------------------------------------

# v2 条目字段顺序固定：保证迁移产物与 json.dumps 逐字节稳定（幂等等式依赖键序一致）。
LEDGER_ENTRY_FIELDS = ("url", "status", "source_id", "first_seen", "last_probed", "http_status")
# 状态机合法取值：pending（已发现未处理）-> published / rejected（单向流转）。
LEDGER_STATUSES = ("pending", "published", "rejected")


def _normalize_ledger_entry(entry: dict) -> dict:
    """把单个台账条目规范化为 v2 六字段（键序固定），非法取值按缺省回填。"""
    status = entry.get("status")
    if status not in LEDGER_STATUSES:
        status = "published"
    http_status = entry.get("http_status")
    if http_status is not None and not isinstance(http_status, int):
        http_status = None
    return {
        "url": str(entry.get("url") or ""),
        "status": status,
        "source_id": str(entry.get("source_id") or ""),
        "first_seen": str(entry.get("first_seen") or ""),
        "last_probed": str(entry.get("last_probed") or ""),
        "http_status": http_status,
    }


def migrate_ledger_v1_to_v2(data: dict) -> dict:
    """幂等纯函数：把 v1（字符串数组）或 v2（对象数组）台账迁移为规范 v2 结构。

    - 幂等：``migrate(v1) == migrate(migrate(v1))``（键序固定 ⇒ 对象结构逐字节一致）；
    - v1 的 ``processed_urls`` -> ``status="published"``，``rejected_urls`` -> ``status="rejected"``；
    - 缺失日期填空串、``http_status`` 填 ``None``；
    - 无静默数据丢失：重复（或空）URL 按**首次出现**去重，并打印被丢弃条数。
    """
    if not isinstance(data, dict):
        data = {}

    entries: list = []
    seen: set = set()
    dropped = 0

    def _append(url, status: str) -> None:
        nonlocal dropped
        cleaned = str(url or "").strip()
        if not cleaned or cleaned in seen:
            dropped += 1
            return
        seen.add(cleaned)
        entries.append(
            {
                "url": cleaned,
                "status": status,
                "source_id": "",
                "first_seen": "",
                "last_probed": "",
                "http_status": None,
            }
        )

    if data.get("version") == 1:
        for url in data.get("processed_urls") or []:
            _append(url, "published")
        for url in data.get("rejected_urls") or []:
            _append(url, "rejected")
    else:
        for item in data.get("processed_urls") or []:
            if isinstance(item, dict):
                normalized = _normalize_ledger_entry(item)
                if not normalized["url"] or normalized["url"] in seen:
                    dropped += 1
                    continue
                seen.add(normalized["url"])
                entries.append(normalized)
            elif isinstance(item, str):
                _append(item, "published")
            else:
                dropped += 1

    if dropped:
        print(f"  ⚠️ 台账迁移：按首次出现去重，丢弃重复/空 URL {dropped} 条")

    return {
        "version": 2,
        "last_updated": str(data.get("last_updated") or ""),
        "processed_urls": entries,
    }


def iter_pending(ledger: dict, source_id: str | None = None) -> list[dict]:
    """返回台账中 ``status == "pending"`` 的条目；传入 ``source_id`` 时按来源过滤。"""
    pending: list = []
    for entry in (ledger or {}).get("processed_urls") or []:
        if not isinstance(entry, dict) or entry.get("status") != "pending":
            continue
        if source_id is not None and entry.get("source_id") != source_id:
            continue
        pending.append(entry)
    return pending


def ledger_seen_urls(ledger: dict) -> set:
    """收集台账中所有已见 URL（published / rejected / pending）供去重使用。

    [C1 阻断项] 兼容对象数组（v2）与字符串数组（历史遗留）：禁止直接 ``set(entries)``，
    否则对象条目因 dict 不可哈希抛 ``TypeError``。
    """
    urls: set = set()
    for entry in (ledger or {}).get("processed_urls") or []:
        if isinstance(entry, dict):
            url = entry.get("url")
            if url:
                urls.add(url)
        elif isinstance(entry, str):
            urls.add(entry)
    return urls


def load_ledger() -> dict:
    """读取台账（**唯一读入口**）：v1 自动迁移为 v2 并写回，打印迁移条数。"""
    data = None
    if os.path.exists(LEDGER_FILE):
        try:
            with open(LEDGER_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = None
    if not isinstance(data, dict):
        data = {"version": 2, "last_updated": "", "processed_urls": []}

    migrated = migrate_ledger_v1_to_v2(data)
    if migrated != data:
        entry_count = len(migrated.get("processed_urls", []))
        print(f"  ✓ 台账已从 v1 迁移到 v2：共 {entry_count} 条")
        save_ledger(migrated)
    return migrated


def save_ledger(ledger: dict):
    """写入台账（**唯一写入口**）。"""
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
    
    # summary 严禁沿用来源页面自带的 description：
    # ADR-0002 双轨制要求「精炼导读 + 原文直达链接」，直接搬运原文句子属版权风险与信任事故。
    # 机器只留占位，必须由维护者通读原文后改写。
    summary = "【待维护者人工提炼】本候选由流水线自动抓取，尚未撰写本站导读摘要，合并前必须通读原文并改写为精炼看点。"

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

<!--
机器生成的候选草稿：正文要点尚未撰写，禁止直接合并。

合并前必须依次完成（PR Checklist 严禁机器自勾选，必须由人核实）：
  1. 跳转 source_url 通读原文，核实主题与本条完全匹配、无张冠李戴；
  2. 把下方三条占位要点改写为 3~4 条真正有医学增量的提炼干货，删除占位文字与本节注释；
  3. 确认零版权搬运：只保留人工提炼要点 + 原文直达链接，删除文末【原出处描述摘录】注释块；
  4. 补写 frontmatter 的 summary 与 reviewed_by。
本文件由 scripts/curate_harvester.py 自动生成，仅完成了外链探活与 Schema 结构校验。
-->

## 核心要点导读

<!-- 以下 3 条为占位符，必须由维护者通读原文后重写，切勿保留原样合并 -->
1. **核心机制与客观认知**：（待人工提炼）
2. **日常自我关注与防范**：（待人工提炼）
3. **常见误区与就医时机**：（待人工提炼）

## 原出处直达

本导读为策展精炼版。完整数据、分型细节与官方建议请点击下方按钮直达**{candidate['source_name']}**原文页面。

<!--
【原出处描述摘录】（仅作审阅参考，合并前必须删除本节）
{candidate.get('raw_desc', '')}
-->
"""
    return mdx


# ---------------------------------------------------------------------------
# M2：信源准入（fail-closed）与 anchor / sitemap / feed 三模式增量发现
# ---------------------------------------------------------------------------

# sitemap 体积保护阈值（三档语义彼此独立、不得互相冒充，任一告警均不中断其余信源）：
#   ① 条目数 MAX_SITEMAP_ENTRIES：超限截断到前 5000 条并告警；
#   ② 字节数 MAX_SITEMAP_BYTES：超限降级到 anchor 模式（不解析超大文档）并告警；
#   ③ max_pages 仅为 sitemap index 递归深度上限，不承担截断职责。
MAX_SITEMAP_ENTRIES = 5000
MAX_SITEMAP_BYTES = 5 * 1024 * 1024


def is_source_admitted(src: dict) -> bool:
    """信源准入判定（fail-closed）。

    仅当 ``admission.status == "admitted"`` 且 ``admission.license`` 为非空字符串时返回 True；
    任何字段缺失 / 类型异常 / 状态非 admitted / license 为空（含纯空白）一律返回 False。
    """
    admission = src.get("admission")
    if not isinstance(admission, dict):
        return False
    if admission.get("status") != "admitted":
        return False
    license_value = admission.get("license")
    if not isinstance(license_value, str) or not license_value.strip():
        return False
    return True


def _localname(tag) -> str:
    """去除 XML 命名空间前缀，返回标签本地名（如 ``{ns}loc`` -> ``loc``）。"""
    if not isinstance(tag, str):
        return ""
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag


def _title_from_url(url: str) -> str:
    """从 URL 派生兜底标题（最后一段路径，经 clean_title 清洗）。"""
    segment = url.rstrip("/").split("/")[-1]
    return clean_title(segment.replace("-", " ").strip())


def _default_sitemap_fetch(url: str) -> str:
    """默认 sitemap 文本获取器（真实网络）。

    递归解析子 sitemap 时使用；测试可向 ``_parse_sitemap`` / ``_collect_sitemap`` 传入
    ``fetcher=`` 形参注入零网络实现（C4：已消除模块级可变 seam ``_SITEMAP_FETCH``）。
    """
    status, text = fetch_url(url, timeout=10)
    if status != 200 or not text:
        return ""
    return text


def _first_child_text(element, child_tag: str) -> str:
    """返回子元素 ``child_tag`` 的文本（去空白）；无匹配返回空串。"""
    for child in element:
        if _localname(child.tag) == child_tag and child.text and child.text.strip():
            return child.text.strip()
    return ""


def _first_child_attr(element, child_tag: str, attr: str) -> str:
    """返回子元素 ``child_tag`` 的 ``attr`` 属性值（去空白）；无匹配返回空串。"""
    for child in element:
        if _localname(child.tag) != child_tag:
            continue
        value = child.get(attr)
        if value and value.strip():
            return value.strip()
    return ""


def _collect_sitemap(
    xml_text: str,
    link_pattern: str,
    max_pages: int,
    depth: int,
    out: list,
    fetcher=None,
) -> None:
    """递归收集 sitemap 页面链接；sitemap index 递归深度受 ``max_pages`` 约束。

    ``fetcher`` 为可选注入形参（默认 ``_default_sitemap_fetch``），递归时逐层透传，
    使「零网络」测试无需依赖模块级可变全局状态（C4）。
    """
    if fetcher is None:
        fetcher = _default_sitemap_fetch
    root = ET.fromstring(xml_text)
    if _localname(root.tag) == "sitemapindex":
        if depth >= max_pages:
            return
        for sitemap_el in root:
            if _localname(sitemap_el.tag) != "sitemap":
                continue
            child_url = _first_child_text(sitemap_el, "loc")
            if not child_url:
                continue
            child_text = fetcher(child_url)
            if child_text:
                _collect_sitemap(child_text, link_pattern, max_pages, depth + 1, out, fetcher)
        return

    for url_el in root:
        if _localname(url_el.tag) != "url":
            continue
        loc = _first_child_text(url_el, "loc")
        if not loc:
            continue
        if link_pattern and not re.search(link_pattern, loc):
            continue
        out.append(loc)


def _parse_sitemap(xml_text: str, link_pattern: str, max_pages: int, fetcher=None) -> list[str]:
    """解析 sitemap XML 文本，返回匹配 ``link_pattern`` 的页面 URL 列表。

    - ``urlset``：提取 ``<url><loc>``；空 sitemap 返回 ``[]``；
    - ``sitemapindex``：经 ``fetcher``（默认 ``_default_sitemap_fetch``）递归抓取子 sitemap，
      深度受 ``max_pages`` 约束（``max_pages`` 仅作递归深度上限，**不承担**截断职责）；
    - 非法 XML 抛 ``xml.etree.ElementTree.ParseError``（由上层捕获并降级为 anchor 模式）。
    """
    results: list[str] = []
    _collect_sitemap(xml_text, link_pattern, max_pages, 1, results, fetcher)
    return results


def _parse_feed(xml_text: str) -> list[str]:
    """解析 feed XML 文本，返回条目链接列表（RSS ``item/link`` + Atom ``entry/link[@href]``）。

    - 空 feed 返回 ``[]``；
    - 非法 XML 抛 ``xml.etree.ElementTree.ParseError``（由上层捕获并降级为 anchor 模式）。
    """
    root = ET.fromstring(xml_text)
    urls: list[str] = []
    for element in root.iter():
        tag = _localname(element.tag)
        if tag == "item":
            link = _first_child_text(element, "link")
            if link:
                urls.append(link)
        elif tag == "entry":
            href = _first_child_attr(element, "link", "href")
            if href:
                urls.append(href)
    return urls


def _build_discovered(urls: list[str], seen_urls: set) -> list[tuple[str, str]]:
    """把 URL 列表规整为 ``(url, title)`` 候选并按 ``seen_urls`` 去重。"""
    results: list[tuple[str, str]] = []
    seen_in_batch: set[str] = set()
    for raw in urls:
        full_url = raw.split("#")[0].rstrip("/")
        if full_url in seen_urls or full_url in seen_in_batch:
            continue
        seen_in_batch.add(full_url)
        results.append((full_url, _title_from_url(full_url)))
    return results


def _discover_via_anchor(src: dict, entry_url: str, link_pattern: str, seen_urls: set) -> list[tuple[str, str]]:
    """anchor 模式：抓取入口页单页并提取带锚文本的链接（与改造前逐字节等价）。"""
    status, html = fetch_url(entry_url)
    if status != 200 or not html:
        print(f"  ⚠️ 入口请求失败 (HTTP {status})，跳过")
        return []

    link_regex = re.compile(
        r"<a[^>]+href=[\"\'](" + link_pattern + r")[\"\'][^>]*>(.*?)</a>",
        re.DOTALL | re.IGNORECASE,
    )
    found_anchors = link_regex.findall(html)
    print(f"  ✓ 匹配到 {len(found_anchors)} 个链接条目")

    base_url = src.get("base_url", "")
    keywords = src.get("keywords", [])
    # [C3] 空 keywords 守卫：显式告警而非静默产出 0 候选（不改变筛选语义）。
    if not keywords:
        print("  ⚠️ 信源 keywords 为空，anchor 模式不会命中任何候选（请为该信源补充 keywords）")
    filtered_items: list[tuple[str, str]] = []
    seen_in_batch: set[str] = set()

    for item in found_anchors:
        rel_url = item[0]
        raw_text = item[-1]
        anchor_title = unescape(re.sub(r"<[^>]+>", "", raw_text)).strip()
        anchor_title = clean_title(anchor_title)

        if rel_url.startswith("http"):
            full_url = rel_url
        elif rel_url.startswith("/"):
            full_url = base_url + rel_url
        else:
            full_url = base_url + "/" + rel_url

        full_url = full_url.split("#")[0].rstrip("/")

        if full_url in seen_urls or full_url in seen_in_batch:
            continue

        has_kw = any(kw in anchor_title for kw in keywords) or any(kw in rel_url for kw in keywords)
        if not has_kw:
            continue

        seen_in_batch.add(full_url)
        filtered_items.append((full_url, anchor_title))

    print(f"  🎯 初筛命中 {len(filtered_items)} 篇未收录相关候选")
    return filtered_items


def _fallback_to_anchor(src: dict, link_pattern: str, seen_urls: set) -> list[tuple[str, str]]:
    """降级到 anchor 模式（sitemap/feed 不可用时使用）。"""
    entry_url = src.get("entry_url") or ""
    return _discover_via_anchor(src, entry_url, src.get("link_pattern", link_pattern), seen_urls)


def _discover_via_sitemap(src: dict, url: str, link_pattern: str, max_pages: int, seen_urls: set) -> list[tuple[str, str]]:
    """sitemap 模式：解析 sitemap（含 index 递归），异常一律降级为 anchor 模式。"""
    if url.lower().endswith(".gz"):
        print("  ⚠️ sitemap 为 gzip 格式（需解码 gzip），本里程碑不支持，降级到 anchor 模式")
        return _fallback_to_anchor(src, link_pattern, seen_urls)

    status, text = fetch_url(url)
    if status != 200 or not text:
        print(f"  ⚠️ sitemap 请求失败 (HTTP {status})，降级到 anchor 模式")
        return _fallback_to_anchor(src, link_pattern, seen_urls)

    # [C2] 字节体积超限：降级到 anchor 模式（不解析超大文档），文案如实描述，不冒充 max_pages 截断。
    if len(text.encode("utf-8")) > MAX_SITEMAP_BYTES:
        print(
            f"  ⚠️ sitemap 文本超过 {MAX_SITEMAP_BYTES} 字节体积上限，"
            f"降级到 anchor 模式（不解析超大文档）"
        )
        return _fallback_to_anchor(src, link_pattern, seen_urls)

    try:
        locs = _parse_sitemap(text, link_pattern, max_pages)
    except ET.ParseError as exc:
        print(f"  ⚠️ sitemap XML 解析失败（{exc}），降级到 anchor 模式")
        return _fallback_to_anchor(src, link_pattern, seen_urls)

    # [C2] 条目数超限：截断到前 MAX_SITEMAP_ENTRIES 条并告警（与字节档互相独立）。
    if len(locs) > MAX_SITEMAP_ENTRIES:
        print(f"  ⚠️ sitemap 条目数 {len(locs)} 超过上限 {MAX_SITEMAP_ENTRIES}，按上限截断")
        locs = locs[:MAX_SITEMAP_ENTRIES]

    print(f"  ✓ sitemap 解析出 {len(locs)} 条匹配链接")
    return _build_discovered(locs, seen_urls)


def _discover_via_feed(src: dict, url: str, link_pattern: str, seen_urls: set) -> list[tuple[str, str]]:
    """feed 模式：解析 RSS / Atom（异常或空结果一律降级为 anchor 模式）。"""
    status, text = fetch_url(url)
    if status != 200 or not text:
        print(f"  ⚠️ feed 请求失败 (HTTP {status})，降级到 anchor 模式")
        return _fallback_to_anchor(src, link_pattern, seen_urls)

    try:
        links = _parse_feed(text)
    except ET.ParseError as exc:
        print(f"  ⚠️ feed XML 解析失败（{exc}），降级到 anchor 模式")
        return _fallback_to_anchor(src, link_pattern, seen_urls)

    if not links:
        print("  ⚠️ feed 未解析出任何条目，降级到 anchor 模式")
        return _fallback_to_anchor(src, link_pattern, seen_urls)

    print(f"  ✓ feed 解析出 {len(links)} 条条目")
    return _build_discovered(links, seen_urls)


def discover_candidates(src: dict, seen_urls: set) -> list[tuple[str, str]]:
    """按发现模式发现候选 ``(url, title)``；未准入信源 fail-closed 直接返回 ``[]``。

    准入判定在任何网络访问**之前**执行（禁止「先抓后判」）。
    ``discovery`` 字段缺省时按 ``{mode: "anchor", url: entry_url, link_pattern: link_pattern}`` 处理
    （现有两条信源配置不改即可继续工作，零破坏升级）。
    """
    if not is_source_admitted(src):
        admission = src.get("admission")
        if isinstance(admission, dict):
            status_text = admission.get("status", "<缺失>")
            license_text = admission.get("license", "")
        else:
            status_text = "<缺失>"
            license_text = ""
        license_desc = "非空" if (isinstance(license_text, str) and license_text.strip()) else "空"
        print(f"  ⛔ 信源未准入 (status={status_text}, license={license_desc})，跳过（fail-closed）")
        return []

    discovery = src.get("discovery")
    if not isinstance(discovery, dict):
        discovery = {}

    mode = discovery.get("mode", "anchor")
    url = discovery.get("url") or src.get("entry_url", "")
    link_pattern = discovery.get("link_pattern") or src.get("link_pattern", "")
    raw_max_pages = discovery.get("max_pages", 3)
    max_pages = raw_max_pages if isinstance(raw_max_pages, int) else 3

    print(f"\n🔍 正在扫描信源: {src.get('name', '')} ({url})")

    if mode == "sitemap":
        return _discover_via_sitemap(src, url, link_pattern, max_pages, seen_urls)
    if mode == "feed":
        return _discover_via_feed(src, url, link_pattern, seen_urls)
    return _discover_via_anchor(src, url, link_pattern, seen_urls)


def harvest_candidates(limit: int = 1, source_id: str | None = None) -> list[dict]:
    if not os.path.exists(SOURCES_FILE):
        print(f"❌ 找不到数据源配置文件: {SOURCES_FILE}")
        return []

    with open(SOURCES_FILE, "r", encoding="utf-8") as f:
        sources = json.load(f)

    ledger = load_ledger()
    # [C1] v2 台账为对象数组，必须以对象口径取 URL（禁止 set(对象数组) 触发 dict 不可哈希）
    seen_ledger_urls = ledger_seen_urls(ledger)
    existing_urls = get_existing_article_urls()
    all_seen_urls = seen_ledger_urls | existing_urls

    candidates = []

    for src in sources:
        if source_id and src.get("id") != source_id:
            continue

        # 候选发现（anchor / sitemap / feed）——未准入信源在此被硬跳过
        discovered = discover_candidates(src, all_seen_urls)

        # 仅对初筛命中的候选发起真实探测
        for full_url, anchor_title in discovered:
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


# ---------------------------------------------------------------------------
# M2：候选池 CLI（--pool）与分类缺口优先排序
# ---------------------------------------------------------------------------

# 四分类（与 src/content.config.ts 的 category 枚举、determine_category_and_tags 口径一致）。
CATEGORIES = ("contraception", "pleasure", "body", "intimacy")
DEFAULT_CATEGORY = "body"
DISCOVERY_MODES = ("anchor", "sitemap", "feed")
ADMISSION_STATUSES = ("admitted", "probing", "rejected")
# --pool 默认输出条数（--limit 未显式传入时生效；harvest 默认仍为 1）。
POOL_DEFAULT_LIMIT = 40


def _normalize_category(candidate: dict) -> str:
    """取候选的推定分类：合法则原样返回，缺失/非法回退到 default_category，再回退到全局默认。"""
    category = candidate.get("category")
    if isinstance(category, str) and category in CATEGORIES:
        return category
    fallback = candidate.get("default_category")
    if isinstance(fallback, str) and fallback in CATEGORIES:
        return fallback
    return DEFAULT_CATEGORY


def rank_candidates(candidates: list, category_counts: dict) -> list:
    """按「分类缺口」重排候选：四分类按当前篇数升序（缺口大者优先），同分类内保持首次发现顺序。

    - **纯函数**：不改动入参，返回元素为浅拷贝并回填规范化后的 ``category``；
    - 排序键 = ``(当前该类已发布篇数, 输入下标)``；缺失的分类按 0 篇处理（缺口最大）；
    - ``category`` 缺失或非法时归入 ``default_category``（**不得丢弃该候选**）；
    - 空 ``candidates`` 返回 ``[]``。
    """
    if not candidates:
        return []
    counts = category_counts if isinstance(category_counts, dict) else {}

    def _sort_key(indexed_item):
        index, candidate = indexed_item
        category = _normalize_category(candidate)
        return (counts.get(category, 0), index)

    ordered = sorted(enumerate(candidates), key=_sort_key)
    return [
        {**candidate, "category": _normalize_category(candidate)}
        for _, candidate in ordered
    ]


def _read_text_file(path: str) -> str:
    """只读读取 UTF-8 文本；不可读时返回空串（使调用方可用守卫子句扁平化处理）。"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def count_articles_by_category() -> dict:
    """统计当前已发布文章的四分类篇数（**只读**：解析 frontmatter 的 ``category`` 字段）。

    口径与内容集合 loader 对齐：仅顶层 ``.mdx``、排除 ``_`` 前缀内部文件。
    """
    counts = {category: 0 for category in CATEGORIES}
    if not os.path.isdir(ARTICLES_DIR):
        return counts
    for name in os.listdir(ARTICLES_DIR):
        if not name.endswith(".mdx") or name.startswith("_"):
            continue
        text = _read_text_file(os.path.join(ARTICLES_DIR, name))
        match = re.search(r'^category:\s*"?([a-zA-Z0-9_-]+)"?', text, re.MULTILINE)
        if not match:
            continue
        category = match.group(1)
        counts[category] = counts.get(category, 0) + 1
    return counts


def collect_pool_candidates(source_id: str | None = None) -> list[dict]:
    """实时发现候选（``--pool`` 的数据源）：``discover_candidates`` 本次发现 − 台账已收录 URL。

    [Task-7 语义钉死] 数据源**不是**「台账里 ``status == "pending"`` 的条目」——当前没有任何
    代码写入 ``pending``，那样实现会永远输出空表。零副作用：仅经 ``load_ledger()`` 只读读取台账，
    **严禁调用 save_ledger()**。
    """
    if not os.path.exists(SOURCES_FILE):
        print(f"❌ 找不到数据源配置文件: {SOURCES_FILE}")
        return []

    with open(SOURCES_FILE, "r", encoding="utf-8") as f:
        sources = json.load(f)

    ledger = load_ledger()
    seen_urls = ledger_seen_urls(ledger) | get_existing_article_urls()

    pool: list = []
    seq = 0
    for src in sources:
        if source_id and src.get("id") != source_id:
            continue
        for full_url, title in discover_candidates(src, seen_urls):
            seen_urls.add(full_url)
            seq += 1
            category, _tags = determine_category_and_tags(title, "", src)
            pool.append(
                {
                    "title": title,
                    "category": category,
                    "default_category": src.get("default_category", DEFAULT_CATEGORY),
                    "source_name": src.get("name", ""),
                    "source_id": src.get("id", ""),
                    "url": full_url,
                    "first_seen": seq,
                }
            )
    return pool


def _print_pool_table(ranked: list, category_counts: dict, limit: int) -> None:
    """打印候选池表格（标题 / 来源 / 推定分类 / 首次发现）与表尾缺口汇总。"""
    shown = ranked[:limit] if limit and limit > 0 else ranked
    print("")
    print("标题 | 来源 | 推定分类 | 首次发现")
    print("-" * 88)
    for candidate in shown:
        print(
            f"{candidate.get('title', '')} | {candidate.get('source_name', '')} | "
            f"{candidate.get('category', '')} | {candidate.get('first_seen', '')}"
        )
    print("-" * 88)
    print(f"候选总数：{len(ranked)} 条（本次输出 {len(shown)} 条，--limit={limit}）")
    print("各分类缺口现状（当前篇数升序，缺口大者优先）：")
    for category in sorted(CATEGORIES, key=lambda name: (category_counts.get(name, 0), name)):
        print(f"  - {category}: 已发布 {category_counts.get(category, 0)} 篇")


def _load_sources() -> list:
    """只读加载 ``scripts/sources.json``；缺失 / 非法 JSON / 非数组时返回 ``[]``。"""
    if not os.path.exists(SOURCES_FILE):
        return []
    try:
        with open(SOURCES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


def _admitted_sources(source_id: str | None = None) -> list:
    """返回已准入（fail-closed 通过）的信源列表；``source_id`` 给定时按 id 过滤。"""
    admitted: list = []
    for src in _load_sources():
        if not isinstance(src, dict) or not is_source_admitted(src):
            continue
        if source_id and src.get("id") != source_id:
            continue
        admitted.append(src)
    return admitted


def _print_empty_pool_hint(source_id: str | None) -> None:
    """按两类空因分别打印可执行下一步（D2：统一为 ``pnpm curate:admit <id>`` 形态）。"""
    print("\n❌ 候选池为空")
    admitted = _admitted_sources(source_id)
    # 守卫子句：无已准入信源 ⇒ 原因(a)；否则为候选耗尽 ⇒ 原因(b)。
    if admitted:
        print(
            f"  原因(b)：已有 {len(admitted)} 个已准入（admitted）信源，但候选已耗尽"
            f"（本次发现结果均已在台账 / 已发布）。\n"
            f"  ➜ 请准入新信源：pnpm curate:admit <id>；"
            f"或扩大现有信源 discovery.link_pattern / keywords 以捕获更多候选。"
        )
        return

    matched = [
        src
        for src in _load_sources()
        if isinstance(src, dict) and source_id and src.get("id") == source_id
    ]
    if source_id and not matched:
        print(
            f"  原因(a)：未在 sources.json 找到信源 '{source_id}'（或该信源尚未准入）。\n"
            f"  ➜ 请先准入信源：pnpm curate:admit {source_id}"
        )
        return
    print(
        "  原因(a)：当前没有任何「已准入（admitted）」信源可供扫描。\n"
        "  ➜ 请先准入信源：pnpm curate:admit <id>（该命令只打印准入证据草案，需人工阅读许可页后填写）"
    )


def run_pool(source_id: str | None = None, limit: int = POOL_DEFAULT_LIMIT) -> int:
    """``--pool`` 分支：输出按分类缺口优先排序的候选池表格（零副作用：只读台账，不写盘/不提 PR）。

    返回进程退出码：0 = 正常输出；1 = 空候选池（Actionable-Empty-State，禁止静默返回空表）。
    """
    print("🔎 [候选池] 数据源 = 实时发现结果 − 台账已收录 URL（只读，零副作用）")
    pool = collect_pool_candidates(source_id=source_id)
    if not pool:
        _print_empty_pool_hint(source_id)
        return 1

    category_counts = count_articles_by_category()
    ranked = rank_candidates(pool, category_counts)
    _print_pool_table(ranked, category_counts, limit)
    return 0


# ---------------------------------------------------------------------------
# M2：草稿生成（--draft-url）与信源准入证据草案（--admit-source）——Task-9
# ---------------------------------------------------------------------------

# 许可页候选路径：仅作「抓取证据收集」的探测清单，绝不代替人工阅读与判定。
LICENSE_PATH_CANDIDATES = (
    "/copyright",
    "/terms",
    "/terms-and-conditions",
    "/legal",
    "/about/policies/publishing/copyright",
)
# 本机出口不可信的站点实测（CI-Egress-Only 提示语，来自计划「Fog of War」）。
LOCAL_EGRESS_UNTRUSTED_NOTE = (
    "本机出口实测结果不可信（cdc.gov 403 / unesco.org 403 / nhc.gov.cn 412 / "
    "scarleteen 与 amaze 000）"
)


def _host_of(url: str) -> str:
    """返回 URL 的 host（解析失败返回空串）。"""
    try:
        return urllib.parse.urlparse(url).netloc
    except ValueError:
        return ""


def _match_source_for_url(url: str, sources: list) -> dict:
    """按 ``base_url`` 前缀匹配信源（取最长匹配）；无匹配返回 ``{}``（零破坏升级）。"""
    best: dict = {}
    best_len = -1
    for src in sources:
        if not isinstance(src, dict):
            continue
        base = src.get("base_url") or ""
        if base and url.startswith(base) and len(base) > best_len:
            best, best_len = src, len(base)
    return best


def _skip_str_literal(text: str, start: int) -> int:
    """从 ``text[start]``（引号字符）起跳过整个字符串字面量，返回闭合引号后的下标。"""
    quote = text[start]
    index = start + 1
    length = len(text)
    while index < length:
        char = text[index]
        if char == "\\":
            index += 2
            continue
        if char == quote:
            return index + 1
        index += 1
    return length


def _find_object_close(text: str, open_index: int) -> int:
    """从 ``open_index``（``{``）起做字符串感知的花括号配平，返回匹配的 ``}`` 下标。

    字符串字面量（单 / 双 / 反引号）内的花括号不参与配平；找不到匹配返回 -1。
    """
    depth = 0
    index = open_index
    length = len(text)
    while index < length:
        char = text[index]
        if char in ("'", '"', "`"):
            index = _skip_str_literal(text, index)
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return -1


def _quiz_has_slug(source: str, slug: str) -> bool:
    """判定 ``DAILY_QUIZZES`` 中是否已存在该 slug 顶层键（``'<slug>': {``）。"""
    pattern = r"^\s*'" + re.escape(slug) + r"'\s*:\s*\{"
    return re.search(pattern, source, flags=re.MULTILINE) is not None


def _quiz_placeholder_entry(slug: str) -> str:
    """构造一条**语法合法**的速测题占位条目（含 articleId 锚点与 TODO 人工补题锚点）。"""
    return (
        f"  '{slug}': {{\n"
        f"    articleId: '{slug}',\n"
        f"    // TODO(human): 人工补题锚点 —— 请通读原文后补全题干 / 选项 / 正确项 / 解析。\n"
        f"    //   机器不得自证：禁止保留占位文字直接合并（G1 门禁强制文章↔速测题 1:1）。\n"
        f"    question: '【待人工补题】请通读原文后填写速测题干',\n"
        f"    options: ['【待人工补题】选项 A', '【待人工补题】选项 B'],\n"
        f"    correctIndex: 0,\n"
        f"    explanation: '【待人工补题】请填写简明权威原理解释',\n"
        f"  }},\n"
    )


def inject_quiz_placeholder(quiz_path: Path, slug: str) -> bool:
    """在 ``DAILY_QUIZZES`` 对象**末尾**插入一条速测题占位条目（幂等）。

    - 已存在同 slug 顶层键 ⇒ 直接返回 ``False`` 且**不改动文件**（幂等，sha256 不变）；
    - 成功插入 ⇒ 返回 ``True``；
    - 找不到 ``DAILY_QUIZZES`` / 花括号不配平 / 不可读 ⇒ 返回 ``False``（不写盘）；
    - 插入条目花括号配平、语法合法（否则 ``pnpm check`` 会红）。
    """
    quiz_path = Path(quiz_path)
    try:
        text = quiz_path.read_text(encoding="utf-8")
    except OSError:
        print(f"❌ 无法读取速测题文件：{quiz_path}")
        return False

    if _quiz_has_slug(text, slug):
        return False

    marker = text.find("DAILY_QUIZZES")
    if marker == -1:
        print(f"❌ 速测题文件缺少 DAILY_QUIZZES 对象：{quiz_path}")
        return False
    open_index = text.find("{", marker)
    if open_index == -1:
        return False
    close_index = _find_object_close(text, open_index)
    if close_index == -1:
        print(f"❌ DAILY_QUIZZES 对象花括号不配平，拒绝注入：{quiz_path}")
        return False

    entry = _quiz_placeholder_entry(slug)
    quiz_path.write_text(text[:close_index] + entry + text[close_index:], encoding="utf-8")
    return True


def _build_draft_candidate(url: str, sources: list) -> dict:
    """为 ``--draft-url`` 构造候选字典（复用既有标题/分类/清理口径，不改内容规范）。"""
    src = _match_source_for_url(url, sources)
    status, html = fetch_url(url, timeout=15)
    if status == 200 and html:
        page_title, desc = extract_metadata(html)
    else:
        print(f"  ⚠️ 候选页抓取失败 (HTTP {status})，改为从 URL 派生标题（人工仍须核对原文）")
        page_title, desc = "", ""

    anchor_title = _title_from_url(url)
    final_title = page_title if (page_title and len(page_title) >= len(anchor_title)) else anchor_title
    final_title = clean_title(final_title) or anchor_title or url

    category, tags = determine_category_and_tags(final_title, desc, src)
    return {
        "title": final_title,
        "summary": desc,
        "raw_desc": desc,
        "category": category,
        "tags": tags,
        "source_url": url,
        "source_name": src.get("name") or _host_of(url),
        "slug": generate_slug(category, src.get("id") or "", url),
        "source_id": src.get("id") or "",
        "http_status": status,
    }


def _register_pending(url: str, source_id: str, http_status) -> None:
    """[D1] 把候选以 ``status="pending"`` 登记入台账（`iter_pending` 的首个生产消费路径）。"""
    ledger = load_ledger()
    if url in ledger_seen_urls(ledger):
        print("  ⏭️ 该候选 URL 已在台账中，跳过 pending 登记")
        return
    today = datetime.date.today().isoformat()
    ledger.setdefault("processed_urls", []).append(
        {
            "url": url,
            "status": "pending",
            "source_id": source_id,
            "first_seen": today,
            "last_probed": today,
            "http_status": http_status,
        }
    )
    save_ledger(ledger)
    print(f"  ✓ 已登记 pending 台账：{LEDGER_FILE}")


def run_draft_url(url: str) -> int:
    """``--draft-url <url>`` 分支：生成 MDX 骨架 + 注入速测题占位 + 登记 pending 台账。

    返回进程退出码：0 = 成功；2 = 参数缺失 / 非法 URL。
    本命令**不**自动提 PR（人工闸门）：仅在本地生成骨架与占位，并打印下一步人工动作。
    """
    url = (url or "").strip()
    if not url:
        print("❌ --draft-url 需要提供候选 URL：pnpm curate:draft <url>")
        return 2
    if not re.match(r"https?://", url):
        print(f"❌ --draft-url 需要 http(s) URL，实际：{url!r}")
        return 2

    candidate = _build_draft_candidate(url, _load_sources())
    slug = candidate["slug"]
    target_path = os.path.join(ARTICLES_DIR, f"{slug}.mdx")
    if os.path.exists(target_path):
        slug = f"{slug}-{int(datetime.datetime.now().timestamp()) % 1000}"
        candidate["slug"] = slug
        target_path = os.path.join(ARTICLES_DIR, f"{slug}.mdx")

    print(f"\n📝 [草稿生成] 候选：{candidate['title']}")
    print(f"   分类={candidate['category']} 来源={candidate['source_name']} slug={slug}")

    # 1) 生成 MDX 骨架（复用 compose_mdx_content，内容规范不得改动）
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(compose_mdx_content(candidate))
    print(f"  ✓ 已生成 MDX 骨架：{target_path}")

    # 2) 注入速测题占位（幂等）
    if inject_quiz_placeholder(Path(QUIZ_FILE), slug):
        print(f"  ✓ 已注入速测题占位（articleId='{slug}'）到：{QUIZ_FILE}")
    else:
        print(f"  ⏭️ 速测题占位已存在（幂等，未改动）：{QUIZ_FILE}")

    # 3) [D1] 登记 pending 台账，并展示 iter_pending 消费路径
    _register_pending(candidate["source_url"], candidate["source_id"], candidate.get("http_status"))
    print(f"  📌 当前台账 pending 队列：{len(iter_pending(load_ledger()))} 条（iter_pending 消费路径已激活）")

    # 4) 打印下一步人工动作指引
    print(
        "\n" + "=" * 72 + "\n"
        "✅ 草稿骨架已生成。请完成以下**人工动作**后再提 PR（机器不得自证）：\n"
        f"  1) 通读原文，把 src/content/articles/{slug}.mdx 的三条占位要点改写为 3~5 条提炼干货，"
        "并删除占位文字与注释块；\n"
        f"  2) 补完速测题占位：编辑 src/data/dailyQuiz.ts 中 '{slug}' 条目，"
        "清空占位文字并填写题干 / 选项 / 正解 / 解析；\n"
        "  3) 运行 pnpm check && pnpm test 确认门禁全绿；\n"
        "  4) 自行提 PR（本工具不自动提交、不自动打勾）。\n"
        + "=" * 72
    )
    return 0


def _license_url_candidates(src: dict) -> list:
    """派生许可页候选 URL（既有 license_url 优先，再补常见路径）。"""
    admission = src.get("admission") if isinstance(src.get("admission"), dict) else {}
    candidates: list = []
    existing = admission.get("license_url")
    if isinstance(existing, str) and existing.strip():
        candidates.append(existing.strip())
    base_url = (src.get("base_url") or "").rstrip("/")
    if base_url:
        for path in LICENSE_PATH_CANDIDATES:
            candidate_url = base_url + path
            if candidate_url not in candidates:
                candidates.append(candidate_url)
    return candidates


def run_admit_source(source_id: str) -> int:
    """``--admit-source <id>`` 分支：打印准入证据草案（**只读，绝不写回 sources.json**）。

    [No-Auto-Approve] 本命令**禁止**自动把 status 改为 admitted、**禁止**自动填 license、
    **禁止**写回 sources.json；信任机制要求人工阅读许可页后自行填写。
    返回进程退出码：0 = 已打印草案；2 = 参数缺失；1 = 未找到该信源。
    """
    source_id = (source_id or "").strip()
    if not source_id:
        print("❌ --admit-source 需要提供信源 ID：pnpm curate:admit <id>")
        return 2

    src = next(
        (s for s in _load_sources() if isinstance(s, dict) and s.get("id") == source_id),
        None,
    )
    if src is None:
        print(f"❌ 未在 {SOURCES_FILE} 找到信源 id='{source_id}'")
        return 1

    base_url = src.get("base_url") or ""
    entry_url = src.get("entry_url") or base_url

    print(f"\n🛡️ [准入证据草案] 信源 id='{source_id}'（{src.get('name', '')}）")
    print("   ⚠️ 本命令只读：不会修改 sources.json，也不会自动置 admitted / 自动填 license。")

    print("\n① 可达性探测（本机出口，仅供参考，不可作准入证据）：")
    for label, probe_url in (("entry_url", entry_url), ("base_url", base_url)):
        if not probe_url:
            continue
        status, _ = fetch_url(probe_url, timeout=10)
        print(f"   - {label}: {probe_url} → HTTP {status}")

    print("\n② 许可页抓取证据收集（license_url 候选）：")
    candidates = _license_url_candidates(src)
    if not candidates:
        print("   - （无 base_url，无法派生许可页候选；请人工补充）")
    for candidate_url in candidates:
        status, _ = fetch_url(candidate_url, timeout=10)
        mark = "✅ 可达" if status == 200 else f"⚠️ 不可达 (HTTP {status})"
        print(f"   - {candidate_url} → {mark}")

    print("\n③ admission 草案（请人工补全后**自行**粘贴到 scripts/sources.json）：")
    draft = {
        "status": "probing",
        "license": "",
        "license_url": candidates[0] if candidates else "",
        "verified_at": "",
        "verified_by_run": "",
    }
    print(json.dumps(draft, ensure_ascii=False, indent=2))

    print(
        "\n⚠️ No-Auto-Approve：本命令**不会**自动通过。请人工打开上述许可页、阅读条款后，"
        "再**自行**填写 license / license_url 并把 status 置为 \"admitted\"。\n"
        "⚠️ CI-Egress-Only：verified_by_run 必须来自 CI 出口（GitHub Actions run URL）——"
        f"{LOCAL_EGRESS_UNTRUSTED_NOTE}。\n"
        "   （在本地执行本命令得到的可达性仅为参考，准入证据须补一次 CI 运行。）"
    )
    return 0


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

        # 更新台账（v2 对象口径；单写者纪律：仅经 load_ledger / save_ledger）
        ledger = load_ledger()
        if candidate["source_url"] not in ledger_seen_urls(ledger):
            today = datetime.date.today().isoformat()
            ledger.setdefault("processed_urls", []).append(
                {
                    "url": candidate["source_url"],
                    "status": "published",
                    "source_id": candidate.get("source_id", ""),
                    "first_seen": today,
                    "last_probed": today,
                    "http_status": 200,
                }
            )
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
    parser.add_argument("--limit", type=int, default=None, help="每次抓取并生成的候选数量（默认 1；--pool 默认 40）")
    parser.add_argument("--source-id", help="限定仅扫描指定信源 ID (who-fact-sheets / msd-women-health)")
    parser.add_argument("--pool", action="store_true", help="输出按分类缺口优先排序的候选池（只读，零副作用）")
    parser.add_argument(
        "--draft-url",
        metavar="URL",
        help="为指定候选 URL 生成 MDX 骨架 + 注入速测题占位 + 登记 pending（用法：pnpm curate:draft <url>）",
    )
    parser.add_argument(
        "--admit-source",
        metavar="SOURCE_ID",
        help="输出指定信源的准入证据草案（只打印，绝不写回 sources.json；用法：pnpm curate:admit <id>）",
    )
    parser.add_argument("--save-draft", action="store_true", help="直接在当前分支保存 .mdx 草稿文件")
    parser.add_argument("--create-pr", action="store_true", help="自动建立特性分支并提交 GitHub Draft PR")

    args = parser.parse_args()

    # --pool：零副作用只读分支（不写台账、不写文章、不建分支、不提 PR，严禁 save_ledger）。
    if args.pool:
        pool_limit = args.limit if args.limit is not None else POOL_DEFAULT_LIMIT
        sys.exit(run_pool(source_id=args.source_id, limit=pool_limit))

    # --draft-url：生成骨架 + 注入速测题占位 + 登记 pending（人工闸门前置，不提 PR）。
    if args.draft_url:
        sys.exit(run_draft_url(args.draft_url))

    # --admit-source：只打印准入证据草案（No-Auto-Approve：绝不写回 sources.json）。
    if args.admit_source:
        sys.exit(run_admit_source(args.admit_source))

    harvest_limit = args.limit if args.limit is not None else 1
    candidates = harvest_candidates(limit=harvest_limit, source_id=args.source_id)
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
