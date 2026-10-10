#!/usr/bin/env python3
"""
scripts/test_pwa_contracts.py — PWA 规范基建与离线急救缓存系统契约测试

覆盖契约：
1. Web Manifest (public/manifest.webmanifest):
   - 存在且为有效 JSON
   - 包含 name, short_name, start_url, display: standalone, background_color, theme_color
   - icons 列表中包含 192x192 与 512x512 尺寸声明，且对应的本地静态文件存在
2. Service Worker (public/sw.js):
   - 存在且包含缓存版本定义 (如 know-her-v)
   - 包含 install, activate, fetch 事件监听
   - 预缓存核心离线急救工具资源 (tools/, guide/decision-tree/)
   - 实现离线缓存策略 (cache-first / stale-while-revalidate 及 network fallback)
3. 根布局绑定 (src/layouts/Base.astro):
   - <head> 声明 <link rel="manifest" href=...manifest.webmanifest...>
   - 包含 theme-color 标签
   - 包含 'serviceWorker' in navigator 的注册脚本并定位至 ${base}sw.js
4. 构建与回归脚本 (package.json):
   - test:graph 中包含 test_pwa_contracts.py 执行命令
"""

import json
import os
import re
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST_FILE = os.path.join(PROJECT_ROOT, "public", "manifest.webmanifest")
SW_FILE = os.path.join(PROJECT_ROOT, "public", "sw.js")
BASE_LAYOUT_FILE = os.path.join(PROJECT_ROOT, "src", "layouts", "Base.astro")
PACKAGE_JSON_FILE = os.path.join(PROJECT_ROOT, "package.json")
PUBLIC_DIR = os.path.join(PROJECT_ROOT, "public")


def test_manifest_contract():
    errors = []
    print("📱 [1/4] 检验 public/manifest.webmanifest PWA 规范契约...")

    if not os.path.isfile(MANIFEST_FILE):
        return [f"缺失 Manifest 配置文件: {MANIFEST_FILE}"]

    try:
        with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return [f"Manifest 文件 JSON 解析失败: {e}"]

    # 1. 基础字段
    if not data.get("name") or "know-her" not in data.get("name", ""):
        errors.append(f"manifest.name 必须非空且包含 'know-her'，当前为: {data.get('name')}")

    if not data.get("short_name") or "know-her" not in data.get("short_name", ""):
        errors.append(f"manifest.short_name 必须非空且包含 'know-her'，当前为: {data.get('short_name')}")

    start_url = data.get("start_url", "")
    if not (start_url == "/know-her/tools/" or "/tools/" in start_url or start_url == "/know-her/"):
        errors.append(f"manifest.start_url 预期包含 /know-her/tools/，当前为: '{start_url}'")

    if data.get("display") != "standalone":
        errors.append(f"manifest.display 必须为 'standalone'，当前为: '{data.get('display')}'")

    bg_color = str(data.get("background_color", "")).upper()
    if bg_color != "#FAF8F5":
        errors.append(f"manifest.background_color 必须为 '#FAF8F5'，当前为: '{data.get('background_color')}'")

    theme_color = str(data.get("theme_color", "")).upper()
    if theme_color != "#FAF8F5":
        errors.append(f"manifest.theme_color 必须为 '#FAF8F5'，当前为: '{data.get('theme_color')}'")

    # 2. icons 字段
    icons = data.get("icons")
    if not isinstance(icons, list) or len(icons) == 0:
        errors.append("manifest.icons 必须是非空列表")
    else:
        has_192 = False
        has_512 = False
        for idx, icon in enumerate(icons):
            sizes = icon.get("sizes", "")
            if "192x192" in sizes:
                has_192 = True
            if "512x512" in sizes:
                has_512 = True
            src = icon.get("src", "")
            if not src:
                errors.append(f"manifest.icons[{idx}] 缺少 src")
            else:
                # 检查图标文件在 public 目录下的物理映射
                clean_src = src.replace("/know-her/", "").lstrip("/")
                local_icon_path = os.path.join(PUBLIC_DIR, clean_src)
                if not os.path.isfile(local_icon_path):
                    errors.append(f"manifest.icons[{idx}] 声明的图标物理文件不存在: {local_icon_path} (src: {src})")

        if not has_192:
            errors.append("manifest.icons 缺少 192x192 规格图标声明")
        if not has_512:
            errors.append("manifest.icons 缺少 512x512 规格图标声明")

    if not errors:
        print("   ✅ Manifest 格式、主色彩、start_url 与多尺寸图标规范完整")
    return errors


