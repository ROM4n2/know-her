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
import xml.etree.ElementTree as ET
from html import unescape

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
ARTICLES_DIR = os.path.join(ROOT_DIR, "src", "content", "articles")
SOURCES_FILE = os.path.join(SCRIPT_DIR, "sources.json")
LEDGER_FILE = os.path.join(SCRIPT_DIR, ".curate-ledger.json")

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
