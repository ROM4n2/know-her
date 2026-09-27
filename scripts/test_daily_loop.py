#!/usr/bin/env python3
"""
test_daily_loop.py — 每日循环不变量门禁 (Daily Loop Invariant Gate)

守护「每天首页内容不重复」这一可判定的数学不变量：
    三池规模 (articles, quiz, glossary) -> 最小公倍数 lcm -> 不重复天数 >= MIN_UNIQUE_CYCLE_DAYS

当日三元组合指纹 (文章索引, 速测索引, 词条索引) 的重复周期 = lcm(三池规模)。
只要 lcm >= 3650（约 10 年），即可断言「工作日均首页新鲜」为可验证事实而非口号。

本文件当前仅实现 G3 组断言（池规模 -> lcm -> >= 3650 天不重复）。
G1（文章↔速测题 1:1）、G2（轮换池非空）、G4（信源准入合法）、
G5（台账 schema）、G6（今日上新窗口）、G7（速测题占位注入）由后续 Task 逐步追加。

范式：与 scripts/test_tools.py 一致 —— errors: list[str] 收集错误，结尾统一 sys.exit(1)。
约束：零第三方依赖（仅标准库）；路径操作统一 pathlib.Path；零 Emoji。
"""

import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent

ARTICLES_DIR = ROOT_DIR / "src" / "content" / "articles"
GLOSSARY_DIR = ROOT_DIR / "src" / "content" / "glossary"
QUIZ_FILE = ROOT_DIR / "src" / "data" / "dailyQuiz.ts"
ROTATION_FILE = ROOT_DIR / "src" / "data" / "rotation.ts"

# 组合指纹不重复天数下限（>= 10 年）。与 src/data/rotation.ts 的 MIN_UNIQUE_CYCLE_DAYS 对齐。
MIN_UNIQUE_CYCLE_DAYS = 3650


def _read_text(path: Path) -> str:
    """以 UTF-8 读取文本文件。"""
    return path.read_text(encoding="utf-8")


def _strip_ts_comments(source: str) -> str:
    """剥离 TypeScript 注释（块注释 + 行注释），避免把注释里的键误计入池规模。"""
    without_block = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    return re.sub(r"//[^\n]*", "", without_block)


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


def validate_g3_pool_cycle(errors: list) -> None:
    """G3 主断言：从真实文件统计三池规模，断言 lcm(sizes) >= MIN_UNIQUE_CYCLE_DAYS。"""
    sizes = [count_article_pool(), count_quiz_pool(), count_glossary_pool()]
    if min(sizes) < 1:
        errors.append(f"轮换池存在空池，无法计算组合指纹周期：articles/quiz/glossary = {sizes}")
        return

    cycle_days = lcm(sizes)
    print(f"[G3] 实际池规模 articles={sizes[0]} quiz={sizes[1]} glossary={sizes[2]}")
    print(
        f"[G3] 组合指纹不重复周期 = lcm({sizes}) = {cycle_days} 天"
        f"（阈值 {MIN_UNIQUE_CYCLE_DAYS}，达标={cycle_days >= MIN_UNIQUE_CYCLE_DAYS}）"
    )
    if cycle_days < MIN_UNIQUE_CYCLE_DAYS:
        errors.append(
            f"组合指纹不重复周期仅 {cycle_days} 天 < 门禁阈值 {MIN_UNIQUE_CYCLE_DAYS} 天；"
            f"请扩充内容池（当前池规模 {sizes}）"
        )


def validate_self_checks(errors: list) -> None:
    """反向用例 + 空池/单元素边界自检（证明门禁本身有效）。"""
    # 反向用例：池规模失衡使 lcm 跌破阈值，门禁必须能识别为「不达标」。
    bad_cycle = lcm([26, 25, 26])
    if bad_cycle >= MIN_UNIQUE_CYCLE_DAYS:
        errors.append(
            f"反向用例失效：失衡池 lcm([26,25,26])={bad_cycle} 应 < {MIN_UNIQUE_CYCLE_DAYS}"
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
        "export const MIN_UNIQUE_CYCLE_DAYS = 3650",
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


def run_gate() -> None:
    print("[gate] 每日循环不变量门禁 (Daily Loop Invariant Gate)")
    print("[gate] 本任务仅实现 G3（池规模 -> lcm -> >= 3650 天不重复）；G1/G2/G4/G5/G6/G7 由后续 Task 追加。")

    errors: list = []

    validate_g3_pool_cycle(errors)
    validate_self_checks(errors)
    validate_rotation_contract(errors)
    validate_daily_quiz_reexport(errors)

    if errors:
        print(f"[FAIL] 每日循环不变量门禁未通过，发现 {len(errors)} 个问题：")
        for err in errors:
            print(f"   - {err}")
        sys.exit(1)

    print("[PASS] G3 全绿：组合指纹不重复周期 >= 3650 天，反向用例与边界自检均通过。")


if __name__ == "__main__":
    run_gate()