def test_service_worker_contract():
    errors = []
    print("⚙️  [2/4] 检验 public/sw.js 离线急救 Service Worker 契约...")

    if not os.path.isfile(SW_FILE):
        return [f"缺失 Service Worker 文件: {SW_FILE}"]

    with open(SW_FILE, "r", encoding="utf-8") as f:
        sw_code = f.read()

    # 1. 缓存版本名称
    if not re.search(r"know-her.*v\d+", sw_code, re.IGNORECASE):
        errors.append("sw.js 必须包含缓存版本定义 (匹配 pattern: know-her.*v\\d+)")

    # 2. 生命周期事件监听
    for event in ["install", "activate", "fetch"]:
        if f"addEventListener('{event}'" not in sw_code and f'addEventListener("{event}"' not in sw_code:
            errors.append(f"sw.js 缺少 '{event}' 生命周期事件监听 (addEventListener('{event}', ...))")

    # 3. 预缓存离线急救工具
    required_cache_paths = ["tools/", "guide/decision-tree/"]
    for path in required_cache_paths:
        if path not in sw_code:
            errors.append(f"sw.js 预缓存清单必须包含离线急救路径: '{path}'")

    # 4. 离线策略关键字
    has_cache_strategy = (
        ("cache.match" in sw_code or "caches.match" in sw_code)
        and "fetch" in sw_code
        and ("cache.put" in sw_code or "caches.open" in sw_code)
    )
    if not has_cache_strategy:
        errors.append("sw.js 必须具备缓存匹配 (cache.match)、网络拉取与写入的策略逻辑")

    # 5. 旧缓存清理
    has_cleanup = bool(
        re.search(r"caches\s*\.\s*keys", sw_code) and re.search(r"caches\s*\.\s*delete", sw_code)
    )
    if not has_cleanup:
        errors.append("sw.js activate 事件中必须包含遍历 (caches.keys) 并清理旧缓存 (caches.delete) 的逻辑")

    if not errors:
        print("   ✅ Service Worker 生命周期、离线预缓存与失效清理逻辑完整")
    return errors


def test_base_layout_contract():
    errors = []
    print("🌐 [3/4] 检验 src/layouts/Base.astro PWA 声明与注册脚本...")

    if not os.path.isfile(BASE_LAYOUT_FILE):
        return [f"缺失根布局文件: {BASE_LAYOUT_FILE}"]

    with open(BASE_LAYOUT_FILE, "r", encoding="utf-8") as f:
        layout_code = f.read()

    # 1. manifest 引用
    manifest_link_pattern = r'<link\s+[^>]*rel=["\']manifest["\'][^>]*manifest\.webmanifest'
    if not re.search(manifest_link_pattern, layout_code):
        errors.append("Base.astro <head> 必须包含链接至 manifest.webmanifest 的 <link rel=\"manifest\" ...>")

    # 2. theme-color 标签
    theme_color_pattern = r'<meta\s+[^>]*name=["\']theme-color["\'][^>]*content=["\']#FAF8F5["\']'
    if not re.search(theme_color_pattern, layout_code, re.IGNORECASE):
        errors.append("Base.astro <head> 必须包含 <meta name=\"theme-color\" content=\"#FAF8F5\" />")

    # 3. Service Worker 注册脚本
    if "'serviceWorker' in navigator" not in layout_code and '"serviceWorker" in navigator' not in layout_code:
        errors.append("Base.astro 必须包含带有 'serviceWorker' in navigator 的特征注册脚本")

    if "sw.js" not in layout_code:
        errors.append("Base.astro 中的 serviceWorker.register 目标必须包含 sw.js")

    if not errors:
        print("   ✅ Base.astro manifest 链接、theme-color 元标签与 sw.js 注册脚本就绪")
    return errors


def test_package_json_contract():
    errors = []
    print("📦 [4/4] 检验 package.json test:graph 脚本串联...")

    if not os.path.isfile(PACKAGE_JSON_FILE):
        return [f"缺失 package.json 文件: {PACKAGE_JSON_FILE}"]

    try:
        with open(PACKAGE_JSON_FILE, "r", encoding="utf-8") as f:
            pkg = json.load(f)
    except Exception as e:
        return [f"package.json JSON 解析失败: {e}"]

    test_graph = pkg.get("scripts", {}).get("test:graph", "")
    if "scripts/test_pwa_contracts.py" not in test_graph:
        errors.append("package.json 的 scripts['test:graph'] 必须包含 'python -X utf8 scripts/test_pwa_contracts.py'")

    if not errors:
        print("   ✅ package.json 成功注册 test_pwa_contracts.py 到自动化测试链路")
    return errors


def main():
    print("=" * 60)
    print("🚀 开始执行 know-her PWA 规范与离线急救缓存系统契约检验")
    print("=" * 60)

    all_errors = []
    all_errors.extend(test_manifest_contract())
    all_errors.extend(test_service_worker_contract())
    all_errors.extend(test_base_layout_contract())
    all_errors.extend(test_package_json_contract())

    print("=" * 60)
    if all_errors:
        print(f"❌ PWA 契约检验失败，发现 {len(all_errors)} 处不符合项：")
        for idx, err in enumerate(all_errors, 1):
            print(f"  {idx}. {err}")
        print("=" * 60)
        sys.exit(1)
    else:
        print("🎉 全部 PWA 契约检验通过！Manifest、SW 与离线缓存契约完整！")
        print("=" * 60)
        sys.exit(0)


if __name__ == "__main__":
    main()
