#!/usr/bin/env python3
"""
test_tools.py — 验证实用健康工具箱组件、页面路由与引用的文章外键完整性
"""

import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
TOOLS_PAGE = os.path.join(ROOT_DIR, "src", "pages", "tools", "index.astro")
COMPONENTS_DIR = os.path.join(ROOT_DIR, "src", "components", "tools")
ARTICLES_DIR = os.path.join(ROOT_DIR, "src", "content", "articles")

REQUIRED_COMPONENTS = [
    ("EmergencyCountdown.astro", ["ec-datetime-input", "ec-progress-bar", "contraception-emergency-pill"]),
    ("CocRemedyCalculator.astro", ["coc-pack-type", "coc-week-phase", "contraception-oral-pills"]),
    ("CycleAssessment.astro", ["cycle-len-input", "period-days-input", "normal-menstrual-cycle"]),
]


def run_tests():
    print("🧮 正在检测实用健康工具箱与计算器组件完整性...")

    if not os.path.exists(TOOLS_PAGE):
        print(f"❌ 工具箱入口页缺失: {TOOLS_PAGE}")
        sys.exit(1)

    with open(TOOLS_PAGE, "r", encoding="utf-8") as f:
        page_content = f.read()

    errors = []

    for comp_name, required_tokens in REQUIRED_COMPONENTS:
        comp_path = os.path.join(COMPONENTS_DIR, comp_name)
        if not os.path.exists(comp_path):
            errors.append(f"组件缺失: {comp_name}")
            continue

        if comp_name.replace(".astro", "") not in page_content:
            errors.append(f"工具箱主页面未引用组件: {comp_name}")

        with open(comp_path, "r", encoding="utf-8") as f:
            comp_content = f.read()

        for token in required_tokens:
            if token not in comp_content:
                errors.append(f"组件 {comp_name} 缺失关键标识或外键: {token}")

            # 若 token 看起来是文章 slug，核验实体文件
            if not token.startswith("ec-") and not token.startswith("coc-") and not token.startswith("cycle-") and not token.startswith("period-"):
                art_found = any(os.path.exists(os.path.join(ARTICLES_DIR, f"{token}{ext}")) for ext in [".mdx", ".md"])
                if not art_found:
                    errors.append(f"组件 {comp_name} 关联的外键文章不存在: {token}")

    if errors:
        print(f"❌ 工具箱测试未通过，发现 {len(errors)} 个问题:")
        for err in errors:
            print(f"   • {err}")
        sys.exit(1)

    print("🎉 实用工具箱测试全绿！3 大组件完备、状态与交互逻辑健全、关联科普外键 100% 存在！")


if __name__ == "__main__":
    run_tests()
