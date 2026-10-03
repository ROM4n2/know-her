#!/usr/bin/env python3
"""
test_daily_loop.py — 每日循环不变量门禁 (Daily Loop Invariant Gate)

守护「每天首页内容不重复」这一可判定的数学不变量：
    真实独立维度 = (文章池 A, 词条池 G) -> 最小公倍数 lcm -> 不重复天数 >= MIN_UNIQUE_CYCLE_DAYS

速测题与今日文章 1:1 绑定（G1 门禁强制），不是独立轮换维度，故不参与周期计算
（修正记录见 Spec §3.1.3）。当日指纹 = ((day-1) mod A, (day-1) mod G)，
其重复周期 = lcm(A, G)；当前 lcm(26, 28) = 364 天（约一年）。

本文件当前实现 G1 / G2 / G3 / G4 / G5 / G6 / G7 / G8 / G9 断言：
    G3（池规模 -> lcm(文章池, 词条池) -> >= 90 天不重复 + 两池不退化）
    G2（三池非空 + lcm(文章池, 词条池) > 文章池，证明词条池真参与周期，含反向用例）
    G1（文章 slug 集合 <-> DAILY_QUIZZES 键集合 双向 1:1，含反向夹具用例）
    G4（信源清单 schema 合法性 + --pool 候选池零副作用：discovery.mode / admission.status
        枚举合法、admitted ⇒ license 非空（fail-closed，含反向用例）、base_url/discovery.url/
        entry_url 均 http(s):// 前缀；rank_candidates 缺口升序排序；--pool 运行前后台账
        sha256 完全一致（以已是 v2 的真实台账驱动，规避 v1 迁移写回误判）；空池必须显式报错）
    G5（候选池台账 v2：v1->v2 迁移结构 / 幂等等式 / 重复 URL 去重 + 丢弃条数打印 /
        真实台账字段完备 / v2 台账下 harvest_candidates 不抛 TypeError（C1 回归））
    G6（今日上新窗口：rotation.pickFreshArticle 源码契约 + 定日边界用例 +
        断言「今日上新」仅作附加展示、不污染轮换索引）
    G8（node 原生载入 rotation.ts 的真实行为断言：指纹/索引/lcm 防空壳假绿，含
        G8a 双时区（TZ=UTC / Asia/Shanghai）一致性 + G8b pickFreshArticle 真行为）
    G7（速测题占位注入幂等：在 tempfile 副本上两次注入须 True/False 且 sha256 不变、
        注入文本含 articleId 锚点且花括号配平；含反向用例证明「非幂等坏实现」可被判红；
        以及 --admit-source 只读性：sources.json sha256 前后不变（No-Auto-Approve））
    G9（草稿模板真实 MDX 编译：compose_mdx_content 输出经 node + 本项目 MDX 引擎真实编译须通过、
        且不含 `<!--`、无抓取文本 raw_desc 泄漏；含反向用例证明 `<!--` 与 JSX 注释内 `*/` 抓取文本
        均可判红；候选分支不带台账（git add 仅暂存 .mdx）；跳过/零进展语义可区分且 ::warning:: 可见）
    G9[P0 止血]（**行为级**断言，拒绝文本扫描：以打桩 subprocess.run 记录的真实实参为物证）
        P0-1 远端分支永不强制覆盖：实际 git push 实参零 --force*/-f（含反空转守卫）+ 推送前
        必须真实调用 git ls-remote --heads origin <branch>；远端已存在 ⇒ 不推送 + 给出解锁指引；
        P0-2 模板不得机器自证（无 last_verified_at / reviewed_by / evidence_tier）；
        P0-3 PR 路径必须注入速测题占位并把 dailyQuiz.ts 纳入 git add；
        E1 判重前置到写盘之前（同一 URL 二次执行只产出 1 个 .mdx / 1 条占位）
    G9[红卡]（远端残留 = **等待人工**，非故障）``PR_RESULT_SKIPPED_REMOTE_EXISTS`` 与
        ``PR_RESULT_SKIPPED_DUPLICATE`` 同列：exit 0 + ``::warning::`` + 解锁命令、零 ``::error::``
    G9[黄卡清理]①占位标记**单一真值源** curate.PLACEHOLDER_MARKERS，且必须覆盖模板 summary 的
        占位文本；②还原 dailyQuiz.ts 失败**必须告警**（禁 ``except OSError: pass``）；
        ③``ls-remote`` 重试 1 次后再 fail-closed；④生产模块零 ``os.system(`` / ``shell=True`` 后门；
        ⑤PR 正文含 dailyQuiz.ts 冲突化解指引（保留双方条目）

范式：与 scripts/test_tools.py 一致 —— errors: list[str] 收集错误，结尾统一 sys.exit(1)。
约束：零第三方依赖（仅标准库）；路径操作统一 pathlib.Path；
      站点内容（.mdx/.astro）零 Emoji；脚本输出沿用仓库既有 ❌/✅/[PASS]/[FAIL] 门禁范式。
"""

import argparse
import contextlib
import datetime
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import curate_harvester as ch
# [黄卡-1] 机器占位标记的**单一真值源**：门禁端（curate.py）定义，测试端只引用、不得另立副本。
import curate

ROOT_DIR = SCRIPT_DIR.parent

LEDGER_FILE = SCRIPT_DIR / ".curate-ledger.json"
SOURCES_FILE = SCRIPT_DIR / "sources.json"
ARTICLES_DIR = ROOT_DIR / "src" / "content" / "articles"
GLOSSARY_DIR = ROOT_DIR / "src" / "content" / "glossary"
QUIZ_FILE = ROOT_DIR / "src" / "data" / "dailyQuiz.ts"
ROTATION_FILE = ROOT_DIR / "src" / "data" / "rotation.ts"
INDEX_FILE = ROOT_DIR / "src" / "pages" / "index.astro"
DAILY_CARD_FILE = ROOT_DIR / "src" / "components" / "DailyCard.astro"
CONTENT_CONFIG_FILE = ROOT_DIR / "src" / "content.config.ts"
ARTICLE_PAGE_FILE = ROOT_DIR / "src" / "pages" / "articles" / "[id].astro"

# 首页当日组合周期下限（一季）。与 src/data/rotation.ts 的 MIN_UNIQUE_CYCLE_DAYS 对齐。
MIN_UNIQUE_CYCLE_DAYS = 90


def _read_text(path: Path) -> str:
    """以 UTF-8 读取文本文件。"""
    return path.read_text(encoding="utf-8")


# 正则字面量起始判定：'/' 之前最近的非空白有效字符属于这些集合时，'/' 更可能是正则而非除法。
_REGEX_PREFIX_CHARS = set("(,=:[!&|?{};+-*%<>~^")
# 关键字之后的 '/' 亦可能是正则（如 return /re/），一并纳入判定。
_REGEX_PREFIX_WORDS = (
    "return", "typeof", "case", "in", "of", "delete",
    "void", "instanceof", "new", "do", "else", "yield", "await",
)


def _skip_string_literal(source: str, start: int) -> int:
    """从 source[start]（引号字符）起跳过整个字符串字面量，返回闭合引号后的下标。

    支持单引号 / 双引号 / 反引号（模板串）；``\\`` 转义后的字符不参与状态判定。
    未闭合时返回源码长度（视为直到文件末尾）。
    """
    quote = source[start]
    index = start + 1
    length = len(source)
    while index < length:
        char = source[index]
        if char == "\\":
            index += 2
            continue
        if char == quote:
            return index + 1
        index += 1
    return length


def _skip_regex_literal(source: str, start: int) -> int:
    """从 source[start]（'/'）起跳过正则字面量，返回闭合 '/' 后的下标。

    字符类 ``[...]`` 内的 '/' 不作闭合判定；``\\`` 转义（如 ``\\/``）跳过两个字符。
    遇到换行说明并非正则字面量，退回 ``start + 1`` 按普通字符处理。
    """
    index = start + 1
    length = len(source)
    in_class = False
    while index < length:
        char = source[index]
        if char == "\\":
            index += 2
            continue
        if char == "[":
            in_class = True
        elif char == "]":
            in_class = False
        elif char == "/" and not in_class:
            return index + 1
        elif char == "\n":
            return start + 1
        index += 1
    return length


def _regex_allowed(prev_char: str, prev_word: str) -> bool:
    """判定当前 '/' 是否可能是正则字面量起始（而非除法运算符）。"""
    if prev_char == "" or prev_char in _REGEX_PREFIX_CHARS:
        return True
    return prev_word in _REGEX_PREFIX_WORDS


def _strip_ts_comments(source: str) -> str:
    """剥离 TypeScript / .astro 注释（块注释 + 行注释 + HTML 注释）。

    本函数同时被用于扫描 .astro 文件，故必须一并剥离 HTML 注释
    （``<!-- getTodayIndex(articles.length) -->`` 之类会造成假绿）；
    TS 块注释/行注释的剥离则避免把注释里的键误计入池规模。

    [G8c 加固] 逐字符状态机剥离：先识别字符串（单/双/反引号）与正则字面量并**原样保留**，
    再识别注释并剔除。否则 ``href="https://…"`` 或正则 ``/https?:\\/\\//`` 里的 ``//``
    会被误判为行注释而截断整行后续代码，造成假红，或**掩盖同一行内的真实违规**；
    字符串内容必须保留，因为 G1 键扫描与 G6 契约扫描依赖字面量内的文本。
    """
    result: list = []
    index = 0
    length = len(source)
    prev_char = ""
    prev_word = ""
    word = ""
    while index < length:
        # HTML 注释
        if source.startswith("<!--", index):
            end = source.find("-->", index + 4)
            index = length if end == -1 else end + 3
            continue
        # 块注释
        if source.startswith("/*", index):
            end = source.find("*/", index + 2)
            index = length if end == -1 else end + 2
            continue
        # 行注释
        if source.startswith("//", index):
            end = source.find("\n", index + 2)
            index = length if end == -1 else end
            continue

        char = source[index]
        # 字符串字面量：原样保留
        if char in ("'", '"', "`"):
            end = _skip_string_literal(source, index)
            result.append(source[index:end])
            prev_char, prev_word, word = char, "", ""
            index = end
            continue
        # 正则字面量：原样保留（仅当上下文允许）
        if char == "/" and _regex_allowed(prev_char, prev_word):
            end = _skip_regex_literal(source, index)
            result.append(source[index:end])
            prev_char, prev_word, word = "/", "", ""
            index = end
            continue

        result.append(char)
        if char.isalnum() or char == "_":
            word += char
        else:
            if word:
                prev_word = word
            word = ""
        if not char.isspace():
            prev_char = char
        index += 1
    return "".join(result)


def _extract_function_body(source: str, func_name: str) -> str:
    """从 TS 源码中抽取指定函数（function <name>(...)）的函数体文本。

    以签名后首个 '{' 为起点做花括号配平，返回其内层文本（不含最外层花括号）。
    找不到函数签名或花括号不配平时返回空字符串（调用方据此判定「函数缺失」）。
    """
    match = re.search(r"function\s+" + re.escape(func_name) + r"\s*\(", source)
    if not match:
        return ""
    start_brace = source.find("{", match.end())
    if start_brace == -1:
        return ""
    depth = 0
    for index in range(start_brace, len(source)):
        char = source[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start_brace + 1 : index]
    return ""


def content_entry_ids(directory: Path, exclude_internal: bool = True) -> list:
    """返回内容集合 loader 口径下的 entry id 列表（相对路径、posix、去扩展名）。

    [YELLOW-4 口径对齐] 严格对齐 astro ``glob({ pattern: '**/*.{md,mdx}' })``：
      - 递归子目录（rglob，等价 '**/*'）；
      - 仅 .md / .mdx 两种扩展名；
      - exclude_internal=True 时排除 basename 以 '_' 开头的内部文件
        （对齐 ``articles/[id].astro`` 的 ``!entry.id.startsWith('_')`` 页面级过滤）。
    调用方据此保证「门禁统计的池规模 == 站点实际可渲染的池规模」。
    """
    if not directory.is_dir():
        return []
    entries: list = []
    for path in sorted(directory.rglob("*")):
        if not path.is_file() or path.suffix not in (".md", ".mdx"):
            continue
        if exclude_internal and path.name.startswith("_"):
            continue
        entries.append(path.relative_to(directory).with_suffix("").as_posix())
    return entries


def count_article_pool() -> int:
    """文章池规模：对齐内容集合 loader 口径（递归 .md/.mdx，排除 '_' 前缀内部文件）。"""
    return len(content_entry_ids(ARTICLES_DIR))


def count_quiz_pool() -> int:
    """速测池规模：dailyQuiz.ts 中形如 '<slug>': { 的键数量（注释内不算）。"""
    if not QUIZ_FILE.is_file():
        return 0
    source = _strip_ts_comments(_read_text(QUIZ_FILE))
    marker = source.find("DAILY_QUIZZES")
    if marker == -1:
        return 0
    # 仅统计对象顶层 slug 键：行首引号 + 纯小写 slug + 紧跟 ': {'。
    region = source[marker:]
    return len(re.findall(r"^\s*'[a-z0-9][a-z0-9-]*'\s*:\s*\{", region, flags=re.MULTILINE))


def count_glossary_pool() -> int:
    """词条池规模：与文章池口径对齐（递归 .md/.mdx，排除 '_' 前缀内部文件）。

    旧实现 ``GLOSSARY_DIR.glob('*.md')`` 仅顶层、不含 .mdx、不排除 '_'，
    与内容 loader 的 ``**/*.{md,mdx}`` 递归口径可能静默脱钩（YELLOW-4）。
    """
    return len(content_entry_ids(GLOSSARY_DIR))


def article_slugs(directory: Path = ARTICLES_DIR) -> set:
    """文章 slug 集合：内容集合 entry id（递归 .md/.mdx，排除 '_' 前缀内部文件）。

    与 count_article_pool 共用 content_entry_ids，保证 G1 的文章集合与池规模计数
    口径完全一致（顶层文件 id 即文件名去扩展名）。
    """
    return set(content_entry_ids(directory))


def quiz_keys(quiz_file: Path = QUIZ_FILE) -> set:
    """速测题键集合：DAILY_QUIZZES 顶层形如 '<slug>': { 的 slug（注释内不算）。"""
    if not quiz_file.is_file():
        return set()
    source = _strip_ts_comments(_read_text(quiz_file))
    marker = source.find("DAILY_QUIZZES")
    if marker == -1:
        return set()
    region = source[marker:]
    return set(
        re.findall(r"^\s*'([a-z0-9][a-z0-9-]*)'\s*:\s*\{", region, flags=re.MULTILINE)
    )


def _gcd(a: int, b: int) -> int:
    """欧几里得算法求最大公约数。"""
    x, y = abs(a), abs(b)
    while y:
        x, y = y, x % y
    return x


def lcm(values: list) -> int:
    """一组正整数的最小公倍数；空数组或含 0/负数时返回 0（与 rotation.ts 口径一致）。"""
    if not values:
        return 0
    result = 1
    for value in values:
        if value <= 0:
            return 0
        result = result // _gcd(result, value) * value
    return result


def check_cycle_threshold(pool_sizes: list, threshold: int) -> list:
    """纯函数：判定一组轮换池规模是否满足「当日组合唯一性周期」门禁。

    输入池规模列表与阈值，返回错误消息列表（空列表 = 通过）。调用者只看返回值，
    因此「坏数据 ⇒ 门禁失败」被直接证明，而非间接推理。
    - 空池守卫：池规模列表为空或任一池 < 1 时记错误并短路。
    - 周期下限：lcm(pool_sizes) < threshold 记为「周期坍缩」错误。
    - 不退化断言：任意两池互相整除（a % b == 0 或 b % a == 0）记为「同相位坍缩」错误，
      防止周期坍缩为 max(a, b)。
    """
    errors: list = []
    if not pool_sizes or any(size < 1 for size in pool_sizes):
        errors.append(f"轮换池存在空池，无法计算当日组合周期：pool_sizes={pool_sizes}")
        return errors

    cycle_days = lcm(pool_sizes)
    if cycle_days < threshold:
        errors.append(
            f"当日组合周期仅 {cycle_days} 天 < 门禁阈值 {threshold} 天（周期坍缩）；"
            f"请扩充内容池（当前池规模 {pool_sizes}）"
        )

    for i in range(len(pool_sizes)):
        for j in range(i + 1, len(pool_sizes)):
            a, b = pool_sizes[i], pool_sizes[j]
            if a % b == 0 or b % a == 0:
                errors.append(
                    f"轮换池同相位坍缩：池规模 {a} 与 {b} 互相整除，"
                    f"当日组合周期坍缩为 max({a}, {b})={max(a, b)}，请确保两池互不整除"
                )
    return errors


def check_glossary_participation(article_pool: int, glossary_pool: int) -> list:
    """纯函数：判定词条池是否真的参与首页当日组合周期计算。

    G2 核心防线：断言 lcm(文章池, 词条池) > 文章池。若词条池与文章池同相位
    （互相整除），lcm 会坍缩回文章池自身，即「加了组件却没接进指纹」的假接入。
    返回错误消息列表（空列表 = 通过）。
    """
    errors: list = []
    if article_pool < 1 or glossary_pool < 1:
        errors.append(
            f"轮换池存在空池，无法证明词条池参与周期："
            f"article_pool={article_pool}, glossary_pool={glossary_pool}"
        )
        return errors

    cycle_days = lcm([article_pool, glossary_pool])
    if cycle_days <= article_pool:
        errors.append(
            f"词条池假接入：lcm({article_pool}, {glossary_pool})={cycle_days} <= 文章池 {article_pool}，"
            f"说明词条池与文章池同相位/被整除，未真正参与当日组合周期计算"
        )
    return errors


def validate_g3_pool_cycle(errors: list) -> None:
    """G3 主断言：真实周期只由 (文章池, 词条池) 决定。

    速测题与今日文章 1:1 绑定（G1 强制），不是独立轮换维度，故不参与周期计算。
    门禁调用纯函数 check_cycle_threshold 判定阈值 + 不退化；周期 < 365 时打印软告警。
    """
    articles = count_article_pool()
    glossary = count_glossary_pool()
    sizes = [articles, glossary]
    cycle_days = lcm(sizes) if min(sizes) >= 1 else 0

    print(f"[G3] 池规模 articles={articles} glossary={glossary}")
    print(
        f"[G3] 首页当日组合周期 = lcm({articles}, {glossary}) = {cycle_days} 天"
        f"（阈值 {MIN_UNIQUE_CYCLE_DAYS}，达标={cycle_days >= MIN_UNIQUE_CYCLE_DAYS}）"
    )
    if 0 < cycle_days < 365:
        print(
            f"[G3] 软告警：首页当日组合周期 {cycle_days} 天 < 365 天（约一年），"
            f"建议扩充内容池以延长新鲜度窗口（不阻断门禁）"
        )

    errors.extend(check_cycle_threshold(sizes, MIN_UNIQUE_CYCLE_DAYS))


def validate_g2_pool_nonempty(errors: list) -> None:
    """G2 主断言：三池（文章 / 速测 / 词条）规模均 >= 1，且词条池真的参与周期计算。

    速测池计数显式复用既有 count_quiz_pool()（不得留无调用方死代码）；
    词条池断言 lcm(文章池, 词条池) > 文章池，证明词条池独立相位而非被整除的假接入。
    """
    articles = count_article_pool()
    quiz = count_quiz_pool()
    glossary = count_glossary_pool()

    print(f"[G2] 三池规模 articles={articles} quiz={quiz} glossary={glossary}")

    # 空池守卫前置：任一池为空即短路返回，避免后续 lcm 把「空池」误当作可计算组合。
    empty_pools = [
        name
        for name, size in (("articles", articles), ("quiz", quiz), ("glossary", glossary))
        if size < 1
    ]
    if empty_pools:
        errors.append(
            f"轮换池存在空池（{', '.join(empty_pools)}）："
            f"articles={articles}, quiz={quiz}, glossary={glossary}，请补齐对应内容源后再轮换"
        )
        return

    cycle_days = lcm([articles, glossary])
    print(
        f"[G2] lcm(文章池, 词条池) = lcm({articles}, {glossary}) = {cycle_days} 天，"
        f"> 文章池 {articles} 天 = {cycle_days > articles}（词条池真参与周期，非假接入）"
    )
    errors.extend(check_glossary_participation(articles, glossary))


def validate_g2_reverse_test(errors: list) -> None:
    """G2 反向用例 [Instinct: Reverse-Test]：词条池与文章池同相位时 G2 必须失败。

    ① 硬编码 (26, 26)（lcm 坍缩回文章池自身）驱动 check_glossary_participation，
       断言返回非空且点名「假接入」；② 互不整除的 (26, 28) 作正向对照断言通过。
    ③ [YELLOW-5 加固] 以**真实文章池规模**驱动同一纯函数（gpool == apool 必为同相位），
       断言防线对真实数据同样生效，而非仅靠一次性手工数值。
    """
    collapsed = check_glossary_participation(26, 26)
    if not collapsed:
        errors.append(
            "反向用例失效：check_glossary_participation(26, 26) 应返回非空错误列表"
            "（lcm(26,26)=26 <= 26，词条池未参与周期），实际为空"
        )
        return

    joined = "\n".join(collapsed)
    if "假接入" not in joined:
        errors.append(
            f"反向用例失效：check_glossary_participation(26, 26) 错误信息未点名「假接入」，不可执行：{joined}"
        )
        return

    healthy = check_glossary_participation(26, 28)
    if healthy:
        errors.append(
            f"正向对照失效：check_glossary_participation(26, 28) 应通过（空错误列表），实际 {healthy}"
        )
        return

    # ③ 真实池反向断言：同相位（词条池 == 文章池）必须被真实规模检出。
    real_articles = count_article_pool()
    real_collapsed = check_glossary_participation(real_articles, real_articles)
    if "假接入" not in "\n".join(real_collapsed):
        errors.append(
            f"真实池反向用例失效：check_glossary_participation({real_articles}, {real_articles}) "
            f"应报「假接入」非空错误（同相位坍缩），实际 {real_collapsed}"
        )
        return

    print(
        f"[G2] 反向用例通过：(26,26) 检出 {len(collapsed)} 条「假接入」错误；"
        f"真实池 ({real_articles},{real_articles}) 亦检出 {len(real_collapsed)} 条；"
        f"正向对照 (26,28) lcm=364 通过"
    )


def validate_self_checks(errors: list) -> None:
    """反向用例 + 空池/单元素边界自检（直接调用门禁纯函数，证明门禁本身有效）。

    [YELLOW-0 加固] 反向用例①不再只断言「非空」，而是钉死**条数与消息文本**：
    ``check_cycle_threshold([26, 26], 90)`` 必须恰好返回 2 条错误，且分别点名
    「周期坍缩」（lcm=26 < 90）与「同相位坍缩」（26 整除 26）。若删掉函数内的整除判定循环，
    条数降为 1 ⇒ 本断言立即失败（证明护栏真实可红）。
    另补「只触发相位分支」的判别用例 ``[100, 50]``（lcm=100 >= 90 过阈值，但 50 整除 100），
    必须恰好 1 条「同相位坍缩」且不误报「周期坍缩」。
    """
    # 反向用例①（周期坍缩 + 同相位坍缩双命中）：条数与文本双钉死。
    collapsed = check_cycle_threshold([26, 26], MIN_UNIQUE_CYCLE_DAYS)
    collapsed_joined = "\n".join(collapsed)
    if len(collapsed) != 2:
        errors.append(
            f"反向用例失效：check_cycle_threshold([26,26], 90) 应返回 2 条错误"
            f"（周期坍缩 + 同相位坍缩），实际 {len(collapsed)} 条：{collapsed}"
        )
    if "周期坍缩" not in collapsed_joined:
        errors.append(
            f"反向用例失效：check_cycle_threshold([26,26], 90) 错误未包含「周期坍缩」：{collapsed}"
        )
    if "同相位坍缩" not in collapsed_joined:
        errors.append(
            "反向用例失效：check_cycle_threshold([26,26], 90) 错误未包含「同相位坍缩」"
            f"（整除判定分支未覆盖，删掉该循环即可骗过门禁）：{collapsed}"
        )
    print(
        f"[G3] 反向用例①通过：[26,26] 恰好 {len(collapsed)} 条错误"
        f"（周期坍缩 + 同相位坍缩），文本双命中"
    )

    # 反向用例②（只触发相位分支）：[100,50] lcm=100 >= 90 过阈值，但 50 | 100 必须仅报 1 条相位错误。
    # 注意：相位错误文案内嵌「当日组合周期坍缩为…」，故不能用「周期坍缩」子串判别阈值分支，
    # 须以阈值分支独有前缀「当日组合周期仅」判别（否则会自我误伤）。
    phase_only = check_cycle_threshold([100, 50], MIN_UNIQUE_CYCLE_DAYS)
    phase_joined = "\n".join(phase_only)
    if len(phase_only) != 1 or "同相位坍缩" not in phase_joined:
        errors.append(
            f"反向用例失效：check_cycle_threshold([100,50], 90) 应恰好 1 条「同相位坍缩」"
            f"（lcm=100 过阈值），实际 {len(phase_only)} 条：{phase_only}"
        )
    if "当日组合周期仅" in phase_joined:
        errors.append(
            f"反向用例失效：check_cycle_threshold([100,50], 90) 不应报「周期坍缩」"
            f"（lcm=100 >= 90）：{phase_only}"
        )
    print("[G3] 反向用例②通过：[100,50] 恰好 1 条「同相位坍缩」且不误报周期坍缩")

    # 正向对照：互不整除的 (26, 28) ⇒ lcm=364 >= 90，必须通过（空错误列表）。
    healthy = check_cycle_threshold([26, 28], MIN_UNIQUE_CYCLE_DAYS)
    if healthy:
        errors.append(
            f"正向对照失效：check_cycle_threshold([26,28], 90) 应通过（空错误列表），"
            f"实际 {healthy}"
        )

    # 边界：空池 -> 0，单元素 -> 自身。
    if lcm([]) != 0:
        errors.append(f"边界自检失效：lcm([]) 应返回 0，实际 {lcm([])}")
    if lcm([1]) != 1:
        errors.append(f"边界自检失效：lcm([1]) 应返回 1，实际 {lcm([1])}")


def validate_rotation_contract(errors: list) -> None:
    """G3 支撑：rotation.ts 单一真值源接口 + 空池守卫契约（含 getTodayIndex(0) -> 0）。"""
    if not ROTATION_FILE.is_file():
        errors.append(f"轮换数学真值源缺失：{ROTATION_FILE} —— 请创建 src/data/rotation.ts")
        return

    source = _read_text(ROTATION_FILE)
    required_exports = [
        "export function getDayOfYear(",
        "export function getTodayIndex(",
        "export function getWeekIndex(",
        "export function lcm(",
        "export function computeFingerprint(",
        "export const MIN_UNIQUE_CYCLE_DAYS = 90",
    ]
    for token in required_exports:
        if token not in source:
            errors.append(f"rotation.ts 缺少必须导出的接口签名：{token}")

    # 空池守卫：getTodayIndex(0) 必须短路返回 0，禁止取模除零。
    if not re.search(r"totalCount\s*<=\s*0\s*\)\s*return\s+0", source):
        errors.append("rotation.ts：getTodayIndex 缺失 'totalCount <= 0 -> 0' 空池守卫子句")
    # computeFingerprint 空池必须不抛异常（显式空池守卫）。
    if not re.search(r"poolSizes\.length\s*===\s*0", source):
        errors.append("rotation.ts：computeFingerprint 缺失空池守卫（poolSizes.length === 0）")


def validate_daily_quiz_reexport(errors: list) -> None:
    """保证既有导入路径不破坏：dailyQuiz.ts 必须从 './rotation' 转出轮换数学。"""
    if not QUIZ_FILE.is_file():
        errors.append(f"速测数据文件缺失：{QUIZ_FILE}")
        return
    source = _read_text(QUIZ_FILE)
    if "from './rotation'" not in source and 'from "./rotation"' not in source:
        errors.append("dailyQuiz.ts 未从 './rotation' 转出轮换数学（单一真值源被破坏）")


def validate_quiz_coverage(
    errors: list,
    articles_dir: Path = ARTICLES_DIR,
    quiz_file: Path = QUIZ_FILE,
) -> list:
    """G1 主断言：文章 slug 集合 <-> DAILY_QUIZZES 键集合 双向 1:1。

    既查缺题（文章无对应速测题），也查孤儿题（速测题无对应文章）；
    任一方向有差集即记错误，错误信息可直接指导修复。
    返回本次新增追加到 errors 的条目（供反向夹具用例断言非空）。
    """
    before = len(errors)
    slugs = article_slugs(articles_dir)
    keys = quiz_keys(quiz_file)

    # 守卫子句：内容池均未就绪则短路，避免在空目录下产生误报噪声。
    if not slugs and not keys:
        return errors[before:]
    # 守卫子句：无文章却有题 -> 全部按孤儿题处理。
    if not slugs:
        for key in sorted(keys):
            errors.append(
                f"❌ 速测题 '{key}' 是孤儿题（无对应文章）→ 请在 src/content/articles/ "
                f"新建 '{key}.mdx' 或从 src/data/dailyQuiz.ts 删除该 key"
            )
        return errors[before:]
    # 守卫子句：有文章却无题 -> 全部按缺题处理，一次性点名所有 slug。
    if not keys:
        for slug in sorted(slugs):
            errors.append(
                f"❌ 文章 '{slug}' 缺少速测题 → 请在 src/data/dailyQuiz.ts 的 "
                f"DAILY_QUIZZES 增加 key '{slug}'"
            )
        return errors[before:]

    for slug in sorted(slugs - keys):
        errors.append(
            f"❌ 文章 '{slug}' 缺少速测题 → 请在 src/data/dailyQuiz.ts 的 "
            f"DAILY_QUIZZES 增加 key '{slug}'"
        )
    for key in sorted(keys - slugs):
        errors.append(
            f"❌ 速测题 '{key}' 是孤儿题（无对应文章）→ 请在 src/content/articles/ "
            f"新建 '{key}.mdx' 或从 src/data/dailyQuiz.ts 删除该 key"
        )

    print(
        f"[G1] 文章 slug 数 ={len(slugs)}，速测题键数 ={len(keys)}，"
        f"1:1 覆盖 ={len(slugs & keys)}（缺题 {len(slugs - keys)}，孤儿题 {len(keys - slugs)}）"
    )
    return errors[before:]


