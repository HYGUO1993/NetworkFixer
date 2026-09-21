"""Tests for Microsoft service diagnostic conclusions."""

from networkfixer.core.ms_diagnostic import (
    DiagnosticSnapshot,
    EnvProxyHit,
    detected_flags,
    is_residual_system_proxy,
    parse_winhttp_direct,
    repair_flags,
    result_flags,
)
from networkfixer.models.result import StepResult


DIRECT_EN = """Current WinHTTP proxy settings:

    Direct access (no proxy server).
"""

DIRECT_ZH = """当前的 WinHTTP 代理服务器设置:

    直接访问(没有代理服务器)。
"""

PROXY_EN = """Current WinHTTP proxy settings:

    Proxy Server(s) :  127.0.0.1:7890
    Bypass List     :  (none)
"""

PROXY_ZH = """当前的 WinHTTP 代理服务器设置:

    代理服务器:  127.0.0.1:7890
    绕过列表     :  (无)
"""


def make_snapshot(**overrides) -> DiagnosticSnapshot:
    data = dict(
        internet_reachable=True,
        residual_system_proxy=False,
        microsoft_available=True,
        proxy_enable=0,
        proxy_server="",
        auto_config_url="",
        winhttp_direct=True,
        winhttp_raw="",
        env_proxies=[],
        endpoints=[],
    )
    data.update(overrides)
    return DiagnosticSnapshot(**data)


def test_parse_winhttp_direct_access_english_and_chinese():
    assert parse_winhttp_direct(DIRECT_EN) is True
    assert parse_winhttp_direct(DIRECT_ZH) is True


def test_parse_winhttp_configured_proxy_english_and_chinese():
    assert parse_winhttp_direct(PROXY_EN) is False
    assert parse_winhttp_direct(PROXY_ZH) is False


def test_parse_winhttp_empty_is_unknown():
    assert parse_winhttp_direct("") is None
    assert parse_winhttp_direct("   ") is None


def test_residual_proxy_covers_enable_server_pac_and_winhttp():
    assert is_residual_system_proxy(1, "", "", True) is True
    assert is_residual_system_proxy(0, "127.0.0.1:7890", "", True) is True
    assert is_residual_system_proxy(0, "", "http://127.0.0.1:7890/pac", True) is True
    assert is_residual_system_proxy(0, "", "", False) is True
    assert is_residual_system_proxy(0, "", "", True) is False
    assert is_residual_system_proxy(0, "", "", None) is False


def test_detected_flags_match_store_failure_with_browsing_ok():
    snapshot = make_snapshot(
        internet_reachable=True,
        residual_system_proxy=True,
        microsoft_available=False,
        env_proxies=[EnvProxyHit("User", "http_proxy", "http://127.0.0.1:7890")],
    )
    assert [(flag.ok, flag.code) for flag in detected_flags(snapshot)] == [
        (True, "ms.check.internet_ok"),
        (False, "ms.check.proxy_residual"),
        (False, "ms.check.microsoft_fail"),
        (False, "ms.check.env_residual"),
    ]


def test_repair_flags_follow_completed_steps():
    flags = repair_flags([
        StepResult(ok=True, title="disable_proxy"),
        StepResult(ok=True, title="flush_dns"),
        StepResult(ok=False, title="reset_winsock"),
        StepResult(ok=True, title="not_a_repair"),
    ])
    assert [(flag.ok, flag.code) for flag in flags] == [
        (True, "ms.repair.disable_proxy"),
        (True, "ms.repair.flush_dns"),
        (False, "ms.repair.reset_winsock"),
    ]


def test_result_flags_report_restored_endpoint_and_cleared_proxy():
    before = make_snapshot(
        residual_system_proxy=True,
        microsoft_available=False,
        env_proxies=[EnvProxyHit("Process", "https_proxy", "http://127.0.0.1:7890")],
    )
    after = make_snapshot(
        residual_system_proxy=False,
        microsoft_available=True,
        env_proxies=[],
    )
    assert [(flag.ok, flag.code) for flag in result_flags(before, after)] == [
        (True, "ms.result.microsoft_restored"),
        (True, "ms.result.proxy_cleared"),
        (True, "ms.result.env_cleared"),
    ]


def test_result_flags_keep_failures_visible():
    before = make_snapshot(residual_system_proxy=True, microsoft_available=False)
    after = make_snapshot(
        residual_system_proxy=True,
        microsoft_available=False,
        env_proxies=[EnvProxyHit("User", "all_proxy", "socks5://127.0.0.1:7890")],
    )
    assert [(flag.ok, flag.code) for flag in result_flags(before, after)] == [
        (False, "ms.result.microsoft_still_down"),
        (False, "ms.result.proxy_remains"),
        (False, "ms.result.env_remains"),
    ]
