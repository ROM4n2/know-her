#!/usr/bin/env python3
"""
test_daily_loop.py — 每日循环不变量门禁 (Daily Loop Invariant Gate)

守护「每天首页内容不重复」这一可判定的数学不变量：
    真实独立维度 = (文章池 A, 词条池 G) -> 最小公倍数 lcm -> 不重复天数 >= MIN_UNIQUE_CYCLE_DAYS

速测题与今日文章 1:1 绑定（G1 门禁强制），不是独立轮换维度，故不参与周期计算
（修正记录见 Spec §3.1.3）。当日指纹 = ((day-1) mod A, (day-1) mod G)，
其重复周期 = lcm(A, G)；当前 lcm(26, 28) = 364 天（约一年）。

本文件当前实现 G1 / G2 / G3 / G4 / G5 / G6 / G8 断言：
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

范式：与 scripts/test_tools.py 一致 —— errors: list[str] 收集错误，结尾统一 sys.exit(1)。
约束：零第三方依赖（仅标准库）；路径操作统一 pathlib.Path；
      站点内容（.mdx/.astro）零 Emoji；脚本输出沿用仓库既有 ❌/✅/[PASS]/[FAIL] 门禁范式。
"""

import contextlib
import datetime
import hashlib
import io
import json
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

    以打桩 fetch_url 驱动 run_admit_source，断言运行前后 scripts/sources.json 的
    sha256 **完全不变**（证明未自动置 admitted / 未自动填 license / 未写盘）。
    """
    if not hasattr(ch, "run_admit_source"):
        errors.append("[G7] curate_harvester 缺少 run_admit_source()（--admit-source 分支未实现）")
        return
    if not SOURCES_FILE.is_file():
        errors.append(f"[G7] 信源清单缺失：{SOURCES_FILE}")
        return

    original_fetch = ch.fetch_url
    ch.fetch_url = lambda *args, **kwargs: (200, "<html><title>许可页</title></html>")
    before = _sha256(SOURCES_FILE)
    buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(buffer):
            code = ch.run_admit_source("plannedparenthood")
    finally:
        ch.fetch_url = original_fetch
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


def run_gate() -> None:
    print("[gate] 每日循环不变量门禁 (Daily Loop Invariant Gate)")
    print("[gate] 已实现 G1（文章<->速测题 1:1）、G2（三池非空 + 词条池真参与周期）、G3（lcm(文章池, 词条池) -> >= 90 天不重复 + 两池不退化）、G4（信源 schema 合法性 + admitted⇒license 非空 + http(s) 前缀 + rank_candidates 缺口升序 + --pool 零副作用/空池可执行报错 + 空池两类成因分别提示）、G5（候选池台账 v2 幂等迁移 + 真实台账字段完备 + v2 下 harvest_candidates 零 TypeError）、G6（今日上新窗口 + 附加展示零扰动轮换索引）、G7（速测题占位注入幂等 tempfile 自证 + 反向坏实现可判红 + --admit-source 只读不改 sources.json）与 G8（node 原生载入 rotation.ts 的真实行为断言，含 G8a 双时区一致 / G8b pickFreshArticle 真行为）。")

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
    # [G7] Task-6 收口：test:graph 必须挂载 test_source_discovery.py（紧接 test_daily_loop.py）
    validate_test_graph_wiring(errors)

    # [G8/G8a/G8b] node 原生载入 rotation.ts 的真实行为断言（探针失败即记明确错误，不静默跳过）
    probe = _run_rotation_probe(errors)
    validate_g8_rotation_behavior(errors, probe)
    validate_g8a_tz_consistency(errors, probe)
    validate_g8b_pick_fresh_behavior(errors, probe)

    if errors:
        print(f"[FAIL] 每日循环不变量门禁未通过，发现 {len(errors)} 个问题：")
        for err in errors:
            print(f"   - {err}")
        sys.exit(1)

    print("[PASS] G1、G2、G3、G4、G5、G6、G7 与 G8 全绿：文章<->速测题 1:1；三池非空且词条池真参与周期；首页当日组合周期 lcm(文章池, 词条池) >= 90 天且两池不退化；信源 schema 合法（含 admitted⇒license 非空 fail-closed 反向用例）且 --pool 零副作用（台账 sha256 前后一致）与空池两类成因分别可执行报错；候选池台账 v2 迁移幂等、真实台账字段完备且 v2 下 harvest_candidates 零 TypeError；今日上新窗口（第7天命中/第8天不命中）成立且仅作附加展示、轮换索引零扰动；速测题占位注入幂等（tempfile 副本二次注入 sha256 不变 + 反向坏实现可判红）且 --admit-source 只读不写 sources.json（No-Auto-Approve）；rotation.ts 真实行为（指纹/索引/lcm）经 node 原生载入断言且 beijingDayNumber 时区无关；计数口径与站点一致；反向用例与边界自检均通过。")


if __name__ == "__main__":
    run_gate()