def validate_quiz_coverage_reverse_test(errors: list) -> None:
    """G1 反向用例 [Instinct: Reverse-Test]：夹具「1 篇文章 + 0 道题」下必须报错。

    若此用例通过（即 G1 在夹具下反而静默），说明门禁形同虚设，记错误。
    """
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        fixture_articles = tmp_dir / "articles"
        fixture_articles.mkdir()
        (fixture_articles / "fixture-article-without-quiz.mdx").write_text(
            "---\ntitle: 夹具\n---\n", encoding="utf-8"
        )
        fixture_quiz = tmp_dir / "dailyQuiz.ts"
        fixture_quiz.write_text(
            "export const DAILY_QUIZZES: Record<string, QuizItem> = {\n};\n",
            encoding="utf-8",
        )
        fixture_errors = validate_quiz_coverage(
            [], articles_dir=fixture_articles, quiz_file=fixture_quiz
        )

    if not fixture_errors:
        errors.append(
            "反向用例失效：夹具（1 篇文章 + 0 道题）下 validate_quiz_coverage "
            "应返回非空错误列表，实际为空"
        )
        return

    joined = "\n".join(fixture_errors)
    if "fixture-article-without-quiz" not in joined:
        errors.append(
            "反向用例失效：夹具错误信息未点名缺失 slug 'fixture-article-without-quiz'，不可执行"
        )
        return

    print(f"[G1] 反向用例通过：夹具（1 篇文章 + 0 道题）下检出 {len(fixture_errors)} 条错误并点名缺失 slug")


def validate_g6_fresh_window_contract(errors: list) -> None:
    """G6 主断言①：rotation.ts 中 pickFreshArticle 的源码契约。

    本项目无 JS 运行时，本组沿用 Task-1/2/3 的源码契约风格（token/正则扫描）；
    Task-5 会补 node --input-type=module 行为断言。此处断言 pickFreshArticle 存在、
    默认窗口 7 天、使用 beijingDayNumber 做 UTC+8 日归一化（禁止毫秒相减），
    且窗口判定同时含下界守卫（daysDiff < 0，排除未来日期）与上界开区间（daysDiff < windowDays）。

    注意（反向验证发现的假绿漏洞）：契约扫描必须先 _strip_ts_comments 剥离注释，
    否则 JSDoc 里出现同名 token（如「daysDiff < windowDays」）会误判通过——
    实测把命中条件放宽为 `<=` 后，若扫原文则正则仍被注释满足而不报错。
    """
    if not ROTATION_FILE.is_file():
        errors.append(f"[G6] 轮换数学真值源缺失：{ROTATION_FILE}")
        return

    source = _strip_ts_comments(_read_text(ROTATION_FILE))
    if "export function pickFreshArticle" not in source:
        errors.append("[G6] rotation.ts 缺少必须导出：export function pickFreshArticle")
    if not re.search(r"windowDays\s*=\s*7", source):
        errors.append("[G6] pickFreshArticle 缺少默认窗口参数 windowDays = 7")
    if "beijingDayNumber" not in source:
        errors.append(
            "[G6] pickFreshArticle 未使用 beijingDayNumber 做 UTC+8 日归一化（禁止毫秒相减）"
        )
    if not re.search(r"daysDiff\s*<\s*windowDays", source):
        errors.append("[G6] pickFreshArticle 缺少窗口上界开区间判定 daysDiff < windowDays")
    if not re.search(r"daysDiff\s*<\s*0", source):
        errors.append("[G6] pickFreshArticle 缺少下界守卫 daysDiff < 0（排除未来日期）")

    print(
        "[G6] rotation.pickFreshArticle 源码契约通过"
        "（存在性 / 默认窗口7 / UTC+8归一化 / 上下界判定）"
    )


def validate_g6_beijing_tz_independent(errors: list) -> None:
    """G6 主断言⑤：beijingDayNumber 必须与构建机时区无关（捕获本轮 RED）。

    RED 事实（编排者真机实测确认，非推测）：旧实现
        const utc = date.getTime() + date.getTimezoneOffset() * 60000;
        return Math.floor((utc + 8 * 3600000) / 86400000);
    中 getTimezoneOffset() 项在 floor 前不会抵消，导致北京日序号随构建机时区漂移
    （同一时刻 2026-10-03T20:00:00Z：TZ=UTC 机得 20730，系统 UTC+8 机得 20729，差 1 天），
    进而使「今日上新」7 天窗口整体漂移 8 小时、第 7/8 天边界错位，
    且骗过此前仅查函数存在性的契约正则。

    必要条件：beijingDayNumber 函数体内不得出现 getTimezoneOffset()——传入的 date 已是绝对
    时间戳，直接加 8 小时再取整即为北京日序号；引入本地偏移项会使结果随构建机时区漂移。
    这与 getDayOfYear 的 TZ 无关性同源。扫描前先 _strip_ts_comments 剥离注释，
    防止把 JSDoc 中出现的同名 token 误当作真实代码。
    """
    if not ROTATION_FILE.is_file():
        errors.append(f"[G6] 轮换数学真值源缺失：{ROTATION_FILE}")
        return

    source = _strip_ts_comments(_read_text(ROTATION_FILE))
    body = _extract_function_body(source, "beijingDayNumber")
    if not body:
        errors.append(
            "[G6] rotation.ts 缺少必须导出：export function beijingDayNumber"
        )
        return
    if "getTimezoneOffset" in body:
        errors.append(
            "[G6] beijingDayNumber 不得引入 getTimezoneOffset()"
            "（会导致窗口随构建机时区漂移）"
        )
        return

    print(
        "[G6] beijingDayNumber 构建机时区无关契约通过"
        "（函数体零 getTimezoneOffset 项）"
    )


def mirror_pick_fresh(pub_dates: list, today, window_days: int = 7):
    """语义镜像：与 rotation.pickFreshArticle 同构，仅用于执行「定日边界」用例。

    返回被选中项索引；无命中返回 None。TS 侧逻辑由
    validate_g6_fresh_window_contract 的正则契约钉死，本镜像仅补齐可执行的边界覆盖
    （无 JS 运行时下无法直接执行 TS，故镜像 + 契约双保险）。
    """
    if not pub_dates:
        return None

    today_no = today.toordinal()
    best_index = None
    best_no = None
    for index, pub in enumerate(pub_dates):
        pub_no = pub.toordinal()
        days_diff = today_no - pub_no
        if days_diff < 0:
            continue
        if days_diff < window_days and (best_no is None or pub_no > best_no):
            best_index = index
            best_no = pub_no
    return best_index


def validate_g6_window_boundaries(errors: list) -> None:
    """G6 主断言②：定日边界用例（含发布第 7 / 8 天边界）。"""
    today = datetime.date(2026, 9, 27)
    cases = [
        ("发布第 7 天(daysDiff=6)命中", [today - datetime.timedelta(days=6)], 0),
        ("发布第 8 天(daysDiff=7)不命中", [today - datetime.timedelta(days=7)], None),
        ("发布当天(daysDiff=0)命中", [today], 0),
        ("未来日期(daysDiff=-1)不命中", [today + datetime.timedelta(days=1)], None),
    ]
    for label, dates, expected in cases:
        actual = mirror_pick_fresh(dates, today)
        if actual != expected:
            errors.append(f"[G6] 边界用例失败：{label} 期望 {expected}，实际 {actual}")

    multi = [today - datetime.timedelta(days=2), today - datetime.timedelta(days=6), today]
    multi_actual = mirror_pick_fresh(multi, today)
    if multi_actual != 2:
        errors.append(
            f"[G6] 边界用例失败：多篇命中应返回 getDate 最新一篇（索引 2），实际 {multi_actual}"
        )

    if mirror_pick_fresh([], today) is not None:
        errors.append("[G6] 边界用例失败：空数组应返回 None")

    print(
        "[G6] 窗口边界用例（Python 镜像，行为断言由 Task-5 G8 补足）通过："
        "第7天命中 / 第8天不命中 / 发布当天命中 / 未来不命中 / 多篇取最新 / 空数组返回 None"
    )


def validate_g6_no_rotation_drift(errors: list) -> None:
    """G6 主断言③：freshArticle 仅作附加展示，绝不污染轮换索引。

    断言 index.astro 中「今日精选」仍由 getTodayIndex(articles.length) 决定，
    freshArticle 只作为额外 prop 传入 <DailyCard />，且从不用作 articles 的索引。
    """
    if not INDEX_FILE.is_file():
        errors.append(f"[G6] 首页文件缺失：{INDEX_FILE}")
        return

    source = _strip_ts_comments(_read_text(INDEX_FILE))
    if not re.search(r"getTodayIndex\(articles\.length\)", source):
        errors.append(
            "[G6] 轮换索引契约被破坏：index.astro 未使用 getTodayIndex(articles.length) 计算今日精选"
        )
    if "pickFreshArticle" not in source:
        errors.append("[G6] index.astro 未引入/调用 pickFreshArticle 计算今日上新")
    if not re.search(r"pickFreshArticle\(\s*articles", source):
        errors.append("[G6] index.astro 未以文章池计算 freshArticle：pickFreshArticle(articles, ...)")
    if not re.search(r"freshArticle=\{freshArticle", source):
        errors.append("[G6] index.astro 未把 freshArticle 作为附加 prop 传入 <DailyCard />")
    if re.search(r"articles\s*\[[^\]]*freshArticle", source):
        errors.append(
            "[G6] 轮换索引被污染：freshArticle 被用作 articles 的索引（应仅附加展示，不参与轮换）"
        )

    print(
        "[G6] 轮换索引零扰动源码契约通过：featuredArticle 仍由 getTodayIndex(articles.length) 决定，"
        "freshArticle 仅附加传入"
    )


def analyze_article_sort_primary(source: str) -> list:
    """纯函数：判定文章排序主键表达式的**语义方向**，返回错误消息列表（空 = 合法降序）。

    [G8/G6 加固] 仅查降序子串存在性会被「取反包裹」的假降序骗过：
        -(b - a) 与 (b - a) * -1  语义均为**升序**，却包含降序子串。
    同时须避免误红：-(a - b) 语义等价于降序，必须接受。

    语义降序（合法）：
        (D)  b.data.pubDate.getTime() - a.data.pubDate.getTime()
        (N)  -(a.data.pubDate.getTime() - b.data.pubDate.getTime())
    语义升序（非法）：
        (A)  a.data.pubDate.getTime() - b.data.pubDate.getTime()
        (Nd) -(b.data.pubDate.getTime() - a.data.pubDate.getTime())
        (Nm) (b.data.pubDate.getTime() - a.data.pubDate.getTime()) * -1
    """
    group_a = r"a\.data\.pubDate\.getTime\(\)"
    group_b = r"b\.data\.pubDate\.getTime\(\)"
    desc = group_b + r"\s*-\s*" + group_a
    asc = group_a + r"\s*-\s*" + group_b
    neg_desc = r"-\s*\(\s*" + desc + r"\s*\)"
    desc_times_neg = r"\(\s*" + desc + r"\s*\)\s*\*\s*-\s*1"
    neg_asc = r"-\s*\(\s*" + asc + r"\s*\)"

    has_desc = re.search(desc, source) is not None
    has_asc = re.search(asc, source) is not None
    has_neg_desc = re.search(neg_desc, source) is not None
    has_desc_times_neg = re.search(desc_times_neg, source) is not None
    has_neg_asc = re.search(neg_asc, source) is not None

    errors: list = []
    if has_neg_desc or has_desc_times_neg:
        errors.append(
            "[G6] index.astro 排序主键被取反包裹（-(b - a) 或 (b - a) * -1），语义实为升序；"
            "会使「今日精选」指向最旧文章"
        )
        return errors
    if has_asc and not has_neg_asc:
        errors.append(
            "[G6] index.astro 文章排序主键为升序（a - b），会使「今日精选」指向最旧文章"
        )
        return errors
    if not (has_desc or has_neg_asc):
        errors.append(
            "[G6] index.astro 文章排序主键缺失 pubDate 降序形态（b - a 或语义等价的 -(a - b)），"
            "排序方向不确定会使「今日精选」随实现漂移"
        )
    return errors


def validate_g6_sort_primary_forms(errors: list) -> None:
    """G6 排序断言「窄漏绿向量」自检：坏形态必须报错、等价降序形态必须放行。

    [G8/G6 加固] 直接以纯函数分析各形态（含取反包裹），证明拒绝面与接受面正确：
        拒绝：-(b - a)、(b - a) * -1、a - b、缺失降序
        接受：b - a、-(a - b)
    """
    prefix = "const cmp = (a, b) => "
    rejected = {
        "-(b - a)": prefix + "-(b.data.pubDate.getTime() - a.data.pubDate.getTime())",
        "(b - a) * -1": prefix + "(b.data.pubDate.getTime() - a.data.pubDate.getTime()) * -1",
        "a - b": prefix + "a.data.pubDate.getTime() - b.data.pubDate.getTime()",
        "缺失降序": prefix + "a.id.localeCompare(b.id)",
    }
    accepted = {
        "b - a": prefix + "b.data.pubDate.getTime() - a.data.pubDate.getTime()",
        "-(a - b)": prefix + "-(a.data.pubDate.getTime() - b.data.pubDate.getTime())",
    }
    for label, snippet in rejected.items():
        if not analyze_article_sort_primary(snippet):
            errors.append(f"[G6] 排序自检失效：坏形态「{label}」应报错，实际放行")
    for label, snippet in accepted.items():
        found = analyze_article_sort_primary(snippet)
        if found:
            errors.append(f"[G6] 排序自检误红：合法降序形态「{label}」应放行，实际 {found}")
    print("[G6] 排序主键方向自检通过（拒绝 -(b-a)/(b-a)*-1/a-b/缺失；接受 b-a 与 -(a-b)）")


def validate_g6_article_sort_descending(errors: list) -> None:
    """G6 主断言⑥：index.astro 文章排序主键必须为 pubDate 降序（防符号翻转）。

    RED 事实（编排者 git 复核定性，非推测）：上一轮修订把比较器主键从
        b.data.pubDate.getTime() - a.data.pubDate.getTime()   // 降序（正确，最新文在索引 0）
    翻转为
        a.data.pubDate.getTime() - b.data.pubDate.getTime()   // 升序（错误，最旧文在索引 0）
    致使 articles[0] 由「最新文」变为「最旧文」，featuredArticle（今日精选）语义被改变，
    且骗过 astro check / build（均不校验排序方向）。

    语义方向判定下沉到纯函数 analyze_article_sort_primary（拒绝取反包裹的假降序，
    接受语义等价的 -(a - b)）。扫描前先 _strip_ts_comments 剥离注释，防注释示例造成假绿/假红。
    """
    if not INDEX_FILE.is_file():
        errors.append(f"[G6] 首页文件缺失：{INDEX_FILE}")
        return

    found = analyze_article_sort_primary(_strip_ts_comments(_read_text(INDEX_FILE)))
    if found:
        errors.extend(found)
        return

    print("[G6] index.astro 文章排序主键降序契约通过（命中 b - a 降序且无取反/升序形态）")


def validate_g6_card_strip(errors: list) -> None:
    """G6 主断言④：DailyCard 今日上新条带契约（条件渲染 / 去重守卫 / 零 innerHTML）。"""
    if not DAILY_CARD_FILE.is_file():
        errors.append(f"[G6] 组件文件缺失：{DAILY_CARD_FILE}")
        return

    source = _strip_ts_comments(_read_text(DAILY_CARD_FILE))
    if not re.search(r"freshArticle\?:\s*CollectionEntry<'articles'>", source):
        errors.append("[G6] DailyCard.astro 缺少可选 Prop freshArticle?: CollectionEntry<'articles'>")
    if not re.search(r"freshArticle\s*&&\s*freshArticle\.id\s*!==\s*article\.id", source):
        errors.append(
            "[G6] DailyCard.astro 缺少去重守卫：freshArticle && freshArticle.id !== article.id"
        )
    if "今日上新" not in source:
        errors.append("[G6] DailyCard.astro 缺少「今日上新」条带文案")
    if not re.search(r"articles/\$\{freshArticle\.id\}/", source):
        errors.append("[G6] DailyCard.astro 缺少新文直达链接 ${base}articles/${freshArticle.id}/")
    if "innerHTML" in source:
        errors.append("[G6] DailyCard.astro 出现 innerHTML（站点硬约束禁止）")

    print("[G6] DailyCard 今日上新条带契约通过（可选 Prop / 去重守卫 / 直链 / 零 innerHTML）")


# ---------------------------------------------------------------------------
# G8：node 原生载入 rotation.ts 的真实行为断言（击穿「空壳假绿」）
# ---------------------------------------------------------------------------

# 探针脚本：以 argv 传入 rotation.ts 路径与 TZ。
# Windows 原生 node.exe 在 Git Bash 下收不到含斜杠的 `TZ=` 内联前缀（收到 undefined），
# 故必须走「argv 传参 + 脚本内 process.env.TZ 赋值」，并以 getTimezoneOffset() 自证时区已切换。
_ROTATION_PROBE = r"""
import { pathToFileURL } from 'node:url';

const rotationPath = process.argv[2];
const tz = process.argv[3];
if (tz) process.env.TZ = tz;

const mod = await import(pathToFileURL(rotationPath).href);

const dayIso = [
  '2026-10-03T16:00:00Z',
  '2026-10-03T15:59:59Z',
  '2026-12-31T23:59:59Z',
  '2026-01-01T00:00:00Z',
];

const today = new Date('2026-09-27T12:00:00+08:00');
const mk = (iso, id) => ({ id, d: new Date(iso) });
const getDate = (x) => x.d;
const pick = (items) => {
  const hit = mod.pickFreshArticle(items, getDate, today, 7);
  return hit ? hit.id : null;
};

const result = {
  tz: process.env.TZ ?? null,
  offset: new Date().getTimezoneOffset(),
  fingerprintJan: mod.computeFingerprint(new Date('2026-01-01T00:00:00+08:00'), [26, 28]),
  fingerprintMar: mod.computeFingerprint(new Date('2026-03-15T12:00:00+08:00'), [26, 28]),
  todayIndexZero: mod.getTodayIndex(0),
  lcm26_28: mod.lcm([26, 28]),
  lcmEmpty: mod.lcm([]),
  dayNumbers: Object.fromEntries(dayIso.map((s) => [s, mod.beijingDayNumber(new Date(s))])),
  fresh: {
    day7: pick([mk('2026-09-21T12:00:00+08:00', 'day7')]),
    day8: pick([mk('2026-09-20T12:00:00+08:00', 'day8')]),
    today: pick([mk('2026-09-27T12:00:00+08:00', 'today')]),
    future: pick([mk('2026-09-28T12:00:00+08:00', 'future')]),
    multi: pick([
      mk('2026-09-25T12:00:00+08:00', 'two'),
      mk('2026-09-21T12:00:00+08:00', 'six'),
      mk('2026-09-27T12:00:00+08:00', 'zero'),
    ]),
    empty: pick([]),
  },
};

process.stdout.write(JSON.stringify(result));
"""


def _run_rotation_probe(errors: list):
    """在 TZ=UTC 与 TZ=Asia/Shanghai 下各以 node 载入 rotation.ts，返回两次事实字典。

    返回 {"utc": {...}, "shanghai": {...}}。若 node 不可用 / 载入失败 / 输出非 JSON，
    记录**明确可执行**的错误并返回 None —— 禁止「node 失败就跳过断言」的静默假绿。
    """
    node = shutil.which("node")
    if not node:
        errors.append(
            "[G8] 无法执行行为断言：PATH 中未找到 node 可执行文件"
            "（需 Node 24+ 以原生类型剥离载入 rotation.ts）→ 请安装 Node 或修正 PATH"
        )
        return None
    if not ROTATION_FILE.is_file():
        errors.append(f"[G8] 轮换数学真值源缺失：{ROTATION_FILE} —— 请创建 src/data/rotation.ts")
        return None

    runs: dict = {}
    with tempfile.TemporaryDirectory() as tmp:
        harness = Path(tmp) / "rotation_probe.mjs"
        harness.write_text(_ROTATION_PROBE, encoding="utf-8")
        for label, tz in (("utc", "UTC"), ("shanghai", "Asia/Shanghai")):
            try:
                proc = subprocess.run(
                    [node, str(harness), str(ROTATION_FILE), tz],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    timeout=60,
                )
            except (OSError, subprocess.SubprocessError) as exc:
                errors.append(f"[G8] node 载入 rotation.ts 失败（TZ={tz}）：{exc}")
                return None
            if proc.returncode != 0:
                errors.append(
                    f"[G8] node 载入 rotation.ts 失败（TZ={tz}），exit={proc.returncode}，"
                    f"stderr 尾部：{proc.stderr.strip()[-500:]}"
                )
                return None
            try:
                runs[label] = json.loads(proc.stdout)
            except json.JSONDecodeError as exc:
                errors.append(
                    f"[G8] node 探针输出非合法 JSON（TZ={tz}）：{exc}；"
                    f"stdout 尾部：{proc.stdout.strip()[-300:]}"
                )
                return None
    return runs


def validate_g8_rotation_behavior(errors: list, probe) -> None:
    """G8 主断言：以真实模块行为钉死 rotation.ts（击穿空壳实现）。

    手算推导（输入时刻转为北京时间后取「积日」，取模得索引）：
      - computeFingerprint(new Date('2026-01-01T00:00:00+08:00'), [26, 28])
        → 北京 2026-01-01，积日 = 1 → (1-1)%26 = 0，(1-1)%28 = 0 → "0-0"
      - computeFingerprint(new Date('2026-03-15T12:00:00+08:00'), [26, 28])
        → 北京 2026-03-15，积日 = 31+28+15 = 74 → (74-1)%26 = 21，(74-1)%28 = 17 → "21-17"
      - getTodayIndex(0) → 空池守卫 → 0
      - lcm([26, 28]) → 364；lcm([]) → 0
    第二组指纹含非零索引，用于击穿「恒返回 0 / 恒返回空串」的空壳实现。
    """
    if probe is None:
        return
    facts = probe["utc"]
    checks = [
        ("computeFingerprint(2026-01-01T00:00:00+08:00, [26,28])", facts.get("fingerprintJan"), "0-0"),
        ("computeFingerprint(2026-03-15T12:00:00+08:00, [26,28])", facts.get("fingerprintMar"), "21-17"),
        ("getTodayIndex(0)", facts.get("todayIndexZero"), 0),
        ("lcm([26,28])", facts.get("lcm26_28"), 364),
        ("lcm([])", facts.get("lcmEmpty"), 0),
    ]
    for label, actual, expected in checks:
        if actual != expected:
            errors.append(
                f"[G8] 行为断言失败：{label} 期望 {expected!r}，实际 {actual!r}"
                f"（空壳实现或真值源被篡改，源码 token 扫描无法发现）"
            )
    print(
        f"[G8] rotation.ts 真实行为断言通过（node 原生载入）："
        f"指纹 {facts.get('fingerprintJan')} / {facts.get('fingerprintMar')}，"
        f"lcm(26,28)={facts.get('lcm26_28')}，lcm([])={facts.get('lcmEmpty')}，"
        f"getTodayIndex(0)={facts.get('todayIndexZero')}"
    )


def validate_g8a_tz_consistency(errors: list, probe) -> None:
    """G8a：beijingDayNumber 必须与构建机时区无关（TZ=UTC vs Asia/Shanghai 结果完全相同）。

    仅断言「函数体不含 getTimezoneOffset」是必要非充分条件（可用 Intl / 本地 getter 绕过）；
    此处以两套 TZ 实跑 + 时区自证（offset 0 vs -480）钉死，防止「两跑其实同环境」的假绿。
    """
    if probe is None:
        return
    utc, shanghai = probe["utc"], probe["shanghai"]
    utc_offset, sh_offset = utc.get("offset"), shanghai.get("offset")
    if utc_offset == sh_offset:
        errors.append(
            f"[G8a] 时区未真正切换（两跑 getTimezoneOffset 均为 {utc_offset}）→ 验证静默失真，"
            f"无法证明 beijingDayNumber 时区无关"
        )
        return
    if (utc_offset, sh_offset) != (0, -480):
        errors.append(
            f"[G8a] 时区自证异常：期望 UTC offset=0、Asia/Shanghai offset=-480，"
            f"实际 {utc_offset} / {sh_offset}"
        )
        return
    if utc.get("dayNumbers") != shanghai.get("dayNumbers"):
        utc_days = utc.get("dayNumbers", {})
        sh_days = shanghai.get("dayNumbers", {})
        diff = {
            iso: (utc_days.get(iso), sh_days.get(iso))
            for iso in utc_days
            if utc_days.get(iso) != sh_days.get(iso)
        }
        errors.append(
            f"[G8a] beijingDayNumber 随构建机时区漂移（UTC vs Asia/Shanghai 不一致）：{diff}"
        )
        return
    print(
        f"[G8a] beijingDayNumber 时区无关性通过：TZ=UTC(offset=0) 与 TZ=Asia/Shanghai(offset=-480) "
        f"对 {len(utc.get('dayNumbers', {}))} 个边界时刻结果完全一致 {utc.get('dayNumbers')}"
    )


def validate_g8b_pick_fresh_behavior(errors: list, probe) -> None:
    """G8b：以 node 载入 rotation.ts 直接断言 pickFreshArticle 真行为（非 Python 镜像）。"""
    if probe is None:
        return
    actual = probe["utc"].get("fresh", {})
    expected = {
        "day7": "day7",
        "day8": None,
        "today": "today",
        "future": None,
        "multi": "zero",
        "empty": None,
    }
    for label, exp in expected.items():
        got = actual.get(label, "<缺失>")
        if got != exp:
            errors.append(f"[G8b] pickFreshArticle 行为断言失败：{label} 期望 {exp!r}，实际 {got!r}")
    print(
        f"[G8b] pickFreshArticle 真行为断言通过（node）：第7天={actual.get('day7')}，"
        f"第8天={actual.get('day8')}，当天={actual.get('today')}，未来={actual.get('future')}，"
        f"多篇取最新={actual.get('multi')}，空数组={actual.get('empty')}"
    )


def validate_strip_ts_comments_literals(errors: list) -> None:
    """[G8c] _strip_ts_comments 字面量盲区自检。

    字符串 / 正则字面量内的 '//'、'/*' 不得触发注释剔除，以免截断整行造成假红，
    或掩盖同一行内的真实违规；真注释仍须被剥离；字符串内容必须保留（G1/G6 依赖）。
    """
    cases_keep = [
        ("双引号字符串内 // 不得截断整行", 'const a = "https://example.com//x"; const b = 1;', "const b = 1"),
        ("单引号字符串内 /* 不得吞后续代码", "const a = '/* not a comment */'; const b = 2;", "const b = 2"),
        ("正则字面量内转义斜杠不得误判行注释", r"const re = /https?:\/\//; const b = 3;", "const b = 3"),
        ("字符串后同行真实违规须保留", 'const u = "https://x/y"; const bad = getTimezoneOffset();', "getTimezoneOffset"),
        ("字符串内容须原样保留", 'const s = "今日上新"; const t = 1;', '"今日上新"'),
    ]
    for label, src, needle in cases_keep:
        stripped = _strip_ts_comments(src)
        if needle not in stripped:
            errors.append(f"[G8c] 剥离自检失败：{label} → 结果未见 {needle!r}：{stripped!r}")

    stripped_line = _strip_ts_comments("const a = 1; // real comment\nconst b = 2;")
    if "real comment" in stripped_line:
        errors.append(f"[G8c] 剥离自检失败：真行注释未被剔除：{stripped_line!r}")
    if "const b = 2" not in stripped_line:
        errors.append(f"[G8c] 剥离自检失败：剔除行注释后误删后续代码：{stripped_line!r}")

    stripped_block = _strip_ts_comments("const a = 1; /* block */ const b = 2;")
    if "block" in stripped_block or "const b = 2" not in stripped_block:
        errors.append(f"[G8c] 剥离自检失败：块注释剔除异常：{stripped_block!r}")

    print("[G8c] _strip_ts_comments 字面量加固自检通过（字符串/正则内 //、/* 不误剔，真注释仍剔除）")


def validate_pool_count_alignment(errors: list) -> None:
    """[YELLOW-4] 保证门禁统计的池规模 == 站点实际可渲染的池规模（口径一致）。

    文章池与词条池统一使用 content_entry_ids（递归 .md/.mdx + 排除 '_' 前缀），与内容集合
    loader ``glob({ pattern: '**/*.{md,mdx}' })`` 口径对齐；再以「页面级过滤契约」证明计数
    等于站点渲染：
      - articles/[id].astro 以 ``!entry.id.startsWith('_')`` 过滤内部文件 ⇒ 文章计数排除 '_' 一致；
      - glossary/index.astro 无 '_' 过滤 ⇒ 词条目录不得存在 '_' 前缀词条（否则门禁少计，Fail-Closed）。
    """
    if CONTENT_CONFIG_FILE.is_file():
        config = _read_text(CONTENT_CONFIG_FILE)
        pattern_hits = len(re.findall(r"pattern:\s*'\*\*/\*\.\{md,mdx\}'", config))
        if pattern_hits < 2:
            errors.append(
                f"[口径] content.config.ts 的 articles/glossary 集合未同时声明递归口径 "
                f"'**/*.{{md,mdx}}'（命中 {pattern_hits} 处），门禁计数口径可能与站点脱钩"
            )
    else:
        errors.append(f"[口径] 内容集合配置文件缺失：{CONTENT_CONFIG_FILE}")

    if not ARTICLE_PAGE_FILE.is_file():
        errors.append(f"[口径] 文章详情页缺失：{ARTICLE_PAGE_FILE}")
    elif not re.search(r"!\s*entry\.id\.startsWith\(\s*['\"]_['\"]\s*\)", _read_text(ARTICLE_PAGE_FILE)):
        errors.append(
            "[口径] articles/[id].astro 未过滤 '_' 前缀内部文件，门禁计数与站点渲染集合可能脱钩"
        )

    visible = content_entry_ids(GLOSSARY_DIR)
    loaded = content_entry_ids(GLOSSARY_DIR, exclude_internal=False)
    if len(visible) != len(loaded):
        hidden = sorted(set(loaded) - set(visible))
        errors.append(
            f"[口径] glossary 目录存在 '_' 前缀词条 {hidden}：索引页不过滤 '_' 会渲染它们，"
            f"而门禁不计 ⇒ 口径漂移（请重命名或由页面显式过滤后再纳入统计）"
        )

    print(
        f"[口径] 池规模口径对齐通过：articles={count_article_pool()}（递归 .md/.mdx + 排除 '_'，"
        f"与详情页 '!'+startsWith('_') 过滤一致）、glossary={count_glossary_pool()}（与索引页无过滤口径一致）"
    )


def validate_pool_count_alignment_fixture(errors: list) -> None:
    """[YELLOW-4] 计数口径夹具反向自检：证明 content_entry_ids 递归 + 双扩展 + 排除 '_' 真生效。"""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "a.md").write_text("x", encoding="utf-8")
        (root / "b.mdx").write_text("x", encoding="utf-8")
        (root / "_internal.md").write_text("x", encoding="utf-8")
        (root / "ignore.txt").write_text("x", encoding="utf-8")
        nested = root / "nested"
        nested.mkdir()
        (nested / "deep.md").write_text("x", encoding="utf-8")
        visible = set(content_entry_ids(root))
        loaded = set(content_entry_ids(root, exclude_internal=False))

    if visible != {"a", "b", "nested/deep"}:
        errors.append(
            f"[口径] 计数夹具失败：visible 期望 {{'a','b','nested/deep'}}，实际 {visible}"
            f"（须递归 + 含 .mdx + 排除 '_' 前缀）"
        )
    if loaded != {"a", "b", "_internal", "nested/deep"}:
        errors.append(
            f"[口径] 计数夹具失败：loader 口径（含内部文件）期望 "
            f"{{'a','b','_internal','nested/deep'}}，实际 {loaded}"
        )
    print("[口径] content_entry_ids 夹具自检通过（递归 + .md/.mdx + 排除 '_'，loader 口径含内部文件）")


