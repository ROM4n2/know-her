#!/usr/bin/env python3
"""
test_source_discovery.py — 信源三模式增量发现与准入 fail-closed 门禁

守护 M2 供给管道的第一块基石：
    候选发现从「入口页单页 anchor」升级为 anchor / sitemap / feed 三模式，
    且未准入信源（`admission.status != "admitted"` 或 `license` 为空）必须被
    **硬跳过**（fail-closed），不得「先抓后判」。

断言覆盖（全部离线，零真实网络请求）：
    T1  _parse_sitemap 从 fixture 提取全部 <loc>
    T2  _parse_sitemap 的 link_pattern 过滤生效（不匹配路径被剔除）
    T3  空 sitemap（<urlset></urlset>）返回 [] 且不抛异常
    T4  单条目 sitemap 返回 1 条
    T5  sitemap index 嵌套递归受 max_pages 上限约束（注入式 fetcher，零网络）
    T6  _parse_feed 提取 RSS 2.0 的 item/link
    T7  _parse_feed 提取 Atom 的 entry/link[@href]，且不混入 feed 级 link
    T8  空 feed 返回 [] 且不抛异常
    T9  非法 XML ⇒ 抛 ET.ParseError（可被上层捕获降级，不得使整批失败）
    T10 is_source_admitted 真值表（含缺字段 fail-closed）
    T11 反向用例（MUST）：admitted+空 license / probing / 缺 admission ⇒
        discover_candidates 返回 [] 且**未发起任何抓取**
    T12 anchor 模式离线发现与 seen_urls 去重

范式：与 scripts/test_tools.py 一致 —— errors: list[str] 收集错误，结尾统一 sys.exit(1)。
约束：零第三方依赖（仅标准库）；路径操作统一 pathlib.Path；测试零真实网络请求。
"""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import curate_harvester as ch

FIXTURES_DIR = SCRIPT_DIR / "fixtures"
SITEMAP_FIXTURE = FIXTURES_DIR / "sitemap-sample.xml"
FEED_RSS_FIXTURE = FIXTURES_DIR / "feed-rss-sample.xml"
FEED_ATOM_FIXTURE = FIXTURES_DIR / "feed-atom-sample.xml"

REQUIRED_INTERFACES = ("is_source_admitted", "discover_candidates", "_parse_sitemap", "_parse_feed")

errors: list[str] = []


def expect(condition: bool, message: str) -> None:
    """记录一条断言失败（不抛异常，收集后统一 exit 1）。"""
    if not condition:
        errors.append(message)


def _read_fixture(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# --- T1 / T2 / T3 / T4：sitemap 解析与边界 -----------------------------------


def test_parse_sitemap_extracts_all_loc() -> None:
    if not hasattr(ch, "_parse_sitemap"):
        return
    text = _read_fixture(SITEMAP_FIXTURE)
    locs = ch._parse_sitemap(text, "", 3)
    expect(
        len(locs) == 5,
        f"[T1] 无过滤应提取全部 5 条 <loc>，实际 {len(locs)}：{locs}",
    )


def test_parse_sitemap_link_pattern_filter() -> None:
    if not hasattr(ch, "_parse_sitemap"):
        return
    text = _read_fixture(SITEMAP_FIXTURE)
    locs = ch._parse_sitemap(text, "/learn/", 3)
    expect(
        len(locs) == 3,
        f"[T2] link_pattern=/learn/ 应保留 3 条，实际 {len(locs)}：{locs}",
    )
    expect(
        all("/learn/" in u for u in locs),
        f"[T2] link_pattern 过滤后不应残留不匹配路径：{locs}",
    )


def test_parse_sitemap_empty_returns_empty() -> None:
    if not hasattr(ch, "_parse_sitemap"):
        return
    try:
        got = ch._parse_sitemap("<urlset></urlset>", "/learn/", 3)
    except Exception as exc:  # noqa: BLE001 — 断言容错
        errors.append(f"[T3] 空 sitemap 不应抛异常，实际 {type(exc).__name__}: {exc}")
        return
    expect(got == [], f"[T3] 空 sitemap 应返回 []，实际 {got}")


def test_parse_sitemap_single_returns_one() -> None:
    if not hasattr(ch, "_parse_sitemap"):
        return
    single = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<urlset><url><loc>https://x/learn/only</loc></url></urlset>"
    )
    got = ch._parse_sitemap(single, "/learn/", 3)
    expect(len(got) == 1, f"[T4] 单条目 sitemap 应返回 1 条，实际 {len(got)}：{got}")


