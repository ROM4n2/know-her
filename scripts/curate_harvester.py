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


def _http_get(url: str, timeout: int = 15) -> tuple[int, str, str]:
    """低层 HTTP GET：返回 ``(status, body, final_url)``。

    [F1 修复] ``final_url`` 取自 ``resp.geturl()``。urllib **默认跟随重定向**，若不回传
    落地 URL，调用方只会看到落地页的状态码（通常 200），无从得知请求的页面其实被重定向。
    ``HTTPError`` ⇒ ``(e.code, "", url)``；其它异常 ⇒ ``(0, "", url)``。
    """
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
            return resp.status, body, resp.geturl()
    except urllib.error.HTTPError as e:
        return e.code, "", url
    except Exception:
        return 0, "", url


def fetch_url(url: str, timeout: int = 15) -> tuple[int, str]:
    """``_http_get`` 的薄包装：**契约冻结**，仍返回 ``(status, body)`` 二元组。

    [契约] anchor/sitemap/feed 三模式发现链路有 5+ 处按二元组解包；**不得**改为三元组，
    否则会静默破坏发现链路。
    """
    status, body, _final_url = _http_get(url, timeout=timeout)
    return status, body


def _url_key(url: str) -> str:
    """归一化比较键：小写 scheme+host、去 fragment、去尾部 ``/``；保留 query。

    例：``https://a.com/x/`` == ``https://a.com/x``；``https://a.com/`` == ``https://a.com``；
    ``https://a.com/x#f`` == ``https://a.com/x``。
    """
    try:
        parts = urllib.parse.urlsplit(url or "")
    except ValueError:
        return (url or "").strip()
    path = parts.path
    if path.endswith("/"):
        path = path.rstrip("/")
    return urllib.parse.urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, parts.query, ""))


def probe_page(url: str, site_root: str, root_length: int = 0, timeout: int = 10) -> dict:
    """探测单页并对「重定向到首页」假阳性作出判定（F1 核心）。

    ``verdict`` 取值：
      - ``unreachable``：``status != 200``；
      - ``redirect_home``：``status == 200`` 且（落回站点根，或内容长度与首页指纹一致）；
      - ``real``：其它；若发生重定向则 ``note`` 记录落地 URL（证据可审计）。
    """
    status, body, final_url = _http_get(url, timeout=timeout)
    content_length = len(body)
    result = {
        "requested_url": url,
        "status": status,
        "final_url": final_url,
        "content_length": content_length,
        "verdict": "real",
        "note": "",
    }

    # 守卫子句化：不可达优先判定（异常/HTTP 错误一律视为不可达）
    if status != 200:
        result["verdict"] = "unreachable"
        return result

    # 主判据：请求的不是首页，却落回站点根
    requested_is_root = _url_key(url) == _url_key(site_root)
    landed_on_root = _url_key(final_url) == _url_key(site_root)
    if landed_on_root and not requested_is_root:
        result["verdict"] = "redirect_home"
        result["note"] = "落回站点根"
        return result

    # 二次指纹信号：发生了重定向，且内容长度与首页一模一样
    # [F1b-H2 口径一致] 用 _url_key 归一化比较，避免「仅尾斜杠不同」被误判为发生过重定向
    # （与同函数上方主判据 _url_key 比较口径保持一致；否则 note 会写出误导性「重定向后落地 …」）。
    redirected = _url_key(final_url) != _url_key(url)
    if redirected and root_length > 0 and content_length == root_length:
        result["verdict"] = "redirect_home"
        result["note"] = "与首页指纹一致"
        return result

    # 判为 real：若曾重定向，note 记录落地 URL 供人工审计
    if redirected:
        result["note"] = f"重定向后落地 {final_url}"
    return result


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