# ---------------------------------------------------------------------------
# G5：候选池台账 v2 与幂等迁移（Task-7）
# ---------------------------------------------------------------------------

LEDGER_ENTRY_FIELDS = ("url", "status", "source_id", "first_seen", "last_probed", "http_status")
LEDGER_STATUSES = {"pending", "published", "rejected"}


def _ledger_entry_field_problems(entry) -> list:
    """返回条目字段完备性问题列表（空 = 完备）。"""
    if not isinstance(entry, dict):
        return [f"条目非对象：{entry!r}"]
    problems: list = []
    for field in LEDGER_ENTRY_FIELDS:
        if field not in entry:
            problems.append(f"缺少字段 '{field}'")
    if entry.get("status") not in LEDGER_STATUSES:
        problems.append(f"status 非法：{entry.get('status')!r}")
    if not entry.get("url"):
        problems.append("url 为空")
    return problems


def validate_g5_migration_structure(errors: list) -> None:
    """G5 断言①：v1（字符串数组）-> v2（对象数组）结构正确、字段完备。"""
    if not hasattr(ch, "migrate_ledger_v1_to_v2"):
        errors.append("[G5] curate_harvester 缺少 migrate_ledger_v1_to_v2()（迁移函数未实现）")
        return

    v1 = {
        "version": 1,
        "last_updated": "2026-09-26T00:00:00+00:00",
        "processed_urls": ["https://a.example/1", "https://a.example/2"],
        "rejected_urls": ["https://a.example/rejected"],
    }
    v2 = ch.migrate_ledger_v1_to_v2(v1)

    if v2.get("version") != 2:
        errors.append(f"[G5] 迁移后 version 应为 2，实际 {v2.get('version')!r}")
    entries = v2.get("processed_urls")
    if not isinstance(entries, list) or len(entries) != 3:
        errors.append(f"[G5] 迁移后应含 3 条（2 published + 1 rejected），实际 {entries!r}")
        return
    for entry in entries:
        problems = _ledger_entry_field_problems(entry)
        if problems:
            errors.append(f"[G5] 迁移条目字段不完备：{problems}；条目={entry!r}")
    status_by_url = {e.get("url"): e.get("status") for e in entries}
    if status_by_url.get("https://a.example/1") != "published":
        errors.append(f"[G5] processed_urls 迁移后 status 应为 published：{status_by_url}")
    if status_by_url.get("https://a.example/rejected") != "rejected":
        errors.append(f"[G5] rejected_urls 迁移后 status 应为 rejected：{status_by_url}")
    print(f"[G5] v1->v2 结构断言通过：3 条条目均含 {list(LEDGER_ENTRY_FIELDS)} 六字段")


def validate_g5_idempotent(errors: list) -> None:
    """G5 断言②：幂等等式 migrate(v1) == migrate(migrate(v1))（键序固定、逐字节一致）。"""
    if not hasattr(ch, "migrate_ledger_v1_to_v2"):
        errors.append("[G5] curate_harvester 缺少 migrate_ledger_v1_to_v2()")
        return
    v1 = {
        "version": 1,
        "last_updated": "2026-09-26T00:00:00+00:00",
        "processed_urls": ["https://a.example/1", "https://a.example/2", "https://a.example/1"],
        "rejected_urls": [],
    }
    once = ch.migrate_ledger_v1_to_v2(v1)
    twice = ch.migrate_ledger_v1_to_v2(once)
    dump_once = json.dumps(once, ensure_ascii=False)
    dump_twice = json.dumps(twice, ensure_ascii=False)
    if dump_once != dump_twice:
        errors.append(
            f"[G5] 迁移幂等性被破坏：migrate(v1) != migrate(migrate(v1))；"
            f"once={dump_once}，twice={dump_twice}"
        )
        return
    print("[G5] 幂等等式通过：migrate(v1) 与 migrate(migrate(v1)) 逐字节一致")


def validate_g5_dedup_prints(errors: list) -> None:
    """G5 断言③：重复 URL 按首次出现去重，且**打印被丢弃条数**（无静默数据丢失）。"""
    if not hasattr(ch, "migrate_ledger_v1_to_v2"):
        errors.append("[G5] curate_harvester 缺少 migrate_ledger_v1_to_v2()")
        return
    v1 = {
        "version": 1,
        "last_updated": "",
        "processed_urls": ["https://a.example/1", "https://a.example/1", "https://a.example/2"],
        "rejected_urls": [],
    }
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        v2 = ch.migrate_ledger_v1_to_v2(v1)
    printed = buffer.getvalue()
    urls = [e.get("url") for e in v2.get("processed_urls", [])]
    if urls != ["https://a.example/1", "https://a.example/2"]:
        errors.append(f"[G5] 重复 URL 去重失败（应按首次出现保留 2 条）：{urls}")
    if "丢弃" not in printed:
        errors.append(f"[G5] 重复 URL 去重未打印被丢弃条数：stdout={printed!r}")
    print(f"[G5] 去重断言通过：3 条输入 -> {len(urls)} 条唯一，丢弃并打印：{printed.strip()!r}")


def validate_g5_real_ledger(errors: list) -> None:
    """G5 断言④：现有 scripts/.curate-ledger.json 已是 v2 且字段完备、url 全局唯一。"""
    if not LEDGER_FILE.is_file():
        errors.append(f"[G5] 台账文件缺失：{LEDGER_FILE}")
        return
    if not hasattr(ch, "load_ledger"):
        errors.append("[G5] curate_harvester 缺少 load_ledger()")
        return
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        ledger = ch.load_ledger()
    if ledger.get("version") != 2:
        errors.append(
            f"[G5] 真实台账 version 应为 2，实际 {ledger.get('version')!r}（未执行迁移落盘）"
        )
    entries = ledger.get("processed_urls")
    if not isinstance(entries, list) or not entries:
        errors.append(f"[G5] 真实台账 processed_urls 应非空对象数组，实际 {entries!r}")
        return
    non_dict = [e for e in entries if not isinstance(e, dict)]
    if non_dict:
        errors.append(
            f"[G5] 真实台账 processed_urls 仍含非对象条目（v1 未迁移为 v2）：{non_dict!r}"
        )
        return
    for entry in entries:
        problems = _ledger_entry_field_problems(entry)
        if problems:
            errors.append(f"[G5] 真实台账条目字段不完备：{problems}；条目={entry!r}")
    urls = [e.get("url") for e in entries]
    if len(urls) != len(set(urls)):
        errors.append(f"[G5] 真实台账 url 非全局唯一：{urls}")
    print(f"[G5] 真实台账断言通过：version=2，共 {len(entries)} 条，字段完备且 url 全局唯一")


def validate_g5_harvest_no_typeerror(errors: list) -> None:
    """G5 断言⑤ [C1 回归]：v2 台账（对象数组）下 harvest_candidates() 不得抛 TypeError。

    直接以 v2 fixture 台账驱动生产路径 harvest_candidates()，并把 fetch_url 打桩为
    零网络返回（(0, "")），断言：① 不抛 TypeError（旧实现 set(对象数组) 会因 dict
    不可哈希崩溃）；② 返回 list；③ 全程零真实网络请求。
    """
    if not hasattr(ch, "harvest_candidates"):
        errors.append("[G5] curate_harvester 缺少 harvest_candidates()")
        return

    fixture_ledger = {
        "version": 2,
        "last_updated": "",
        "processed_urls": [
            {
                "url": "https://fixture.example/seen-1",
                "status": "published",
                "source_id": "fixture",
                "first_seen": "2026-09-01",
                "last_probed": "2026-09-02",
                "http_status": 200,
            },
            {
                "url": "https://fixture.example/seen-2",
                "status": "rejected",
                "source_id": "fixture",
                "first_seen": "2026-09-01",
                "last_probed": "2026-09-02",
                "http_status": 404,
            },
        ],
    }

    original_load = ch.load_ledger
    original_fetch = ch.fetch_url
    stub_calls: list = []

    def zero_network_fetch(*args, **kwargs):
        stub_calls.append(args)
        return 0, ""

    ch.load_ledger = lambda: fixture_ledger
    ch.fetch_url = zero_network_fetch
    try:
        result = ch.harvest_candidates(limit=1)
    except TypeError as exc:
        errors.append(
            f"[G5][C1] v2 台账（对象数组）下 harvest_candidates 抛 TypeError：{exc}"
            f"（台账读写未改为对象口径，set(entries) 因 dict 不可哈希而崩溃）"
        )
        return
    except Exception as exc:  # noqa: BLE001 — 断言容错
        errors.append(f"[G5][C1] harvest_candidates 意外异常 {type(exc).__name__}: {exc}")
        return
    finally:
        ch.load_ledger = original_load
        ch.fetch_url = original_fetch

    if not isinstance(result, list):
        errors.append(f"[G5][C1] harvest_candidates 应返回 list，实际 {type(result).__name__}")
        return
    print(
        f"[G5][C1] v2 台账下 harvest_candidates 正常返回（{len(result)} 条候选，"
        f"{len(stub_calls)} 次打桩抓取，零真实网络）"
    )


# ---------------------------------------------------------------------------
# G4：信源清单 schema 合法性与 --pool 候选池零副作用（Task-8）
# ---------------------------------------------------------------------------

DISCOVERY_MODES = ("anchor", "sitemap", "feed")
ADMISSION_STATUSES = ("admitted", "probing", "rejected")


def _sha256(path: Path) -> str:
    """返回文件内容的 sha256 十六进制摘要（用于校验 --pool 零副作用）。"""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_schema_problems(src) -> list:
    """纯函数：返回单条信源 schema 的合法性问题列表（空 = 合法）。

    覆盖 G4 四类断言：
      ① discovery.mode ∈ {anchor, sitemap, feed}；
      ② admission.status ∈ {admitted, probing, rejected}；
      ③ fail-closed：status == "admitted" ⇒ license 必须非空；
      ④ base_url / discovery.url / entry_url 必须以 http(s):// 开头。
    """
    if not isinstance(src, dict):
        return [f"信源非对象：{src!r}"]
    src_id = src.get("id", "<无 id>")
    problems: list = []

    discovery = src.get("discovery")
    if not isinstance(discovery, dict):
        problems.append(f"[{src_id}] 缺少 discovery 对象")
        discovery = {}
    if discovery.get("mode") not in DISCOVERY_MODES:
        problems.append(
            f"[{src_id}] discovery.mode 非法：{discovery.get('mode')!r}（合法：{DISCOVERY_MODES}）"
        )

    admission = src.get("admission")
    if not isinstance(admission, dict):
        problems.append(f"[{src_id}] 缺少 admission 对象")
        admission = {}
    status = admission.get("status")
    if status not in ADMISSION_STATUSES:
        problems.append(
            f"[{src_id}] admission.status 非法：{status!r}（合法：{ADMISSION_STATUSES}）"
        )
    license_value = admission.get("license")
    if status == "admitted" and not (isinstance(license_value, str) and license_value.strip()):
        problems.append(
            f"[{src_id}] fail-closed 违背：admission.status == 'admitted' 但 license 为空"
            f"（admitted 信源必须携带非空 license）"
        )

    for label, value in (
        ("base_url", src.get("base_url")),
        ("discovery.url", discovery.get("url")),
        ("entry_url", src.get("entry_url")),
    ):
        if not (isinstance(value, str) and re.match(r"https?://", value)):
            problems.append(f"[{src_id}] {label} 必须以 http(s):// 开头：{value!r}")
    return problems


def validate_g4_source_schema(errors: list) -> None:
    """G4 主断言①：遍历真实 scripts/sources.json，逐条校验 schema 合法性。"""
    if not SOURCES_FILE.is_file():
        errors.append(f"[G4] 信源清单缺失：{SOURCES_FILE}")
        return
    try:
        sources = json.loads(_read_text(SOURCES_FILE))
    except json.JSONDecodeError as exc:
        errors.append(f"[G4] sources.json 非法 JSON：{exc}")
        return
    if not isinstance(sources, list) or not sources:
        errors.append(f"[G4] sources.json 应为非空数组，实际 {type(sources).__name__}")
        return

    for src in sources:
        for problem in _source_schema_problems(src):
            errors.append(f"[G4] {problem}")
    print(
        f"[G4] 信源 schema 断言通过：{len(sources)} 条信源的 discovery.mode / admission.status / "
        f"admitted⇒license 非空 / http(s) 前缀均合法"
    )


def validate_g4_source_schema_reverse(errors: list) -> None:
    """G4 反向用例（MUST）：构造 admitted 但 license 为空的信源，断言校验函数返回非空错误。

    证明 fail-closed 的「admitted ⇒ license 非空」校验真生效（而非恰好通过）。
    """
    bad = {
        "id": "bad-admitted-empty-license",
        "name": "坏信源（admitted 但 license 空）",
        "entry_url": "https://example.org/entry",
        "base_url": "https://example.org",
        "discovery": {"mode": "anchor", "url": "https://example.org/entry"},
        "admission": {"status": "admitted", "license": ""},
    }
    problems = _source_schema_problems(bad)
    if not problems:
        errors.append(
            "[G4] 反向用例失效：admitted 但 license 为空必须返回非空错误列表（fail-closed），实际为空"
        )
        return
    if not any("license" in p for p in problems):
        errors.append(f"[G4] 反向用例失效：错误信息未点名 license（fail-closed 未覆盖）：{problems}")
        return
    print(f"[G4] 反向用例通过：admitted+空 license 检出 {len(problems)} 条错误（fail-closed 生效）")


def validate_g4_rank_candidates(errors: list) -> None:
    """G4 主断言②：rank_candidates 纯函数语义。

    - 分类缺口升序优先（当前篇数少者排前），同分类内保持输入（首次发现）顺序；
    - 不得丢弃候选、不得改动入参；空输入返回 []；
    - category 缺失/非法 ⇒ 归入 default_category 并参与排序（不丢弃）。

    变异自证①：若把排序改为「分类篇数降序（缺口小者优先）」，本断言立即失败。
    """
    if not hasattr(ch, "rank_candidates"):
        errors.append("[G4] curate_harvester 缺少 rank_candidates()")
        return

    counts = {"contraception": 0, "pleasure": 2, "body": 5, "intimacy": 1}
    candidates = [
        {"title": "b1", "category": "body"},
        {"title": "p1", "category": "pleasure"},
        {"title": "c1", "category": "contraception"},
        {"title": "i1", "category": "intimacy"},
        {"title": "b2", "category": "body"},
        {"title": "c2", "category": "contraception"},
    ]
    snapshot = [c["title"] for c in candidates]

    ordered = ch.rank_candidates(candidates, counts)
    order = [c["title"] for c in ordered]
    expected = ["c1", "c2", "i1", "p1", "b1", "b2"]
    if order != expected:
        errors.append(
            f"[G4] rank_candidates 排序错误：期望 {expected}（分类缺口升序 + 同分类稳定），实际 {order}"
        )
    if len(ordered) != len(candidates):
        errors.append(f"[G4] rank_candidates 不得丢弃候选：输入 {len(candidates)}，实际 {len(ordered)}")
    if [c["title"] for c in candidates] != snapshot:
        errors.append("[G4] rank_candidates 不得改动入参（输入顺序被破坏）")

    if ch.rank_candidates([], counts) != []:
        errors.append("[G4] rank_candidates 空输入必须返回 []")

    messy = [
        {"title": "x1"},
        {"title": "x2", "category": "not-a-category"},
        {"title": "x3", "category": "intimacy"},
    ]
    messy_ordered = ch.rank_candidates(messy, counts)
    if len(messy_ordered) != 3:
        errors.append(f"[G4] rank_candidates 不得丢弃缺/非法分类候选：{messy_ordered}")
    elif messy_ordered[0]["title"] != "x3":
        errors.append(
            f"[G4] 缺/非法分类应归入 default_category 并参与排序（intimacy 缺口更大应排前），"
            f"实际 {[c['title'] for c in messy_ordered]}"
        )
    elif messy_ordered[1].get("category") not in ("body",):
        errors.append(
            f"[G4] 缺/非法分类未归入 default_category：{messy_ordered[1]!r}"
        )
    print(
        f"[G4] rank_candidates 断言通过：缺口升序 {order}；空池 -> []；"
        f"缺/非法分类归入 default_category 且不丢弃"
    )


def validate_g4_pool_zero_side_effect(errors: list) -> None:
    """G4 主断言③：--pool 零副作用——运行前后台账文件 sha256 完全一致。

    [Task-7 语义钉死] 必须以**已是 v2** 的真实台账驱动（load_ledger 仅在读到 v1 时才写回；
    若用 v1 夹具，迁移写回会被误判为 --pool 的副作用）。全程打桩 fetch_url，零真实网络。
    变异自证②：若在 --pool 路径加入 save_ledger(...) 调用，sha256 立即变化 ⇒ 本断言失败。
    """
    if not hasattr(ch, "run_pool"):
        errors.append("[G4] curate_harvester 缺少 run_pool()（--pool 分支未实现）")
        return
    if not LEDGER_FILE.is_file():
        errors.append(f"[G4] 台账文件缺失：{LEDGER_FILE}")
        return

    fixture_html = (
        "<html><body>"
        '<a href="/zh/news-room/fact-sheets/detail/fixture-pool-a">避孕方法</a>'
        '<a href="/zh/news-room/fact-sheets/detail/fixture-pool-b">月经周期</a>'
        "</body></html>"
    )
    original_fetch = ch.fetch_url
    ch.fetch_url = lambda *args, **kwargs: (200, fixture_html)
    before = _sha256(LEDGER_FILE)
    buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(buffer):
            code = ch.run_pool(limit=40)
    finally:
        ch.fetch_url = original_fetch
    after = _sha256(LEDGER_FILE)
    printed = buffer.getvalue()

    if before != after:
        errors.append(
            f"[G4] --pool 产生副作用：台账 sha256 变化 {before} -> {after}"
            f"（--pool 路径必须只读，严禁调用 save_ledger）"
        )
    if code != 0:
        errors.append(
            f"[G4] --pool 应零副作用正常返回 0（打桩发现非空候选），实际 exit={code}：stdout={printed[:400]}"
        )
    if "候选总数" not in printed:
        errors.append(f"[G4] --pool 未输出汇总（候选总数 + 分类缺口）：stdout={printed[:400]}")
    print(f"[G4] --pool 零副作用通过：台账 sha256 前后一致 {before[:12]}…（{len(printed)} 字节 stdout）")


def validate_g4_pool_empty_state(errors: list) -> None:
    """G4 主断言④ [Actionable-Empty-State]：空候选池必须显式报错并给出下一步。

    [Task-9 D2 收口] 空池提示统一为 npm 脚本形态 ``pnpm curate:admit <id>``（不再是原始
    flag ``--admit-source``），并**按两类空因分别提示**：
      (a) 无任何已准入（admitted）信源 ⇒ 提示先准入信源；
      (b) 有已准入信源但候选耗尽 ⇒ 提示准入新信源或扩大 link_pattern。
    断言 run_pool 返回非 0 且打印对应文案，禁止静默返回空表。
    变异自证③：若空池改为静默返回（exit 0 且无告警），本断言立即失败。
    """
    if not hasattr(ch, "run_pool"):
        errors.append("[G4] curate_harvester 缺少 run_pool()")
        return

    # 原因(a)：指定一个不存在的 source_id ⇒ 过滤后无已准入信源。
    original_fetch = ch.fetch_url
    ch.fetch_url = lambda *args, **kwargs: (0, "")  # 零网络
    buffer_a = io.StringIO()
    try:
        with contextlib.redirect_stdout(buffer_a):
            code_a = ch.run_pool(source_id="__no_such_source__", limit=40)
    finally:
        ch.fetch_url = original_fetch
    printed_a = buffer_a.getvalue()

    if code_a == 0:
        errors.append("[G4] 空候选池必须返回非零退出码（禁止静默返回空表），实际 exit=0")
    if "候选池为空" not in printed_a:
        errors.append(f"[G4] 空候选池必须打印显式告警「候选池为空」，实际 stdout={printed_a!r}")
    if "pnpm curate:admit" not in printed_a:
        errors.append(
            f"[G4] 空候选池告警必须给出可执行下一步（pnpm curate:admit <id>），实际 stdout={printed_a!r}"
        )
    if "--admit-source" in printed_a:
        errors.append(
            f"[G4] 空候选池告警仍残留原始 flag「--admit-source」（D2 要求统一为 pnpm curate:admit）：{printed_a!r}"
        )
    if "原因(a)" not in printed_a:
        errors.append(f"[G4] 无已准入信源时必须走「原因(a)」分支提示先准入信源：{printed_a!r}")

    # 原因(b)：真实信源（WHO / 默沙东为 admitted）下零候选 ⇒ 候选耗尽。
    original_fetch = ch.fetch_url
    ch.fetch_url = lambda *args, **kwargs: (0, "")  # 零网络
    buffer_b = io.StringIO()
    try:
        with contextlib.redirect_stdout(buffer_b):
            code_b = ch.run_pool(source_id=None, limit=40)
    finally:
        ch.fetch_url = original_fetch
    printed_b = buffer_b.getvalue()

    if code_b == 0:
        errors.append("[G4] 已准入信源候选耗尽时也必须返回非零退出码，实际 exit=0")
    if "原因(b)" not in printed_b:
        errors.append(
            f"[G4] 有已准入信源但候选耗尽时必须走「原因(b)」分支（提示准入新信源/扩大 link_pattern）：{printed_b!r}"
        )
    if "link_pattern" not in printed_b:
        errors.append(f"[G4] 原因(b) 提示须包含「扩大 link_pattern」的可执行建议：{printed_b!r}")

    print(
        f"[G4] 空池 Actionable-Empty-State 通过：exit={code_a}/{code_b}，"
        f"含「候选池为空」+「pnpm curate:admit」，且 (a)/(b) 两类空因分别提示"
    )


# ---------------------------------------------------------------------------
# G7：速测题占位注入幂等与 --admit-source 只读性（Task-9）
# ---------------------------------------------------------------------------

# 最小可注入的 TS 种子：绝不复用真实 src/data/dailyQuiz.ts 做注入测试（安全红线），
# 仅需形如 DAILY_QUIZZES 的对象字面量即可驱动注入路径。
_G7_QUIZ_SEED = (
    "export interface QuizItem {\n"
    "  articleId: string;\n"
    "}\n"
    "\n"
    "export const DAILY_QUIZZES: Record<string, QuizItem> = {\n"
    "  'existing-slug': {\n"
    "    articleId: 'existing-slug',\n"
    "    question: '既有题目',\n"
    "  },\n"
    "};\n"
)


def _brace_balance(text: str) -> tuple:
    """返回 (左花括号数, 右花括号数)（按字符计数，供 G7 配平断言）。"""
    return text.count("{"), text.count("}")


def _count_key_occurrences(text: str, slug: str) -> int:
    """统计 DAILY_QUIZZES 中该 slug 顶层键（``'<slug>': {``）出现次数。"""
    return len(
        re.findall(r"^\s*'" + re.escape(slug) + r"'\s*:\s*\{", text, flags=re.MULTILINE)
    )


def _bad_inject_always_append(quiz_path: Path, slug: str) -> bool:
    """非幂等坏实现（仅用于 G7 反向用例自证）：从不检测已存在，永远追加并返回 True。"""
    text = quiz_path.read_text(encoding="utf-8")
    entry = "  '" + slug + "': {\n    articleId: '" + slug + "',\n  },\n"
    close = text.rfind("};")
    quiz_path.write_text(text[:close] + entry + text[close:], encoding="utf-8")
    return True


def validate_g7_idempotent_injection(errors: list) -> None:
    """G7 主断言①②：占位注入幂等（tempfile 副本，严禁触碰真实 dailyQuiz.ts）。

    - 第一次注入返回 True，第二次返回 False；
    - 第二次前后文件 sha256 **完全不变**（无副作用）；
    - 注入后文本含 ``articleId: '<slug>'`` 锚点，且花括号配平（``{`` 数 == ``}`` 数）；
    - 同一 slug 顶层键恰好 1 条（不产生第二条占位）。
    """
    if not hasattr(ch, "inject_quiz_placeholder"):
        errors.append("[G7] curate_harvester 缺少 inject_quiz_placeholder()")
        return

    slug = "g7-fixture-slug"
    with tempfile.TemporaryDirectory() as tmp:
        copy_path = Path(tmp) / "dailyQuiz.ts"
        copy_path.write_text(_G7_QUIZ_SEED, encoding="utf-8")

        first = ch.inject_quiz_placeholder(copy_path, slug)
        after_first = _read_text(copy_path)
        sha_mid = _sha256(copy_path)

        second = ch.inject_quiz_placeholder(copy_path, slug)
        after_second = _read_text(copy_path)
        sha_end = _sha256(copy_path)

    if first is not True:
        errors.append(f"[G7] 首次注入应返回 True，实际 {first!r}")
    if second is not False:
        errors.append(f"[G7] 二次注入应返回 False（幂等），实际 {second!r}")
    if sha_mid != sha_end:
        errors.append(
            f"[G7] 二次注入产生副作用：副本 sha256 变化 {sha_mid[:12]}… -> {sha_end[:12]}…"
        )
    if after_first != after_second:
        errors.append("[G7] 二次注入后文本内容发生变化（幂等性被破坏）")
    if f"articleId: '{slug}'" not in after_first:
        errors.append(f"[G7] 注入文本缺少 articleId 锚点 articleId: '{slug}'")
    left, right = _brace_balance(after_first)
    if left != right:
        errors.append(f"[G7] 注入后花括号不配平：{left} 个 {{ vs {right} 个 }}")
    occurrences = _count_key_occurrences(after_first, slug)
    if occurrences != 1:
        errors.append(f"[G7] 同一 slug 顶层键应恰好 1 条占位，实际 {occurrences} 条")

    # 既有 slug 二次注入必须直接返回 False 且不改动文件。
    with tempfile.TemporaryDirectory() as tmp:
        exist_path = Path(tmp) / "dailyQuiz.ts"
        exist_path.write_text(_G7_QUIZ_SEED, encoding="utf-8")
        sha_before = _sha256(exist_path)
        repeat = ch.inject_quiz_placeholder(exist_path, "existing-slug")
        sha_after = _sha256(exist_path)
    if repeat is not False:
        errors.append(f"[G7] 对已存在 slug 注入应返回 False，实际 {repeat!r}")
    if sha_before != sha_after:
        errors.append("[G7] 对已存在 slug 注入却改动了文件（应原样返回 False）")

    print(
        f"[G7] 占位注入幂等通过：首次 True / 二次 False，副本 sha256 不变 {sha_end[:12]}…，"
        f"含 articleId 锚点且花括号配平（{left} 对）"
    )


def validate_g7_reverse_bad_impl(errors: list) -> None:
    """G7 反向用例（MUST）：非幂等坏实现必须被 G7 判红语义捕获。

    以「永远追加、二次仍返回 True」的坏实现驱动同一 tempfile 副本，断言其确实
    破坏了 G7 三条不变量（二次 True / sha256 变化 / 出现 2 条占位）——
    从而证明 G7 的幂等断言对坏实现**可红**（非恰好通过的假绿）。
    """
    slug = "g7-bad-slug"
    with tempfile.TemporaryDirectory() as tmp:
        bad_path = Path(tmp) / "dailyQuiz.ts"
        bad_path.write_text(_G7_QUIZ_SEED, encoding="utf-8")
        bad_first = _bad_inject_always_append(bad_path, slug)
        bad_sha_mid = _sha256(bad_path)
        bad_second = _bad_inject_always_append(bad_path, slug)
        bad_sha_end = _sha256(bad_path)
        bad_text = _read_text(bad_path)

    bad_occurrences = _count_key_occurrences(bad_text, slug)
    if not (bad_first is True and bad_second is True):
        errors.append(
            f"[G7] 反向用例失效：坏实现应两次均返回 True，实际 {bad_first!r} / {bad_second!r}"
        )
    if bad_sha_mid == bad_sha_end:
        errors.append("[G7] 反向用例失效：坏实现二次注入本应改变 sha256（幂等语义被破坏）")
    if bad_occurrences != 2:
        errors.append(f"[G7] 反向用例失效：坏实现应产生 2 条占位，实际 {bad_occurrences} 条")

    if not hasattr(ch, "inject_quiz_placeholder"):
        errors.append("[G7] curate_harvester 缺少 inject_quiz_placeholder()")
        return
    # 正向对照：真实实现驱动同一副本必须收敛为 1 条且二次 False。
    with tempfile.TemporaryDirectory() as tmp:
        good_path = Path(tmp) / "dailyQuiz.ts"
        good_path.write_text(_G7_QUIZ_SEED, encoding="utf-8")
        good_first = ch.inject_quiz_placeholder(good_path, slug)
        good_sha_mid = _sha256(good_path)
        good_second = ch.inject_quiz_placeholder(good_path, slug)
        good_sha_end = _sha256(good_path)
        good_occurrences = _count_key_occurrences(_read_text(good_path), slug)

    if not (good_first is True and good_second is False):
        errors.append(
            f"[G7] 正向对照失效：真实实现应 True/False，实际 {good_first!r} / {good_second!r}"
        )
    if good_sha_mid != good_sha_end:
        errors.append("[G7] 正向对照失效：真实实现二次注入改变了 sha256")
    if good_occurrences != 1:
        errors.append(f"[G7] 正向对照失效：真实实现应恰好 1 条占位，实际 {good_occurrences} 条")

    print(
        f"[G7] 反向用例通过：非幂等坏实现破坏 3 条不变量（二次 True / sha256 变化 / "
        f"{bad_occurrences} 条占位）；真实实现收敛为 1 条且二次 False"
    )


