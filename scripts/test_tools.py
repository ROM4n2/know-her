#!/usr/bin/env python3
"""
test_tools.py — 验证实用健康工具箱组件、页面路由与引用的文章外键完整性
"""

import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
TOOLS_PAGE = os.path.join(ROOT_DIR, "src", "pages", "tools", "index.astro")
COMPONENTS_DIR = os.path.join(ROOT_DIR, "src", "components", "tools")
ARTICLES_DIR = os.path.join(ROOT_DIR, "src", "content", "articles")
DATA_DIR = os.path.join(ROOT_DIR, "src", "data")
CONTRACEPTION_DATA_FILE = os.path.join(DATA_DIR, "contraceptionMethods.ts")
CLINIC_DATA_FILE = os.path.join(DATA_DIR, "clinicQuestions.ts")
POSITION_DATA_FILE = os.path.join(DATA_DIR, "positionMatrix.ts")
CHECKLIST_DATA_FILE = os.path.join(DATA_DIR, "intimacyChecklist.ts")

REQUIRED_COMPONENTS = [
    ("EmergencyCountdown.astro", ["ec-datetime-input", "ec-progress-bar", "contraception-emergency-pill"]),
    ("CocRemedyCalculator.astro", ["coc-pack-type", "coc-week-phase", "contraception-oral-pills"]),
    ("CycleAssessment.astro", ["cycle-len-input", "period-days-input", "normal-menstrual-cycle"]),
    ("ArousalBrakesChecklist.astro", ["brakes-calc-container", "brakes-copy-btn", "pleasure-responsive-desire-dual-control"]),
    ("ClinicMemo.astro", ["clinic-memo-container", "clinic-copy-btn", "abnormal-uterine-bleeding"]),
    ("ContraceptionMatrix.astro", ["matrix-filter-container", "matrix-card", "contraception-condoms"]),
    ("PositionAndIntimacyGuide.astro", ["position-filter-container", "position-card", "intimacy-checklist-root", "pleasure-woman-on-top-mechanics"]),
]


def extract_array_block(content: str, const_name: str) -> str:
    """提取 TS 文件中指定导出的数组内容（包含方括号），自动处理嵌套与引号"""
    pattern = rf"export\s+const\s+{const_name}[^=]*=\s*\["
    m = re.search(pattern, content)
    if not m:
        return ""
    start_pos = m.end() - 1
    depth = 0
    in_string = False
    quote_char = ""
    i = start_pos
    while i < len(content):
        c = content[i]
        if in_string:
            if c == "\\":
                i += 2
                continue
            if c == quote_char:
                in_string = False
            i += 1
            continue
        if c in ("'", '"', '`'):
            in_string = True
            quote_char = c
            i += 1
            continue
        if c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                return content[start_pos : i + 1]
        i += 1
    return ""


def extract_objects_from_array(array_str: str) -> list:
    """从 TS 数组文本中提取所有顶级对象字符串"""
    objects = []
    brace_depth = 0
    in_string = False
    quote_char = ''
    start_pos = -1

    i = 0
    while i < len(array_str):
        c = array_str[i]
        if in_string:
            if c == '\\':
                i += 2
                continue
            if c == quote_char:
                in_string = False
            i += 1
            continue

        if c in ("'", '"', '`'):
            in_string = True
            quote_char = c
            i += 1
            continue

        if c == '{':
            if brace_depth == 0:
                start_pos = i
            brace_depth += 1
        elif c == '}':
            brace_depth -= 1
            if brace_depth == 0 and start_pos != -1:
                objects.append(array_str[start_pos:i+1])
                start_pos = -1
        i += 1

    return objects