# [B 修复] 草稿模板必须产出「MDX 合法」正文：MDX 不接受 HTML 注释 `<!-- -->`（构建报
# `Unexpected character '!' ... use {/* text */}`），故所有**静态**提示一律用 JSX 注释 `{/* ... */}`。
#
# 抓取来的文本（candidate['raw_desc']）**严禁**放进 MDX（包含 JSX 注释），理由有二：
#   ① 外部文本不可控：一旦含 `*/`，会**提前闭合** `{/* ... */}` 注释，余下内容随即被当作 JSX/JS
#      解析（真机实测：`{/* grab: a */ tail */}` 报 “Unexpected end of file in expression”），
#      整篇构建崩溃；静态文案可安全放入注释，抓取文本不行。
#   ② ADR-0002 双轨制：只允许「精炼导读 + 原文直达链接」，原出处描述摘录仅作审阅参考，
#      不得进入文章正文。
#   因此第三段「原出处描述摘录」块从 MDX 中移除，改由候选 PR 正文（gh pr create --body）承载。
def compose_mdx_content(candidate: dict) -> str:
    """把候选合成为 MDX 草稿正文（输出必须能被 `pnpm build` 的 MDX 编译器接受）。

    [B 修复] 输出不得含 HTML 注释 `<!--`；抓取文本 raw_desc 一律不进正文（见上方说明）。
    """
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    tags_yaml = "\n".join([f"  - {t}" for t in candidate["tags"]])
    
    # summary 严禁沿用来源页面自带的 description：
    # ADR-0002 双轨制要求「精炼导读 + 原文直达链接」，直接搬运原文句子属版权风险与信任事故。
    # 机器只留占位，必须由维护者通读原文后改写。
    summary = "【待维护者人工提炼】本候选由流水线自动抓取，尚未撰写本站导读摘要，合并前必须通读原文并改写为精炼看点。"

    # [P0-2 修复] 机器阶段**严禁**写入证据等级 / 复审人 / 最后核验日期三个字段：
    #   · evidence_tier 曾硬编码 "A"（全站最高等级）——机器自评证据等级属「机器自证」，
    #     且 harvest_candidates 从不产出该键 ⇒ 恒取 A。现一律**省略**该键，由
    #     src/content.config.ts 的 schema default（'B'）兜底：**Schema 是唯一真值源**，此处不得写死任何值；
    #   · 复审人与最后核验日期同理：机器填今天 / 填空串 ⇒ 页面向读者显示「已核验」，
    #     实为未核验。二者一律省略，由人工核验后补写。
    mdx = f"""---
title: "{candidate['title']}"
pubDate: {today_str}
summary: "{summary}"
category: "{candidate['category']}"
tags:
{tags_yaml}
source_url: "{candidate['source_url']}"
source_name: "{candidate['source_name']}"
author: "{candidate['source_name']}"
is_full_text: false
---

{{/*
机器生成的候选草稿：正文要点尚未撰写，禁止直接合并。

合并前必须依次完成（PR Checklist 严禁机器自勾选，必须由人核实）：
  1. 跳转 source_url 通读原文，核实主题与本条完全匹配、无张冠李戴；
  2. 把下方三条占位要点改写为 3~4 条真正有医学增量的提炼干货，删除占位文字与本注释块；
  3. 确认零版权搬运：只保留人工提炼要点 + 原文直达链接（抓取来的原出处描述摘录仅存于 PR 描述，
     严禁搬入正文）；
  4. 补写 frontmatter 的 summary；证据等级 / 复审人 / 最后核验日期三类字段一律由人工核验后填写，
     机器不得代填（禁止机器自证）；
  5. 补全速测题占位：在 src/data/dailyQuiz.ts 中找到与本文件同名的条目（articleId 与本站文件名一致），
     把题干 / 选项 / 正确项 / 解析四项写完整——G1 门禁强制文章↔速测题 1:1，占位未补全即判定
     「文章缺少速测题」而必红，占位文字绝不可直接合并。
本文件由 scripts/curate_harvester.py 自动生成，仅完成了外链探活与 Schema 结构校验。
*/}}

## 核心要点导读

{{/* 以下 3 条为占位符，必须由维护者通读原文后重写，切勿保留原样合并 */}}
1. **核心机制与客观认知**：（待人工提炼）
2. **日常自我关注与防范**：（待人工提炼）
3. **常见误区与就医时机**：（待人工提炼）

## 原出处直达

本导读为策展精炼版。完整数据、分型细节与官方建议请点击下方按钮直达**{candidate['source_name']}**原文页面。
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


def _existing_article_path_for_url(url: str) -> str:
    """返回 ``ARTICLES_DIR`` 中 ``source_url`` == ``url`` 的 .mdx 路径（无则返回空串）。

    [E1] 供「判重前置」命中时打印**指向已存在文件**的路径，避免维护者以为工具坏了。
    """
    if not os.path.isdir(ARTICLES_DIR):
        return ""
    for name in sorted(os.listdir(ARTICLES_DIR)):
        if not name.endswith(".mdx"):
            continue
        path = os.path.join(ARTICLES_DIR, name)
        try:
            with open(path, "r", encoding="utf-8") as f:
                m = re.search(r"source_url:\s*\"([^\"]+)\"", f.read())
        except OSError:
            continue
        if m and m.group(1).strip() == url:
            return path
    return ""


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

    # [E1 修复] 判重必须**前置到写盘之前**。原实现先写 .mdx + 注入速测题占位、再由
    # _register_pending 内部判重 ⇒ 同一 URL 二次执行产出**两个** .mdx 与**两条**占位
    # （台账仅 1 条，第二次仍打印误导性的「跳过 pending 登记」），而 G1 因双份对称**恒绿**
    # ⇒ 重复文章可直接上线。命中台账或既有文章即早退，不写任何文件。
    if url in ledger_seen_urls(load_ledger()) or url in get_existing_article_urls():
        exists_at = _existing_article_path_for_url(url) or f"（台账已登记，见 {LEDGER_FILE}）"
        print(f"\n⏭️ 该 URL 已存在，未重复生成：{exists_at}")
        print("   若确需重新生成：先删除上述 .mdx（并同步移除 dailyQuiz.ts 中同名条目），"
              "或从台账移除该 URL 后重试。")
        return 0

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


def _print_license_probe(candidate_url: str, info: dict) -> None:
    """按 verdict 三态渲染单条许可页候选探测结果。

    [F1 修复] 严禁把 ``redirect_home`` 显示为「✅ 可达」——那会误导人工照着假页面核许可条款。
    """
    verdict = info.get("verdict")
    if verdict == "real":
        final = info.get("final_url")
        suffix = f", final={final}" if final and final != candidate_url else ""
        print(f"   - {candidate_url} → ✅ 可达（真实页面, len={info.get('content_length', 0)}{suffix}）")
        return
    if verdict == "redirect_home":
        print(
            f"   - {candidate_url} → ⚠️ 疑似重定向到首页（非真实许可页）："
            f"请求 {candidate_url} → 落地 {info.get('final_url')}，"
            f"len={info.get('content_length', 0)}（{info.get('note', '')}）"
        )
        return
    print(f"   - {candidate_url} → ⚠️ 不可达 (HTTP {info.get('status')})")


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
    # [F1b-H1 接线] 复用**已有**的 base_url 探测响应作为「首页内容长度指纹」，供 ② 许可页候选的
    # 二次指纹判据使用——**不新增任何网络请求**（base_url 探测本就发生在此处，仅捕获其 content_length）。
    # 这使 probe_page 的二次指纹判据（status==200 且发生重定向 且 content_length==首页长度）在生产态
    # 真正可触发，而非仅在测试显式传 root_length 时才激活（消除「测试专用激活」的假绿）。
    # [有意降级] base_url 探测失败（status != 200）或 content_length == 0 ⇒ root_length 保持 0，
    # 二次指纹判据自然休眠（宁可漏报、不可误报；主判据「落回站点根即 redirect_home」仍始终生效）。
    root_length = 0
    for label, probe_url in (("entry_url", entry_url), ("base_url", base_url)):
        if not probe_url:
            continue
        info = probe_page(probe_url, base_url, timeout=10)
        print(
            f"   - {label}: {probe_url} → HTTP {info['status']} 落地 {info['final_url']} "
            f"[{info['verdict']}]"
        )
        if label == "base_url" and info["status"] == 200 and info["content_length"] > 0:
            root_length = info["content_length"]

    print("\n② 许可页抓取证据收集（license_url 候选）：")
    candidates = _license_url_candidates(src)
    if not candidates:
        print("   - （无 base_url，无法派生许可页候选；请人工补充）")
    probes = [
        (candidate_url, probe_page(candidate_url, base_url, root_length=root_length, timeout=10))
        for candidate_url in candidates
    ]
    for candidate_url, info in probes:
        _print_license_probe(candidate_url, info)
    if candidates:
        real_count = sum(1 for _, info in probes if info["verdict"] == "real")
        print(f"   - 真实可用候选：{real_count} / 总候选 {len(candidates)}")

    print("\n③ admission 草案（请人工补全后**自行**粘贴到 scripts/sources.json）：")
    real_license_url = next(
        (candidate_url for candidate_url, info in probes if info["verdict"] == "real"),
        "",
    )
    if not real_license_url:
        print("   ⚠️ 未找到真实可用的许可页候选，请人工补充 license_url")
    draft = {
        "status": "probing",
        "license": "",
        "license_url": real_license_url,
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


# [D 修复] create_draft_pr 的三种结果必须**可区分**：禁止再用布尔 True 同时表示
# 「创建成功」与「因已有待审 PR 跳过」——否则 main() 会把「跳过」当成功 ⇒ 每日取同一榜首候选
# → 打印 ⏭️ → exit 0（连续多日零产出却全绿）。
PR_RESULT_CREATED = "created"
PR_RESULT_SKIPPED_DUPLICATE = "skipped_duplicate"
# [P0-1] 远端**已残留**该候选分支（关闭/未创建的 PR 都会把分支留在远端，可能含人工提交）：
# 此时**绝不**推送，返回本可区分结果，并打印可执行的解锁指引（git push origin --delete <branch>）。
PR_RESULT_SKIPPED_REMOTE_EXISTS = "skipped_remote_exists"
PR_RESULT_ERROR = "error"

# [R3 修复] 本常量**仅**用于限制「发现」候选的开销（每次抓取多少个候选供选择），
# 不再是判定「本日零进展」的依据——零进展已由 run_create_pr 的「一次性预排除已被占用的候选」
# 逻辑判定（见 fetch_open_candidate_branches / run_create_pr）。故适当提高上限，避免
# 积压 >= 5 时候选批被已有待审 PR 全部占满而复现零进展死锁。
PR_CANDIDATE_BATCH = 10


class DraftPrResult(str):
    """[R1 修复] ``create_draft_pr`` 的返回值：``==`` PR_RESULT_* 常量，并额外携带分支名。

    继承 ``str`` 以**保持既有契约**（``result == PR_RESULT_CREATED`` 等断言不变、布尔误用仍可判红），
    同时通过 ``.branch`` 把新建分支名**返回**给上层（``run_create_pr`` / 工作流），
    使「本地无 ``$GITHUB_OUTPUT``」时上游仍能拿到分支名。``branch`` 为空串表示未创建分支。
    """

    branch: str

    def __new__(cls, result: str, branch: str = ""):
        obj = super().__new__(cls, result)
        obj.branch = branch
        return obj


def _emit_step_output(key: str, value: str) -> None:
    """[R1 修复] 把 ``key=value`` 追加写入 ``$GITHUB_OUTPUT``（指向可写文件时）。

    本地运行无该环境变量（或不可写）时**静默跳过**：分支名仍由 ``create_draft_pr`` 的
    ``DraftPrResult.branch`` 返回给上层，两条通道互补。
    """
    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        return
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"{key}={value}\n")
    except OSError:
        pass


# [R3 修复] ``--create-pr`` 一次性取回的 open 候选 PR 分支缓存：
#   ``set`` = 已取回（权威，create_draft_pr 据此跳过被占用候选，**不再逐个候选打 API**）；
#   ``None`` = 未取回（取回失败，退回逐个候选的 ``gh pr list --head`` 检查，即现状逻辑）。
_OPEN_CANDIDATE_BRANCHES: "set | None" = None


def fetch_open_candidate_branches() -> "set | None":
    """[R3 修复] **一次** ``gh pr list`` 取回全部 open 候选 PR 的分支名（仅 ``candidate/`` 前缀）。

    成功返回分支名集合（含空集）；网络/权限/解析失败返回 ``None``（调用方据此退回逐个候选检查，
    不直接崩溃）。单次调用取代「对每个候选各打一次 ``--head``」的 O(N) 开销。
    """
    res = subprocess.run(
        ["gh", "pr", "list", "--state", "open", "--json", "headRefName"],
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        print(
            "  ⚠️ 一次性取回 open PR 列表失败，退回逐个候选 --head 检查："
            f"{(res.stderr or '').strip()[:160]}"
        )
        return None
    try:
        payload = json.loads(res.stdout or "[]")
    except json.JSONDecodeError:
        print("  ⚠️ open PR 列表输出非 JSON，退回逐个候选 --head 检查")
        return None
    branches: set = set()
    for item in payload if isinstance(payload, list) else []:
        name = (item or {}).get("headRefName") if isinstance(item, dict) else None
        if isinstance(name, str) and name.startswith("candidate/"):
            branches.add(name)
    return branches


# [黄卡-3] 远端探测次数 = 首次 + 重试 1 次：单次网络抖动不得让整批候选被误判「远端已存在」而跳过
# （fail-closed 是正确语义，但**只在确认探测真的失败时**才成立；抖动不是失败）。
LS_REMOTE_ATTEMPTS = 2


def _remote_branch_exists(branch_name: str) -> bool:
    """[P0-1] 探测远端是否已存在该分支（fail-closed：探测**确认**失败一律按「已存在」处理 ⇒ 不推送）。

    背景（已实测）：关闭候选 PR **不会**删除远端分支；``--force-with-lease`` 在不带显式期望值时
    基准取自 ``refs/remotes/origin/<branch>``，而本仓 refspec（含 CI 的 ``fetch-depth: 0``）保证
    ``origin/<branch>`` 存在 ⇒ lease **恒成立** ⇒ 次日 force 推送会**静默覆盖**人工提交且不可恢复。
    故本仓库对候选分支**永不**强制覆盖：不存在才正常 push，存在即跳过并给出解锁指引。

    [黄卡-3] 单次抖动即整批误跳过（每个候选都判「远端已存在」）是**假故障**，故先重试 1 次；
    重试后仍失败才 fail-closed（宁可不推，也不覆盖人工提交）。
    """
    cmd = ["git", "ls-remote", "--heads", "origin", branch_name]
    last_stderr = ""
    for attempt in range(1, LS_REMOTE_ATTEMPTS + 1):
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            return bool((res.stdout or "").strip())
        last_stderr = (res.stderr or "").strip()[:160]
        print(
            f"  ⚠️ 远端分支探测第 {attempt}/{LS_REMOTE_ATTEMPTS} 次失败"
            f"（git ls-remote 非零退出），重试中…：{last_stderr}"
        )
    print(
        f"  ⚠️ 远端分支探测连续 {LS_REMOTE_ATTEMPTS} 次失败，按 fail-closed 视为「已存在」并跳过："
        f"{last_stderr}"
    )
    return True


def _delete_remote_branch(branch_name: str) -> None:
    """[P0-1] best-effort 删除远端候选分支：失败仅告警，**绝不**抛出（不得让流程崩溃）。

    用途：``gh pr create`` 失败时分支已推送到远端，若不清理，新的 ls-remote 守卫会把该候选
    **永久阻塞**（每次都判「远端已存在」）。清理失败时打印人工可执行命令兜底。
    """
    try:
        res = subprocess.run(
            ["git", "push", "origin", "--delete", branch_name],
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"  ⚠️ 清理远端分支 {branch_name} 时异常（请人工执行下方命令）：{exc}")
        res = None
    if res is not None and res.returncode == 0:
        print(f"  ✓ 已清理远端残留分支：{branch_name}")
        return
    detail = "" if res is None else (res.stderr or "").strip()[:160]
    print(
        f"  ⚠️ 清理远端分支 {branch_name} 失败（该候选会被远端守卫跳过，"
        f"请人工执行：git push origin --delete {branch_name}）：{detail}"
    )


def _branch_already_open(branch_name: str) -> bool:
    """[R3] 判定候选分支是否已有待审 PR：优先用一次性缓存，缺失时退回逐个 ``--head`` 检查。"""
    cached = _OPEN_CANDIDATE_BRANCHES
    if cached is not None:
        return branch_name in cached
    dup = subprocess.run(
        ["gh", "pr", "list", "--head", branch_name, "--state", "open", "--json", "number"],
        capture_output=True,
        text=True,
    )
    return dup.returncode == 0 and dup.stdout.strip() not in ("", "[]")


def create_draft_pr(candidate: dict) -> "DraftPrResult":
    """为单个候选创建 Draft PR，返回**可区分**的 ``DraftPrResult``。

    ``==`` ``PR_RESULT_CREATED`` / ``PR_RESULT_SKIPPED_DUPLICATE`` / ``PR_RESULT_ERROR``；
    调用方（``run_create_pr``）据其继续尝试下一个候选或判定「本日零进展」。

    [R1 修复] 成功创建分支后：把 ``branch=<branch_name>`` 写入 ``$GITHUB_OUTPUT``（缺失即静默跳过），
    并通过返回值的 ``.branch`` 把分支名交回上层；跳过 / 失败时 ``branch`` 为**空串**（下游不得误以为有分支）。
    """
    slug = candidate["slug"]
    branch_name = f"candidate/{slug}"
    target_file = os.path.join(ARTICLES_DIR, f"{slug}.mdx")

    # 1. 检查 git 状态
    st = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
    if st.stdout.strip():
        print("❌ 当前 Git 工作区存在未提交变更，请先保存后再发起 Draft PR")
        _emit_step_output("branch", "")
        return DraftPrResult(PR_RESULT_ERROR, "")

    current_branch = subprocess.run(
        ["git", "branch", "--show-current"], capture_output=True, text=True
    ).stdout.strip()

    # [P0-3] 速测题占位注入会**改动** src/data/dailyQuiz.ts：未成功提交时（校验/暂存/提交任一失败）
    # 该改动会被 `git checkout` 带回主工作区并污染后续候选 ⇒ 备份后按需逐字节还原。
    quiz_backup = None
    committed = False

    print(f"\n🚀 开始自动化 PR 流程: {branch_name}")
    try:
        # 防重复守卫：该候选分支若已有待审 PR，直接跳过，避免每日重复刷 PR。
        # [R3] 优先用一次性取回的缓存（无逐候选 API）；缓存缺失时退回 --head 检查。
        if _branch_already_open(branch_name):
            # [D 修复] 跳过必须是**可区分**的结果（不再是当成功的 True）：调用方据此继续尝试下一候选。
            print(f"  ⏭️ 分支 {branch_name} 已存在待审 PR，跳过本候选（尝试下一个）")
            _emit_step_output("branch", "")
            return DraftPrResult(PR_RESULT_SKIPPED_DUPLICATE, "")

        # [P0-1] 远端分支存在性守卫（推送之前）：关闭候选 PR 不会删除远端分支，残留分支可能含
        # 人工提交。此时**一律不推送**（本项目永不强制覆盖），改而给出可执行的解锁指引。
        if _remote_branch_exists(branch_name):
            print(f"  ⏭️ 远端分支 {branch_name} 已存在，跳过本候选（未推送、未覆盖任何提交）")
            print(
                f"::warning::远端分支 {branch_name} 已存在（可能含人工提交），已跳过且未推送。"
                f"若要重新提案，请先删除：git push origin --delete {branch_name}"
            )
            _emit_step_output("branch", "")
            return DraftPrResult(PR_RESULT_SKIPPED_REMOTE_EXISTS, "")

        # 创建分支
        subprocess.run(["git", "checkout", "-b", branch_name], check=True)

        # 写入 MDX
        mdx_content = compose_mdx_content(candidate)
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(mdx_content)
        print(f"  ✓ 已生成草稿文件: {target_file}")

        # [R2 修复] 此处**不再**写入台账（方案 A）：候选分支已不提交台账（C 修复）⇒ CI 中该写入
        # 不持久化、纯属无用写入；且在 push/pr 失败时会污染工作区、拖垮后续候选的入口预检。
        # 本地人工流程的 D1 台账登记保留在 run_draft_url（未被本批改动）。

        # 验证合规性
        # [P0-2] --allow-machine-draft：草稿按设计含人工占位（要点/速测题/核验字段），
        # 占位防呆只作用于**合并门禁**（pnpm curate:check），不拦截机器自检结构合法性。
        chk = subprocess.run(
            ["python", os.path.join(SCRIPT_DIR, "curate.py"), "check", "--allow-machine-draft"],
            capture_output=True, text=True,
        )
        if chk.returncode != 0:
            print(f"❌ 草稿结构校验失败:\n{chk.stdout}\n{chk.stderr}")
            raise RuntimeError("curate check failed")

        # [P0-3 修复] 每日 PR 路径必须**同样**注入速测题占位：此前只有本地 run_draft_url 注入，
        # ⇒ 候选分支内只有 .mdx 没有题，[G1]「文章缺少速测题」必红，而 PR 正文与模板都没点名速测题，
        # 维护者做完所有可见指引仍无法变绿且不知缺什么。
        try:
            quiz_backup = Path(QUIZ_FILE).read_text(encoding="utf-8")
        except OSError:
            quiz_backup = None
        if inject_quiz_placeholder(Path(QUIZ_FILE), slug):
            print(f"  ✓ 已注入速测题占位（articleId='{slug}'）到：{QUIZ_FILE}")
        else:
            print(f"  ⏭️ 速测题占位已存在或无法注入（幂等，未改动）：{QUIZ_FILE}")

        # Git commit
        # [C 修复] 只提交草稿文件与速测题占位，**不**提交 scripts/.curate-ledger.json：台账是机器状态，
        # master 侧每日运行也会写它 ⇒ 把它提交进候选分支必然与 master 冲突（PR #4 mergeable=CONFLICTING
        # 即由此而来）。故候选分支只携带 .mdx 与 dailyQuiz.ts。
        subprocess.run(["git", "add", target_file, QUIZ_FILE], check=True)
        commit_msg = f"feat(curate): 自动生成候选导读草稿《{candidate['title']}》"
        subprocess.run(["git", "commit", "-m", commit_msg], check=True)
        committed = True

        # Git push (带重试机制，防止网络抖动)
        # [P0-1] 普通推送，无任何 --force*：远端分支已由上方 ls-remote 守卫确认**不存在**，
        # 故不需要强制覆盖；若推送仍失败（non-fast-forward）说明守卫之外仍有残留 ⇒ 交给人工解锁。
        print(f"  ⬆️ 正在推送分支 {branch_name} 至远端 GitHub...")
        pushed = False
        for attempt in range(1, 4):
            try:
                subprocess.run(
                    ["git", "push", "-u", "origin", branch_name],
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
- [ ] **补全速测题占位**：`src/data/dailyQuiz.ts` 中本条（articleId `{slug}`）的占位条目已写全
      **题干 / 选项 / 正确项 / 解析**四项——G1 门禁强制文章↔速测题 **1:1**，占位未补全即判定
      「文章缺少速测题」而必红，占位文字绝不可直接合并；
- [ ] **版权合规核验**：遵循 ADR-0002 双轨制（精炼导读 + 原文直达链接，无侵权搬运）；
- [ ] **冲突化解**：若本 PR 显示与主分支冲突，`src/data/dailyQuiz.ts` 的冲突只需**保留双方条目**
      （各条目按 articleId 独立），勿删他人条目；
- [ ] **CI 门禁全绿**：Astro 编译与外链真实探测均 PASS。

### 📎 原出处描述摘录（仅作审阅参考，严禁搬运进文章正文）
{candidate.get('raw_desc', '') or '（来源页未提供 description）'}
"""

        # gh pr create
        print("  📋 正在创建 GitHub Draft PR...")
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
            # [R1] 分支确已提交并推送成功：把分支名交给上层（$GITHUB_OUTPUT + 返回值）。
            _emit_step_output("branch", branch_name)
            return DraftPrResult(PR_RESULT_CREATED, branch_name)
        print(f"❌ gh pr create 失败: {res.stderr}")
        # [P0-1] 分支此时**已推送**到远端但 PR 未建成 ⇒ 残留分支会让新的 ls-remote 守卫把该候选
        # **永久阻塞**（此后每天都判「远端已存在」）。故 best-effort 删除（失败也不得让流程崩溃）。
        _delete_remote_branch(branch_name)
        _emit_step_output("branch", "")
        return DraftPrResult(PR_RESULT_ERROR, "")

    except Exception as e:
        print(f"❌ 流程异常: {e}")
        _emit_step_output("branch", "")
        return DraftPrResult(PR_RESULT_ERROR, "")
    finally:
        # 无论成功失败，恢复原分支
        subprocess.run(["git", "checkout", current_branch], check=False)
        # [P0-3] 未成功提交时，速测题占位的改动不会随 checkout 消失（会被带回主工作区），
        # 必须按备份逐字节还原，否则批次内后续候选的入口预检会因工作区脏而直接判 ERROR。
        if not committed and quiz_backup is not None:
            try:
                Path(QUIZ_FILE).write_text(quiz_backup, encoding="utf-8")
            except OSError as exc:
                # [黄卡-2] 此处**严禁**静默吞异常：还原失败 ⇒ 速测题占位的改动留在工作区而无人知晓，
                # 批次内**后续候选**会因入口预检「工作区脏」直接判 ERROR——现象在后续候选、
                # 根因却在本次还原失败，静默后无从排查（与「机器不得自证」同源：异常也必须可见）。
                print(
                    f"  ⚠️ 还原 {QUIZ_FILE} 失败（{exc}）：速测题占位改动仍留在工作区，"
                    f"后续候选可能因工作区脏而直接判 ERROR。请人工核对并还原该文件后重跑本批次。"
                )
        # [R2 修复] 清理可能残留的（未提交 / 未跟踪）草稿文件：恢复原分支后，若该 .mdx 仍留在
        # 工作区，会让批次内**后续候选**的入口预检 `git status --porcelain` 直接判 ERROR。
        # 成功路径下草稿已提交在候选分支、master 上不存在此文件，此清理为无害空操作。
        if os.path.exists(target_file):
            try:
                os.remove(target_file)
            except OSError:
                pass