def validate_g7_admit_source_readonly(errors: list) -> None:
    """G7 主断言④ [No-Auto-Approve]：--admit-source 只打印草案，绝不写回 sources.json。

    以打桩 _http_get 驱动 run_admit_source，断言运行前后 scripts/sources.json 的
    sha256 **完全不变**（证明未自动置 admitted / 未自动填 license / 未写盘）。
    """
    if not hasattr(ch, "run_admit_source"):
        errors.append("[G7] curate_harvester 缺少 run_admit_source()（--admit-source 分支未实现）")
        return
    if not SOURCES_FILE.is_file():
        errors.append(f"[G7] 信源清单缺失：{SOURCES_FILE}")
        return

    # [F1 修复] run_admit_source 现经 probe_page -> _http_get 探测；打桩低层函数保持零网络。
    original_get = ch._http_get
    ch._http_get = lambda *args, **kwargs: (
        200,
        "<html><title>许可页</title></html>",
        "https://stub.example/license",
    )
    before = _sha256(SOURCES_FILE)
    buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(buffer):
            code = ch.run_admit_source("plannedparenthood")
    finally:
        ch._http_get = original_get
    after = _sha256(SOURCES_FILE)
    printed = buffer.getvalue()

    if before != after:
        errors.append(
            f"[G7] --admit-source 产生副作用：sources.json sha256 变化 {before[:12]}… -> {after[:12]}…"
            f"（No-Auto-Approve：严禁自动写回 sources.json）"
        )
    if code != 0:
        errors.append(f"[G7] --admit-source 应正常打印草案并返回 0，实际 exit={code}")
    if "admission" not in printed:
        errors.append(f"[G7] --admit-source 未打印 admission 草案：stdout={printed[:300]}")
    if "人工" not in printed:
        errors.append(f"[G7] --admit-source 未提示「请人工阅读许可页后自行填写」：stdout={printed[:300]}")
    if "verified_by_run" not in printed:
        errors.append(f"[G7] --admit-source 未提示 verified_by_run（须来自 CI 出口）：stdout={printed[:300]}")
    print(
        f"[G7] --admit-source 只读性通过：sources.json sha256 前后一致 {before[:12]}…，"
        f"打印 admission 草案（{len(printed)} 字节）"
    )


# --- F1 缺陷修复（准入探测假阳性）新增断言 -------------------------------------
# 根因：fetch_url 丢弃 resp.geturl()，urllib 默认跟随重定向 ⇒ 状态码恒为落地页 200，
# 「请求 /copyright 却落回首页」被误报为「✅ 可达」，误导人工照着假页面核许可条款。
# 本组断言以打桩 _http_get 驱动 probe_page / run_admit_source，全程零真实网络。

_G7_PROBE_SOURCE = {
    "id": "g7-probe-fixture",
    "name": "G7 探测夹具",
    "base_url": "https://example.test",
    "entry_url": "https://example.test/",
    "admission": {"license_url": ""},
}
_G7_SITE_ROOT = "https://example.test"
_G7_ROOT_LANDING = "https://example.test/"


def _g7_extract_draft(printed: str) -> dict:
    """从 run_admit_source 输出中解析 ③ admission 草案 JSON（零网络）。"""
    match = re.search(r'\{\s*"status".*?\n\}', printed, re.DOTALL)
    if not match:
        return {}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}


def _g7_run_admit_stubbed(responder, source: dict) -> tuple:
    """打桩 _http_get + 夹具信源驱动 run_admit_source（零网络），返回 (exit_code, stdout)。"""
    original_http = ch._http_get
    original_load = ch._load_sources
    ch._http_get = lambda url, timeout=15: responder(url)
    ch._load_sources = lambda: [source]
    buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(buffer):
            code = ch.run_admit_source(source["id"])
    finally:
        ch._http_get = original_http
        ch._load_sources = original_load
    return code, buffer.getvalue()


def _g7_probe_with_stub(url, responder, site_root=_G7_SITE_ROOT, root_length=0):
    """打桩 _http_get 驱动 probe_page（零网络）。"""
    original = ch._http_get
    ch._http_get = lambda u, timeout=15: responder(u)
    try:
        return ch.probe_page(url, site_root, root_length=root_length, timeout=10)
    finally:
        ch._http_get = original


def validate_g7_probe_page_verdicts(errors: list) -> None:
    """G7 新增（F1 缺陷修复）：probe_page 判定 + 草案 license_url 只取真实候选。

    覆盖：redirect_home 主判据 / real 正例 / unreachable / 容错 (0,"",url) / 二次指纹 /
    反向用例（只看状态码的坏实现必被误判为 real，须判红）。
    """
    missing = [n for n in ("_http_get", "probe_page", "_url_key") if not hasattr(ch, n)]
    if missing:
        errors.append(f"[G7] curate_harvester 缺少 F1 探测函数：{missing}")
        return

    # ① redirect_home 主判据：请求非首页却落回站点根 ⇒ 必须判 redirect_home
    def responder_to_root(url):
        return (200, "R" * 120, _G7_ROOT_LANDING)

    info = _g7_probe_with_stub("https://example.test/copyright", responder_to_root)
    if info.get("verdict") != "redirect_home":
        errors.append(
            f"[G7] F1 主判据失败：请求 /copyright 落回首页应判 redirect_home，实际 {info.get('verdict')!r}"
        )
    if info.get("final_url") != _G7_ROOT_LANDING:
        errors.append(
            f"[G7] F1 未回传最终 URL：期望 {_G7_ROOT_LANDING!r}，实际 {info.get('final_url')!r}"
        )

    # ①-草案：redirect_home 候选严禁写入草案 license_url（钉死第二处泄漏点）
    code, printed = _g7_run_admit_stubbed(responder_to_root, _G7_PROBE_SOURCE)
    draft = _g7_extract_draft(printed)
    if code != 0:
        errors.append(f"[G7] F1 草案运行应返回 0，实际 exit={code}")
    if draft.get("license_url") != "":
        errors.append(
            f"[G7] F1 第二处泄漏：redirect_home 候选被写入草案 license_url={draft.get('license_url')!r}"
            "（应置空并提示人工补充）"
        )
    if "疑似重定向到首页" not in printed:
        errors.append("[G7] F1 输出未提示「疑似重定向到首页（非真实许可页）」")
    if "未找到真实可用的许可页候选" not in printed:
        errors.append("[G7] F1 无真实候选时未提示「未找到真实可用的许可页候选，请人工补充 license_url」")
    if "真实可用候选：" not in printed:
        errors.append("[G7] F1 输出缺少「真实可用候选：N / 总候选 M」汇总行")

    # ⑦ 反向用例（MUST）：只看状态码的坏实现必然返回 real —— 钉死 verdict != real 防 F1 回归
    if info.get("verdict") == "real":
        errors.append(
            "[G7] F1 回归守卫：请求 /copyright 落回首页被误判为 real（只看 HTTP 200 的坏实现未被判红）"
            "—— 此断言专防「重定向到首页」假阳性回归"
        )

    # ② real 正例：final_url == requested 且 200 ⇒ real，首个真实候选进草案
    def responder_terms_real(url):
        if url.endswith("/terms"):
            return (200, "terms-body", url)
        return (404, "", url)

    info_real = _g7_probe_with_stub("https://example.test/terms", responder_terms_real)
    if info_real.get("verdict") != "real":
        errors.append(f"[G7] F1 real 正例失败：期望 real，实际 {info_real.get('verdict')!r}")
    _code2, printed2 = _g7_run_admit_stubbed(responder_terms_real, _G7_PROBE_SOURCE)
    draft2 = _g7_extract_draft(printed2)
    if draft2.get("license_url") != "https://example.test/terms":
        errors.append(
            f"[G7] F1 real 草案应取首个真实候选 /terms，实际 {draft2.get('license_url')!r}"
        )

    # ③ unreachable：404 ⇒ unreachable 且草案为空
    def responder_404(url):
        return (404, "", url)

    info_404 = _g7_probe_with_stub("https://example.test/copyright", responder_404)
    if info_404.get("verdict") != "unreachable":
        errors.append(f"[G7] F1 unreachable 判定失败：期望 unreachable，实际 {info_404.get('verdict')!r}")
    _code3, printed3 = _g7_run_admit_stubbed(responder_404, _G7_PROBE_SOURCE)
    if _g7_extract_draft(printed3).get("license_url") != "":
        errors.append("[G7] F1 全 404 时草案 license_url 应为空")

    # ④ 容错：(0, "", url) ⇒ unreachable 且不抛异常
    def responder_zero(url):
        return (0, "", url)

    try:
        info_zero = _g7_probe_with_stub("https://example.test/copyright", responder_zero)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"[G7] F1 容错失败：(0,\"\",url) 不应抛异常，实际 {exc!r}")
    else:
        if info_zero.get("verdict") != "unreachable":
            errors.append(f"[G7] F1 容错：期望 unreachable，实际 {info_zero.get('verdict')!r}")

    # ⑥ 二次指纹：final_url != requested 且 content_length == root_length(>0) ⇒ redirect_home
    def responder_fingerprint(url):
        return (200, "F" * 500, "https://example.test/other-landing")

    info_fp = _g7_probe_with_stub(
        "https://example.test/copyright", responder_fingerprint, root_length=500
    )
    if info_fp.get("verdict") != "redirect_home":
        errors.append(
            f"[G7] F1 二次指纹失败：内容长度与首页一致应判 redirect_home，实际 {info_fp.get('verdict')!r}"
        )

    # ⑤ (F1b-H2) 口径一致：final_url 与 requested **仅尾斜杠不同** ⇒ 不得判为「发生过重定向」，
    # 更不得在 note 写出误导性「重定向后落地 …」（redirected 必须用 _url_key 归一化比较）。
    def responder_trailing_slash(url):
        return (200, "terms-body", url + "/")

    info_slash = _g7_probe_with_stub("https://example.test/terms", responder_trailing_slash)
    if info_slash.get("verdict") != "real":
        errors.append(
            f"[G7][H2] 口径一致：仅尾斜杠不同应判 real，实际 {info_slash.get('verdict')!r}"
        )
    if info_slash.get("note") != "":
        errors.append(
            f"[G7][H2] 口径不一致：仅尾斜杠不同被误判为发生重定向，note={info_slash.get('note')!r}"
            "（raw 字符串比较回归；应改用 _url_key 归一化比较，不写误导性「重定向后落地 …」）"
        )

    print(
        "[G7] F1 探测判定通过：redirect_home / real / unreachable / 容错 / 二次指纹 均正确，"
        "redirect_home 不进草案 license_url；且仅尾斜杠不同不误判为发生重定向"
    )


def validate_g7_admit_e2e_root_length_wiring(errors: list) -> None:
    """G7 新增（F1b-H1）：经 run_admit_source **端到端** 断言 root_length 已接线到生产路径。

    [假绿防线] 既有 F1 测试**直接调用 probe_page 并显式传 root_length**，无法发现
    「生产调用（run_admit_source）从未传值 ⇒ 二次指纹判据永假（休眠）」这类假绿。本断言
    打桩 _http_get + _load_sources 走 run_admit_source 全程（零网络）：站点根探测返回 200
    且 body 长度 L；某许可页候选返回 200，但落地 URL 在站点根之外、body 长度也 == L
    ⇒ 该候选**必须**被判 redirect_home，且**不得**写入草案 license_url。
    「撤销 H1 接线（run_admit_source 不再传 root_length）」将使本断言立即判红。
    """
    required = ("run_admit_source", "_http_get", "_load_sources", "_url_key", "probe_page")
    missing = [n for n in required if not hasattr(ch, n)]
    if missing:
        errors.append(f"[G7][H1] curate_harvester 缺少端到端断言所需函数：{missing}")
        return

    home_body = "H" * 400  # L：首页内容长度指纹

    def responder_root_and_lookalike(url):
        # 站点根（entry_url / base_url）：200，落地即自身，长度 L
        if ch._url_key(url) == ch._url_key(_G7_SITE_ROOT):
            return (200, home_body, url)
        # 许可页候选：200，但落地 URL 在站点根之外，长度也 == L（首页指纹一致）
        return (200, home_body, "https://cdn.other.test/mirror")

    code, printed = _g7_run_admit_stubbed(responder_root_and_lookalike, _G7_PROBE_SOURCE)
    if code != 0:
        errors.append(f"[G7][H1] 端到端运行应返回 0，实际 exit={code}")
    if "疑似重定向到首页" not in printed:
        errors.append(
            "[G7][H1] 生产未接线：run_admit_source 未把 base_url 探测的 content_length 作为 "
            "root_length 传给许可页候选 probe_page ⇒ 二次指纹判据休眠，落地站点根之外（长度与首页一致）的"
            "假候选未被判 redirect_home —— 此断言专防「生产未接线 ⇒ 判据休眠」的假绿"
        )
    draft = _g7_extract_draft(printed)
    if draft.get("license_url") != "":
        errors.append(
            f"[G7][H1] 生产未接线泄漏：指纹一致的假候选被写入草案 license_url={draft.get('license_url')!r}"
            "（应判 redirect_home 并置空）"
        )
    print(
        "[G7][H1] 端到端接线通过：base_url 内容长度已作为 root_length 传入候选探测，"
        "假候选判 redirect_home 且不进草案 license_url"
    )


def validate_g7_url_key_normalization(errors: list) -> None:
    """G7 新增（F1）：_url_key 归一化比较键边界（尾部斜杠 / fragment / 大小写）。"""
    if not hasattr(ch, "_url_key"):
        errors.append("[G7] curate_harvester 缺少 _url_key()")
        return
    pairs = (
        ("https://a.com/x/", "https://a.com/x"),
        ("https://a.com/", "https://a.com"),
        ("https://a.com/x#f", "https://a.com/x"),
    )
    for left, right in pairs:
        if ch._url_key(left) != ch._url_key(right):
            errors.append(
                f"[G7] F1 _url_key 归一化失败：{left!r} 与 {right!r} 键不相等"
                f"（{ch._url_key(left)!r} vs {ch._url_key(right)!r}）"
            )
    # 反向：不同路径必须不等（防止归一化过度塌缩）
    if ch._url_key("https://a.com/x") == ch._url_key("https://a.com/y"):
        errors.append("[G7] F1 _url_key 过度归一化：/x 与 /y 键不应相等")
    print("[G7] F1 _url_key 归一化通过：尾部斜杠 / fragment 等价，不同路径仍区分")


def validate_g7_fetch_url_contract(errors: list) -> None:
    """G7 新增（F1）：fetch_url 二元组契约零回归（防改成三元组无声破坏 5+ 处发现调用点）。"""
    if not hasattr(ch, "_http_get"):
        errors.append("[G7] curate_harvester 缺少 _http_get()（fetch_url 契约断言需打桩它）")
        return
    original = ch._http_get
    ch._http_get = lambda url, timeout=15: (200, "<html>ok</html>", "https://example.test/final")
    try:
        result = ch.fetch_url("https://example.test/x")
    finally:
        ch._http_get = original
    if not isinstance(result, tuple):
        errors.append(f"[G7] F1 fetch_url 契约：返回值应为 tuple，实际 {type(result).__name__}")
        return
    if len(result) != 2:
        errors.append(f"[G7] F1 fetch_url 契约破裂：应返回二元组，实际长度 {len(result)}")
    if not isinstance(result[0], int):
        errors.append(f"[G7] F1 fetch_url 契约：首元素应为 int 状态码，实际 {type(result[0]).__name__}")
    print(
        f"[G7] F1 fetch_url 二元组契约零回归通过：返回长度={len(result)}，"
        f"首元素类型={type(result[0]).__name__}"
    )


def validate_test_graph_wiring(errors: list) -> None:
    """G7 支撑断言（Task-6 收口）：确认 test_source_discovery.py 已挂入 ``test:graph``。

    [假安全感防线] Task-6 新建的 scripts/test_source_discovery.py 若未挂入 test:graph，
    则「写了门禁但没接线」，CI 中永不执行。此处以 package.json 文本断言钉死接线与**位置**
    （必须紧接 scripts/test_daily_loop.py 之后），使「移除接线」立即变红（变异自证④）。
    """
    pkg_file = ROOT_DIR / "package.json"
    if not pkg_file.is_file():
        errors.append(f"[G7] package.json 缺失：{pkg_file}")
        return
    try:
        scripts = json.loads(_read_text(pkg_file)).get("scripts", {})
    except json.JSONDecodeError as exc:
        errors.append(f"[G7] package.json 非法 JSON：{exc}")
        return

    graph = scripts.get("test:graph", "")
    if "scripts/test_source_discovery.py" not in graph:
        errors.append(
            "[G7] test:graph 未挂入 scripts/test_source_discovery.py"
            "（写了门禁却没接线 ⇒ CI 永不执行，属假安全感）"
        )
        return

    expected = "scripts/test_daily_loop.py && python -X utf8 scripts/test_source_discovery.py"
    if expected not in graph:
        errors.append(
            "[G7] test_source_discovery.py 未紧接 scripts/test_daily_loop.py 之后挂入 test:graph"
            f"（期望包含：{expected!r}）"
        )
        return
    print("[G7] test:graph 接线通过：test_source_discovery.py 紧接 test_daily_loop.py 之后已挂载")


# ---------------------------------------------------------------------------
# G9：草稿模板真实 MDX 编译 + 候选 PR 语义（B/C/D/E① 缺陷修复）
# ---------------------------------------------------------------------------
# 缺陷（均已实测确诊，见编排者物证）：
#   B  草稿模板用 HTML 注释 `<!-- -->` ⇒ MDX 非法，机器生成的草稿天生 pnpm build 必红；
#   C  候选 PR 提交了 scripts/.curate-ledger.json ⇒ 与 master 侧台账必然冲突（CONFLICTING）；
#   D  防重复守卫把「跳过」当成功返回 True ⇒ 每日取同一榜首候选 → 打印 ⏭️ → exit 0（绿灯假死）。

# 夹具候选：raw_desc 含 `<`、`{`、`}`、`` ` ``（外部抓取文本不可控），用于钉死
# 「抓取文本不得进 MDX / JSX 注释」这一约束。
_G9_FIXTURE_CANDIDATE = {
    "title": "G9 夹具：口服避孕药权威实况",
    "summary": "夹具摘要（严禁沿用来源描述）",
    "raw_desc": "抓取文本可能含 <b>标签</b>、{花括号}、`反引号`——严禁进入 MDX/JSX 注释",
    "category": "contraception",
    "tags": ["安全避孕", "避孕科普"],
    "source_url": "https://example.test/g9-fixture",
    "source_name": "WHO 夹具信源",
    "slug": "g9-fixture",
    "source_id": "who-facts-sheets",
    "evidence_tier": "A",
}

# node 编译探针：读入 .mdx，用指定 MDX 编译器真实编译，输出 JSON 结果（零网络）。
_MDX_COMPILE_PROBE = r"""
import { pathToFileURL } from 'node:url';
import { readFile } from 'node:fs/promises';

const modUrl = process.argv[2];
const mode = process.argv[3];
const mdxFile = process.argv[4];

let source;
try {
  source = await readFile(mdxFile, 'utf8');
} catch (err) {
  process.stdout.write(JSON.stringify({ ok: false, error: 'read-failed: ' + String(err) }));
  process.exit(0);
}

let fn;
try {
  const mod = await import(modUrl);
  fn = mode === 'mdx-js' ? mod.compile : mod.mdxToJs;
  if (typeof fn !== 'function') {
    process.stdout.write(JSON.stringify({ ok: false, error: 'compiler-export-missing: ' + mode }));
    process.exit(0);
  }
} catch (err) {
  process.stdout.write(JSON.stringify({ ok: false, error: 'import-failed: ' + String((err && err.message) || err) }));
  process.exit(0);
}

try {
  await fn(source);
  process.stdout.write(JSON.stringify({ ok: true }));
} catch (err) {
  process.stdout.write(JSON.stringify({ ok: false, error: String((err && err.message) || err) }));
}
"""


def _package_entry(pkg_dir: Path):
    """读取 package.json 的 exports['.'] / module / main，返回入口文件 Path（找不到返回 None）。"""
    pkg_json = pkg_dir / "package.json"
    if not pkg_json.is_file():
        return None
    try:
        meta = json.loads(_read_text(pkg_json))
    except (OSError, json.JSONDecodeError):
        return None
    entry = None
    exports = meta.get("exports")
    if isinstance(exports, dict):
        dot = exports.get(".")
        if isinstance(dot, str):
            entry = dot
        elif isinstance(dot, dict):
            entry = dot.get("import") or dot.get("default")
    if not isinstance(entry, str):
        entry = meta.get("module") or meta.get("main")
    if not isinstance(entry, str):
        return None
    entry_path = pkg_dir / entry
    return entry_path.resolve() if entry_path.is_file() else None


def _resolve_mdx_compiler() -> tuple:
    """定位可用 MDX 编译器，返回 (mode, module_file_url)；不可用返回 (None, "")。

    优先任务书指定的 ``@mdx-js/mdx``；本仓库实为 Astro 新工具链，``@mdx-js/mdx`` 未安装，
    退回 ``satteri``（Astro 本项目 MDX 引擎，node_modules 已有，零新增依赖）——其 parser 与
    CI 构建报错**逐字同源**（``mdx-jsx:unexpected-character``），故仍是真实 MDX 编译。
    """
    node_modules = ROOT_DIR / "node_modules"
    search = (
        ("mdx-js", "@mdx-js/mdx/package.json",
         ".pnpm/@mdx-js+mdx@*/node_modules/@mdx-js/mdx/package.json"),
        ("satteri", "satteri/package.json",
         ".pnpm/satteri@*/node_modules/satteri/package.json"),
    )
    for mode, *patterns in search:
        for pattern in patterns:
            for pkg_json in sorted(node_modules.glob(pattern)):
                entry = _package_entry(pkg_json.parent)
                if entry is not None:
                    return mode, entry.as_uri()
    return None, ""


