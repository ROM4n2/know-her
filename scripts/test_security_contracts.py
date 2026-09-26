#!/usr/bin/env python3
"""
scripts/test_security_contracts.py — 外链安全协议约束与链路探测弹性门禁测试

覆盖契约：
1. Zod URL 协议安全约束：严禁 javascript: / data: / ftp: / file: 等高危伪协议，仅允许 http(s)://
2. curate.py 403 降级探测容错：若初次 403 后重试出现 404/410/网络中断，严禁误报为 True (防爬成功)，必须判定为 False
"""
import io
import json
import os
import re
import subprocess
import sys
from email.message import Message
from unittest.mock import patch, MagicMock
import urllib.error

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")
CONTENT_CONFIG_FILE = os.path.join(PROJECT_ROOT, "src", "content.config.ts")

if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from curate import check_single_url


def test_zod_protocol_validation():
    print("🔒 [1/2] 正在检验 src/content.config.ts 的 source_url 协议安全性契约...")
    if not os.path.exists(CONTENT_CONFIG_FILE):
        return [f"配置文件不存在: {CONTENT_CONFIG_FILE}"]

    with open(CONTENT_CONFIG_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    match = re.search(r"source_url:\s*([\s\S]*?),\s*(?:\n\s*/\*\*|\n\s*[a-zA-Z_])", content)
    if not match:
        return ["未能从 src/content.config.ts 提取到 source_url 的 Zod Schema 定义"]

    schema_code = match.group(1).strip()
    node_script = f"""
import {{ z }} from 'zod';
const schema = {schema_code};

const testCases = [
    {{ url: 'javascript:alert(1)', expected: false, label: 'javascript: 伪协议' }},
    {{ url: 'data:text/html,<script>alert(1)</script>', expected: false, label: 'data: 伪协议注入' }},
    {{ url: 'ftp://ftp.example.com/file', expected: false, label: 'ftp: 文件传输协议' }},
    {{ url: 'file:///etc/passwd', expected: false, label: 'file: 本地文件协议' }},
    {{ url: 'https://www.who.int/news-room/fact-sheets/detail/emergency-contraception', expected: true, label: 'https:// 权威外链' }},
    {{ url: 'http://example.com/health', expected: true, label: 'http:// 常用外链' }}
];

const results = testCases.map(tc => {{
    const res = schema.safeParse(tc.url);
    return {{
        url: tc.url,
        label: tc.label,
        expected: tc.expected,
        actual: res.success,
        error: res.success ? null : (res.error?.issues?.[0]?.message || 'validation failed')
    }};
}});

console.log(JSON.stringify(results));
"""
    try:
        proc = subprocess.run(
            ["node", "--input-type=module", "-e", node_script],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
            cwd=PROJECT_ROOT,
        )
        test_results = json.loads(proc.stdout)
    except Exception as e:
        stderr_info = getattr(e, 'stderr', '')
        return [f"Node 校验执行异常: {e}\nSTDERR: {stderr_info}"]

    errors = []
    for r in test_results:
        if r["actual"] != r["expected"]:
            errors.append(
                f"协议安全断言失败 [{r['label']}]: 输入 '{r['url']}' 预期 valid={r['expected']}, 但实际 safeParse 结果为 valid={r['actual']}"
            )
        else:
            status = "✅ 拒绝" if not r["expected"] else "✅ 放行"
            print(f"   {status}: {r['label']} ({r['url']})")

    return errors


def test_curate_link_resilience():
    print("🛡️ [2/2] 正在检验 scripts/curate.py 403 重试与 404 漏报防御弹性...")
    errors = []

    def make_http_error(url: str, code: int, msg: str):
        return urllib.error.HTTPError(url, code, msg, Message(), None)

    def probe_with_mock(side_effect):
        with patch("urllib.request.urlopen", side_effect=side_effect), patch("sys.stdout", new_callable=io.StringIO):
            return check_single_url("https://example.com/test", "article.mdx", "机构")

    # 1. 直接 404 必须判定为 False
    err404 = make_http_error("https://example.com/test", 404, "Not Found")
    ok = probe_with_mock(err404)
    if ok is not False:
        errors.append("直接响应 404 时，check_single_url 应返回 False，实际返回 True")
    else:
        print("   ✅ 直接 404 判定通过: 返回 False")

    # 2. 初始 403 遭遇 WAF，降级重试依然遭遇 404，严禁误报为 True
    err403 = make_http_error("https://example.com/test", 403, "Forbidden")
    ok = probe_with_mock([err403, err404])
    if ok is not False:
        errors.append("初次 403 但降级重试返回 404 时，check_single_url 应返回 False，实际误报为 True (403漏报Bug)")
    else:
        print("   ✅ 403 降级探测 404 拦截通过: 返回 False")

    # 3. 初始 403 遭遇 WAF，降级重试出现 410 (Gone)，必须判定为 False
    err410 = make_http_error("https://example.com/test", 410, "Gone")
    ok = probe_with_mock([err403, err410])
    if ok is not False:
        errors.append("初次 403 但降级重试返回 410 时，check_single_url 应返回 False，实际误报为 True")
    else:
        print("   ✅ 403 降级探测 410 拦截通过: 返回 False")

    # 4. 初始 403 遭遇 WAF，降级重试出现 500/502/503 错误，必须判定为 False
    err500 = make_http_error("https://example.com/test", 500, "Server Error")
    ok = probe_with_mock([err403, err500])
    if ok is not False:
        errors.append("初次 403 但降级重试返回 500 时，check_single_url 应返回 False，实际误报为 True")
    else:
        print("   ✅ 403 降级探测 500 拦截通过: 返回 False")

    # 5. 初始 403 遭遇 WAF，降级重试出现网络中断/DNS/超时异常，必须判定为 False
    err_network = urllib.error.URLError("Connection refused")
    ok = probe_with_mock([err403, err_network])
    if ok is not False:
        errors.append("初次 403 但降级重试发生网络异常时，check_single_url 应返回 False，实际误报为 True")
    else:
        print("   ✅ 403 降级探测网络中断拦截通过: 返回 False")

    # 6. 初始 403 遭遇 WAF，降级重试依然为 403 (确认目标站点防爬反爬机制严格，但链接存在)，应放行返回 True
    err403_second = make_http_error("https://example.com/test", 403, "Forbidden")
    ok = probe_with_mock([err403, err403_second])
    if ok is not True:
        errors.append("两次探测均返回 403 时，应确认为 BOT_BLOCKED 防爬机制并返回 True，实际返回了 False")
    else:
        print("   ✅ 两次 403 确认 BOT_BLOCKED 通过: 返回 True")

    # 7. 初始 403 遭遇 WAF，降级重试成功 (200 OK)，应放行返回 True
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.__enter__.return_value = mock_resp
    ok = probe_with_mock([err403, mock_resp])
    if ok is not True:
        errors.append("初始 403 降级重试 200 OK 时，应返回 True，实际返回了 False")
    else:
        print("   ✅ 403 降级探测 200 成功通过: 返回 True")

    return errors


def main():
    print("🚀 开始执行安全契约与外链弹性门禁测试...\n")
    all_errors = []
    all_errors.extend(test_zod_protocol_validation())
    all_errors.extend(test_curate_link_resilience())

    if all_errors:
        print(f"\n❌ 安全契约检测未通过，共发现 {len(all_errors)} 项违规:")
        for err in all_errors:
            print(f"   • {err}")
        sys.exit(1)

    print("\n🎉 安全契约与外链弹性测试全部通过！Zod 协议与 curate 403 降级防御均合规！")
    sys.exit(0)


if __name__ == "__main__":
    main()
