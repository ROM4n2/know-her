#!/usr/bin/env python3
"""
test_decision_tree.py — 决策树图连通性与数据完整性自动化测试
确保决策树无死胡同、无悬空节点、无无效文章链接。
"""

import json
import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
DATA_FILE = os.path.join(ROOT_DIR, "src", "data", "decisionTree.ts")
ARTICLES_DIR = os.path.join(ROOT_DIR, "src", "content", "articles")


def extract_json_from_ts(ts_content: str) -> dict:
    """提取 TS 文件中导出的 DECISION_TREE 对象并解析"""
    # 查找 export const DECISION_TREE: DecisionTreeData = { ... };
    m = re.search(r"export\s+const\s+DECISION_TREE\s*(?::\s*DecisionTreeData\s*)?=\s*({[\s\S]*});?\s*$", ts_content)
    if not m:
        # 尝试更宽泛的正则
        m = re.search(r"export\s+const\s+DECISION_TREE\s*=\s*({[\s\S]*?});?\s*$", ts_content, re.MULTILINE)
    if not m:
        raise ValueError("无法在 decisionTree.ts 中匹配到 DECISION_TREE 常量定义")

    raw_js = m.group(1).strip()
    # 移除行内注释 //
    raw_js = re.sub(r"//.*$", "", raw_js, flags=re.MULTILINE)
    # 移除多行注释 /* ... */
    raw_js = re.sub(r"/\*[\s\S]*?\*/", "", raw_js)
    # 将 JS key 转化为有效 JSON 引号: key: -> "key":
    raw_js = re.sub(r"([{,]\s*)([a-zA-Z0-9_]+)\s*:", r'\1"\2":', raw_js)
    # 移除末尾逗号: , } -> }
    raw_js = re.sub(r",\s*([}\]])", r"\1", raw_js)

    return json.loads(raw_js)


def run_tests():
    if not os.path.exists(DATA_FILE):
        print(f"❌ 数据文件不存在: {DATA_FILE}")
        sys.exit(1)

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    try:
        data = extract_json_from_ts(content)
    except Exception as e:
        print(f"❌ TS 语法/提取 JSON 失败: {e}")
        sys.exit(1)

    categories = data.get("initialCategories", [])
    nodes = data.get("nodes", {})
    outcomes = data.get("outcomes", {})

    print(f"📊 正在检测决策树: {len(categories)} 大类, {len(nodes)} 个问题节点, {len(outcomes)} 个结果行动卡...")

    assert len(categories) >= 3, "必须包含至少 3 个核心应急大类"
    assert len(nodes) >= 6, "必须包含至少 6 个分支判定节点"
    assert len(outcomes) >= 8, "必须包含至少 8 个明确的行动决策卡"

    errors = []
    visited_nodes = set()
    visited_outcomes = set()

    # 1. 验证分类起始点
    for cat in categories:
        start_id = cat.get("startNodeId")
        if start_id not in nodes:
            errors.append(f"分类 [{cat.get('title')}] 的起始节点 '{start_id}' 不存在于 nodes 中")
        else:
            visited_nodes.add(start_id)

    # 2. 遍历所有节点与边
    for node_id, node in nodes.items():
        options = node.get("options", [])
        if not options:
            errors.append(f"节点 '{node_id}' 没有配置任何选项 (options)")

        for opt_idx, opt in enumerate(options):
            next_node = opt.get("nextNodeId")
            outcome_id = opt.get("outcomeId")

            if not next_node and not outcome_id:
                errors.append(f"节点 '{node_id}' 的选项 {opt_idx}既无 nextNodeId 也无 outcomeId (死胡同)")

            if next_node:
                if next_node not in nodes:
                    errors.append(f"节点 '{node_id}' 指向的下个节点 '{next_node}' 不存在")
                else:
                    visited_nodes.add(next_node)

            if outcome_id:
                if outcome_id not in outcomes:
                    errors.append(f"节点 '{node_id}' 指向的结果卡 '{outcome_id}' 不存在")
                else:
                    visited_outcomes.add(outcome_id)

    # 3. 验证是否有未抵达的孤儿节点
    orphan_nodes = set(nodes.keys()) - visited_nodes
    if orphan_nodes:
        errors.append(f"发现无法抵达的孤儿节点: {orphan_nodes}")

    unreachable_outcomes = set(outcomes.keys()) - visited_outcomes
    if unreachable_outcomes:
        errors.append(f"发现无法抵达的结果卡: {unreachable_outcomes}")

    # 4. 验证关联文章链接
    for out_id, outcome in outcomes.items():
        slug = outcome.get("relatedArticleSlug")
        if slug:
            article_path = os.path.join(ARTICLES_DIR, f"{slug}.mdx")
            if not os.path.exists(article_path):
                errors.append(f"结果卡 '{out_id}' 关联的科普词条不存在: {slug}.mdx")

    if errors:
        print(f"\n❌ 发现 {len(errors)} 个结构或图连通性错误：")
        for err in errors:
            print(f"  • {err}")
        sys.exit(1)

    print("🎉 决策树全图连通性测试通过！无孤立节点、无死胡同选项、关联词条均 100% 存在！")


if __name__ == "__main__":
    run_tests()