def validate_contraception_data(errors: list):
    """验证避孕全景数据集契约"""
    if not os.path.exists(CONTRACEPTION_DATA_FILE):
        errors.append(f"避孕数据集文件缺失: {CONTRACEPTION_DATA_FILE}")
        return

    with open(CONTRACEPTION_DATA_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    if "CONTRACEPTION_METHODS" not in content or "export const CONTRACEPTION_METHODS" not in content:
        errors.append("contraceptionMethods.ts 未导出 CONTRACEPTION_METHODS")
        return

    arr_str = extract_array_block(content, "CONTRACEPTION_METHODS")
    if not arr_str:
        errors.append("无法解析 CONTRACEPTION_METHODS 数组内容")
        return

    methods = extract_objects_from_array(arr_str)
    if len(methods) < 10:
        errors.append(f"CONTRACEPTION_METHODS 包含的避孕方式不足 10 种，当前为 {len(methods)} 种")

    required_fields = [
        "id", "name", "category", "failure_rate_typical",
        "failure_rate_perfect", "duration", "protects_sti",
        "hormone_type", "related_article"
    ]

    for idx, block in enumerate(methods):
        for field in required_fields:
            if not re.search(rf"\b{field}\s*:", block):
                errors.append(f"避孕方式 [索引 {idx}] 缺失必要字段: '{field}'")

        art_match = re.search(r"\brelated_article\s*:\s*['\"]([^'\"]+)['\"]", block)
        if art_match:
            slug = art_match.group(1).strip()
            art_found = any(os.path.exists(os.path.join(ARTICLES_DIR, f"{slug}{ext}")) for ext in [".mdx", ".md"])
            if not art_found:
                errors.append(f"避孕方式 [索引 {idx}] 关联的外键文章不存在: {slug}")
        else:
            errors.append(f"避孕方式 [索引 {idx}] 未能解析出 related_article 值")


def validate_clinic_data(errors: list):
    """验证门诊就医问诊知识库契约"""
    if not os.path.exists(CLINIC_DATA_FILE):
        errors.append(f"就医问诊数据集文件缺失: {CLINIC_DATA_FILE}")
        return

    with open(CLINIC_DATA_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    if "CLINIC_SYMPTOM_CONFIGS" not in content or "export const CLINIC_SYMPTOM_CONFIGS" not in content:
        errors.append("clinicQuestions.ts 未导出 CLINIC_SYMPTOM_CONFIGS")
        return

    if "RED_FLAG_SYMPTOMS" not in content or "export const RED_FLAG_SYMPTOMS" not in content:
        errors.append("clinicQuestions.ts 未导出 RED_FLAG_SYMPTOMS")
        return

    arr_symptoms = extract_array_block(content, "CLINIC_SYMPTOM_CONFIGS")
    if not arr_symptoms:
        errors.append("无法解析 CLINIC_SYMPTOM_CONFIGS 数组定义")
    else:
        symptoms = extract_objects_from_array(arr_symptoms)
        if len(symptoms) != 4:
            errors.append(f"CLINIC_SYMPTOM_CONFIGS 应包含 4 大主诉，当前为 {len(symptoms)} 个")

        for idx, block in enumerate(symptoms):
            for field in ["id", "title", "relatedArticle"]:
                if not re.search(rf"\b{field}\s*:", block):
                    errors.append(f"主诉配置 [索引 {idx}] 缺失必要字段: '{field}'")

            art_match = re.search(r"\brelatedArticle\s*:\s*['\"]([^'\"]+)['\"]", block)
            if art_match:
                slug = art_match.group(1).strip()
                art_found = any(os.path.exists(os.path.join(ARTICLES_DIR, f"{slug}{ext}")) for ext in [".mdx", ".md"])
                if not art_found:
                    errors.append(f"主诉配置 [索引 {idx}] 关联的外键文章不存在: {slug}")
            else:
                errors.append(f"主诉配置 [索引 {idx}] 未能解析出 relatedArticle 值")

    arr_redflags = extract_array_block(content, "RED_FLAG_SYMPTOMS")
    if not arr_redflags:
        errors.append("无法解析 RED_FLAG_SYMPTOMS 数组定义")
    else:
        redflags = extract_objects_from_array(arr_redflags)
        if len(redflags) < 3:
            errors.append(f"RED_FLAG_SYMPTOMS 必须包含至少 3 个急腹症红旗预警，当前为 {len(redflags)} 个")
        for idx, block in enumerate(redflags):
            if not re.search(r"\bid\s*:", block):
                errors.append(f"急腹症红旗预警 [索引 {idx}] 缺失 'id' 字段")


def validate_position_data(errors: list):
    """验证体位力学全景数据集契约"""
    if not os.path.exists(POSITION_DATA_FILE):
        errors.append(f"体位力学数据集文件缺失: {POSITION_DATA_FILE}")
        return

    with open(POSITION_DATA_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    if "POSITION_METHODS" not in content or "export const POSITION_METHODS" not in content:
        errors.append("positionMatrix.ts 未导出 POSITION_METHODS")
        return

    arr_str = extract_array_block(content, "POSITION_METHODS")
    if not arr_str:
        errors.append("无法解析 POSITION_METHODS 数组内容")
        return

    positions = extract_objects_from_array(arr_str)
    if len(positions) < 8:
        errors.append(f"POSITION_METHODS 包含的体位不足 8 种，当前为 {len(positions)} 种")

    required_fields = [
        "id", "name", "en_name", "category",
        "clitoral_access", "cervical_collision_risk", "energy_expenditure",
        "pelvic_support_advice", "coital_angle_desc", "pros", "cons",
        "communication_tip", "related_article"
    ]

    for idx, block in enumerate(positions):
        for field in required_fields:
            if not re.search(rf"\b{field}\s*:", block):
                errors.append(f"体位力学数据 [索引 {idx}] 缺失必要字段: '{field}'")

        art_match = re.search(r"\brelated_article\s*:\s*['\"]([^'\"]+)['\"]", block)
        if art_match:
            slug = art_match.group(1).strip()
            art_found = any(os.path.exists(os.path.join(ARTICLES_DIR, f"{slug}{ext}")) for ext in [".mdx", ".md"])
            if not art_found:
                errors.append(f"体位力学数据 [索引 {idx}] 关联的外键文章不存在: {slug}")
        else:
            errors.append(f"体位力学数据 [索引 {idx}] 未能解析出 related_article 值")


def validate_checklist_data(errors: list):
    """验证伴侣知情探索题库契约"""
    if not os.path.exists(CHECKLIST_DATA_FILE):
        errors.append(f"伴侣知情清单数据集文件缺失: {CHECKLIST_DATA_FILE}")
        return

    with open(CHECKLIST_DATA_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    if "INTIMACY_CHECKLIST_CONFIGS" not in content or "export const INTIMACY_CHECKLIST_CONFIGS" not in content:
        errors.append("intimacyChecklist.ts 未导出 INTIMACY_CHECKLIST_CONFIGS")
        return

    arr_str = extract_array_block(content, "INTIMACY_CHECKLIST_CONFIGS")
    if not arr_str:
        errors.append("无法解析 INTIMACY_CHECKLIST_CONFIGS 数组内容")
        return

    categories = extract_objects_from_array(arr_str)
    if len(categories) < 5:
        errors.append(f"INTIMACY_CHECKLIST_CONFIGS 包含的分类不足 5 个，当前为 {len(categories)} 个")

    category_fields = ["id", "name", "description", "items"]
    item_fields = ["id", "title", "physiological_reason", "suggestion_text"]
    total_items_count = 0

    for cat_idx, cat_block in enumerate(categories):
        for field in category_fields:
            if not re.search(rf"\b{field}\s*:", cat_block):
                errors.append(f"清单分类 [索引 {cat_idx}] 缺失必要字段: '{field}'")

        items_arr_match = re.search(r"\bitems\s*:\s*\[", cat_block)
        if not items_arr_match:
            errors.append(f"清单分类 [索引 {cat_idx}] 未能定位 items 数组")
            continue

        start_pos = items_arr_match.end() - 1
        depth = 0
        in_string = False
        quote_char = ""
        items_arr_str = ""
        i = start_pos
        while i < len(cat_block):
            c = cat_block[i]
            if in_string:
                if c == "\\":
                    i += 2
                    continue
                if c == quote_char:
                    in_string = False
                i += 1
                continue
            if c in ("'", '"', '`'):
                in_string = True
                quote_char = c
                i += 1
                continue
            if c == "[":
                depth += 1
            elif c == "]":
                depth -= 1
                if depth == 0:
                    items_arr_str = cat_block[start_pos : i + 1]
                    break
            i += 1

        if not items_arr_str:
            errors.append(f"清单分类 [索引 {cat_idx}] 无法解析 items 数组结构")
            continue

        items = extract_objects_from_array(items_arr_str)
        total_items_count += len(items)

        for item_idx, item_block in enumerate(items):
            for field in item_fields:
                if not re.search(rf"\b{field}\s*:", item_block):
                    errors.append(f"清单分类 [索引 {cat_idx}] 题目项 [索引 {item_idx}] 缺失字段: '{field}'")

    if total_items_count < 15:
        errors.append(f"INTIMACY_CHECKLIST_CONFIGS 包含的题目项不足 15 项，当前共 {total_items_count} 项")


def run_tests():
    print("🧮 正在检测实用健康工具箱、避孕数据集与问诊契约完整性...")

    if not os.path.exists(TOOLS_PAGE):
        print(f"❌ 工具箱入口页缺失: {TOOLS_PAGE}")
        sys.exit(1)

    with open(TOOLS_PAGE, "r", encoding="utf-8") as f:
        page_content = f.read()

    errors = []

    # 1. 验证已有实用组件
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
            if (
                not token.startswith("ec-")
                and not token.startswith("coc-")
                and not token.startswith("cycle-")
                and not token.startswith("period-")
                and not token.startswith("brakes-")
                and not token.startswith("clinic-")
                and not token.startswith("matrix-")
                and not token.startswith("position-")
                and not token.startswith("intimacy-")
            ):
                art_found = any(os.path.exists(os.path.join(ARTICLES_DIR, f"{token}{ext}")) for ext in [".mdx", ".md"])
                if not art_found:
                    errors.append(f"组件 {comp_name} 关联的外键文章不存在: {token}")

    # 2. 验证避孕数据集契约
    validate_contraception_data(errors)

    # 3. 验证就医问诊契约
    validate_clinic_data(errors)

    # 4. 验证体位力学数据集契约
    validate_position_data(errors)

    # 5. 验证伴侣知情探索契约
    validate_checklist_data(errors)

    if errors:
        print(f"❌ 工具箱与数据契约测试未通过，发现 {len(errors)} 个问题:")
        for err in errors:
            print(f"   • {err}")
        sys.exit(1)

    print(f"🎉 实用工具箱与数据契约测试全绿！组件、避孕全景数据、就诊问诊知识库、体位力学与伴侣清单 100% 合规！")


if __name__ == "__main__":
    run_tests()