def _append_step_summary(markdown: str) -> None:
    """把结论追加写入 $GITHUB_STEP_SUMMARY（环境变量缺失时静默跳过，等价于本地运行）。"""
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    try:
        with open(summary_path, "a", encoding="utf-8") as f:
            f.write(markdown)
    except OSError:
        pass


def _report_backlog(reason: str) -> None:
    """[R4 修复] 上报**积压**（候选全部已有待审 PR，即「轮到人审了」）：非故障。

    打印 ``::warning::`` + 运行摘要，措辞明确点名「积压 / 等待人工审阅」，**不**含「故障」字样；
    调用方应据此 ``exit 0``——定时 Harvest **不得**因积压而每天变红。
    """
    message = f"本日零进展：{reason}"
    print(f"\n⏸️ {message}")
    print(f"::warning::{message}")
    _append_step_summary(
        f"### ⏸️ {message}\n\n"
        "- 结论：**积压**（非故障）——本轮发现的候选均已有待审 PR，请人工审阅并合并后即可恢复产出。\n"
        "- 定时 Harvest 不会因此次积压变红（exit 0）。\n"
    )


def _report_failure(reason: str) -> None:
    """[R4 修复] 上报**真故障**（创建 PR 过程出现 error / 候选池为空）：``::error::`` + 摘要。

    措辞明确点名「故障」，调用方据此 ``exit 1``（与「积压」严格区分，人工一眼可辨）。
    """
    message = f"本日零进展（故障）：{reason}"
    print(f"\n❌ {message}")
    print(f"::error::{message}")
    _append_step_summary(
        f"### ❌ {message}\n\n"
        "- 结论：**故障**（非积压）——创建候选 PR 的流程出现错误，需人工排查流水线。\n"
    )


