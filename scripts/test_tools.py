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
DECISION_TREE_FILE = os.path.join(DATA_DIR, "decisionTree.ts")
DECISION_GUIDE_COMPONENT = os.path.join(ROOT_DIR, "src", "components", "DecisionGuide.astro")
MEMO_EXPORTER_FILE = os.path.join(ROOT_DIR, "src", "lib", "ui", "memoImageExporter.ts")
SEARCH_COMPONENT = os.path.join(ROOT_DIR, "src", "components", "Search.astro")
ARTICLE_DETAIL_PAGE = os.path.join(ROOT_DIR, "src", "pages", "articles", "[id].astro")

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


def validate_floating_bars(errors: list):
    """验证悬浮对比条容器在移动端的吸底避让 (bottom-20)"""
    bars = [
        ("ContraceptionMatrix.astro", "matrix-floating-bar"),
        ("PositionAndIntimacyGuide.astro", "position-floating-bar"),
    ]
    for comp_name, bar_id in bars:
        comp_path = os.path.join(COMPONENTS_DIR, comp_name)
        if not os.path.exists(comp_path):
            errors.append(f"组件缺失: {comp_name}")
            continue
        with open(comp_path, "r", encoding="utf-8") as f:
            content = f.read()
        match = re.search(rf'<div[^>]*id=["\']{bar_id}["\'][^>]*>', content, re.DOTALL)
        if not match or "bottom-20" not in match.group(0):
            errors.append(f"组件 {comp_name} 的悬浮对比条 (#{bar_id}) 缺失 'bottom-20' 移动端避让类名")


def validate_cross_tool_handoff(errors: list, page_content: str):
    """验证决策树与工具箱之间的 URL 参数状态透传契约"""
    # 1. 工具箱页面必须包含 URLSearchParams 参数解析逻辑
    if "URLSearchParams" not in page_content:
        errors.append("工具箱主页面 (tools/index.astro) 缺失 URLSearchParams 参数解析处理逻辑")

    # 2. 工具箱页面必须实现 tool -> 锚点平滑滚动映射与参数预填
    for token in ["sec-ec-countdown", "sec-clinic-memo"]:
        if token not in page_content:
            errors.append(f"工具箱主页面缺失工具锚点: {token}")

    # 3. 决策树数据必须至少配置 4 个 directToolLink 直达工具
    if not os.path.exists(DECISION_TREE_FILE):
        errors.append(f"决策树数据文件缺失: {DECISION_TREE_FILE}")
    else:
        with open(DECISION_TREE_FILE, "r", encoding="utf-8") as f:
            tree_content = f.read()

        if "directToolLink" not in tree_content:
            errors.append("decisionTree.ts 未定义 directToolLink 字段")
        else:
            link_count = len(re.findall(r"\bdirectToolLink\s*:", tree_content))
            if link_count < 4:
                errors.append(
                    f"decisionTree.ts 配置 directToolLink 的结果卡不足 4 个，当前为 {link_count} 个"
                )

        if "export interface DecisionOutcome" in tree_content and not re.search(
            r"directToolLink\?\s*:\s*\{", tree_content
        ):
            errors.append("decisionTree.ts 的 DecisionOutcome 接口未声明 directToolLink 可选字段")

    # 4. 决策树组件必须渲染直达工具按钮
    if not os.path.exists(DECISION_GUIDE_COMPONENT):
        errors.append(f"决策树组件缺失: {DECISION_GUIDE_COMPONENT}")
    else:
        with open(DECISION_GUIDE_COMPONENT, "r", encoding="utf-8") as f:
            guide_content = f.read()
        for token in ["dg-tool-link", "directToolLink"]:
            if token not in guide_content:
                errors.append(f"DecisionGuide.astro 缺失跨工具直达元素或字段引用: {token}")


def validate_emergency_localization(errors: list):
    """验证紧急避孕本土药品可及性校准与 2 小时服药吸收观察计时器契约"""
    comp_path = os.path.join(COMPONENTS_DIR, "EmergencyCountdown.astro")
    if not os.path.exists(comp_path):
        errors.append("组件缺失: EmergencyCountdown.astro")
        return

    with open(comp_path, "r", encoding="utf-8") as f:
        content = f.read()

    required_tokens = [
        "ec-vomit-timer-container",
        "ec-vomit-timer-btn",
        "ec-vomit-timer-display",
        "金毓婷",
        "暂未普及",
        "米非司酮",
    ]
    for token in required_tokens:
        if token not in content:
            errors.append(f"EmergencyCountdown.astro 缺失本土化用药或计时器标识: {token}")

    if "2 小时" not in content and "2小时" not in content:
        errors.append("EmergencyCountdown.astro 缺失服药后 2 小时胃部吸收观察的循证说明")


