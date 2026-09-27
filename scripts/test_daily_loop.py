#!/usr/bin/env python3
"""
test_daily_loop.py — 每日循环不变量门禁 (Daily Loop Invariant Gate)

守护「每天首页内容不重复」这一可判定的数学不变量：
    真实独立维度 = (文章池 A, 词条池 G) -> 最小公倍数 lcm -> 不重复天数 >= MIN_UNIQUE_CYCLE_DAYS

速测题与今日文章 1:1 绑定（G1 门禁强制），不是独立轮换维度，故不参与周期计算
（修正记录见 Spec §3.1.3）。当日指纹 = ((day-1) mod A, (day-1) mod G)，
其重复周期 = lcm(A, G)；当前 lcm(26, 28) = 364 天（约一年）。

本文件当前实现 G1 / G2 / G3 / G6 四组断言：
    G3（池规模 -> lcm(文章池, 词条池) -> >= 90 天不重复 + 两池不退化）
    G2（三池非空 + lcm(文章池, 词条池) > 文章池，证明词条池真参与周期，含反向用例）
    G1（文章 slug 集合 <-> DAILY_QUIZZES 键集合 双向 1:1，含反向夹具用例）
    G6（今日上新窗口：rotation.pickFreshArticle 源码契约 + 定日边界用例 +
        断言「今日上新」仅作附加展示、不污染轮换索引）
G4（信源准入合法）、G5（台账 schema）、G7（速测题占位注入）由后续 Task 逐步追加。

范式：与 scripts/test_tools.py 一致 —— errors: list[str] 收集错误，结尾统一 sys.exit(1)。
约束：零第三方依赖（仅标准库）；路径操作统一 pathlib.Path；零 Emoji。
"""

import datetime
import re
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent

ARTICLES_DIR = ROOT_DIR / "src" / "content" / "articles"
GLOSSARY_DIR = ROOT_DIR / "src" / "content" / "glossary"
QUIZ_FILE = ROOT_DIR / "src" / "data" / "dailyQuiz.ts"
ROTATION_FILE = ROOT_DIR / "src" / "data" / "rotation.ts"
INDEX_FILE = ROOT_DIR / "src" / "pages" / "index.astro"
DAILY_CARD_FILE = ROOT_DIR / "src" / "components" / "DailyCard.astro"

# 首页当日组合周期下限（一季）。与 src/data/rotation.ts 的 MIN_UNIQUE_CYCLE_DAYS 对齐。
MIN_UNIQUE_CYCLE_DAYS = 90


def _read_text(path: Path) -> str:
    """以 UTF-8 读取文本文件。"""
    return path.read_text(encoding="utf-8")


def _strip_ts_comments(source: str) -> str:
    """剥离 TypeScript 注释（块注释 + 行注释）与 HTML 注释。

    本函数同时被用于扫描 .astro 文件，故必须一并剥离 HTML 注释
    （``<!-- getTodayIndex(articles.length) -->`` 之类会造成假绿）；
    TS 块注释/行注释的剥离则避免把注释里的键误计入池规模。
    """
    without_html = re.sub(r"<!--.*?-->", "", source, flags=re.DOTALL)
    without_block = re.sub(r"/\*.*?\*/", "", without_html, flags=re.DOTALL)
    return re.sub(r"//[^\n]*", "", without_block)


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


def count_article_pool() -> int:
    """文章池规模：src/content/articles/*.mdx，排除以 '_' 开头的模板/草稿。"""
    if not ARTICLES_DIR.is_dir():
        return 0
    return sum(1 for path in ARTICLES_DIR.glob("*.mdx") if not path.name.startswith("_"))


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
    """词条池规模：src/content/glossary/*.md。"""
    if not GLOSSARY_DIR.is_dir():
        return 0
    return sum(1 for _ in GLOSSARY_DIR.glob("*.md"))


def article_slugs(directory: Path = ARTICLES_DIR) -> set:
    """文章 slug 集合：*.mdx 文件名（不含扩展名），排除以 '_' 开头的模板/草稿。"""
    if not directory.is_dir():
        return set()
    return {path.stem for path in directory.glob("*.mdx") if not path.name.startswith("_")}


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

    直接以 (26, 26)（lcm 坍缩回文章池自身）驱动 check_glossary_participation，
    断言其返回非空「假接入」错误；并以互不整除的 (26, 28) 作正向对照断言通过。
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

    print(
        f"[G2] 反向用例通过：(26,26) 检出 {len(collapsed)} 条「假接入」错误；"
        f"正向对照 (26,28) lcm=364 通过"
    )