def run_create_pr(candidates: list) -> int:
    """``--create-pr`` 批次执行路径：逐个尝试候选，成功创建一个 Draft PR 即停止。

    [D 修复]
      - 「创建成功」（``PR_RESULT_CREATED``）与「因已有待审 PR 跳过」（``PR_RESULT_SKIPPED_DUPLICATE``）
        是**可区分**的两种结果；遇到跳过时**继续尝试下一个候选**，避免每日取同一榜首候选而永久跳过。

    [R3 修复] 开始处**一次** ``gh pr list`` 取回所有 open 候选分支并预先排除被占用的候选，
    再按顺序取首个未被占用者创建；取回失败则退回逐个候选 ``--head`` 检查（不崩）。

    [R4 修复] 收尾分两类：
      - **积压**（发现到的候选**全部**已有待审 PR）⇒ ``exit 0`` + ``::warning::`` + 摘要；
      - **真故障**（创建过程出现 error）或**候选池为空** ⇒ ``exit 1`` + ``::error::``。

    [红卡修复] ``PR_RESULT_SKIPPED_REMOTE_EXISTS``（远端分支已残留，可能含人工提交）与
    ``PR_RESULT_SKIPPED_DUPLICATE`` 同属「**等待人工**」而非故障：两者都只计入各自的跳过计数、
    **继续尝试下一个候选**，收尾走 ``_report_backlog``（exit 0 + ``::warning::``）。
    此前该返回态**无分支处理** ⇒ 落入 ``failed`` ⇒ ``::error::`` + exit 1，且措辞是误导性的
    「真故障（等待人工介入）」——只要存在「PR 已关闭但分支未删」（关闭 PR 不会删分支）或
    ``ls-remote`` 抖动，定时任务就会**每天红灯**（R4 消灭过的「每天变红」被重新造回）。

    返回进程退出码：0 = 成功创建 1 个候选 PR 或「积压（等待人审 / 等待解锁）」；1 = 真故障 / 空池。
    """
    global _OPEN_CANDIDATE_BRANCHES
    found = len(candidates)
    _OPEN_CANDIDATE_BRANCHES = fetch_open_candidate_branches()
    try:
        if _OPEN_CANDIDATE_BRANCHES is not None:
            remaining = [
                c for c in candidates if f"candidate/{c['slug']}" not in _OPEN_CANDIDATE_BRANCHES
            ]
            excluded = found - len(remaining)
            if excluded:
                print(
                    f"\n  ⏭️ [R3] 单次 gh 调用预排除 {excluded}/{found} 个候选：其候选分支已有待审 PR"
                )
            candidates = remaining

        total = len(candidates)
        if total == 0:
            # [R4] 全部候选均已被占用 ⇒ 积压（非故障）⇒ exit 0。
            _report_backlog(f"{found} 个候选均已有待审 PR，等待人工审阅")
            return 0

        skipped = 0
        remote_skipped = 0
        remote_blocked: list = []
        failed = 0
        for index, candidate in enumerate(candidates, 1):
            result = create_draft_pr(candidate)
            if result == PR_RESULT_CREATED:
                print(f"\n✅ 本日已创建候选 PR（候选 {index}/{total}，成功创建一个即停止）")
                return 0
            if result == PR_RESULT_SKIPPED_DUPLICATE:
                skipped += 1
                continue
            # [红卡修复] 远端分支已残留 = 「等待人工解锁」（可能含人工提交，机器绝不覆盖），
            # 与「已有待审 PR」同属等待人工，**不得**计入 failed（否则每天红灯 + 措辞误导）。
            if result == PR_RESULT_SKIPPED_REMOTE_EXISTS:
                remote_skipped += 1
                remote_blocked.append(f"candidate/{candidate.get('slug', '')}")
                continue
            failed += 1
            print(f"  ⚠️ 候选 {candidate.get('slug', '')} 创建失败，继续尝试下一个候选")

        if failed == 0 and (skipped or remote_skipped):
            # [红卡修复] 未被创建且无任何失败 ⇒ 全部在等人工（待审 PR 或 待解锁远端分支）
            # ⇒ 积压（非故障）⇒ exit 0 + ::warning::，并给出**可执行**的解锁命令。
            unlock = "；".join(f"git push origin --delete {b}" for b in remote_blocked)
            detail = (
                f"{total} 个候选均未能创建 PR：{skipped} 个已有待审 PR（等待人工审阅合并）、"
                f"{remote_skipped} 个远端分支已残留（等待人工解锁，未推送、未覆盖任何提交）"
            )
            if unlock:
                detail = f"{detail}，解锁命令：{unlock}"
            _report_backlog(detail)
            return 0
        # [R4] 出现创建失败 ⇒ 真故障 ⇒ exit 1 + ::error::。
        _report_failure(
            f"{total} 个候选均未能创建 PR（已有待审 PR 跳过 {skipped}，"
            f"远端分支残留跳过 {remote_skipped}，失败 {failed}），等待人工介入"
        )
        return 1
    finally:
        _OPEN_CANDIDATE_BRANCHES = None


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
    # [D/R3 修复] --create-pr 需要候选批次：若只取 1 个候选，遇「已有待审 PR」即无候选可退；
    # 现改为取 PR_CANDIDATE_BATCH（=10）个候选，再由 run_create_pr 用一次性 gh 调用预排除已被
    # 占用的候选后取首个未被占用者。本上限**仅**限制发现开销，不再作为「零进展」的判据。
    if args.create_pr:
        harvest_limit = max(harvest_limit, PR_CANDIDATE_BATCH)

    candidates = harvest_candidates(limit=harvest_limit, source_id=args.source_id)
    if not candidates:
        if args.create_pr:
            # [R4 修复] 候选池为空属**真故障**（非积压）：显式 ::error:: + 摘要，exit 1。
            _report_failure("候选池为空（未发现任何新候选，或全部候选均已在台账 / 已发布）")
            sys.exit(1)
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
        # [D 修复] 逐个尝试候选直到成功创建一个（避免一次刷多个 PR）；全被跳过 ⇒ 显式报「本日零进展」。
        sys.exit(run_create_pr(candidates))


if __name__ == "__main__":
    main()