# --- T5：sitemap index 递归受 max_pages 约束（注入 fetcher，零网络） ----------


def test_parse_sitemap_index_recursion_bounded() -> None:
    if not hasattr(ch, "_parse_sitemap"):
        return
    root = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<sitemapindex><sitemap><loc>https://x/sitemap-a.xml</loc></sitemap></sitemapindex>"
    )
    index_a = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<sitemapindex><sitemap><loc>https://x/sitemap-a1.xml</loc></sitemap></sitemapindex>"
    )
    urlset_a1 = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<urlset>"
        "<url><loc>https://x/learn/p1</loc></url>"
        "<url><loc>https://x/learn/p2</loc></url>"
        "<url><loc>https://x/other/p3</loc></url>"
        "</urlset>"
    )
    pages = {"https://x/sitemap-a.xml": index_a, "https://x/sitemap-a1.xml": urlset_a1}

    original = getattr(ch, "_SITEMAP_FETCH", None)
    calls: list[str] = []

    def fake_fetch(url, *args, **kwargs):
        calls.append(url)
        return pages.get(url, "")

    ch._SITEMAP_FETCH = fake_fetch
    try:
        deep = ch._parse_sitemap(root, "/learn/", 3)
        shallow = ch._parse_sitemap(root, "/learn/", 2)
    finally:
        ch._SITEMAP_FETCH = original

    expect(
        len(deep) == 2,
        f"[T5] max_pages=3 应递归至最深 urlset 得到 2 条 /learn/，实际 {len(deep)}：{deep}",
    )
    expect(
        shallow == [],
        f"[T5] max_pages=2 应在触及最深 urlset 前截断返回 []，实际 {shallow}",
    )
    expect(calls != [], "[T5] 递归路径应通过注入 fetcher 读取子 sitemap（不得真实联网）")


# --- T6 / T7 / T8：feed 解析与边界 -------------------------------------------


def test_parse_feed_rss() -> None:
    if not hasattr(ch, "_parse_feed"):
        return
    urls = ch._parse_feed(_read_fixture(FEED_RSS_FIXTURE))
    expect(len(urls) == 2, f"[T6] RSS 应提取 2 条 item/link，实际 {len(urls)}：{urls}")
    expect(
        "https://www.guokr.com/article/100001/" in urls,
        f"[T6] RSS 应含 article/100001，实际 {urls}",
    )


def test_parse_feed_atom() -> None:
    if not hasattr(ch, "_parse_feed"):
        return
    urls = ch._parse_feed(_read_fixture(FEED_ATOM_FIXTURE))
    expect(len(urls) == 2, f"[T7] Atom 应提取 2 条 entry/link[@href]，实际 {len(urls)}：{urls}")
    expect(
        "https://example.org/entry/1" in urls and "https://example.org/entry/2" in urls,
        f"[T7] Atom 应含 entry/1 与 entry/2，实际 {urls}",
    )
    expect(
        "https://example.org/" not in urls,
        f"[T7] feed 级 <link href> 不得混入条目列表，实际 {urls}",
    )


def test_parse_feed_empty_returns_empty() -> None:
    if not hasattr(ch, "_parse_feed"):
        return
    try:
        got = ch._parse_feed("<rss version=\"2.0\"><channel></channel></rss>")
    except Exception as exc:  # noqa: BLE001 — 断言容错
        errors.append(f"[T8] 空 feed 不应抛异常，实际 {type(exc).__name__}: {exc}")
        return
    expect(got == [], f"[T8] 空 feed 应返回 []，实际 {got}")