def validate_self_checks(errors: list) -> None:
    """反向用例 + 空池/单元素边界自检（直接调用门禁纯函数，证明门禁本身有效）。"""
    # 反向用例①（同相位周期坍缩）：(26, 26) ⇒ lcm=26 < 90 且互相整除，必须返回非空错误。
    collapsed = check_cycle_threshold([26, 26], MIN_UNIQUE_CYCLE_DAYS)
    if not collapsed:
        errors.append(
            "反向用例失效：check_cycle_threshold([26,26], 90) 应返回非空错误列表"
            "（周期坍缩 + 同相位坍缩），实际为空"
        )
    print(
        f"[G3] 反向用例①通过：[26,26] 检出 {len(collapsed)} 条错误"
        f"（周期坍缩 + 同相位坍缩）"
    )

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


def validate_g6_article_sort_descending(errors: list) -> None:
    """G6 主断言⑥：index.astro 文章排序主键必须为 pubDate 降序（防符号翻转）。

    RED 事实（编排者 git 复核定性，非推测）：上一轮修订把比较器主键从
        b.data.pubDate.getTime() - a.data.pubDate.getTime()   // 降序（正确，最新文在索引 0）
    翻转为
        a.data.pubDate.getTime() - b.data.pubDate.getTime()   // 升序（错误，最旧文在索引 0）
    致使 articles[0] 由「最新文」变为「最旧文」，featuredArticle（今日精选）语义被改变，
    且骗过 astro check / build（均不校验排序方向）。

    降序形态 `b...getTime() - a...getTime()` 与升序形态 `a...getTime() - b...getTime()`
    互不为子串，可独立判别：必须命中降序形态，且不得命中升序形态。
    扫描前先 _strip_ts_comments 剥离注释，防止注释中的示例片段造成假绿/假红。
    """
    if not INDEX_FILE.is_file():
        errors.append(f"[G6] 首页文件缺失：{INDEX_FILE}")
        return

    source = _strip_ts_comments(_read_text(INDEX_FILE))
    descending = r"b\.data\.pubDate\.getTime\(\)\s*-\s*a\.data\.pubDate\.getTime\(\)"
    ascending = r"a\.data\.pubDate\.getTime\(\)\s*-\s*b\.data\.pubDate\.getTime\(\)"

    if re.search(ascending, source):
        errors.append(
            "[G6] index.astro 文章排序主键必须为 pubDate 降序（b - a）；"
            "当前为升序（a - b），会使「今日精选」指向最旧文章"
        )
        return
    if not re.search(descending, source):
        errors.append(
            "[G6] index.astro 文章排序主键缺失 pubDate 降序形态"
            "（b.data.pubDate.getTime() - a.data.pubDate.getTime()），"
            "排序方向不确定会使「今日精选」随实现漂移"
        )
        return

    print(
        "[G6] index.astro 文章排序主键降序契约通过"
        "（命中 b - a 降序；无 a - b 升序形态）"
    )


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


def run_gate() -> None:
    print("[gate] 每日循环不变量门禁 (Daily Loop Invariant Gate)")
    print("[gate] 已实现 G1（文章<->速测题 1:1）、G2（三池非空 + 词条池真参与周期）、G3（lcm(文章池, 词条池) -> >= 90 天不重复 + 两池不退化）与 G6（今日上新窗口 + 附加展示零扰动轮换索引）；G4/G5/G7 由后续 Task 追加。")

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
    validate_g6_article_sort_descending(errors)
    validate_g6_card_strip(errors)

    if errors:
        print(f"[FAIL] 每日循环不变量门禁未通过，发现 {len(errors)} 个问题：")
        for err in errors:
            print(f"   - {err}")
        sys.exit(1)

    print("[PASS] G1、G2、G3 与 G6 全绿：文章<->速测题 1:1；三池非空且词条池真参与周期；首页当日组合周期 lcm(文章池, 词条池) >= 90 天且两池不退化；今日上新窗口（第7天命中/第8天不命中）成立且仅作附加展示、轮换索引零扰动；反向用例与边界自检均通过。")


if __name__ == "__main__":
    run_gate()