def _run_mdx_compile(mdx_text: str) -> tuple:
    """用 node 对给定 MDX 文本做真实编译，返回 ``(ok, detail)``（零网络）。

    - ``ok`` 为 True/False 时，``detail`` 分别为空串 / 编译错误信息；
    - 编译器或 node 不可用时返回 ``(None, 原因)``，调用方据此**记明确错误**（不静默跳过）。
    """
    mode, mod_url = _resolve_mdx_compiler()
    if mode is None:
        return None, "未找到可用的 MDX 编译器（@mdx-js/mdx 与 satteri 均不在 node_modules）"
    node = shutil.which("node")
    if node is None:
        return None, "PATH 中未找到 node 可执行文件"
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        harness = tmp_dir / "mdx_compile_probe.mjs"
        harness.write_text(_MDX_COMPILE_PROBE, encoding="utf-8")
        target = tmp_dir / "candidate.mdx"
        target.write_text(mdx_text, encoding="utf-8")
        try:
            proc = subprocess.run(
                [node, str(harness), mod_url, mode, str(target)],
                capture_output=True, text=True, encoding="utf-8", timeout=90,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return None, f"node 编译探针执行失败：{exc}"
        if proc.returncode != 0:
            return None, f"node 编译探针非零退出（exit={proc.returncode}）：{proc.stderr.strip()[-400:]}"
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError:
            return None, f"node 编译探针输出非 JSON：{proc.stdout.strip()[-300:]}"
    return bool(payload.get("ok")), str(payload.get("error") or "")


class _FakeCompleted:
    """subprocess.CompletedProcess 的极简替身（仅暴露 returncode/stdout/stderr）。"""

    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _make_pr_subprocess_stub(
    recorded: list,
    existing_open_pr: bool,
    *,
    open_pr_branches=(),
    prefetch_ok: bool = True,
    push_fail_slugs=(),
    gh_create_fail: bool = False,
    status_dirty_fn=None,
    remote_exists_branches=(),
    ls_remote_fail_times: int = 0,
):
    """构造记录型 ``subprocess.run`` 替身：模拟 git/gh，零真实进程、零网络。

    - ``existing_open_pr``：**逐个候选** ``gh pr list --head`` 的返回（True ⇒ 已有 open PR）；
    - ``open_pr_branches``：**一次性** ``gh pr list --state open`` 预取返回的分支名集合；
    - ``prefetch_ok``：预取是否成功（False ⇒ 返回非零，触发逐候选 ``--head`` 回退）；
    - ``push_fail_slugs``：命中这些子串的分支 ``git push`` 返回非零（模拟 push 阶段失败）；
    - ``gh_create_fail``：``gh pr create`` 返回非零（模拟创建失败）；
    - ``status_dirty_fn``：可选回调，返回 True 时 ``git status --porcelain`` 报脏（模拟失败候选污染工作区）；
    - ``remote_exists_branches``：``git ls-remote --heads origin <branch>`` 返回非空输出的分支
      （模拟「远端已残留该分支，可能含人工提交」；[P0-1] 的默认空集 = 远端不存在 ⇒ 正常推送）；
    - ``ls_remote_fail_times``：前 N 次 ``git ls-remote`` 返回**非零**（模拟网络抖动），
      用于断言「重试 1 次后再 fail-closed」（单次抖动不得让整批候选被误判「远端已存在」而跳过）。
    遵守 ``check=True`` 语义：非零退出码时抛 ``CalledProcessError``（否则 push 重试/失败逻辑无法触发）。
    """
    occupied = {str(b) for b in (open_pr_branches or ())}
    remote_occupied = {str(b) for b in (remote_exists_branches or ())}
    ls_remote_state = {"calls": 0}

    def _complete(returncode, stdout="", stderr="", check=False, cmd=None):
        result = _FakeCompleted(returncode, stdout, stderr)
        if check and returncode != 0:
            raise subprocess.CalledProcessError(returncode, cmd or [], stdout, stderr)
        return result

    def fake_run(cmd, *args, **kwargs):
        recorded.append(list(cmd))
        check = bool(kwargs.get("check", False))
        head = list(cmd[:3])
        if head[:2] == ["git", "status"]:
            dirty = bool(status_dirty_fn()) if callable(status_dirty_fn) else False
            return _complete(0, " M some-dirty-file\n" if dirty else "", check=check, cmd=cmd)
        if head == ["git", "branch", "--show-current"]:
            return _complete(0, "master\n", check=check, cmd=cmd)
        if head[:2] == ["git", "ls-remote"]:
            ls_remote_state["calls"] += 1
            if ls_remote_state["calls"] <= ls_remote_fail_times:
                return _complete(1, "", "git: network jitter", check=check, cmd=cmd)
            branch = cmd[-1]
            if branch in remote_occupied:
                return _complete(
                    0, f"deadbeef1234567890\trefs/heads/{branch}\n", check=check, cmd=cmd
                )
            return _complete(0, "", check=check, cmd=cmd)
        if head[:3] == ["gh", "pr", "list"]:
            if "--head" in cmd:
                return _complete(
                    0, '[{"number": 1}]' if existing_open_pr else "[]", check=check, cmd=cmd
                )
            if not prefetch_ok:
                return _complete(1, "", "gh: network error", check=check, cmd=cmd)
            payload = [{"headRefName": b} for b in sorted(occupied)]
            return _complete(0, json.dumps(payload), check=check, cmd=cmd)
        if head[:3] == ["gh", "pr", "create"]:
            if gh_create_fail:
                return _complete(1, "", "gh: pr create failed", check=check, cmd=cmd)
            return _complete(0, "https://github.com/example/repo/pull/1\n", check=check, cmd=cmd)
        if head[:2] == ["git", "push"]:
            branch = cmd[-1]
            if any(s in branch for s in push_fail_slugs):
                return _complete(1, "", "! [rejected] non-fast-forward", check=check, cmd=cmd)
            return _complete(0, "", check=check, cmd=cmd)
        return _complete(0, "", check=check, cmd=cmd)

    return fake_run


@contextlib.contextmanager
def _stubbed_create_draft_pr_env(existing_open_pr: bool, **stub_kwargs):
    """在临时 ARTICLES_DIR/LEDGER_FILE + 记录型 subprocess 替身下运行候选 PR 逻辑。

    零真实 git/gh/subprocess、零网络、零 src/ 改动；退出时逐项还原，避免污染真实环境。
    ``stub_kwargs`` 透传给 ``_make_pr_subprocess_stub``（预取分支 / 失败注入等）。
    """
    recorded: list = []
    original_run = subprocess.run
    original_articles = ch.ARTICLES_DIR
    original_ledger = ch.LEDGER_FILE
    original_quiz = ch.QUIZ_FILE
    original_cache = getattr(ch, "_OPEN_CANDIDATE_BRANCHES", None)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        articles_dir = tmp_dir / "articles"
        articles_dir.mkdir(parents=True, exist_ok=True)
        ch.ARTICLES_DIR = str(articles_dir)
        ch.LEDGER_FILE = str(tmp_dir / ".curate-ledger.json")
        # [P0-3] create_draft_pr 会**真实写入** src/data/dailyQuiz.ts（注入速测题占位）。
        # 不重定向就会污染仓库真文件（G1 的 1:1 随即被破坏）⇒ 复制到 temp 后再注入。
        quiz_file = tmp_dir / "dailyQuiz.ts"
        try:
            quiz_file.write_text(_read_text(Path(original_quiz)), encoding="utf-8")
        except OSError:
            quiz_file.write_text("export const DAILY_QUIZZES = {};\n", encoding="utf-8")
        ch.QUIZ_FILE = str(quiz_file)
        if hasattr(ch, "_OPEN_CANDIDATE_BRANCHES"):
            ch._OPEN_CANDIDATE_BRANCHES = None
        subprocess.run = _make_pr_subprocess_stub(recorded, existing_open_pr, **stub_kwargs)
        try:
            yield recorded
        finally:
            subprocess.run = original_run
            ch.ARTICLES_DIR = original_articles
            ch.LEDGER_FILE = original_ledger
            ch.QUIZ_FILE = original_quiz
            if hasattr(ch, "_OPEN_CANDIDATE_BRANCHES"):
                ch._OPEN_CANDIDATE_BRANCHES = original_cache


def validate_g9_compose_template_mdx(errors: list) -> None:
    """G9 主断言①[B]：compose_mdx_content 输出必须是**可编译的真实 MDX**。

    - 廉价断言：输出不含 HTML 注释 `<!--`（MDX 不接受，pnpm build 必红）；
    - 廉价断言：抓取文本 raw_desc 不得出现在 MDX（外部文本不可控，应移入 PR 正文）；
    - 真实编译：用 node + 本项目 MDX 引擎对输出做真实编译（与 CI 报错同源）。
    """
    if not hasattr(ch, "compose_mdx_content"):
        errors.append("[G9] curate_harvester 缺少 compose_mdx_content()")
        return

    mdx = ch.compose_mdx_content(dict(_G9_FIXTURE_CANDIDATE))

    if "<!--" in mdx:
        errors.append(
            "[G9] 草稿模板含 HTML 注释 `<!--`（MDX 不接受，机器生成的草稿天生 pnpm build 必红）"
        )
    # [R5 修复] 非空守卫：若夹具 raw_desc 为空，下方「不得进 MDX」断言会**空转退化**（永真/永假皆不可信）。
    raw_desc = _G9_FIXTURE_CANDIDATE.get("raw_desc")
    if not raw_desc:
        errors.append(
            "[G9][R5] 夹具 raw_desc 不得为空——否则「raw_desc 不得进 MDX」守卫空转退化，失去判别力"
        )
    elif raw_desc in mdx:
        errors.append(
            "[G9] 抓取文本 raw_desc 泄漏进 MDX 草稿（外部文本不可控：含 `*/` 会提前闭合 JSX 注释、"
            "炸掉构建；应移入 PR 正文）"
        )

    ok, detail = _run_mdx_compile(mdx)
    if ok is None:
        errors.append(f"[G9] 无法执行真实 MDX 编译门禁：{detail}")
        return
    if not ok:
        errors.append(f"[G9] 草稿模板真实 MDX 编译失败（机器生成的草稿 pnpm build 会红）：{detail}")
        return
    print(
        "[G9] 草稿模板真实 MDX 编译通过（node + 本项目 MDX 引擎），"
        "且不含 `<!--`、无 raw_desc 泄漏"
    )


def validate_g9_reverse_bad_templates(errors: list) -> None:
    """G9 反向用例（MUST）：证明 MDX 编译门禁对三类模板的真实判别力。

    - 含 `<!--` 的模板 ⇒ 必须编译失败（即 B 缺陷形态，可判红）；
    - JSX 注释内含 `*/` 的抓取文本 ⇒ 必须编译失败（提前闭合注释，外部文本的真实隐患）；
    - 合法 JSX 注释模板 ⇒ 必须编译通过（正向对照，防门禁过严）。
    """
    bad_html = '---\ntitle: "x"\n---\n\n## H\n\n<!-- 坏注释 -->\n'
    ok_html, detail_html = _run_mdx_compile(bad_html)

    bad_star = '---\ntitle: "x"\n---\n\n## H\n\n{/* 抓取：a */ tail */}\n'
    ok_star, detail_star = _run_mdx_compile(bad_star)

    good_jsx = '---\ntitle: "x"\n---\n\n## H\n\n{/* 合法静态注释 */}\n\n正文。\n'
    ok_good, detail_good = _run_mdx_compile(good_jsx)

    if ok_html is not False:
        errors.append(
            "[G9] 反向用例失效：含 `<!--` 的 MDX 应编译失败（判红可判别 B 缺陷形态），"
            f"实际 {ok_html!r}（{detail_html}）"
        )
    if ok_star is not False:
        errors.append(
            "[G9] 反向用例失效：JSX 注释内含 `*/` 的抓取文本应编译失败（提前闭合注释），"
            f"实际 {ok_star!r}（{detail_star}）"
        )
    if ok_good is not True:
        errors.append(
            f"[G9] 正向对照失效：合法 JSX 注释模板应编译通过，实际 {ok_good!r}（{detail_good}）"
        )
    if ok_html is False and ok_star is False and ok_good is True:
        print(
            "[G9] 反向用例通过：`<!--` 判红；JSX 注释内 `*/` 抓取文本判红；合法 JSX 注释模板通过"
        )


def _run_create_draft_pr_stubbed(candidate: dict, existing_open_pr: bool) -> tuple:
    """在临时环境 + 记录型 subprocess 替身下运行真实 create_draft_pr，返回 (结果, 记录命令)。"""
    with _stubbed_create_draft_pr_env(existing_open_pr) as recorded:
        result = ch.create_draft_pr(candidate)
    return result, recorded


def validate_g9_create_draft_pr_contract(errors: list) -> None:
    """G9 主断言②[C/D]：候选分支不得携带台账，且返回值语义可区分。

    - [C] git add 只暂存草稿 .mdx，绝不暂存 scripts/.curate-ledger.json（否则必与 master 冲突）；
    - [D] 「已有待审 PR ⇒ 跳过」必须返回**可区分**的结果常量，禁止再用布尔 True 当成功。
    全程记录型 subprocess 替身 + 临时 ARTICLES_DIR/LEDGER_FILE：零真实 git/gh、零网络、零 src/ 改动。
    """
    required = ("create_draft_pr", "PR_RESULT_CREATED", "PR_RESULT_SKIPPED_DUPLICATE")
    missing = [name for name in required if not hasattr(ch, name)]
    if missing:
        errors.append(f"[G9] curate_harvester 缺少候选 PR 语义所需成员：{missing}")
        return

    if ch.PR_RESULT_CREATED == ch.PR_RESULT_SKIPPED_DUPLICATE:
        errors.append("[G9][D] PR_RESULT_CREATED 与 PR_RESULT_SKIPPED_DUPLICATE 必须不同")

    # [C] 无待审 PR ⇒ 走完整创建路径：断言 git add 只暂存 .mdx、不含台账
    created_result, created_cmds = _run_create_draft_pr_stubbed(
        dict(_G9_FIXTURE_CANDIDATE), existing_open_pr=False
    )
    if created_result != ch.PR_RESULT_CREATED:
        errors.append(
            f"[G9][C] 正常路径 create_draft_pr 应返回 PR_RESULT_CREATED，实际 {created_result!r}"
        )
    staged = [arg for cmd in created_cmds if cmd[:2] == ["git", "add"] for arg in cmd[2:]]
    if any("curate-ledger" in arg for arg in staged):
        errors.append(
            f"[G9][C] 候选分支携带机器状态台账（git add 含 .curate-ledger.json）：{staged}"
            "—— 与 master 侧台账必然冲突（PR 必 CONFLICTING）"
        )
    if not any(arg.endswith(".mdx") for arg in staged):
        errors.append(f"[G9][C] create_draft_pr 未把草稿 .mdx 纳入 git add：{staged}")

    # [R5 修复] 断言 raw_desc 确实**进入 PR 正文**（证明「移出 MDX」是移入 PR 描述，而非被丢弃）。
    pr_create = next((cmd for cmd in created_cmds if cmd[:3] == ["gh", "pr", "create"]), None)
    raw_desc = _G9_FIXTURE_CANDIDATE.get("raw_desc")
    if pr_create is None:
        errors.append("[G9][R5] 未捕获 gh pr create 调用，无法断言 raw_desc 进入 PR 正文")
    elif not raw_desc:
        errors.append("[G9][R5] 夹具 raw_desc 为空，PR 正文字断言会空转退化")
    else:
        try:
            body = pr_create[pr_create.index("--body") + 1]
        except (ValueError, IndexError):
            body = ""
        if raw_desc not in body:
            errors.append(
                "[G9][R5] raw_desc 未出现在 gh pr create 的 --body 中——"
                "「移出 MDX」必须改为「移入 PR 正文」，不得被静默丢弃"
            )

    # [D] 已有待审 PR ⇒ 必须返回可区分的「跳过」结果（不得是布尔 True）
    skip_result, _ = _run_create_draft_pr_stubbed(
        dict(_G9_FIXTURE_CANDIDATE), existing_open_pr=True
    )
    if isinstance(skip_result, bool) or skip_result != ch.PR_RESULT_SKIPPED_DUPLICATE:
        errors.append(
            "[G9][D] 已有待审 PR 时应返回可区分的 PR_RESULT_SKIPPED_DUPLICATE（非布尔成功），"
            f"实际 {skip_result!r}（用 True 当成功 ⇒ 跳过被判成功 ⇒ 连续多日零产出却全绿）"
        )

    print(
        f"[G9] create_draft_pr 契约通过：git add 仅暂存 {[a for a in staged if a.endswith('.mdx')]}；"
        f"跳过返回 {skip_result!r}、成功返回 {created_result!r}（语义可区分）"
    )


def validate_g9_zero_progress_visible(errors: list) -> None:
    """G9 主断言③[D/R4]：「积压」与「真故障」的日志与退出码必须**明确区分**。

    - 积压（全部候选均已有待审 PR）⇒ **exit 0** + `::warning::本日零进展：…均已有待审 PR…`，
      且**不得**出现 `::error::`（定时 Harvest 不得因积压每天变红）；
    - 真故障（创建 PR 出现 error）⇒ **exit 1** + `::error::`，措辞点名「故障」；
    - 混合批次（前两个跳过、第三个成功）⇒ 成功创建一个即停止，且不再尝试后续候选。
    """
    if not hasattr(ch, "run_create_pr"):
        errors.append(
            "[G9][D] curate_harvester 缺少 run_create_pr()（--create-pr 批次/零进展逻辑未实现）"
        )
        return

    candidates = [{**_G9_FIXTURE_CANDIDATE, "slug": f"g9-batch-{i}"} for i in range(1, 6)]
    occupied = [f"candidate/g9-batch-{i}" for i in range(1, 6)]

    # ① 积压：一次预取即全部占用（真实 create_draft_pr + 记录型 subprocess 替身）⇒ exit 0 + ::warning::
    with _stubbed_create_draft_pr_env(existing_open_pr=True, open_pr_branches=occupied):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code_backlog = ch.run_create_pr(candidates)
    printed_backlog = buffer.getvalue()
    if code_backlog != 0:
        errors.append(
            f"[G9][R4] 积压（全部候选均已有待审 PR）必须 exit 0（不得每日变红），实际 exit={code_backlog}"
        )
    if "本日零进展" not in printed_backlog:
        errors.append(f"[G9][R4] 积压未打印「本日零进展」标记行：{printed_backlog[-300:]!r}")
    if "::warning::本日零进展" not in printed_backlog:
        errors.append(
            f"[G9][R4] 积压未输出 ::warning::（Actions UI 不可见）：{printed_backlog[-300:]!r}"
        )
    if "均已有待审 PR" not in printed_backlog:
        errors.append(f"[G9][R4] 积压原因未点名「均已有待审 PR」：{printed_backlog[-300:]!r}")
    if "::error::" in printed_backlog:
        errors.append("[G9][R4] 积压不得使用 ::error::（须与真故障区分，否则每天变红）")

    # ② 真故障：全部候选创建失败（gh pr create 非零）⇒ exit 1 + ::error::
    with _stubbed_create_draft_pr_env(existing_open_pr=False, gh_create_fail=True):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code_fail = ch.run_create_pr(candidates)
    printed_fail = buffer.getvalue()
    if code_fail == 0:
        errors.append(f"[G9][R4] 真故障（创建 PR 全失败）必须 exit 1，实际 exit={code_fail}")
    if "::error::" not in printed_fail:
        errors.append(f"[G9][R4] 真故障未输出 ::error::：{printed_fail[-300:]!r}")
    if "故障" not in printed_fail:
        errors.append(f"[G9][R4] 真故障措辞未点名「故障」（与积压不可混同）：{printed_fail[-300:]!r}")

    # ③ 混合批次：替身控制 create_draft_pr 返回值，断言「成功一个即停」且跳过中间候选
    if not all(hasattr(ch, name) for name in ("PR_RESULT_CREATED", "PR_RESULT_SKIPPED_DUPLICATE")):
        print("[G9][D] 跳过混合批次断言：返回常量暂缺")
        return
    calls: list = []

    def fake_create(candidate):
        calls.append(candidate["slug"])
        if len(calls) < 3:
            return ch.PR_RESULT_SKIPPED_DUPLICATE
        return ch.PR_RESULT_CREATED

    original_create = ch.create_draft_pr
    ch.create_draft_pr = fake_create
    buffer = io.StringIO()
    try:
        with _stubbed_create_draft_pr_env(existing_open_pr=False):
            with contextlib.redirect_stdout(buffer):
                code_mixed = ch.run_create_pr(candidates)
    finally:
        ch.create_draft_pr = original_create
    if code_mixed != 0:
        errors.append(f"[G9][R4] 混合批次成功创建 1 个应返回 0，实际 exit={code_mixed}")
    if calls != ["g9-batch-1", "g9-batch-2", "g9-batch-3"]:
        errors.append(f"[G9][R4] 混合批次应在第 3 个候选成功即停止，实际调用序列 {calls}")

    if (
        code_backlog == 0
        and code_fail != 0
        and "::warning::本日零进展" in printed_backlog
        and "::error::" in printed_fail
        and calls == ["g9-batch-1", "g9-batch-2", "g9-batch-3"]
    ):
        print(
            "[G9][R4] 收尾语义通过：积压 ⇒ exit 0 + ::warning::；真故障 ⇒ exit 1 + ::error::（措辞分明）；"
            "混合批次成功一个即停"
        )


def validate_g9_branch_output_wiring(errors: list) -> None:
    """G9[R1]：``create_draft_pr`` 必须把新建分支名交给上层（``$GITHUB_OUTPUT`` + 返回值 ``.branch``）。

    成功 ⇒ 写 ``branch=candidate/<slug>`` 且 ``.branch`` 同值；
    跳过 ⇒ ``$GITHUB_OUTPUT`` 写**空** ``branch=`` 且 ``.branch`` 为空串（下游不得误以为有分支）。
    """
    if not hasattr(ch, "create_draft_pr") or not hasattr(ch, "_emit_step_output"):
        errors.append("[G9][R1] curate_harvester 缺少 create_draft_pr / _emit_step_output")
        return
    original_output = os.environ.get("GITHUB_OUTPUT")
    ok_text = skip_text = ""
    ok_branch = skip_branch = None
    try:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            out_ok = tmp_dir / "out_ok.txt"
            out_skip = tmp_dir / "out_skip.txt"
            os.environ["GITHUB_OUTPUT"] = str(out_ok)
            with _stubbed_create_draft_pr_env(existing_open_pr=False):
                with contextlib.redirect_stdout(io.StringIO()):
                    res_ok = ch.create_draft_pr(dict(_G9_FIXTURE_CANDIDATE))
            ok_text = out_ok.read_text(encoding="utf-8") if out_ok.exists() else ""
            ok_branch = getattr(res_ok, "branch", None)
            os.environ["GITHUB_OUTPUT"] = str(out_skip)
            with _stubbed_create_draft_pr_env(existing_open_pr=True):
                with contextlib.redirect_stdout(io.StringIO()):
                    res_skip = ch.create_draft_pr(dict(_G9_FIXTURE_CANDIDATE))
            skip_text = out_skip.read_text(encoding="utf-8") if out_skip.exists() else ""
            skip_branch = getattr(res_skip, "branch", None)
    finally:
        if original_output is None:
            os.environ.pop("GITHUB_OUTPUT", None)
        else:
            os.environ["GITHUB_OUTPUT"] = original_output

    expected = "candidate/g9-fixture"
    if f"branch={expected}" not in ok_text:
        errors.append(
            f"[G9][R1] 成功创建后未把分支名写入 $GITHUB_OUTPUT（期望 branch={expected}）：{ok_text!r}"
        )
    if ok_branch != expected:
        errors.append(f"[G9][R1] create_draft_pr 未通过返回值提供分支名 .branch：{ok_branch!r}")
    if skip_text.strip() != "branch=":
        errors.append(
            f"[G9][R1] 跳过时 $GITHUB_OUTPUT 必须写空 branch=（不得误报有分支）：{skip_text!r}"
        )
    if skip_branch not in ("", None):
        errors.append(f"[G9][R1] 跳过时 .branch 应为空串，实际 {skip_branch!r}")
    if "candidate/" in (skip_text or ""):
        errors.append("[G9][R1] 跳过路径不得让下游误以为有分支（$GITHUB_OUTPUT 出现 candidate/）")
    if f"branch={expected}" in ok_text and ok_branch == expected and skip_text.strip() == "branch=":
        print(
            f"[G9][R1] 分支输出接线通过：成功 ⇒ $GITHUB_OUTPUT branch={expected} 且 .branch 同值；"
            "跳过 ⇒ 空 branch=（不误报）"
        )


def validate_g9_failed_candidate_isolated(errors: list) -> None:
    """G9[R2]：一次失败的候选**不得**让后续候选因工作区脏而失败。

    - 断言 ``create_draft_pr`` **不再写入台账**（方案 A：移除已不持久化的台账写入）；
    - 首个候选在 push 阶段失败 ⇒ 第二个候选仍能被尝试并创建成功（工作区未被污染）；
    - 失败候选残留的未跟踪草稿 ``.mdx`` 已清理（否则拖垮后续候选入口预检）。
    """
    if not hasattr(ch, "run_create_pr"):
        errors.append("[G9][R2] curate_harvester 缺少 run_create_pr()")
        return
    candidates = [
        {**_G9_FIXTURE_CANDIDATE, "slug": "g9-fail-first"},
        {**_G9_FIXTURE_CANDIDATE, "slug": "g9-ok-second"},
    ]
    recorded: list = []
    ledger_calls: list = []
    original_run = subprocess.run
    original_save = ch.save_ledger
    original_articles = ch.ARTICLES_DIR
    original_ledger = ch.LEDGER_FILE
    original_quiz = ch.QUIZ_FILE
    original_cache = getattr(ch, "_OPEN_CANDIDATE_BRANCHES", None)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        articles_dir = tmp_dir / "articles"
        articles_dir.mkdir(parents=True, exist_ok=True)
        ch.ARTICLES_DIR = str(articles_dir)
        ch.LEDGER_FILE = str(tmp_dir / ".curate-ledger.json")
        # [P0-3] 速测题占位注入必须落在 temp 副本，不得污染仓库真文件
        quiz_file = tmp_dir / "dailyQuiz.ts"
        try:
            quiz_file.write_text(_read_text(Path(original_quiz)), encoding="utf-8")
        except OSError:
            quiz_file.write_text("export const DAILY_QUIZZES = {};\n", encoding="utf-8")
        ch.QUIZ_FILE = str(quiz_file)
        state = {"ledger_dirty": False}

        def _save_probe(ledger):
            ledger_calls.append(1)
            state["ledger_dirty"] = True

        def _status_dirty():
            # 台账被写坏 或 残留未跟踪草稿 ⇒ git status 报脏（模拟真实污染）
            return state["ledger_dirty"] or any(articles_dir.glob("*.mdx"))

        if hasattr(ch, "_OPEN_CANDIDATE_BRANCHES"):
            ch._OPEN_CANDIDATE_BRANCHES = None
        ch.save_ledger = _save_probe
        subprocess.run = _make_pr_subprocess_stub(
            recorded, False, push_fail_slugs=("g9-fail-first",), status_dirty_fn=_status_dirty
        )
        buffer = io.StringIO()
        try:
            with contextlib.redirect_stdout(buffer):
                code = ch.run_create_pr(candidates)
        finally:
            subprocess.run = original_run
            ch.save_ledger = original_save
            ch.ARTICLES_DIR = original_articles
            ch.LEDGER_FILE = original_ledger
            ch.QUIZ_FILE = original_quiz
            if hasattr(ch, "_OPEN_CANDIDATE_BRANCHES"):
                ch._OPEN_CANDIDATE_BRANCHES = original_cache
        printed = buffer.getvalue()
        leftover = sorted(p.name for p in articles_dir.glob("*.mdx"))
    attempted = [c[-1] for c in recorded if c[:3] == ["git", "checkout", "-b"]]

    if ledger_calls:
        errors.append(
            "[G9][R2] create_draft_pr 仍写入台账（save_ledger 被调用）——"
            "候选分支已不提交台账，该写入无价值且污染工作区，应移除（方案 A）"
        )
    if "candidate/g9-ok-second" not in attempted:
        errors.append(
            f"[G9][R2] 首个候选 push 失败后，第二个候选未被尝试（工作区被污染）：attempted={attempted}"
        )
    if code != 0:
        errors.append(
            f"[G9][R2] 首个候选失败不应拖垮后续：第二个候选应创建成功 ⇒ exit 0，"
            f"实际 {code}；输出尾部：{printed[-200:]!r}"
        )
    if leftover:
        errors.append(f"[G9][R2] 失败候选残留未跟踪草稿未清理：{leftover}")
    if not ledger_calls and "candidate/g9-ok-second" in attempted and code == 0 and not leftover:
        print(
            "[G9][R2] 失败候选隔离通过：create_draft_pr 不再写台账；首个候选 push 失败后"
            "第二个候选仍成功创建（exit 0）、无残留草稿"
        )


def validate_g9_prefetch_exclude(errors: list) -> None:
    """G9[R3]：``--create-pr`` 用**一次** ``gh`` 调用预取 open 候选分支并预排除被占用者；失败则回退。

    - ``PR_CANDIDATE_BATCH`` 已提高（仅限制发现开销，不再作为零进展判据）；
    - 预取成功 ⇒ 只对「首个未被占用」候选创建，且**不**逐个候选调用 ``gh pr list --head``；
    - 预取失败 ⇒ 打印告警并退回逐个候选 ``--head`` 检查（不崩，积压走 exit 0）。
    """
    batch = getattr(ch, "PR_CANDIDATE_BATCH", 0)
    if not isinstance(batch, int) or batch < 10:
        errors.append(f"[G9][R3] PR_CANDIDATE_BATCH 应提高（>=10，仅限制发现开销），实际 {batch!r}")
    if not hasattr(ch, "fetch_open_candidate_branches"):
        errors.append("[G9][R3] curate_harvester 缺少 fetch_open_candidate_branches()")
        return

    candidates = [{**_G9_FIXTURE_CANDIDATE, "slug": f"g9-r3-{i}"} for i in range(1, 4)]
    occupied = ["candidate/g9-r3-1", "candidate/g9-r3-2"]

    with _stubbed_create_draft_pr_env(existing_open_pr=True, open_pr_branches=occupied) as rec1:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = ch.run_create_pr(candidates)
    prefetch_calls = [c for c in rec1 if c[:3] == ["gh", "pr", "list"] and "--head" not in c]
    # 仅「逐个候选 `gh pr list --head`」才算逐候选检查；`gh pr create --head` 不算。
    head_calls = [c for c in rec1 if c[:3] == ["gh", "pr", "list"] and "--head" in c]
    created_branch = [c[-1] for c in rec1 if c[:3] == ["git", "checkout", "-b"]]

    if len(prefetch_calls) != 1:
        errors.append(
            f"[G9][R3] 应**恰好一次** `gh pr list --state open` 预取候选分支，实际 {len(prefetch_calls)} 次"
        )
    if head_calls:
        errors.append(
            f"[G9][R3] 预取成功后不应再逐个候选 --head 检查，实际 {len(head_calls)} 次：{head_calls[:1]}"
        )
    if created_branch != ["candidate/g9-r3-3"]:
        errors.append(
            f"[G9][R3] 应跳过被占用的前 2 个候选、只创建首个未被占用者（g9-r3-3），实际 {created_branch}"
        )
    if code != 0:
        errors.append(f"[G9][R3] 预排除后被占用前置候选不应阻断创建 ⇒ exit 0，实际 {code}")

    # 回退：预取失败 ⇒ 逐个候选 --head 检查（不崩）
    with _stubbed_create_draft_pr_env(existing_open_pr=True, prefetch_ok=False) as rec2:
        buffer2 = io.StringIO()
        with contextlib.redirect_stdout(buffer2):
            code2 = ch.run_create_pr(candidates)
    printed2 = buffer2.getvalue()
    head_calls2 = [c for c in rec2 if c[:3] == ["gh", "pr", "list"] and "--head" in c]
    if not head_calls2:
        errors.append("[G9][R3] 预取失败时应退回逐个候选 --head 检查，实际 0 次")
    if "退回" not in printed2:
        errors.append("[G9][R3] 预取失败应打印明确告警（含「退回」字样），不直接崩溃")
    if code2 != 0:
        errors.append(
            f"[G9][R3] 预取失败回退：全部候选已有待审 PR ⇒ 积压 exit 0，实际 exit={code2}"
        )
    if (
        len(prefetch_calls) == 1
        and not head_calls
        and created_branch == ["candidate/g9-r3-3"]
        and code == 0
        and head_calls2
        and "退回" in printed2
        and code2 == 0
    ):
        print(
            "[G9][R3] 预过滤通过：单次预取即排除 2 个被占用候选、只创建首个未被占用者；"
            "预取失败退回逐个 --head 检查（不崩，积压 exit 0）"
        )


# [黄卡-1] 机器占位标记：命中即说明「机器替人陈述内容已就绪」，属机器自证，禁止进库。
# **单一真值源**：一律引用 curate.py（门禁端）的 PLACEHOLDER_MARKERS。此前测试端另存一份字面量
# 副本 ⇒ 与门禁端必然漂移（本轮实证：模板 summary 的占位文本「待维护者人工提炼」门禁表缺失，
# 测试副本无感 ⇒ 维护者忘了 summary 时 curate:check 仍绿，占位描述直达读者）。
PLACEHOLDER_MARKERS = tuple(curate.PLACEHOLDER_MARKERS)


def _is_force_flag(arg) -> bool:
    """[P0-1] 判定一个 git 实参是否属于「强制推送族」。

    覆盖 ``--force`` / ``--force-with-lease`` / ``--force-if-includes`` 等长参，
    以及 ``-f`` 与其组合短参（``-uf`` / ``-fu``，git 允许短参合并书写）。
    """
    text = str(arg)
    if text.startswith("--force"):
        return True
    if text.startswith("-") and not text.startswith("--"):
        return "f" in set(text[1:])
    return False


def _drive_create_draft_pr(**stub_kwargs) -> tuple:
    """在**全打桩**环境里真实驱动一次 ``create_draft_pr``，返回 ``(result, calls, printed)``。

    ``calls`` 是打桩 ``subprocess.run`` 收到的每一次**真实实参**（按调用顺序），
    是行为断言的唯一物证来源：零真实 git、零真实 gh、零网络。
    """
    buffer = io.StringIO()
    with _stubbed_create_draft_pr_env(existing_open_pr=False, **stub_kwargs) as recorded:
        with contextlib.redirect_stdout(buffer):
            result = ch.create_draft_pr(dict(_G9_FIXTURE_CANDIDATE))
        calls = [list(cmd) for cmd in recorded]
    return result, calls, buffer.getvalue()


def validate_g9_no_force_overwrite(errors: list) -> None:
    """G9[P0-1]：候选分支**永不**强制覆盖远端（关闭 PR 后次日 force 推送会静默覆盖人工提交）。

    **本断言是行为级的，不是文本扫描**（历史教训：``inspect.getsource`` 里正则找 ``--force``
    会命中解释性注释中的字面量 ⇒ 注释里写个 ``--force*`` 就误判红、删掉注释就不判红，
    判别力完全取决于注释措辞，属脆弱门禁，已废弃）。

    行为断言的做法：打桩 ``subprocess.run`` 记录每一次真实实参，驱动一次完整的
    ``create_draft_pr``（远端不存在 ⇒ 真正走推送路径），据此断言：

    - 实际发出的**每条** ``git push`` 实参中都不出现任何 ``--force*`` / ``-f``；
    - 推送**之前**确实调用过 ``git ls-remote --heads origin <branch>``（守卫真执行了，非摆设）；
    - 反空转：正常路径必须观测到 >= 1 次 ``git push``，否则「零 force」退化成永真断言。

    另两条实测（同为行为级）：

    - ``ls-remote`` 返回非空 ⇒ 返回 ``PR_RESULT_SKIPPED_REMOTE_EXISTS``、**不推送**，
      且打印 ``::warning::`` 与**可执行的解锁指引**（``git push origin --delete <branch>``）；
    - 相互作用：``gh pr create`` 失败把分支留在远端，若不清理会被新守卫永久阻塞
      ⇒ 必须 best-effort 执行 ``git push origin --delete``。
    """
    required = (
        "create_draft_pr",
        "PR_RESULT_CREATED",
        "PR_RESULT_SKIPPED_DUPLICATE",
        "PR_RESULT_SKIPPED_REMOTE_EXISTS",
        "PR_RESULT_ERROR",
    )
    missing = [name for name in required if not hasattr(ch, name)]
    if missing:
        errors.append(f"[G9][P0-1] curate_harvester 缺少远端守卫所需成员：{missing}")
        return
    values = [getattr(ch, name) for name in required[1:]]
    if len(set(values)) != len(values):
        errors.append(f"[G9][P0-1] PR_RESULT_* 四个常量必须两两不同，实际 {values}")

    branch = "candidate/g9-fixture"
    ls_remote_cmd = ["git", "ls-remote", "--heads", "origin", branch]

    # —— 行为断言①：正常路径（远端不存在）⇒ 真实推送，且实参零 force ——
    result_ok, rec_ok, printed_ok = _drive_create_draft_pr()
    pushes_ok = [cmd for cmd in rec_ok if cmd[:2] == ["git", "push"]]
    force_hits = [(cmd, arg) for cmd in pushes_ok for arg in cmd if _is_force_flag(arg)]
    ls_remote_idx = next((i for i, c in enumerate(rec_ok) if c[:2] == ["git", "ls-remote"]), None)
    first_push_idx = next((i for i, c in enumerate(rec_ok) if c[:2] == ["git", "push"]), None)

    if force_hits:
        errors.append(
            "[G9][P0-1] 行为断言：实际执行的 git push 携带强制推送参数（会静默覆盖远端人工提交，"
            f"不可恢复）：{force_hits}"
        )
    if not pushes_ok:
        errors.append(
            "[G9][P0-1] 行为断言空转：正常路径未观测到任何 git push"
            "（「零 --force*」将退化为永真断言，失去判别力）："
            f"recorded={rec_ok}"
        )
    if ls_remote_cmd not in rec_ok:
        errors.append(
            "[G9][P0-1] 推送前未真实调用 `git ls-remote --heads origin <branch>`"
            "（存在性守卫未执行 ⇒ 残留分支会被静默覆盖）："
            f"实际 ls-remote 调用={[c for c in rec_ok if c[:2] == ['git', 'ls-remote']]}"
        )
    if (
        ls_remote_idx is not None
        and first_push_idx is not None
        and ls_remote_idx > first_push_idx
    ):
        errors.append(
            f"[G9][P0-1] ls-remote 探测发生在 push 之后（idx {ls_remote_idx} > {first_push_idx}）"
            "⇒ 守卫形同虚设，覆盖风险仍在"
        )
    if result_ok != ch.PR_RESULT_CREATED:
        errors.append(
            f"[G9][P0-1] 远端不存在时应正常创建并返回 PR_RESULT_CREATED，实际 {result_ok!r}"
            f"（输出尾部：{printed_ok[-200:]!r}）"
        )

    # —— 行为断言②：远端已存在 ⇒ 返回可区分的「已存在」常量、git push 从未被调用 ——
    result, rec_exists, printed = _drive_create_draft_pr(remote_exists_branches=(branch,))
    pushes = [cmd for cmd in rec_exists if cmd[:2] == ["git", "push"]]
    if result != ch.PR_RESULT_SKIPPED_REMOTE_EXISTS:
        errors.append(
            f"[G9][P0-1] 远端分支已存在时应返回 PR_RESULT_SKIPPED_REMOTE_EXISTS，实际 {result!r}"
        )
    if pushes:
        errors.append(f"[G9][P0-1] 远端分支已存在时仍执行了 git push（会覆盖人工提交）：{pushes}")
    if "::warning::" not in printed:
        errors.append(f"[G9][P0-1] 跳过未在 Actions UI 可见（缺 ::warning::）：{printed[-300:]!r}")
    if "git push origin --delete" not in printed:
        errors.append(
            f"[G9][P0-1] 跳过提示缺少**可执行**的解锁指引（git push origin --delete）：{printed[-300:]!r}"
        )
    if branch not in printed:
        errors.append(f"[G9][P0-1] 跳过提示未点名分支（维护者无从执行解锁）：{printed[-300:]!r}")

    # —— 行为断言③：相互作用 —— gh pr create 失败 ⇒ 分支已留在远端 ⇒ 必须 best-effort 删除
    _result2, rec2, _printed2 = _drive_create_draft_pr(gh_create_fail=True)
    deletes = [cmd for cmd in rec2 if cmd[:2] == ["git", "push"] and "--delete" in cmd]
    if not deletes:
        errors.append(
            "[G9][P0-1] gh pr create 失败后未 best-effort 删除远端残留分支"
            "（该候选会被新增的 ls-remote 守卫永久阻塞）"
        )

    # —— 静态守卫（行为断言的补强）——：行为断言只钉住「记录的实参」，若有绕过 subprocess
    # 记录的隐藏通道（os.system / shell=True）仍可真推。故生产模块源码**不得**出现二者。
    # 只扫生产模块（curate_harvester.py / curate.py），不扫本测试文件（本文件含二者字面量）。
    shell_backdoors = []
    for module_name in ("curate_harvester.py", "curate.py"):
        try:
            source = _read_text(SCRIPT_DIR / module_name)
        except OSError as exc:
            errors.append(f"[G9][P0-1] 无法读取生产模块 {module_name} 源码以做后门扫描：{exc}")
            continue
        for token in ("os.system(", "shell=True"):
            if token in source:
                shell_backdoors.append((module_name, token))
    if shell_backdoors:
        errors.append(
            f"[G9][P0-1] 生产模块存在绕过行为断言的隐藏执行通道 {shell_backdoors}"
            "（os.system / shell=True 可真推而不被 subprocess 打桩观测到）"
        )

    if (
        not missing
        and len(set(values)) == len(values)
        and not force_hits
        and bool(pushes_ok)
        and ls_remote_cmd in rec_ok
        and not (ls_remote_idx is not None and first_push_idx is not None and ls_remote_idx > first_push_idx)
        and result_ok == ch.PR_RESULT_CREATED
        and result == ch.PR_RESULT_SKIPPED_REMOTE_EXISTS
        and not pushes
        and "::warning::" in printed
        and "git push origin --delete" in printed
        and branch in printed
        and deletes
        and not shell_backdoors
    ):
        print(
            "[G9][P0-1] 远端守卫通过（**行为断言**，非文本扫描）："
            f"实际发出的 {len(pushes_ok)} 次 git push 实参零 --force*/-f（反空转：已观测到真实推送）；"
            f"推送前先执行 `git ls-remote --heads origin {branch}`；远端已存在 ⇒ 返回 "
            f"{result!r}、git push 从未被调用、并给出可删除指引；gh pr create 失败后 best-effort 删除远端分支；"
            "生产模块零 os.system( / shell=True 隐藏执行通道"
        )


def validate_g9_no_machine_self_attestation(errors: list) -> None:
    """G9[P0-2]：机器不得替人声明「已核验」/ 自评全站最高证据等级。

    - ``compose_mdx_content`` 产物**不得**含 ``last_verified_at`` / ``reviewed_by`` / ``evidence_tier``
      （省略后者以让 ``src/content.config.ts`` 的 schema default 成为唯一真值源）；
    - 占位防呆：任一既有 ``src/content/articles/*.mdx`` 命中机器占位标记 ⇒ 判红。
    """
    if not hasattr(ch, "compose_mdx_content"):
        errors.append("[G9][P0-2] curate_harvester 缺少 compose_mdx_content()")
        return

    mdx = ch.compose_mdx_content(dict(_G9_FIXTURE_CANDIDATE))
    for forbidden in ("last_verified_at", "reviewed_by"):
        if forbidden in mdx:
            errors.append(
                f"[G9][P0-2] 草稿模板仍由机器自填 `{forbidden}`"
                "（机器替人向读者声明「已核验」，踩中「机器不得自证」红线）"
            )
    if "evidence_tier" in mdx:
        errors.append(
            "[G9][P0-2] 草稿模板仍写入 evidence_tier（应省略以走 schema 默认 B；"
            "硬编码 A = 机器自评全站最高证据等级）"
        )

    hits = []
    for path in sorted(ARTICLES_DIR.glob("*.mdx")):
        text = _read_text(path)
        found = [m for m in PLACEHOLDER_MARKERS if m in text]
        if found:
            hits.append((path.name, found))
    if hits:
        errors.append(
            f"[G9][P0-2] 既有文章残留机器占位标记（线上已有占位内容，须人工补写后方可合并）：{hits}"
        )

    ok = (
        "last_verified_at" not in mdx
        and "reviewed_by" not in mdx
        and "evidence_tier" not in mdx
        and not hits
    )
    if ok:
        print(
            "[G9][P0-2] 机器不自证通过：草稿模板不含 last_verified_at / reviewed_by / evidence_tier"
            f"（证据等级交给 schema 默认）；{len(list(ARTICLES_DIR.glob('*.mdx')))} 篇既有文章零占位标记"
        )


def validate_g9_pr_path_quiz_placeholder(errors: list) -> None:
    """G9[P0-3]：每日 PR 路径必须与本地路径一样注入速测题占位，且**所有可见指引**都点名速测题。

    - ``create_draft_pr`` 必须调用 ``inject_quiz_placeholder`` 并把 ``dailyQuiz.ts`` 纳入 ``git add``；
    - 模板注释块 与 PR 正文 checklist 各须含一条「补全速测题占位」，且说明 G1 强制 1:1。
    """
    if not hasattr(ch, "create_draft_pr"):
        errors.append("[G9][P0-3] curate_harvester 缺少 create_draft_pr()")
        return

    mdx = ch.compose_mdx_content(dict(_G9_FIXTURE_CANDIDATE))
    if "速测题" not in mdx:
        errors.append(
            "[G9][P0-3] 草稿模板注释块缺少「补全速测题占位」指引"
            "（维护者照模板做完仍会红在 [G1] 且不知缺什么）"
        )
    if "1:1" not in mdx:
        errors.append("[G9][P0-3] 模板速测题指引未说明 G1 门禁强制文章↔速测题 1:1")

    with _stubbed_create_draft_pr_env(existing_open_pr=False) as recorded:
        with contextlib.redirect_stdout(io.StringIO()):
            result = ch.create_draft_pr(dict(_G9_FIXTURE_CANDIDATE))
        quiz_text = Path(ch.QUIZ_FILE).read_text(encoding="utf-8")
    staged = [arg for cmd in recorded if cmd[:2] == ["git", "add"] for arg in cmd[2:]]
    if not any(str(arg).endswith("dailyQuiz.ts") for arg in staged):
        errors.append(f"[G9][P0-3] create_draft_pr 未把 dailyQuiz.ts 纳入 git add：{staged}")
    if "articleId: 'g9-fixture'" not in quiz_text:
        errors.append(
            "[G9][P0-3] create_draft_pr 未注入速测题占位"
            "（候选分支内缺题 ⇒ [G1] 判定「文章缺少速测题」，PR 在分支内无法自洽）"
        )
    pr_create = next((cmd for cmd in recorded if cmd[:3] == ["gh", "pr", "create"]), None)
    body = ""
    if pr_create is not None and "--body" in pr_create:
        body = pr_create[pr_create.index("--body") + 1]
    if "速测题" not in body:
        errors.append("[G9][P0-3] PR 正文 checklist 缺少速测题条目（可见指引不完整 ⇒ 维护者无法变绿）")
    if "1:1" not in body:
        errors.append("[G9][P0-3] PR 正文速测题条目未说明 G1 门禁强制文章↔速测题 1:1")
    # [黄卡-5] 冲突化解指引：dailyQuiz.ts 的冲突只需「保留双方条目」（各条目按 articleId 独立），
    # 否则维护者按「二选一」的直觉解法删掉他人条目 ⇒ G1 的 1:1 被破坏、他人文章立刻没了题。
    if "冲突" not in body:
        errors.append(
            "[G9][P0-3][黄卡-5] PR 正文缺少「冲突化解」指引（多候选并行时 dailyQuiz.ts 必然冲突，"
            "维护者不知如何解 ⇒ 易误删他人条目）"
        )
    if "保留双方条目" not in body:
        errors.append(
            "[G9][P0-3][黄卡-5] PR 正文未点明「保留双方条目」（dailyQuiz.ts 冲突的正确解法；"
            "缺省会被理解成二选一 ⇒ 删他人条目即破 G1 的 1:1）"
        )

    ok = (
        "速测题" in mdx
        and "1:1" in mdx
        and any(str(arg).endswith("dailyQuiz.ts") for arg in staged)
        and "articleId: 'g9-fixture'" in quiz_text
        and "速测题" in body
        and "1:1" in body
        and "冲突" in body
        and "保留双方条目" in body
    )
    if ok:
        print(
            "[G9][P0-3] PR 路径速测题自洽通过：create_draft_pr 注入占位并把 dailyQuiz.ts 纳入提交"
            f"（结果 {result!r}）；模板与 PR 正文均点名「补全速测题」且说明 G1 强制 1:1；"
            "PR 正文含 dailyQuiz.ts 冲突化解指引（保留双方条目）"
        )


def validate_g9_draft_url_dedupe_before_write(errors: list) -> None:
    """G9[E1]：``--draft-url`` 的判重必须**前置到写盘之前**（不得先产出再判重）。

    同一 URL 连续两次执行 ⇒ 只产出 **1 个** ``.mdx`` + **1 条**速测题占位，第二次打印
    「已存在，未重复生成」并指向已存在文件；否则重复文章可借 G1 的对称性恒绿直接上线。
    """
    if not hasattr(ch, "run_draft_url"):
        errors.append("[G9][E1] curate_harvester 缺少 run_draft_url()")
        return

    url = "https://example.test/g9-dedupe-fixture"
    candidate = {**_G9_FIXTURE_CANDIDATE, "slug": "g9-dedupe", "source_url": url}
    original_build = ch._build_draft_candidate
    original_articles = ch.ARTICLES_DIR
    original_ledger = ch.LEDGER_FILE
    original_quiz = ch.QUIZ_FILE
    code1 = code2 = None
    printed1 = printed2 = ""
    count1 = count2 = 0
    quiz_text = ""
    try:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            articles_dir = tmp_dir / "articles"
            articles_dir.mkdir(parents=True, exist_ok=True)
            ch.ARTICLES_DIR = str(articles_dir)
            ch.LEDGER_FILE = str(tmp_dir / ".curate-ledger.json")
            quiz_file = tmp_dir / "dailyQuiz.ts"
            try:
                quiz_file.write_text(_read_text(Path(original_quiz)), encoding="utf-8")
            except OSError:
                quiz_file.write_text("export const DAILY_QUIZZES = {};\n", encoding="utf-8")
            ch.QUIZ_FILE = str(quiz_file)
            # 零网络：直接替换候选构造（真实实现会 fetch_url）
            ch._build_draft_candidate = lambda _url, _sources: dict(candidate)
            buffer1 = io.StringIO()
            with contextlib.redirect_stdout(buffer1):
                code1 = ch.run_draft_url(url)
            printed1 = buffer1.getvalue()
            count1 = len(list(articles_dir.glob("*.mdx")))
            buffer2 = io.StringIO()
            with contextlib.redirect_stdout(buffer2):
                code2 = ch.run_draft_url(url)
            printed2 = buffer2.getvalue()
            count2 = len(list(articles_dir.glob("*.mdx")))
            quiz_text = quiz_file.read_text(encoding="utf-8")
    finally:
        ch._build_draft_candidate = original_build
        ch.ARTICLES_DIR = original_articles
        ch.LEDGER_FILE = original_ledger
        ch.QUIZ_FILE = original_quiz

    entries = quiz_text.count("articleId: 'g9-dedupe'")
    if count1 != 1:
        errors.append(f"[G9][E1] 首次执行应产出 1 个 .mdx，实际 {count1}（输出：{printed1[-200:]!r}）")
    if count2 != 1:
        errors.append(
            f"[G9][E1] 同一 URL 二次执行后 .mdx 数应仍为 1，实际 {count2}"
            "（判重仍在写盘之后 ⇒ 重复文章可直接上线）"
        )
    if entries != 1:
        errors.append(f"[G9][E1] 速测题占位应只有 1 条，实际 {entries} 条（判重未前置 ⇒ 重复占位）")
    if "已存在" not in printed2 or "未重复生成" not in printed2:
        errors.append(
            f"[G9][E1] 二次执行未打印明确的「已存在，未重复生成」语义：{printed2[-300:]!r}"
        )
    if ".mdx" not in printed2:
        errors.append(f"[G9][E1] 二次执行未指向已存在的文件路径：{printed2[-300:]!r}")
    if code2 != 0:
        errors.append(f"[G9][E1] 二次执行（去重跳过）应 exit 0，实际 {code2}")

    if count1 == 1 and count2 == 1 and entries == 1 and "未重复生成" in printed2 and code2 == 0:
        print(
            "[G9][E1] 判重前置通过：同一 URL 二次执行只产出 1 个 .mdx / 1 条速测题占位，"
            f"第二次 exit={code2} 并打印「已存在，未重复生成」+ 既有文件路径"
        )


def validate_g9_remote_exists_is_backlog_not_failure(errors: list) -> None:
    """[红卡] ``PR_RESULT_SKIPPED_REMOTE_EXISTS`` 属「等待人工解锁」而非故障：exit 0 + ``::warning::``。

    实证缺陷：``run_create_pr`` 对该返回态**无任何分支处理** ⇒ 落入 ``failed += 1`` ⇒
    ``_report_failure`` ⇒ ``::error::`` + exit 1。只要存在「候选 PR 已关闭但分支未删」
    （现实已存在 ``candidate/contraception-oral-contraceptives``：PR #4 已关、#5 仍开）或
    ``ls-remote`` 单次网络抖动，定时任务就**每天红灯**，且措辞是误导性的「真故障（等待人工介入）」。

    断言（驱动真实 ``run_create_pr``，全部候选的 ls-remote 打桩返回非空）：

    - exit **0**、输出**不含** ``::error::``（不得每天红灯）；
    - 输出含 ``::warning::`` 且**点名两类原因**（待审 PR / 远端分支残留）与**解锁命令**
      ``git push origin --delete candidate/<slug>``；
    - 反空转：每个候选都被真实尝试（ls-remote 次数 == 候选数），且**零** ``git push``。
    """
    if not hasattr(ch, "run_create_pr") or not hasattr(ch, "PR_RESULT_SKIPPED_REMOTE_EXISTS"):
        errors.append(
            "[G9][红卡] curate_harvester 缺少 run_create_pr() / PR_RESULT_SKIPPED_REMOTE_EXISTS"
        )
        return

    slugs = [f"g9-remote-{i}" for i in range(1, 4)]
    candidates = [{**_G9_FIXTURE_CANDIDATE, "slug": slug} for slug in slugs]
    branches = [f"candidate/{slug}" for slug in slugs]

    # ① 全部候选远端分支均已残留 ⇒ 全部「等待人工」⇒ exit 0 + ::warning::
    with _stubbed_create_draft_pr_env(
        existing_open_pr=False, open_pr_branches=(), remote_exists_branches=branches
    ) as recorded:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = ch.run_create_pr(candidates)
    printed = buffer.getvalue()
    ls_remote_calls = [cmd for cmd in recorded if cmd[:2] == ["git", "ls-remote"]]
    pushes = [cmd for cmd in recorded if cmd[:2] == ["git", "push"]]

    if code != 0:
        errors.append(
            f"[G9][红卡] 远端分支已存在属「等待人工解锁」（非故障），必须 exit 0，实际 exit={code}"
            f"（输出尾部：{printed[-300:]!r}）"
        )
    if "::error::" in printed:
        errors.append(
            f"[G9][红卡] 远端分支已存在不得输出 ::error::（会让定时 Harvest 每天红灯）：{printed[-300:]!r}"
        )
    if "::warning::" not in printed:
        errors.append(f"[G9][红卡] 未输出 ::warning::（Actions UI 不可见）：{printed[-300:]!r}")
    if "git push origin --delete" not in printed:
        errors.append(
            f"[G9][红卡] 收尾文案未给出**解锁命令**（git push origin --delete）：{printed[-300:]!r}"
        )
    if not any(branch in printed for branch in branches):
        errors.append(f"[G9][红卡] 收尾文案未点名被阻塞的分支（维护者无从解锁）：{printed[-300:]!r}")
    if "远端" not in printed:
        errors.append(f"[G9][红卡] 收尾文案未点名「远端分支残留」这一原因：{printed[-300:]!r}")
    if "待审 PR" not in printed:
        errors.append(
            f"[G9][红卡] 收尾文案未点名「已有待审 PR」这一原因（两类成因须同时可辨）：{printed[-300:]!r}"
        )
    if len(ls_remote_calls) != len(branches):
        errors.append(
            f"[G9][红卡] 被远端守卫跳过后必须**继续尝试下一个候选**：ls-remote 调用 {len(ls_remote_calls)} 次，"
            f"候选 {len(branches)} 个"
        )
    if pushes:
        errors.append(f"[G9][红卡] 远端分支已存在时仍执行了 git push（会覆盖人工提交）：{pushes}")

    # ② 混合批次：首个候选被远端守卫跳过 ⇒ 继续并在第二个候选上真实创建成功（exit 0）
    with _stubbed_create_draft_pr_env(
        existing_open_pr=False, open_pr_branches=(), remote_exists_branches=[branches[0]]
    ) as recorded_mixed:
        buffer_mixed = io.StringIO()
        with contextlib.redirect_stdout(buffer_mixed):
            code_mixed = ch.run_create_pr(candidates)
    printed_mixed = buffer_mixed.getvalue()
    created_push = [
        cmd for cmd in recorded_mixed if cmd[:2] == ["git", "push"] and branches[1] in cmd
    ]
    if code_mixed != 0:
        errors.append(
            f"[G9][红卡] 首个候选被远端守卫跳过后应在第二个候选上成功创建并 exit 0，实际 {code_mixed}"
            f"（输出尾部：{printed_mixed[-300:]!r}）"
        )
    if not created_push:
        errors.append(
            f"[G9][红卡] 首个候选被跳过后未继续创建第二个候选（未观测到 {branches[1]} 的 push）："
            f"{[c for c in recorded_mixed if c[:2] == ['git', 'push']]}"
        )

    if (
        code == 0
        and "::error::" not in printed
        and "::warning::" in printed
        and "git push origin --delete" in printed
        and any(branch in printed for branch in branches)
        and "远端" in printed
        and "待审 PR" in printed
        and len(ls_remote_calls) == len(branches)
        and not pushes
        and code_mixed == 0
        and created_push
    ):
        print(
            "[G9][红卡] 远端残留 ⇒ 积压（非故障）通过：exit 0 + ::warning::、零 ::error::，"
            f"文案点名「待审 PR / 远端分支残留」两类成因并给出解锁命令；{len(ls_remote_calls)} 个候选"
            "全部被真实尝试（跳过后续继下一个）、零 git push；混合批次在第二个候选上真实创建成功"
        )


def validate_g9_placeholder_marker_covers_summary(errors: list) -> None:
    """[黄卡-1] 占位标记表必须**覆盖模板 summary 的真实占位文本**，且全仓只有**一份**真值源。

    实证缺陷：模板 summary 的占位文本是 ``【待维护者人工提炼】``，而标记表只收
    ``待人工提炼`` / ``待人工补题`` / ``TODO(human)`` ⇒ 维护者改完三条要点却忘了 summary 时
    ``curate:check`` **仍绿**，占位描述直达读者。测试端另存一份字面量副本更是必然漂移的温床。

    断言：

    - 真值源唯一：测试端 ``PLACEHOLDER_MARKERS`` == ``curate.PLACEHOLDER_MARKERS``；
    - 标记表含 ``待维护者人工提炼``（覆盖模板 summary 占位文本）；
    - 覆盖性（反空转）：``compose_mdx_content`` 的 summary 行必须命中标记表；
    - 行为实测：含该占位 summary 的 .mdx 经 ``curate.cmd_check`` 判红；占位改写后判绿。
    """
    if not hasattr(curate, "PLACEHOLDER_MARKERS"):
        errors.append("[G9][黄卡-1] curate.py 缺少 PLACEHOLDER_MARKERS（占位防呆无真值源）")
        return
    if not hasattr(ch, "compose_mdx_content"):
        errors.append("[G9][黄卡-1] curate_harvester 缺少 compose_mdx_content()")
        return

    markers = tuple(curate.PLACEHOLDER_MARKERS)
    if not markers:
        errors.append("[G9][黄卡-1] curate.PLACEHOLDER_MARKERS 为空 ⇒ 占位防呆整体空转退化")
        return
    if tuple(PLACEHOLDER_MARKERS) != markers:
        errors.append(
            "[G9][黄卡-1] 测试端 PLACEHOLDER_MARKERS 与 curate.py 不一致（两份副本必然漂移）："
            f"{tuple(PLACEHOLDER_MARKERS)} != {markers}"
        )
    if "待维护者人工提炼" not in markers:
        errors.append(
            f"[G9][黄卡-1] 标记表未收「待维护者人工提炼」——模板 summary 的占位文本正是它，"
            f"缺失 ⇒ 维护者忘了 summary 时 curate:check 仍绿（占位描述直达读者）：{markers}"
        )

    # 覆盖性：模板 summary 行必须命中标记表（否则标记表与模板漂移，防呆空转）
    mdx = ch.compose_mdx_content(dict(_G9_FIXTURE_CANDIDATE))
    summary_match = re.search(r'^summary:\s*"(.*)"\s*$', mdx, re.MULTILINE)
    summary = summary_match.group(1) if summary_match else ""
    if not summary:
        errors.append("[G9][黄卡-1] 无法从模板中解析 summary 行（覆盖性断言空转退化，失去判别力）")
    elif not any(marker in summary for marker in markers):
        errors.append(
            f"[G9][黄卡-1] 模板 summary 占位文本未命中任何占位标记 ⇒ 占位摘要可直达读者：{summary[:80]!r}"
        )

    # 行为实测：把模板草稿放进临时 ARTICLES_DIR，走真实 curate.cmd_check
    original_dir = curate.ARTICLES_DIR
    code_dirty = None
    code_clean = None
    out_dirty = ""
    out_clean = ""
    try:
        with tempfile.TemporaryDirectory() as tmp:
            articles = Path(tmp) / "articles"
            articles.mkdir(parents=True, exist_ok=True)
            curate.ARTICLES_DIR = str(articles)

            (articles / "g9-placeholder.mdx").write_text(mdx, encoding="utf-8")
            buffer_dirty = io.StringIO()
            with contextlib.redirect_stdout(buffer_dirty):
                try:
                    curate.cmd_check(argparse.Namespace(allow_machine_draft=False))
                    code_dirty = 0
                except SystemExit as exc:
                    code_dirty = exc.code
            out_dirty = buffer_dirty.getvalue()

            # 反向对照（反空转）：占位全部改写为人工内容 ⇒ 不得判红
            (articles / "g9-placeholder.mdx").unlink()
            clean_text = mdx.replace("【待维护者人工提炼】", "")
            for marker in markers:
                clean_text = clean_text.replace(marker, "人工已提炼")
            (articles / "g9-clean.mdx").write_text(clean_text, encoding="utf-8")
            buffer_clean = io.StringIO()
            with contextlib.redirect_stdout(buffer_clean):
                try:
                    curate.cmd_check(argparse.Namespace(allow_machine_draft=False))
                    code_clean = 0
                except SystemExit as exc:
                    code_clean = exc.code
            out_clean = buffer_clean.getvalue()
    finally:
        curate.ARTICLES_DIR = original_dir

    if code_dirty == 0:
        errors.append(
            f"[G9][黄卡-1] 含占位 summary（【待维护者人工提炼】）的草稿经 curate:check 竟判绿"
            f"（占位描述会直达读者）：{out_dirty[-300:]!r}"
        )
    if code_dirty is not None and code_dirty != 1:
        errors.append(f"[G9][黄卡-1] 占位草稿判红时退出码应为 1，实际 {code_dirty}")
    if "❌" not in out_dirty:
        errors.append(f"[G9][黄卡-1] 占位草稿判红未打印 ❌ 原因行：{out_dirty[-300:]!r}")
    if code_clean != 0:
        errors.append(
            f"[G9][黄卡-1] 占位已人工改写后仍判红（门禁过严 / 误伤）：{out_clean[-300:]!r}"
        )

    if (
        "待维护者人工提炼" in markers
        and summary
        and any(marker in summary for marker in markers)
        and code_dirty == 1
        and "❌" in out_dirty
        and code_clean == 0
    ):
        print(
            "[G9][黄卡-1] 占位标记单一真值源通过：测试端引用 curate.PLACEHOLDER_MARKERS（零副本漂移）；"
            f"标记表{len(markers)} 项覆盖模板 summary 占位文本；含占位 summary 的草稿经 curate.cmd_check "
            f"判红（exit 1），人工改写后判绿（反空转）"
        )


def validate_g9_quiz_restore_prints_warning(errors: list) -> None:
    """[黄卡-2] 还原 ``dailyQuiz.ts`` 失败时**必须打印明确告警**（禁止 ``except OSError: pass`` 静默吞异常）。

    实证缺陷：``create_draft_pr`` 的 ``finally`` 里 ``except OSError: pass`` ⇒ 还原失败静默，
    速测题占位的改动留在工作区而无人知晓，批次内**后续候选**会因入口预检「工作区脏」直接判 ERROR
    （现象是后续候选报错，根因却在上一候选，无从排查）。

    断言：打桩令该文件的 ``write_text`` 抛 ``OSError`` ⇒ 输出含告警（⚠️ + 还原/速测题 + 工作区提示）。
    """
    if not hasattr(ch, "create_draft_pr"):
        errors.append("[G9][黄卡-2] curate_harvester 缺少 create_draft_pr()")
        return

    original_path = ch.Path
    # 必须继承**具体** flavour 类（WindowsPath / PosixPath）：直接继承 pathlib.Path 会因
    # 缺失 ``_flavour`` 而在实例化时炸掉（pathlib.Path 本身不带 flavour）。
    concrete_path_cls = type(original_path("."))

    class _WriteFailPath(concrete_path_cls):  # type: ignore[misc, valid-type]
        """仅在写入 ``dailyQuiz.ts`` 时抛 OSError，其余行为与 pathlib.Path 完全一致。"""

        def write_text(self, *args, **kwargs):
            if self.name == "dailyQuiz.ts":
                raise OSError("simulated write failure")
            return super().write_text(*args, **kwargs)

    buffer = io.StringIO()
    try:
        ch.Path = _WriteFailPath
        with _stubbed_create_draft_pr_env(existing_open_pr=False):
            with contextlib.redirect_stdout(buffer):
                ch.create_draft_pr(dict(_G9_FIXTURE_CANDIDATE))
    finally:
        ch.Path = original_path
    printed = buffer.getvalue()

    if "⚠️" not in printed:
        errors.append(
            f"[G9][黄卡-2] 还原 dailyQuiz.ts 失败时未打印告警（异常被静默吞掉）：{printed[-400:]!r}"
        )
    if "还原" not in printed:
        errors.append(
            f"[G9][黄卡-2] 告警未点名「还原」这一动作（维护者无从知晓备份未写回）：{printed[-400:]!r}"
        )
    if "dailyQuiz" not in printed:
        errors.append(
            f"[G9][黄卡-2] 告警未点名 dailyQuiz.ts 这一文件：{printed[-400:]!r}"
        )
    if "工作区" not in printed:
        errors.append(
            f"[G9][黄卡-2] 告警未提示「后续候选可能因工作区脏而报错」（根因不可见）：{printed[-400:]!r}"
        )

    if "⚠️" in printed and "还原" in printed and "dailyQuiz" in printed and "工作区" in printed:
        print(
            "[G9][黄卡-2] 还原失败告警通过：dailyQuiz.ts 写回抛 OSError 时打印明确告警"
            "（点名还原动作 / 文件名 / 工作区脏会让后续候选报错），异常不再被静默吞掉"
        )


def validate_g9_ls_remote_retry_then_fail_closed(errors: list) -> None:
    """[黄卡-3] ``git ls-remote`` 必须**重试 1 次**后再 fail-closed（单次网络抖动不得整批误跳过）。

    实证缺陷：探测只做一次 ⇒ 单次抖动即按 fail-closed 判「远端已存在」⇒ 整批候选被误跳过
    （且与红卡叠加时表现为每日红灯）。

    断言：

    - 首次失败、重试成功且分支**不存在** ⇒ 正常创建（不得误跳过）；
    - 两次均失败 ⇒ 仍 fail-closed（返回 ``PR_RESULT_SKIPPED_REMOTE_EXISTS``）。
    """
    if not hasattr(ch, "create_draft_pr") or not hasattr(ch, "PR_RESULT_SKIPPED_REMOTE_EXISTS"):
        errors.append(
            "[G9][黄卡-3] curate_harvester 缺少 create_draft_pr() / PR_RESULT_SKIPPED_REMOTE_EXISTS"
        )
        return

    branch = "candidate/g9-fixture"

    # ① 首次抖动、重试成功（远端无该分支）⇒ 正常创建，ls-remote 共 2 次
    result_recovered, calls_recovered, printed_recovered = _drive_create_draft_pr(
        ls_remote_fail_times=1
    )
    ls_remote_recovered = [cmd for cmd in calls_recovered if cmd[:2] == ["git", "ls-remote"]]
    pushes_recovered = [cmd for cmd in calls_recovered if cmd[:2] == ["git", "push"]]
    if len(ls_remote_recovered) != 2:
        errors.append(
            f"[G9][黄卡-3] ls-remote 首次失败后应重试 1 次（共 2 次），实际 {len(ls_remote_recovered)} 次"
            f"（单次抖动 ⇒ 整批误跳过）：{ls_remote_recovered}"
        )
    if result_recovered != ch.PR_RESULT_CREATED:
        errors.append(
            f"[G9][黄卡-3] 抖动后重试成功且远端无分支时应正常创建，实际 {result_recovered!r}"
            f"（输出尾部：{printed_recovered[-300:]!r}）"
        )
    if not pushes_recovered:
        errors.append(
            f"[G9][黄卡-3] 重试成功后应继续正常推送，实际未观测到 git push：{calls_recovered}"
        )

    # ② 两次均失败 ⇒ fail-closed（跳过、不推送）
    result_failed, calls_failed, printed_failed = _drive_create_draft_pr(ls_remote_fail_times=2)
    ls_remote_failed = [cmd for cmd in calls_failed if cmd[:2] == ["git", "ls-remote"]]
    pushes_failed = [cmd for cmd in calls_failed if cmd[:2] == ["git", "push"]]
    if len(ls_remote_failed) != 2:
        errors.append(
            f"[G9][黄卡-3] ls-remote 失败两次的场景应只重试 1 次（共 2 次），实际 {len(ls_remote_failed)} 次"
        )
    if result_failed != ch.PR_RESULT_SKIPPED_REMOTE_EXISTS:
        errors.append(
            f"[G9][黄卡-3] ls-remote 连续失败应 fail-closed 返回 PR_RESULT_SKIPPED_REMOTE_EXISTS，"
            f"实际 {result_failed!r}（输出尾部：{printed_failed[-300:]!r}）"
        )
    if pushes_failed:
        errors.append(
            f"[G9][黄卡-3] ls-remote 连续失败时不得推送（fail-closed 被反转）：{pushes_failed}"
        )

    if (
        len(ls_remote_recovered) == 2
        and result_recovered == ch.PR_RESULT_CREATED
        and pushes_recovered
        and len(ls_remote_failed) == 2
        and result_failed == ch.PR_RESULT_SKIPPED_REMOTE_EXISTS
        and not pushes_failed
    ):
        print(
            "[G9][黄卡-3] ls-remote 重试通过：首次抖动后重试 1 次（共 2 次）⇒ 远端无分支则正常创建并推送"
            "（不再被单次抖动整批误跳过）；连续失败仍 fail-closed ⇒ "
            f"{result_failed!r}、零推送；守卫分支 {branch}"
        )


def validate_g9_empty_pool_error(errors: list) -> None:
    """G9[R4]：候选池为空 ⇒ 真故障 ⇒ ``main()`` exit 1 + ``::error::``（不得静默 exit 0 假绿）。"""
    if not hasattr(ch, "main"):
        errors.append("[G9][R4] curate_harvester 缺少 main()")
        return
    original_harvest = ch.harvest_candidates
    original_argv = list(sys.argv)
    buffer = io.StringIO()
    code = 0
    ch.harvest_candidates = lambda **kwargs: []
    sys.argv = ["curate_harvester.py", "--create-pr"]
    try:
        with contextlib.redirect_stdout(buffer):
            try:
                ch.main()
            except SystemExit as exc:
                code = exc.code if isinstance(exc.code, int) else 1
    finally:
        ch.harvest_candidates = original_harvest
        sys.argv = original_argv
    printed = buffer.getvalue()
    if code != 1:
        errors.append(f"[G9][R4] 候选池为空必须 exit 1（真故障），实际 exit={code}")
    if "::error::" not in printed:
        errors.append(f"[G9][R4] 候选池为空未输出 ::error::：{printed[-200:]!r}")
    if "故障" not in printed:
        errors.append(f"[G9][R4] 候选池为空措辞未点名「故障」：{printed[-200:]!r}")
    if code == 1 and "::error::" in printed and "故障" in printed:
        print("[G9][R4] 空池收尾通过：exit 1 + ::error::（真故障，不得静默假绿）")


def validate_g9_workflow_selfcheck_wiring(errors: list) -> None:
    """G9[R1]：工作流自检步骤必须**检出候选分支**再编译草稿，且措辞不得假绿。

    - create-pr 步骤须有 ``id``，并把 ``branch`` 通过 ``outputs`` 暴露；
    - 自检步骤须读取 ``steps.<id>.outputs.branch``、非空时 ``git fetch``+``checkout`` 该分支、
      断言草稿文件确实存在；
    - 无分支时须写明「本次未创建新分支，跳过草稿构建自检」，且**删除**「对当前分支草稿编译」的假绿陈述。
    """
    workflow = ROOT_DIR / ".github" / "workflows" / "harvest-candidates.yml"
    if not workflow.is_file():
        errors.append(f"[G9][R1] 工作流文件缺失：{workflow}")
        return
    text = _read_text(workflow)
    if "id: create_pr" not in text:
        errors.append("[G9][R1] create-pr 步骤缺少 id: create_pr，outputs 无法接线")
    if "steps.create_pr.outputs.branch" not in text:
        errors.append("[G9][R1] 自检步骤未读取 steps.create_pr.outputs.branch")
    if "git fetch origin" not in text:
        errors.append("[G9][R1] 自检步骤未 git fetch 候选分支")
    if "git checkout" not in text:
        errors.append("[G9][R1] 自检步骤未 git checkout 候选分支")
    if "test -f" not in text and "! -f" not in text:
        errors.append("[G9][R1] 自检步骤未断言草稿文件确实存在（test -f / [ ! -f ]）")
    if "本次未创建新分支，跳过草稿构建自检" not in text:
        errors.append("[G9][R1] 无分支时未写明「本次未创建新分支，跳过草稿构建自检」")
    if "已对当前分支的草稿做真实 MDX 编译" in text:
        errors.append("[G9][R1] 残留假绿陈述：「已对当前分支的草稿做真实 MDX 编译」（实际编译的是 master）")
    if "candidate/" not in text:
        errors.append("[G9][R1] 自检步骤未从 branch 推导 slug（candidate/ 前缀）")
    if (
        "id: create_pr" in text
        and "steps.create_pr.outputs.branch" in text
        and "git fetch origin" in text
        and "git checkout" in text
        and "test -f" in text
        and "本次未创建新分支，跳过草稿构建自检" in text
        and "已对当前分支的草稿做真实 MDX 编译" not in text
        and "candidate/" in text
    ):
        print(
            "[G9][R1] 工作流自检接线通过：id/outputs 已接、按 branch 检出、断言草稿存在、"
            "无分支如实跳过且无假绿陈述"
        )


# ---------------------------------------------------------------------------
# [P1 批次] 三条 P1 的可判红断言（详见各 validate_p1_* 的 docstring）
# ---------------------------------------------------------------------------

# 台账夹具：同一个 URL 以 pending 身份登记（= 维护者起草中或已放弃）。
_P1_PENDING_URL = "https://example.test/p1-pending-topic"
_P1_PUBLISHED_URL = "https://example.test/p1-published-topic"
_P1_REJECTED_URL = "https://example.test/p1-rejected-topic"


def _p1_pending_ledger() -> dict:
    """构造含 pending / published / rejected 三态的台账夹具（纯内存，不触碰真实台账）。"""
    return {
        "version": 2,
        "last_updated": "2026-09-27T00:00:00+00:00",
        "processed_urls": [
            {
                "url": _P1_PENDING_URL,
                "status": "pending",
                "source_id": "p1-fixture",
                "first_seen": "2026-09-27",
                "last_probed": "2026-09-27",
                "http_status": 200,
            },
            {
                "url": _P1_PUBLISHED_URL,
                "status": "published",
                "source_id": "p1-fixture",
                "first_seen": "2026-09-20",
                "last_probed": "2026-09-26",
                "http_status": 200,
            },
            {
                "url": _P1_REJECTED_URL,
                "status": "rejected",
                "source_id": "p1-fixture",
                "first_seen": "2026-09-18",
                "last_probed": "2026-09-25",
                "http_status": 200,
            },
        ],
    }


def _p1_drive_collect_pool(ledger: dict, discovered: list) -> tuple:
    """在**全打桩**环境驱动一次 ``collect_pool_candidates``，返回 ``(pool, save_ledger_calls)``。

    零真实网络（``discover_candidates`` 打桩）、零真实台账写盘（``load_ledger`` 返回夹具、
    ``save_ledger`` 只记账）、``finally`` 逐项还原。
    """
    original_ledger = ch.LEDGER_FILE
    original_sources = ch.SOURCES_FILE
    original_articles = ch.ARTICLES_DIR
    original_load = ch.load_ledger
    original_save = ch.save_ledger
    original_discover = ch.discover_candidates
    original_existing = ch.get_existing_article_urls
    saved_calls: list = []
    try:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            sources_file = tmp_dir / "sources.json"
            sources_file.write_text(
                json.dumps(
                    [
                        {
                            "id": "p1-fixture",
                            "name": "P1 夹具信源",
                            "base_url": "https://example.test",
                            "default_category": "body",
                        }
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            articles_dir = tmp_dir / "articles"
            articles_dir.mkdir(parents=True, exist_ok=True)

            def fake_discover(_src, seen_urls):
                return [(url, f"标题-{url}") for url in discovered if url not in seen_urls]

            ch.LEDGER_FILE = str(tmp_dir / ".curate-ledger.json")
            ch.SOURCES_FILE = str(sources_file)
            ch.ARTICLES_DIR = str(articles_dir)
            ch.load_ledger = lambda: ledger
            ch.save_ledger = lambda data: saved_calls.append(data)
            ch.discover_candidates = fake_discover
            ch.get_existing_article_urls = lambda: set()
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                pool = ch.collect_pool_candidates()
    finally:
        ch.LEDGER_FILE = original_ledger
        ch.SOURCES_FILE = original_sources
        ch.ARTICLES_DIR = original_articles
        ch.load_ledger = original_load
        ch.save_ledger = original_save
        ch.discover_candidates = original_discover
        ch.get_existing_article_urls = original_existing
    return pool, saved_calls


def validate_p1_pending_visible_in_pool(errors: list) -> None:
    """[P1-1] 台账 ``pending`` **必须在 ``--pool`` 里仍可见**，但仍被 ``harvest_candidates`` 排除。

    实证缺陷：``ledger_seen_urls`` 三种状态全收，且 ``collect_pool_candidates``（人的视图）与
    ``harvest_candidates``（机器的视图）**都**用它 ⇒ 维护者登记过一个 pending 后，即便决定这个
    选题不好、不做了，该 URL 也**永久**不再出现在 ``--pool`` 里，只能手工编辑
    ``scripts/.curate-ledger.json`` 恢复（而该文件的存在从未在输出中告知）。

    断言（两个消费方口径必须分离，且意图显式）：
      - ``ledger_seen_urls(ledger, exclude_pending=True)``（--pool 口径）**不含** pending URL；
      - ``ledger_seen_urls(ledger, exclude_pending=False)``（harvest 口径）**含** pending URL；
      - ``collect_pool_candidates`` 在 pending 台账下**仍返回** pending 候选；
      - ``--pool`` 仍零副作用（本路径不得出现任何 ``save_ledger`` 调用）。
    """
    if not hasattr(ch, "ledger_seen_urls"):
        errors.append("[P1-1] curate_harvester 缺少 ledger_seen_urls()")
        return

    import inspect as _inspect

    try:
        params = _inspect.signature(ch.ledger_seen_urls).parameters
    except (TypeError, ValueError):
        params = {}
    if "exclude_pending" not in params:
        errors.append(
            "[P1-1] ledger_seen_urls 必须提供显式参数 exclude_pending（两个消费方口径分离，"
            "不得靠调用方隐式约定）"
        )
        return

    ledger = _p1_pending_ledger()
    human_view = ch.ledger_seen_urls(ledger, exclude_pending=True)
    machine_view = ch.ledger_seen_urls(ledger, exclude_pending=False)

    if _P1_PENDING_URL in human_view:
        errors.append(
            "[P1-1] --pool 口径（exclude_pending=True）仍把 pending 计入已见 ⇒ "
            "维护者起草中/已放弃的选题会永久从候选池消失"
        )
    if _P1_PENDING_URL not in machine_view:
        errors.append(
            "[P1-1] harvest 口径（exclude_pending=False）必须仍把 pending 计入已见 ⇒ "
            "会对「正在起草中」的选题重复开 PR"
        )
    if _P1_PUBLISHED_URL not in human_view or _P1_REJECTED_URL not in human_view:
        errors.append(
            "[P1-1] exclude_pending=True 只能排除 pending，published / rejected 必须仍计入已见："
            f"{sorted(human_view)}"
        )

    # 行为级：--pool 实际候选收集路径仍返回 pending 候选，且零副作用。
    pool, saved_calls = _p1_drive_collect_pool(ledger, [_P1_PENDING_URL])
    pool_urls = [c.get("url") for c in pool]
    if _P1_PENDING_URL not in pool_urls:
        errors.append(
            f"[P1-1] --pool 候选收集未返回 pending 候选（维护者再也看不到自己登记的选题）："
            f"实际返回 {pool_urls}"
        )
    if saved_calls:
        errors.append(f"[P1-1] --pool 出现台账写副作用（严禁 save_ledger）：{len(saved_calls)} 次")

    if (
        _P1_PENDING_URL not in human_view
        and _P1_PENDING_URL in machine_view
        and _P1_PENDING_URL in pool_urls
        and not saved_calls
    ):
        print(
            "[P1-1] pending 可见性分口径通过：--pool 口径排除 pending（候选仍可见，pool_urls="
            f"{pool_urls}），harvest 口径保留 pending（不重复开 PR）；--pool 零 save_ledger 调用"
        )


# 四种注入失败场景的 dailyQuiz.ts 内容（缺 DAILY_QUIZZES / 花括号不配平 / 无对象起始花括号）。
_P1_QUIZ_NO_MARKER = "export interface QuizItem {\n  articleId: string;\n}\n"
_P1_QUIZ_UNBALANCED = (
    "export const DAILY_QUIZZES: Record<string, QuizItem> = {\n"
    "  'existing-slug': {\n"
    "    articleId: 'existing-slug',\n"
)
_P1_QUIZ_NO_OPEN_BRACE = "export const DAILY_QUIZZES: string = 'oops-no-brace';\n"


def _p1_drive_run_draft_url(quiz_text, make_quiz: bool = True) -> tuple:
    """在 tempfile 沙箱内驱动一次 ``run_draft_url``，返回 ``(exit_code, printed)``。

    零真实网络（``_build_draft_candidate`` 打桩）、零真实台账/文章/速测题改动，``finally`` 还原。
    """
    original_build = ch._build_draft_candidate
    original_articles = ch.ARTICLES_DIR
    original_ledger = ch.LEDGER_FILE
    original_quiz = ch.QUIZ_FILE
    candidate = {**_G9_FIXTURE_CANDIDATE, "slug": "p1-inject", "source_url": "https://example.test/p1"}
    try:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            articles_dir = tmp_dir / "articles"
            articles_dir.mkdir(parents=True, exist_ok=True)
            quiz_file = tmp_dir / "dailyQuiz.ts"
            if make_quiz:
                quiz_file.write_text(
                    _read_text(Path(original_quiz)) if quiz_text is None else quiz_text,
                    encoding="utf-8",
                )
            ch.ARTICLES_DIR = str(articles_dir)
            ch.LEDGER_FILE = str(tmp_dir / ".curate-ledger.json")
            ch.QUIZ_FILE = str(quiz_file)
            ch._build_draft_candidate = lambda _url, _sources: dict(candidate)
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                code = ch.run_draft_url(candidate["source_url"])
            printed = buffer.getvalue()
    finally:
        ch._build_draft_candidate = original_build
        ch.ARTICLES_DIR = original_articles
        ch.LEDGER_FILE = original_ledger
        ch.QUIZ_FILE = original_quiz
    return code, printed


def validate_p1_inject_result_distinguishable(errors: list) -> None:
    """[P1-2] 占位注入的**多种失败**不得统一报成「已存在」，且失败时命令不得 exit 0。

    实证缺陷：``inject_quiz_placeholder`` 的四条失败路径（文件不可读 / 花括号不配平 / 缺
    ``DAILY_QUIZZES`` / ``open_index == -1``）**全部**返回 ``False`` 并汇流到同一句
    「⏭️ 已存在」；随后照常打印「✅ 草稿骨架已生成」并 exit 0 ⇒ 维护者以为占位就位，实际
    文件里没有，G1 必红且无从追溯。

    断言：
      - 共享入口返回**可区分**结果（``(ok, reason)``，reason ∈ injected / already_present /
        failed:<原因>），且既有 ``inject_quiz_placeholder(...) -> bool`` 签名与语义不变；
      - ``run_draft_url`` 在**每一种**失败下都打印 ❌（而非 ⏭️）且退出码非零；
      - ``run_draft_url`` 在「已存在」路径下仍打印 ⏭️ 且 exit 0。
    """
    if not hasattr(ch, "ensure_quiz_placeholder"):
        errors.append(
            "[P1-2] curate_harvester 缺少共享入口 ensure_quiz_placeholder()"
            "（禁止用 False 同时表达「已存在」与「失败」）"
        )
        return

    if not hasattr(ch, "inject_quiz_placeholder"):
        errors.append("[P1-2] curate_harvester 缺少既有 inject_quiz_placeholder()（G7 依赖）")
        return

    # 共享入口的可区分性（tempfile 副本，零真实 src/ 改动）
    outcomes: dict = {}
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        injected = tmp_dir / "injected.ts"
        injected.write_text(_G7_QUIZ_SEED, encoding="utf-8")
        outcomes["injected"] = ch.ensure_quiz_placeholder(injected, "p1-shared")
        outcomes["already_present"] = ch.ensure_quiz_placeholder(injected, "p1-shared")

        missing_marker = tmp_dir / "no-marker.ts"
        missing_marker.write_text(_P1_QUIZ_NO_MARKER, encoding="utf-8")
        outcomes["missing_marker"] = ch.ensure_quiz_placeholder(missing_marker, "p1-shared")

        unbalanced = tmp_dir / "unbalanced.ts"
        unbalanced.write_text(_P1_QUIZ_UNBALANCED, encoding="utf-8")
        outcomes["unbalanced"] = ch.ensure_quiz_placeholder(unbalanced, "p1-shared")

        no_open_brace = tmp_dir / "no-open-brace.ts"
        no_open_brace.write_text(_P1_QUIZ_NO_OPEN_BRACE, encoding="utf-8")
        outcomes["no_open_brace"] = ch.ensure_quiz_placeholder(no_open_brace, "p1-shared")

        unreadable = tmp_dir / "missing-dir" / "none.ts"
        unreadable.parent.mkdir(parents=True, exist_ok=True)
        outcomes["unreadable"] = ch.ensure_quiz_placeholder(unreadable, "p1-shared")

    if outcomes["injected"] != (True, "injected"):
        errors.append(
            f"[P1-2] 首次注入应返回 (True, 'injected')，实际 {outcomes['injected']!r}"
        )
    if outcomes["already_present"] != (False, "already_present"):
        errors.append(
            "[P1-2] 二次注入应返回 (False, 'already_present')，实际 "
            f"{outcomes['already_present']!r}（「已存在」必须是可区分的结果）"
        )
    failure_keys = ("missing_marker", "unbalanced", "no_open_brace", "unreadable")
    for key in failure_keys:
        outcome = outcomes[key]
        ok, reason = outcome if isinstance(outcome, tuple) and len(outcome) == 2 else (outcome, "")
        if ok is not False or not str(reason).startswith("failed:"):
            errors.append(
                f"[P1-2] 注入失败场景 {key} 应返回 (False, 'failed:<原因>')，实际 {outcome!r}"
                "（失败与「已存在」被混为一谈 ⇒ 调用方无从区分）"
            )
    distinct_reasons = {outcomes[key][1] for key in failure_keys if isinstance(outcomes[key], tuple)}
    if len(distinct_reasons) < len(failure_keys):
        errors.append(
            f"[P1-2] 四种失败路径的 reason 必须可区分（便于人工定位），实际 {sorted(distinct_reasons)}"
        )

    # 既有 bool 入口语义不变（G7 依赖）：成功 True / 已存在 False。
    with tempfile.TemporaryDirectory() as tmp:
        legacy_path = Path(tmp) / "dailyQuiz.ts"
        legacy_path.write_text(_G7_QUIZ_SEED, encoding="utf-8")
        legacy_first = ch.inject_quiz_placeholder(legacy_path, "p1-legacy")
        legacy_second = ch.inject_quiz_placeholder(legacy_path, "p1-legacy")
    if legacy_first is not True or legacy_second is not False:
        errors.append(
            "[P1-2] 既有 inject_quiz_placeholder(...) -> bool 的语义不得改变（G7 依赖），实际 "
            f"{legacy_first!r} / {legacy_second!r}"
        )

    # 行为级：四种失败路径下 run_draft_url 必须 ❌ + 非零退出（而不是 ⏭️ + exit 0）。
    failure_cases = (
        ("unreadable", None, False),
        ("missing_marker", _P1_QUIZ_NO_MARKER, True),
        ("unbalanced", _P1_QUIZ_UNBALANCED, True),
        ("no_open_brace", _P1_QUIZ_NO_OPEN_BRACE, True),
    )
    for name, quiz_text, make_quiz in failure_cases:
        code, printed = _p1_drive_run_draft_url(quiz_text, make_quiz=make_quiz)
        if code == 0:
            errors.append(
                f"[P1-2] 注入失败场景 {name} 下 run_draft_url 必须返回非零退出码，实际 exit=0"
                "（命令打 ✅ 却 exit 0 ⇒ 维护者以为占位就位，G1 必红且无从追溯）"
            )
        if "❌" not in printed:
            errors.append(
                f"[P1-2] 注入失败场景 {name} 未打印 ❌（失败被报成「已存在」）：{printed[-300:]!r}"
            )
        if "⏭️ 速测题占位已存在" in printed:
            errors.append(
                f"[P1-2] 注入失败场景 {name} 竟打印「⏭️ 速测题占位已存在」（失败与已存在混流）："
                f"{printed[-300:]!r}"
            )

    # 「已存在」路径仍应 ⏭️ + exit 0（预置同 slug 占位，使注入判定为 already_present）。
    already_seed = (
        "export const DAILY_QUIZZES: Record<string, QuizItem> = {\n"
        "  'p1-inject': {\n"
        "    articleId: 'p1-inject',\n"
        "    question: '【待人工补题】请通读原文后填写速测题干',\n"
        "  },\n"
        "};\n"
    )
    already_code, already_printed = _p1_drive_run_draft_url(already_seed, make_quiz=True)
    if "⏭️ 速测题占位已存在" not in already_printed:
        errors.append(
            "[P1-2] 「已存在」路径必须仍打印 ⏭️ 速测题占位已存在："
            f"{already_printed[-300:]!r}"
        )
    if already_code != 0:
        errors.append(f"[P1-2] 「已存在」路径应 exit 0，实际 exit={already_code}")

    if (
        outcomes["injected"] == (True, "injected")
        and outcomes["already_present"] == (False, "already_present")
        and all(
            outcomes[key][0] is False and str(outcomes[key][1]).startswith("failed:")
            for key in failure_keys
        )
        and "⏭️ 速测题占位已存在" in already_printed
        and already_code == 0
    ):
        print(
            "[P1-2] 注入结果可区分通过：共享入口返回 (ok, reason)，reason ∈ injected / "
            "already_present / failed:<原因>；四种失败路径各自 ❌ + 非零退出，「已存在」仍 ⏭️ + exit 0；"
            "既有 inject_quiz_placeholder(...) -> bool 语义不变"
        )


def validate_p1_pool_table_has_url(errors: list) -> None:
    """[P1-8] ``curate:pool`` 表格必须输出**完整 URL** 并给出可直接复制的取用指引。

    实证缺陷：``_print_pool_table`` 只打印「标题 | 来源 | 推定分类 | 首次发现」四列，**无 URL**；
    而候选 dict 里确实有 ``url``。``curate:draft`` 的入参就是 URL ⇒ 维护者只能把标题复制去
    搜索引擎重找原文页。另：「首次发现」列显示的其实是**本次运行内的序号**，列头误导。

    断言：URL 作为最后一列完整打印；列头改为「发现序」；表尾给出与序号对应的可复制取用命令。
    """
    if not hasattr(ch, "_print_pool_table"):
        errors.append("[P1-8] curate_harvester 缺少 _print_pool_table()")
        return

    ranked = [
        {
            "title": f"P1 夹具标题 {index}",
            "category": "body",
            "source_name": "P1 夹具信源",
            "url": f"https://example.test/p1-topic-{index}",
            "first_seen": index,
        }
        for index in (1, 2, 3)
    ]
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        ch._print_pool_table(ranked, {"body": 3}, 0)
    printed = buffer.getvalue()

    if "URL" not in printed:
        errors.append(
            f"[P1-8] 候选池表格未输出 URL 列（维护者只能把标题复制去搜索引擎重找原文页）：{printed[:400]!r}"
        )
    for candidate in ranked:
        if candidate["url"] not in printed:
            errors.append(
                f"[P1-8] 候选池表格缺少第 {candidate['first_seen']} 条的完整 URL "
                f"{candidate['url']}：{printed[:600]!r}"
            )

    header_line = next((line for line in printed.splitlines() if "|" in line), "")
    if "首次发现" in header_line:
        errors.append(
            f"[P1-8] 表头仍写「首次发现」，该列实为本次运行内的发现序号，列头误导：{header_line!r}"
        )
    if "发现序" not in header_line:
        errors.append(f"[P1-8] 表头缺少如实命名的「发现序」列：{header_line!r}")

    # URL 必须是最后一列：每条数据行的 URL 之后不得再有列。
    for line in printed.splitlines():
        if "https://example.test/p1-topic-" not in line:
            continue
        tail = line.split("https://example.test/p1-topic-", 1)[1]
        if "|" in tail:
            errors.append(
                f"[P1-8] URL 必须是表格最后一列（长 URL 换行会破坏前几列可扫读性）：{line!r}"
            )

    # 表尾取用指引：可直接复制粘贴，且与序号对应。
    if "pnpm curate:draft" not in printed:
        errors.append(
            f"[P1-8] 候选池表尾缺少可直接复制粘贴的取用指引（pnpm curate:draft）：{printed[-500:]!r}"
        )
    for index, candidate in enumerate(ranked, start=1):
        expected = f'pnpm curate:draft "{candidate["url"]}"'
        if expected not in printed:
            errors.append(
                f"[P1-8] 表尾取用指引缺少与序号对应的可复制命令 {expected!r}：{printed[-500:]!r}"
            )
        if f"第 {index} 条" not in printed:
            errors.append(
                f"[P1-8] 表尾取用指引未与表格序号对应（维护者需能说「取第 {index} 条」）："
                f"{printed[-500:]!r}"
            )

    if (
        "URL" in printed
        and "发现序" in printed
        and all(c["url"] in printed for c in ranked)
        and 'pnpm curate:draft "https://example.test/p1-topic-1"' in printed
    ):
        print(
            f"[P1-8] 候选池表格输出 URL 通过：URL 作为最后一列完整打印、表头如实命名为「发现序」、"
            f"表尾给出与序号对应的可复制取用命令（{len(ranked)} 条夹具）"
        )


# ---------------------------------------------------------------------------
# [S2 批次] 信号通道与强制执行点
#   S2-1 积压（唯一「必须人行动」的状态）必须有独立于 run 颜色的通知通道，且**绝不重复开单**；
#   S2-2 ::error::/::warning:: 必须**同时**写 stdout（产生 annotation）与 summary（人看）；
#   S2-3 内容门禁（pnpm test:graph）必须有强制执行点（master 的 push 覆盖 + 部署前阻断）。
#
# 范式说明：本节以「**行为级**断言」为主 —— 逐字节取出工作流里真实的 shell / github-script
# 脚本，在全打桩的沙箱里真跑一遍（bash 桩 git/pnpm、node 桩 github SDK），
# 观察**真实产物**（stdout 是否出现 ::error::、是否真的调用 issues.create），
# 而不是正则扫描 YAML 文本（文本扫描会被注释措辞影响、判别力脆弱）。
# ---------------------------------------------------------------------------


def _yaml_block_scalar(body_lines: list, key: str, step_indent: int) -> str:
    """从步骤块行列表中提取 ``key:`` 的值文本（纯 stdlib 文本解析，零第三方依赖）。

    同时支持两种 YAML 写法：块标量 ``key: |``（多行脚本）与行内标量 ``key: pnpm build``。
    ``body_lines`` 为某一步骤（含其 ``- name:`` 行）的全部行；``step_indent`` 为该步骤 ``-`` 的缩进。
    找不到该键时返回空串。
    """
    start = None
    child_indent = 0
    for index, line in enumerate(body_lines):
        matched = re.match(r"^(\s*)" + re.escape(key) + r":(?:\s*\|.*)?$", line)
        if matched and matched.group(0).rstrip().endswith(("|", "|-", "|+")):
            key_indent = len(matched.group(1))
            if key_indent > step_indent:
                start = index + 1
                child_indent = key_indent + 2
            break
        inline = re.match(r"^(\s*)" + re.escape(key) + r":\s+(\S.*)$", line)
        if inline and len(inline.group(1)) > step_indent:
            return inline.group(2).strip()
    if start is None:
        return ""
    collected: list = []
    for line in body_lines[start:]:
        if not line.strip():
            collected.append("")
            continue
        current = len(line) - len(line.lstrip())
        if current < child_indent:
            break
        collected.append(line[child_indent:])
    return "\n".join(collected).strip("\n")


def _workflow_step_blocks(text: str) -> list:
    """把工作流文本切成「步骤块」列表（纯 stdlib 文本解析，零第三方依赖）。

    每个块为 dict：``name`` / ``indent`` / ``body``（含 ``- name:`` 行的整段文本）/
    ``run``（``run: |`` 块标量的去缩进脚本）/ ``script``（github-script 的 ``with.script``）。
    """
    lines = text.splitlines()
    starts: list = []
    for index, line in enumerate(lines):
        matched = re.match(r"^(\s*)- name: (.*)$", line)
        if matched:
            starts.append((index, len(matched.group(1)), matched.group(2).strip()))

    blocks: list = []
    for start, indent, name in starts:
        end = len(lines)
        for cursor in range(start + 1, len(lines)):
            line = lines[cursor]
            if not line.strip():
                continue
            current = len(line) - len(line.lstrip())
            if current <= indent:
                end = cursor
                break
        body_lines = lines[start:end]
        blocks.append(
            {
                "name": name,
                "indent": indent,
                "body": "\n".join(body_lines),
                "run": _yaml_block_scalar(body_lines, "run", indent),
                "script": _yaml_block_scalar(body_lines, "script", indent),
            }
        )
    return blocks


def _find_workflow_step(text: str, name_fragment: str) -> dict:
    """按步骤名片段取出步骤块；未找到返回 ``{}``。"""
    for block in _workflow_step_blocks(text):
        if name_fragment in block["name"]:
            return block
    return {}


def _workflow_on_block(text: str) -> str:
    """取出 ``on:`` 触发器块（含其下缩进的所有行）的原始文本。"""
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if re.match(r"^on:\s*$", line):
            collected = [line]
            for cursor in range(index + 1, len(lines)):
                nxt = lines[cursor]
                if not nxt.strip() or not nxt.startswith((" ", "\t")):
                    break
                collected.append(nxt)
            return "\n".join(collected)
    return ""


# --- 沙箱①：node 桩 github SDK，真跑工作流里的 github-script 积压开单逻辑 ---
_BACKLOG_PROBE_JS = r"""
const fs = require('fs');
const scriptSrc = fs.readFileSync(process.argv[2], 'utf8');
const scenario = process.argv[3];
const calls = [];
const pr = (n, ref) => ({ html_url: 'https://github.com/know-her/know-her/pull/' + n, head: { ref: ref } });
const prs = scenario === 'dedup'
  ? [pr(11, 'candidate/alpha-facts'), pr(12, 'candidate/beta-guide')]
  : [pr(13, 'candidate/gamma-guide')];
const openIssues = scenario === 'dedup'
  ? [{ number: 42, title: '[Pipeline B 积压] 候选积压 2 个，等待人工审阅', labels: [{ name: 'curate-backlog' }] }]
  : [];
const github = {
  rest: {
    pulls: { list: async () => ({ data: prs }) },
    issues: {
      listForRepo: async () => ({ data: openIssues }),
      create: async (args) => { calls.push({ name: 'issues.create', args: args }); return { data: { number: 99 } }; },
      createComment: async (args) => { calls.push({ name: 'issues.createComment', args: args }); return { data: { id: 1 } }; },
      getLabel: async () => ({ data: { name: 'curate-backlog' } }),
      createLabel: async (args) => { calls.push({ name: 'issues.createLabel', args: args }); return { data: { name: 'curate-backlog' } }; }
    }
  },
  paginate: async (fn, args) => (await fn(args)).data
};
const context = { repo: { owner: 'know-her', repo: 'know-her' }, runId: 4242, serverUrl: 'https://github.com' };
const core = { info: (m) => calls.push({ name: 'core.info', args: { message: m } }) };
const wrapped = 'return (async () => {\n' + scriptSrc + '\n})()';
new Function('github', 'context', 'core', wrapped)(github, context, core).then(() => {
  process.stdout.write(JSON.stringify(calls));
}).catch((e) => {
  process.stderr.write(String((e && e.stack) || e));
  process.exit(1);
});
"""


def _run_backlog_script_in_sandbox(script: str, scenario: str) -> list:
    """在 node 沙箱里真跑工作流里的积压开单 github-script，返回其对 github SDK 的**真实调用序列**。

    全部打桩：``github.rest`` / ``github.paginate`` / ``context`` / ``core`` 均为本地假对象，
    **零真实网络、零真实 GitHub 写**。``scenario='dedup'`` 时桩里已存在一个未关闭的积压 issue。
    """
    node = shutil.which("node")
    if not node:
        raise RuntimeError("PATH 中未找到 node 可执行文件（需 Node 18+ 以运行 github-script 沙箱探针）")
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        probe = tmp_dir / "backlog_probe.cjs"
        probe.write_text(_BACKLOG_PROBE_JS, encoding="utf-8")
        target = tmp_dir / "backlog_script.js"
        target.write_text(script, encoding="utf-8")
        proc = subprocess.run(
            [node, str(probe), str(target), scenario],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
        )
    if proc.returncode != 0:
        raise RuntimeError(
            f"积压脚本沙箱执行失败（scenario={scenario}），exit={proc.returncode}，"
            f"stderr 尾部：{proc.stderr.strip()[-500:]}"
        )
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"积压脚本沙箱输出非合法 JSON（scenario={scenario}）：{exc}；"
            f"stdout 尾部：{proc.stdout.strip()[-300:]}"
        ) from exc


# --- 沙箱②：bash 桩 git/pnpm，真跑工作流里自检步骤的 run 脚本，观察真实 stdout 与 summary ---
def _sandbox_run_selfcheck(
    script: str, *, branch: str, draft_exists: bool, pnpm_exit: int
) -> tuple:
    """在 tempfile + bash 沙箱里真跑一次自检步骤的 ``run`` 脚本。

    ``git`` / ``pnpm`` 被打桩为 shell 函数（**零真实 git 写、零网络、零 src/ 改动**：工作目录是
    临时目录，``${{ ... }}`` 表达式已替换为夹具分支名）。返回 ``(stdout, summary_text)``。
    """
    bash = shutil.which("bash")
    if not bash:
        raise RuntimeError("PATH 中未找到 bash 可执行文件（需 bash 以运行自检步骤沙箱探针）")
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        tmp_posix = tmp_dir.as_posix()
        rendered = re.sub(r"\$\{\{.*?\}\}", lambda _m: branch, script)
        rendered = rendered.replace("/tmp/", f"{tmp_posix}/")
        step_file = tmp_dir / "step.sh"
        with open(step_file, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(rendered)
        if draft_exists:
            slug = branch.split("/", 1)[1] if "/" in branch else branch
            draft = tmp_dir / "src" / "content" / "articles" / f"{slug}.mdx"
            draft.parent.mkdir(parents=True, exist_ok=True)
            draft.write_text("---\ntitle: \"x\"\n---\n", encoding="utf-8")
        summary = tmp_dir / "summary.md"
        wrapper = tmp_dir / "wrapper.sh"
        with open(wrapper, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(
                "git() { echo \"[stub git] $*\"; return 0; }\n"
                f"pnpm() {{ echo \"[stub pnpm] $*\"; return {pnpm_exit}; }}\n"
                f'. "{step_file.as_posix()}"\n'
            )
        env = dict(os.environ)
        env["GITHUB_STEP_SUMMARY"] = str(summary).replace("\\", "/")
        proc = subprocess.run(
            [bash, str(wrapper)],
            cwd=str(tmp_dir),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=120,
        )
        summary_text = summary.read_text(encoding="utf-8") if summary.is_file() else ""
        return proc.stdout, summary_text


# ---------------------------------------------------------------------------
# [S2-1] 积压自动开 issue：唯一「必须人行动」的状态，必须有独立于 run 颜色的通知通道
# ---------------------------------------------------------------------------


def validate_s2_backlog_issue_channel(errors: list) -> None:
    """[S2-1] 积压（机器在等人）必须**自动开 issue**，且**绝不重复开单**。

    实证缺陷：``_report_backlog`` 走 ``exit 0`` + ``::warning::``，而 GitHub 对定时任务的
    邮件 / 通知**只按 exit code 决定** ⇒ 积压**产生零通知**，必须有人主动点进一个绿色 run
    才看得见；同是真故障反而发红 ⇒ 信号优先级是反的。同仓 ``daily-routine.yml`` 与
    ``weekly-full-audit.yml`` 早已有成熟的「异常 → 自动开 issue」通道，唯独 Pipeline B 没有。

    判定为「行为级」：逐字节取出工作流里真实的 github-script，在 node 沙箱里以**全打桩**的
    ``github`` / ``context`` / ``core`` 真跑一遍，观察**真实调用序列**：

    - 场景 A（尚无未关闭的积压 issue）⇒ 恰好调用一次 ``issues.create``，且
      标题 / 正文含**积压数量**、**待审 PR 的链接列表**、**可执行的解锁命令**
      （``git push origin --delete candidate/<slug>``），并带固定 label ``curate-backlog``；
    - 场景 B（已存在未关闭的积压 issue）⇒ ``issues.create`` **零调用**（否则每天开一个新单），
      且脚本以可识别方式「跳过」而不是硬失败；
    - 触发条件：只在本轮收尾为**积压**（exit 0 且无候选分支）时触发，
      **真故障**（exit 1）已由红灯 + 通知覆盖，不得走本通道（避免双重噪音）。
    """
    workflow = ROOT_DIR / ".github" / "workflows" / "harvest-candidates.yml"
    if not workflow.is_file():
        errors.append(f"[S2-1] 工作流文件缺失：{workflow}")
        return
    text = _read_text(workflow)

    # —— 权限：只加 issues: write，不得越权拿 actions: write ——
    permissions = re.search(r"^permissions:\n((?:[ \t]+.*\n|\n)*)", text, re.MULTILINE)
    if permissions is None:
        errors.append("[S2-1] harvest-candidates.yml 缺少 permissions 段（无法授予 issues: write）")
    else:
        perm_text = permissions.group(1)
        if not re.search(r"^\s+issues:\s*write\s*$", perm_text, re.MULTILINE):
            errors.append("[S2-1] harvest-candidates.yml 未授予 `issues: write`（积压无法自动开 issue）")
        if re.search(r"^\s+actions:\s*write\s*$", perm_text, re.MULTILINE):
            errors.append("[S2-1] harvest-candidates.yml 不得授予 `actions: write`（本任务只需 issues: write）")

    step = _find_workflow_step(text, "积压")
    if not step:
        errors.append("[S2-1] harvest-candidates.yml 缺少「积压」收尾步骤（积压仍无独立通知通道）")
        return
    if not re.search(r"^\s*if:\s*always\(\)", step["body"], re.MULTILINE):
        errors.append("[S2-1] 积压步骤的 if 必须是 always()（故障收尾时也必须给出积压判定）")

    cond_block = re.search(r"^\s*if:\s*(.+)$", step["body"], re.MULTILINE)
    condition = cond_block.group(1) if cond_block else ""
    # 真故障（create_pr 步骤 exit 1 ⇒ outcome=failure）不得走本通道
    if "failure()" in condition:
        errors.append("[S2-1] 积压步骤的 if 不得含 failure()（真故障已有红灯 + 通知，双通道会制造双重噪音）")
    if "steps.create_pr.outcome" not in condition or "success" not in condition:
        errors.append(
            "[S2-1] 积压步骤的 if 必须以 steps.create_pr.outcome == 'success' 收口"
            "（exit 1 的真故障不得走积压通道）"
        )
    if "steps.create_pr.outputs.branch" not in condition or "== ''" not in condition:
        errors.append(
            "[S2-1] 积压步骤的 if 必须以 steps.create_pr.outputs.branch == '' 收口"
            "（exit 0 且无候选分支 ⇔ 收尾为积压；exit 0 且有分支 ⇔ 已成功创建 PR）"
        )

    script = step["script"]
    if "actions/github-script" not in step["body"]:
        errors.append("[S2-1] 积压步骤未复用 actions/github-script（与 daily-routine.yml 的既有惯例不一致）")
    if "issues.create" not in script:
        errors.append("[S2-1] 积压脚本未调用 github.rest.issues.create")
    if "curate-backlog" not in script:
        errors.append("[S2-1] 积压脚本未使用固定 label `curate-backlog`（去重必须靠固定 label）")
    if "git push origin --delete" not in script:
        errors.append("[S2-1] 积压脚本未给出可执行的解锁命令 `git push origin --delete <branch>`")

    if not script:
        errors.append("[S2-1] 积压步骤的 github-script `with.script` 为空")
        return

    # —— 行为断言 A：无既有积压 issue ⇒ 恰好开一个单 ——
    try:
        calls_fresh = _run_backlog_script_in_sandbox(script, "fresh")
    except RuntimeError as exc:
        errors.append(f"[S2-1] 无法执行积压脚本行为断言：{exc}")
        return
    creates_fresh = [c for c in calls_fresh if c["name"] == "issues.create"]
    if len(creates_fresh) != 1:
        errors.append(
            f"[S2-1] 行为断言：首次积压应恰好调用一次 issues.create，实际 {len(creates_fresh)} 次"
            f"（全部调用={[c['name'] for c in calls_fresh]}）"
        )
    else:
        args = creates_fresh[0]["args"]
        title = str(args.get("title", ""))
        body = str(args.get("body", ""))
        labels = [str(x) for x in (args.get("labels") or [])]
        if "curate-backlog" not in labels:
            errors.append(f"[S2-1] 新建积压 issue 未打固定 label `curate-backlog`（去重依赖它）：{labels}")
        if "alpha-facts" not in title and not re.search(r"\d", title):
            errors.append(f"[S2-1] 积压 issue 标题未点明积压数量：{title!r}")
        if "pull/13" not in body:
            errors.append(f"[S2-1] 积压 issue 正文缺少待审 PR 的链接列表：{body[-400:]!r}")
        if "git push origin --delete candidate/gamma-guide" not in body:
            errors.append(f"[S2-1] 积压 issue 正文缺少该 PR 对应的可执行解锁命令：{body[-400:]!r}")

    # —— 行为断言 B：已存在未关闭的积压 issue ⇒ 绝不重复开单 ——
    try:
        calls_dedup = _run_backlog_script_in_sandbox(script, "dedup")
    except RuntimeError as exc:
        errors.append(f"[S2-1] 无法执行积压脚本去重行为断言：{exc}")
        return
    creates_dedup = [c for c in calls_dedup if c["name"] == "issues.create"]
    if creates_dedup:
        errors.append(
            "[S2-1] 行为断言：已存在未关闭的积压 issue 时**仍然**调用了 issues.create"
            f"（会每天开一个新单）：{[c['args'].get('title') for c in creates_dedup]}"
        )

    if len(creates_fresh) == 1 and not creates_dedup:
        print(
            "[S2-1] 积压通知通道行为断言通过：首次积压开 1 个带 `curate-backlog` label 的 issue"
            "（含积压数量 / 待审 PR 链接 / 可执行解锁命令）；已存在未关闭积压 issue 时零重复开单"
        )


# ---------------------------------------------------------------------------
# [S2-2] ::error:: / ::warning:: 必须同时写 stdout（annotation）与 summary（人看）
# ---------------------------------------------------------------------------


def validate_s2_gate_annotations_reach_stdout(errors: list) -> None:
    """[S2-2] 自检步骤的 ``::error::`` / ``::warning::`` 必须**双写** stdout + ``$GITHUB_STEP_SUMMARY``。

    实证缺陷（已实测 annotation 数为 0）：GitHub 的 workflow command（``::error::`` /
    ``::warning::``）**只在 stdout 被解析**；而 ``harvest-candidates.yml`` 把它们重定向进
    ``$GITHUB_STEP_SUMMARY``，那只是普通 markdown 文本 ⇒ 唯一的失败信号完全失效，
    维护者只看到一行裸的 ``::error::`` 字面量，annotations 面板永远空白。

    判定为「行为级」：逐字节取出该步骤真实的 ``run`` 脚本，在 tempfile + bash 沙箱里
    （``git`` / ``pnpm`` 均为桩 ⇒ 零真实 git 写、零网络、零 src/ 改动）真跑两遍，
    观察**真实 stdout** 与**真实 summary 文件**：

    - 「门禁 FAIL 分支」：桩 pnpm 退出非零 ⇒ stdout 出现 ``::error::``，且 summary 也有可读说明；
    - 「候选分支缺草稿文件」分支：stdout 出现 ``::error::``，且 summary 也有可读说明。

    反空转守卫：两分支的 stdout 探针**不得**靠「脚本压根没跑」蒙混 —— 桩 pnpm 必须被真实调用。
    """
    workflow = ROOT_DIR / ".github" / "workflows" / "harvest-candidates.yml"
    if not workflow.is_file():
        errors.append(f"[S2-2] 工作流文件缺失：{workflow}")
        return
    text = _read_text(workflow)
    step = _find_workflow_step(text, "机器可验证门禁自检")
    if not step:
        errors.append("[S2-2] 未找到「机器可验证门禁自检」步骤")
        return
    script = step["run"]
    if not script:
        errors.append("[S2-2] 自检步骤的 run 脚本为空，无法产生任何信号")
        return

    if not re.search(r"^\s*continue-on-error:\s*true\s*$", step["body"], re.MULTILINE):
        errors.append("[S2-2] 自检步骤必须保留 continue-on-error: true（草稿按设计必红，不得让 Harvest 变红）")

    # 反向：不得把 ::error:: / ::warning:: 整体重定向进 summary（那正是被证伪的旧写法）
    for line in script.splitlines():
        if ("::error::" in line or "::warning::" in line) and re.search(
            r">>\s*\"?\$GITHUB_STEP_SUMMARY", line
        ):
            errors.append(
                "[S2-2] 存在把 ::error::/::warning:: 只重定向进 $GITHUB_STEP_SUMMARY 的写法"
                "（workflow command 只在 stdout 被解析 ⇒ annotations 面板永远空白）："
                f"{line.strip()!r}"
            )

    branch = "candidate/s2-fixture"

    # —— 分支①：门禁 FAIL（桩 pnpm 退出 1）——
    try:
        stdout_fail, summary_fail = _sandbox_run_selfcheck(
            script, branch=branch, draft_exists=True, pnpm_exit=1
        )
    except RuntimeError as exc:
        errors.append(f"[S2-2] 无法执行自检脚本行为断言：{exc}")
        return
    # 反空转守卫：pnpm 桩的输出被 run_gate 重定向进 /tmp/gate_self_check.log 并 tail 进 summary，
    # 故「桩确被调用」由 summary 里的桩痕迹证明（而不是 stdout —— stdout 只有 annotation 通道）。
    if "[stub pnpm]" not in summary_fail:
        errors.append(
            "[S2-2] 行为断言空转：门禁 FAIL 场景下沙箱内 pnpm 桩压根没被调用（断言会永真）："
            f"summary 尾部={summary_fail[-300:]!r}"
        )
    if "::error::" not in stdout_fail:
        errors.append(
            "[S2-2] 门禁 FAIL 分支未把 ::error:: 写到 **stdout**"
            "（⇒ 无 annotation，唯一的失败信号失效；仅写 summary 只是普通 markdown）："
            f"stdout 尾部={stdout_fail[-300:]!r}"
        )
    if "pnpm check" not in summary_fail:
        errors.append(f"[S2-2] 门禁 FAIL 分支的 summary 未记录失败的门禁名：{summary_fail[-300:]!r}")

    # —— 分支②：候选分支缺草稿文件 ——
    try:
        stdout_nodraft, summary_nodraft = _sandbox_run_selfcheck(
            script, branch=branch, draft_exists=False, pnpm_exit=0
        )
    except RuntimeError as exc:
        errors.append(f"[S2-2] 无法执行自检脚本「缺草稿文件」行为断言：{exc}")
        return
    if "::error::" not in stdout_nodraft:
        errors.append(
            "[S2-2] 「候选分支缺草稿文件」分支未把 ::error:: 写到 **stdout**"
            f"（⇒ 无 annotation）：stdout 尾部={stdout_nodraft[-300:]!r}"
        )
    if "s2-fixture.mdx" not in summary_nodraft:
        errors.append(
            "[S2-2] 「候选分支缺草稿文件」分支的 summary 未记录缺失的草稿文件名"
            f"（人看不到任何说明）：{summary_nodraft[-300:]!r}"
        )

    if (
        "::error::" in stdout_fail
        and "::error::" in stdout_nodraft
        and "pnpm check" in summary_fail
        and "s2-fixture.mdx" in summary_nodraft
    ):
        print(
            "[S2-2] annotation 双写行为断言通过：「门禁 FAIL」与「候选分支缺草稿文件」两处 "
            "::error:: 均出现在真实 stdout（产生 annotation）且 summary 同步留有可读说明"
        )


# ---------------------------------------------------------------------------
# [S2-3] 内容门禁（pnpm test:graph）必须有强制执行点
# ---------------------------------------------------------------------------


def validate_s2_content_gate_enforced(errors: list) -> None:
    """[S2-3] 内容门禁（文章↔速测题 1:1 等 G1~G9，全在 ``pnpm test:graph``）必须有强制执行点。

    实证缺陷（已实测）：``branches/master/protection`` → 404、``/rulesets`` → ``[]``（无任何强制检查）；
    ``ci.yml`` 的 ``push`` 带 ``branches-ignore: [ master ]`` ⇒ **合并到 master 也不跑门禁**；
    ``deploy.yml`` 在 build 前只跑 ``curate:check`` / ``curate:links`` / ``pnpm build``，
    **不含** ``pnpm test:graph`` ⇒ 内容门禁在合并前后都没人执行。

    断言（结构级，零网络、零 GitHub API）：
      - ``ci.yml`` 的 ``push`` 触发器**不得**排除 master，且其中含 ``pnpm test:graph``
        且该步骤**非** ``continue-on-error``；
      - ``deploy.yml`` 在 ``pnpm build`` **之前**必须有一步执行 ``pnpm test:graph``，
        且该步**非** ``continue-on-error``（内容门禁失败必须**阻断部署**）。

    反向守卫：``test:graph`` 步若被改成 ``continue-on-error: true``（只警告不阻断），
    本断言必须判红 —— 故对每个含 ``pnpm test:graph`` 的步骤逐一核对。
    """
    ci_path = ROOT_DIR / ".github" / "workflows" / "ci.yml"
    deploy_path = ROOT_DIR / ".github" / "workflows" / "deploy.yml"
    for path in (ci_path, deploy_path):
        if not path.is_file():
            errors.append(f"[S2-3] 工作流文件缺失：{path}")
    if errors and any("[S2-3] 工作流文件缺失" in e for e in errors):
        return

    ci_text = _read_text(ci_path)
    deploy_text = _read_text(deploy_path)

    # —— ci.yml：master 的 push 也必须被门禁覆盖 ——
    on_block = _workflow_on_block(ci_text)
    if not on_block:
        errors.append("[S2-3] ci.yml 的 on: 触发器块无法解析")
    else:
        if "push" not in on_block:
            errors.append("[S2-3] ci.yml 缺少 push 触发器")
        excluded = re.findall(r"^\s*branches-ignore:\s*\[(.*?)\]\s*$", on_block, re.MULTILINE)
        ignored_masters = [m for m in excluded if "master" in m]
        if ignored_masters:
            errors.append(
                "[S2-3] ci.yml 的 push 触发器仍排除 master"
                f"（branches-ignore={ignored_masters}）⇒ 合并到 master 也不跑任何门禁，"
                "内容门禁在合并环节彻底失守"
            )

    # —— ci.yml / deploy.yml：test:graph 步骤必须阻断，且不得被 continue-on-error 稀释 ——
    all_graph_blocking = True
    for label, path, text in (("ci.yml", ci_path, ci_text), ("deploy.yml", deploy_path, deploy_text)):
        blocks = _workflow_step_blocks(text)
        graph_steps = [b for b in blocks if "pnpm test:graph" in b["run"]]
        if not graph_steps:
            errors.append(f"[S2-3] {label} 中没有任何步骤执行 `pnpm test:graph`（G1~G9 内容门禁无执行点）")
            all_graph_blocking = False
            continue
        for block in graph_steps:
            if re.search(r"^\s*continue-on-error:\s*true\s*$", block["body"], re.MULTILINE):
                errors.append(
                    f"[S2-3] {label} 的 `pnpm test:graph` 步骤被标为 continue-on-error: true"
                    f"（内容门禁失败不再阻断 ⇒ 门禁形同虚设）：步骤「{block['name']}」"
                )
                all_graph_blocking = False

    # —— deploy.yml：test:graph 必须在 pnpm build 之前（build 后跑等于没跑）——
    deploy_blocks = _workflow_step_blocks(deploy_text)
    graph_idx = [i for i, b in enumerate(deploy_blocks) if "pnpm test:graph" in b["run"]]
    build_idx = [i for i, b in enumerate(deploy_blocks) if re.search(r"pnpm build", b["run"])]
    if not build_idx:
        errors.append("[S2-3] deploy.yml 中找不到执行 `pnpm build` 的步骤（无法判定门禁次序）")
    elif not graph_idx:
        errors.append("[S2-3] deploy.yml 在 build 前未接入 `pnpm test:graph`（内容门禁失败不会阻断部署）")
    elif min(graph_idx) > min(build_idx):
        errors.append(
            f"[S2-3] deploy.yml 的 `pnpm test:graph`（#{min(graph_idx)}）排在 `pnpm build`"
            f"（#{min(build_idx)}）**之后**（build 后再跑内容门禁已无阻断意义）"
        )

    if (
        on_block
        and "push" in on_block
        and not [m for m in excluded if "master" in m]
        and all_graph_blocking
        and graph_idx
        and build_idx
        and min(graph_idx) < min(build_idx)
    ):
        print(
            "[S2-3] 内容门禁强制执行点通过：ci.yml 的 push 不再排除 master 且含 pnpm test:graph；"
            "deploy.yml 在 pnpm build **之前**阻断式执行 pnpm test:graph（无 continue-on-error）"
        )


def run_gate() -> None:
    print("[gate] 每日循环不变量门禁 (Daily Loop Invariant Gate)")
    print("[gate] 已实现 G1（文章<->速测题 1:1）、G2（三池非空 + 词条池真参与周期）、G3（lcm(文章池, 词条池) -> >= 90 天不重复 + 两池不退化）、G4（信源 schema 合法性 + admitted⇒license 非空 + http(s) 前缀 + rank_candidates 缺口升序 + --pool 零副作用/空池可执行报错 + 空池两类成因分别提示）、G5（候选池台账 v2 幂等迁移 + 真实台账字段完备 + v2 下 harvest_candidates 零 TypeError）、G6（今日上新窗口 + 附加展示零扰动轮换索引）、G7（速测题占位注入幂等 tempfile 自证 + 反向坏实现可判红 + --admit-source 只读不改 sources.json）与 G8（node 原生载入 rotation.ts 的真实行为断言，含 G8a 双时区一致 / G8b pickFreshArticle 真行为）以及 G9（草稿模板经 node + 本项目 MDX 引擎真实编译须通过、且不含 `<!--` / 无 raw_desc 泄漏；候选分支不带台账；跳过-成功返回值语义可区分且零进展 ::warning:: 可见；R1~R5 收口：候选分支名经 $GITHUB_OUTPUT 与返回值交给上层且工作流自检在候选分支上、失败候选不污染后续、--create-pr 一次性预取预排除被占用候选、积压 exit 0 与真故障 exit 1 措辞分明、raw_desc 进 PR 正文且泄漏守卫不空转）。")

    errors: list = []

    validate_quiz_coverage(errors)
    validate_quiz_coverage_reverse_test(errors)
    validate_g3_pool_cycle(errors)
    validate_g2_pool_nonempty(errors)
    validate_g2_reverse_test(errors)
    validate_self_checks(errors)
    validate_rotation_contract(errors)
    validate_daily_quiz_reexport(errors)
    validate_g6_fresh_window_contract(errors)
    validate_g6_beijing_tz_independent(errors)
    validate_g6_window_boundaries(errors)
    validate_g6_no_rotation_drift(errors)
    validate_g6_sort_primary_forms(errors)
    validate_g6_article_sort_descending(errors)
    validate_g6_card_strip(errors)

    # [G8c] 注释剥离字面量加固自检
    validate_strip_ts_comments_literals(errors)
    # [YELLOW-4] 门禁计数口径与运行时口径对齐
    validate_pool_count_alignment(errors)
    validate_pool_count_alignment_fixture(errors)

    # [G5] 候选池台账 v2：迁移结构 / 幂等 / 去重打印 / 真实台账 / C1 零 TypeError
    validate_g5_migration_structure(errors)
    validate_g5_idempotent(errors)
    validate_g5_dedup_prints(errors)
    validate_g5_real_ledger(errors)
    validate_g5_harvest_no_typeerror(errors)

    # [G4] 信源清单 schema 合法性 + 反向用例 + rank_candidates + --pool 零副作用/空池可执行报错
    validate_g4_source_schema(errors)
    validate_g4_source_schema_reverse(errors)
    validate_g4_rank_candidates(errors)
    validate_g4_pool_zero_side_effect(errors)
    validate_g4_pool_empty_state(errors)

    # [G7] 速测题占位注入幂等（tempfile 自证 + 反向坏实现可判红）+ --admit-source 只读不改 sources.json
    validate_g7_idempotent_injection(errors)
    validate_g7_reverse_bad_impl(errors)
    validate_g7_admit_source_readonly(errors)
    # [G7] F1 缺陷修复：准入探测假阳性（redirect_home 判定 + 草案只取真实候选 + 契约零回归）
    validate_g7_probe_page_verdicts(errors)
    # [G7] F1b-H1：端到端（经 run_admit_source）断言 root_length 已接线到生产路径
    validate_g7_admit_e2e_root_length_wiring(errors)
    validate_g7_url_key_normalization(errors)
    validate_g7_fetch_url_contract(errors)
    # [G7] Task-6 收口：test:graph 必须挂载 test_source_discovery.py（紧接 test_daily_loop.py）
    validate_test_graph_wiring(errors)

    # [G8/G8a/G8b] node 原生载入 rotation.ts 的真实行为断言（探针失败即记明确错误，不静默跳过）
    probe = _run_rotation_probe(errors)
    validate_g8_rotation_behavior(errors, probe)
    validate_g8a_tz_consistency(errors, probe)
    validate_g8b_pick_fresh_behavior(errors, probe)

    # [G9] 草稿模板真实 MDX 编译（B）+ 候选分支不带台账（C）+ 跳过/零进展语义（D）
    validate_g9_compose_template_mdx(errors)
    validate_g9_reverse_bad_templates(errors)
    validate_g9_create_draft_pr_contract(errors)
    validate_g9_zero_progress_visible(errors)
    # [G9/R1~R5 收口] 分支输出接线 / 失败候选隔离 / 预取预排除 / 空池真故障 / 工作流自检接线
    validate_g9_branch_output_wiring(errors)
    validate_g9_failed_candidate_isolated(errors)
    validate_g9_prefetch_exclude(errors)
    validate_g9_empty_pool_error(errors)
    validate_g9_workflow_selfcheck_wiring(errors)
    # [P0 止血回合] 远端永不强制覆盖 / 机器不自证 / PR 路径自洽 / 判重前置
    validate_g9_no_force_overwrite(errors)
    validate_g9_no_machine_self_attestation(errors)
    validate_g9_pr_path_quiz_placeholder(errors)
    validate_g9_draft_url_dedupe_before_write(errors)
    # [红卡 + 黄卡清理] 远端残留属「等待人工」不得判故障 / 占位标记单一真值源 /
    # 还原失败必须告警 / ls-remote 重试 1 次后 fail-closed
    validate_g9_remote_exists_is_backlog_not_failure(errors)
    validate_g9_placeholder_marker_covers_summary(errors)
    validate_g9_quiz_restore_prints_warning(errors)
    validate_g9_ls_remote_retry_then_fail_closed(errors)

    # [P1 批次] 三条 P1：pending 可见性分口径 / 注入结果可区分 / 候选池表格输出 URL
    validate_p1_pending_visible_in_pool(errors)
    validate_p1_inject_result_distinguishable(errors)
    validate_p1_pool_table_has_url(errors)

    # [S2 批次] 信号通道与强制执行点：积压自动开 issue（去重）/ annotation 双写 / 内容门禁强制点
    validate_s2_backlog_issue_channel(errors)
    validate_s2_gate_annotations_reach_stdout(errors)
    validate_s2_content_gate_enforced(errors)

    if errors:
        print(f"[FAIL] 每日循环不变量门禁未通过，发现 {len(errors)} 个问题：")
        for err in errors:
            print(f"   - {err}")
        sys.exit(1)

    print("[PASS] G1、G2、G3、G4、G5、G6、G7、G8 与 G9 全绿：文章<->速测题 1:1；三池非空且词条池真参与周期；首页当日组合周期 lcm(文章池, 词条池) >= 90 天且两池不退化；信源 schema 合法（含 admitted⇒license 非空 fail-closed 反向用例）且 --pool 零副作用（台账 sha256 前后一致）与空池两类成因分别可执行报错；候选池台账 v2 迁移幂等、真实台账字段完备且 v2 下 harvest_candidates 零 TypeError；今日上新窗口（第7天命中/第8天不命中）成立且仅作附加展示、轮换索引零扰动；速测题占位注入幂等（tempfile 副本二次注入 sha256 不变 + 反向坏实现可判红）且 --admit-source 只读不写 sources.json（No-Auto-Approve）；rotation.ts 真实行为（指纹/索引/lcm）经 node 原生载入断言且 beijingDayNumber 时区无关；计数口径与站点一致；反向用例与边界自检均通过；G9：草稿模板经 node + 本项目 MDX 引擎真实编译通过且不含 `<!--`/无 raw_desc 泄漏（含反向用例可判红）、候选分支不带台账（git add 仅暂存 .mdx）、跳过-成功返回值语义可区分且零进展 ::warning:: 可见。R1~R5 收口：create_draft_pr 成功即把分支名写 $GITHUB_OUTPUT 并经返回值 ``.branch`` 交给上层、工作流自检在候选分支上检出后编译且无假绿陈述；失败的候选不再写台账、不残留草稿拖垮后续；--create-pr 用单次 gh 调用预排除被占用候选（失败退回首逐 --head 检查）；积压（均已有待审 PR）exit 0 + ::warning::，真故障 / 空池 exit 1 + ::error:: 措辞分明；raw_desc 进入 PR 正文且泄漏守卫带非空防呆。")


if __name__ == "__main__":
    run_gate()