# --- T9：非法 XML 必须抛 ET.ParseError（可被上层捕获降级） --------------------


def test_invalid_xml_raises_parse_error() -> None:
    if hasattr(ch, "_parse_sitemap"):
        try:
            ch._parse_sitemap("this is < not xml", "/learn/", 3)
            errors.append("[T9] 非法 sitemap XML 应抛 ET.ParseError，但未抛任何异常")
        except ET.ParseError:
            pass
        except Exception as exc:  # noqa: BLE001
            errors.append(
                f"[T9] 非法 sitemap XML 应抛 ET.ParseError，实际 {type(exc).__name__}: {exc}"
            )
    if hasattr(ch, "_parse_feed"):
        try:
            ch._parse_feed("this is < not xml")
            errors.append("[T9] 非法 feed XML 应抛 ET.ParseError，但未抛任何异常")
        except ET.ParseError:
            pass
        except Exception as exc:  # noqa: BLE001
            errors.append(
                f"[T9] 非法 feed XML 应抛 ET.ParseError，实际 {type(exc).__name__}: {exc}"
            )


# --- T10：准入真值表 ----------------------------------------------------------


def test_is_source_admitted_truth_table() -> None:
    if not hasattr(ch, "is_source_admitted"):
        return
    cases = [
        ({"admission": {"status": "admitted", "license": "link-only"}}, True, "admitted+非空 license"),
        ({"admission": {"status": "probing", "license": ""}}, False, "probing"),
        ({"admission": {"status": "admitted", "license": ""}}, False, "admitted+空 license"),
        ({"admission": {"status": "admitted", "license": "   "}}, False, "admitted+纯空白 license"),
        ({"admission": {"status": "rejected", "license": "cc-by"}}, False, "rejected"),
        ({}, False, "缺 admission 字段"),
        ({"admission": None}, False, "admission 为 None"),
        ({"id": "x", "name": "无准入字段信源"}, False, "仅 id/name"),
    ]
    for src, want, label in cases:
        got = ch.is_source_admitted(src)
        expect(got is want, f"[T10] is_source_admitted({label}) 应为 {want}，实际 {got}")


# --- T11：反向用例（MUST）——fail-closed 且零抓取 -----------------------------


def test_discover_candidates_fail_closed_no_fetch() -> None:
    if not hasattr(ch, "discover_candidates"):
        return
    admitted_but_no_license = {
        "id": "bad-admitted",
        "name": "坏信源A（admitted 但 license 空）",
        "entry_url": "https://127.0.0.1:1/never",
        "base_url": "https://127.0.0.1:1",
        "link_pattern": "/x/([a-z]+)",
        "discovery": {
            "mode": "anchor",
            "url": "https://127.0.0.1:1/never",
            "link_pattern": "/x/([a-z]+)",
        },
        "admission": {"status": "admitted", "license": ""},
    }
    probing_source = {
        "id": "probing-source",
        "name": "探测信源B（probing）",
        "entry_url": "https://127.0.0.1:1/never",
        "base_url": "https://127.0.0.1:1",
        "link_pattern": "/y/([a-z]+)",
        "discovery": {
            "mode": "sitemap",
            "url": "https://127.0.0.1:1/sitemap.xml",
            "link_pattern": "/learn/",
            "max_pages": 3,
        },
        "admission": {
            "status": "probing",
            "license": "",
            "license_url": "",
            "verified_at": "",
            "verified_by_run": "",
        },
    }

    fetch_calls: list = []
    original_fetch = ch.fetch_url

    def recording_fetch(*args, **kwargs):
        fetch_calls.append(args)
        return 0, ""

    ch.fetch_url = recording_fetch
    try:
        got_admitted_no_license = ch.discover_candidates(admitted_but_no_license, set())
        got_probing = ch.discover_candidates(probing_source, set())
        got_missing = ch.discover_candidates({}, set())
    finally:
        ch.fetch_url = original_fetch

    expect(
        got_admitted_no_license == [],
        f"[T11] admitted 但 license 为空必须返回 []（fail-closed），实际 {got_admitted_no_license}",
    )
    expect(
        got_probing == [],
        f"[T11] probing 信源必须返回 []，实际 {got_probing}",
    )
    expect(
        got_missing == [],
        f"[T11] 缺 admission 字段必须返回 []，实际 {got_missing}",
    )
    expect(
        fetch_calls == [],
        f"[T11] 未准入信源禁止发起任何抓取（fail-closed 禁止先抓后判），实际抓取 {fetch_calls}",
    )