def validate_memo_image_exporter(errors: list):
    """验证纯前端零依赖 Canvas 纸墨风格便签长图导出器契约"""
    if not os.path.exists(MEMO_EXPORTER_FILE):
        errors.append(f"便签长图导出器缺失: {MEMO_EXPORTER_FILE}")
    else:
        with open(MEMO_EXPORTER_FILE, "r", encoding="utf-8") as f:
            exporter_content = f.read()

        for token in ["exportMemoAsImage", "MemoExportOptions", "toBlob", "createElement('canvas')"]:
            if token not in exporter_content:
                errors.append(f"memoImageExporter.ts 缺失必要实现标识: {token}")

        if "devicePixelRatio" not in exporter_content:
            errors.append("memoImageExporter.ts 未按设备像素比 (DPR) 渲染高清长图")

        # 零第三方重型依赖守卫：禁止引入 html2canvas 等外部库
        for forbidden in ["html2canvas", "dom-to-image", "import("]:
            if forbidden in exporter_content:
                errors.append(f"memoImageExporter.ts 引入了违规重型依赖: {forbidden}")

    # 两个便签组件必须接入保存长图按钮
    for comp_name in ["ClinicMemo.astro", "PositionAndIntimacyGuide.astro"]:
        comp_path = os.path.join(COMPONENTS_DIR, comp_name)
        if not os.path.exists(comp_path):
            errors.append(f"组件缺失: {comp_name}")
            continue
        with open(comp_path, "r", encoding="utf-8") as f:
            comp_content = f.read()
        for token in ["memo-export-image-btn", "memoImageExporter"]:
            if token not in comp_content:
                errors.append(f"组件 {comp_name} 缺失便签长图导出接入标识: {token}")


def validate_search_intent_pills(errors: list):
    """验证首页突发场景意图搜索胶囊与长文医学名词速查悬浮预览契约"""
    required_intents = [
        "避孕套滑脱破损",
        "紧急避孕",
        "漏服短效口服药",
        "异常褐血与月经紊乱",
        "同房疼痛与痉挛",
        "怎么跟医生讲主诉",
    ]

    if not os.path.exists(SEARCH_COMPONENT):
        errors.append(f"搜索组件缺失: {SEARCH_COMPONENT}")
    else:
        with open(SEARCH_COMPONENT, "r", encoding="utf-8") as f:
            search_content = f.read()

        if "search-intent-pills" not in search_content:
            errors.append("Search.astro 缺失高频场景意图胶囊容器: search-intent-pills")

        if not re.search(r"\bintent-pill\b", search_content):
            errors.append("Search.astro 缺失意图胶囊样式钩子: intent-pill")

        missing_intents = [intent for intent in required_intents if intent not in search_content]
        if missing_intents:
            errors.append(
                f"Search.astro 高频突发场景意图胶囊不足 6 个，缺失: {'、'.join(missing_intents)}"
            )

        # 意图胶囊必须指向站内真实路由（决策树 / 工具箱 / 词条 / 科普详情）
        for route_fragment in ["guide/decision-tree", "tools/?tool=", "articles/"]:
            if route_fragment not in search_content:
                errors.append(f"Search.astro 意图胶囊缺失站内直达路由片段: {route_fragment}")

    if not os.path.exists(ARTICLE_DETAIL_PAGE):
        errors.append(f"文章详情页缺失: {ARTICLE_DETAIL_PAGE}")
    else:
        with open(ARTICLE_DETAIL_PAGE, "r", encoding="utf-8") as f:
            article_content = f.read()

        for token in ["glossary-inline-term", "glossary-inline-badge"]:
            if token not in article_content:
                errors.append(f"articles/[id].astro 缺失医学名词 In-situ 速查微标签: {token}")


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

    # 6. 验证移动端吸底避让样式 (floating bars)
    validate_floating_bars(errors)

    # 7. 验证决策树与工具箱跨工具状态透传契约
    validate_cross_tool_handoff(errors, page_content)

    # 8. 验证紧急避孕本土化用药指引与 2 小时服药观察计时器
    validate_emergency_localization(errors)

    # 9. 验证纯前端 Canvas 便签长图导出器契约
    validate_memo_image_exporter(errors)

    # 10. 验证首页突发场景意图胶囊与长文医学名词速查悬浮预览
    validate_search_intent_pills(errors)

    if errors:
        print(f"❌ 工具箱与数据契约测试未通过，发现 {len(errors)} 个问题:")
        for err in errors:
            print(f"   • {err}")
        sys.exit(1)

    print(f"🎉 实用工具箱与数据契约测试全绿！组件、避孕全景数据、就诊问诊知识库、体位力学与伴侣清单 100% 合规！")


if __name__ == "__main__":
    run_tests()