# --- T12：anchor 模式离线发现与 seen_urls 去重 --------------------------------


def test_anchor_mode_discovery_offline() -> None:
    if not hasattr(ch, "discover_candidates"):
        return
    html = (
        "<html><body>"
        '<a href="/learn/foo">避孕方法</a>'
        '<a href="/learn/bar">月经周期</a>'
        '<a href="/about">关于我们</a>'
        "</body></html>"
    )
    src = {
        "id": "anchor-test",
        "name": "本地 anchor 信源",
        "entry_url": "https://example.org/entry",
        "base_url": "https://example.org",
        "link_pattern": "/learn/([a-zA-Z]+)",
        "keywords": ["避孕", "月经"],
        "discovery": {
            "mode": "anchor",
            "url": "https://example.org/entry",
            "link_pattern": "/learn/([a-zA-Z]+)",
            "max_pages": 3,
        },
        "admission": {"status": "admitted", "license": "link-only"},
    }
    original_fetch = ch.fetch_url
    ch.fetch_url = lambda *args, **kwargs: (200, html)
    try:
        got = ch.discover_candidates(src, set())
        got_dedup = ch.discover_candidates(src, {"https://example.org/learn/foo"})
    finally:
        ch.fetch_url = original_fetch

    urls = [u for u, _ in got]
    expect("https://example.org/learn/foo" in urls, f"[T12] anchor 应发现 /learn/foo，实际 {got}")
    expect("https://example.org/learn/bar" in urls, f"[T12] anchor 应发现 /learn/bar，实际 {got}")
    expect(all("/about" not in u for u in urls), f"[T12] 不匹配 link_pattern 的链接应被剔除：{got}")
    expect(
        [u for u, _ in got_dedup] == ["https://example.org/learn/bar"],
        f"[T12] seen_urls 应剔除已见链接，实际 {got_dedup}",
    )


def main() -> int:
    if not (SITEMAP_FIXTURE.exists() and FEED_RSS_FIXTURE.exists() and FEED_ATOM_FIXTURE.exists()):
        errors.append(f"❌ 缺少 fixture：请确认 {FIXTURES_DIR} 下三个样本文件存在")

    for name in REQUIRED_INTERFACES:
        if not hasattr(ch, name):
            errors.append(f"❌ curate_harvester 缺少必需接口: {name}()")

    test_parse_sitemap_extracts_all_loc()
    test_parse_sitemap_link_pattern_filter()
    test_parse_sitemap_empty_returns_empty()
    test_parse_sitemap_single_returns_one()
    test_parse_sitemap_index_recursion_bounded()
    test_parse_feed_rss()
    test_parse_feed_atom()
    test_parse_feed_empty_returns_empty()
    test_invalid_xml_raises_parse_error()
    test_is_source_admitted_truth_table()
    test_discover_candidates_fail_closed_no_fetch()
    test_anchor_mode_discovery_offline()

    if errors:
        print("❌ [gate] 信源三模式发现与准入 fail-closed 门禁未通过：")
        for e in errors:
            print("   " + e)
        print(f"   共 {len(errors)} 条失败")
        return 1

    print("✅ [gate] 信源三模式发现与准入 fail-closed 门禁全部通过（12 组断言）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
