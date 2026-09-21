"""Microsoft service diagnostic.

Records WinHTTP proxy, user proxy settings, and TCP reachability of Microsoft
endpoints before and after a repair. This targets the case where browsing still
works, but Microsoft Store / login / winget fail after a proxy client exits.
"""

import logging
import socket
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

from ..models.result import StepResult
from .executor import get_executor
from .proxy_env import ProxyEnvScanner
from .registry import ProxyRegistry

logger = logging.getLogger(__name__)

_DIRECT_MARKERS = (
    "direct access",
    "no proxy server",
    "直接访问",
    "没有代理服务器",
)

REPAIR_CODES = {
    "disable_proxy": "ms.repair.disable_proxy",
    "flush_dns": "ms.repair.flush_dns",
    "reset_winsock": "ms.repair.reset_winsock",
    "reset_ip": "ms.repair.reset_ip",
    "reset_tcpip": "ms.repair.reset_tcpip",
    "restart_adapter": "ms.repair.restart_adapter",
}


@dataclass
class EnvProxyHit:
    scope: str
    name: str
    value: str


@dataclass
class EndpointProbe:
    host: str
    port: int
    ok: bool
    detail: str = ""


@dataclass
class DiagnosticFlag:
    ok: bool
    code: str


@dataclass
class DiagnosticSnapshot:
    internet_reachable: bool
    residual_system_proxy: bool
    microsoft_available: bool
    proxy_enable: int
    proxy_server: str
    auto_config_url: str
    winhttp_direct: Optional[bool]
    winhttp_raw: str
    env_proxies: List[EnvProxyHit] = field(default_factory=list)
    endpoints: List[EndpointProbe] = field(default_factory=list)


def parse_winhttp_direct(output: str) -> Optional[bool]:
    """Return True for direct access, False when a proxy is set, None if unknown.

    Direct-access text is checked first. Both the English phrase
    "no proxy server" and the Chinese header "代理服务器" contain the words
    that also appear in a configured-proxy report.
    """
    if not output or not output.strip():
        return None

    lowered = output.lower()
    for marker in _DIRECT_MARKERS:
        if marker in output or marker in lowered:
            return True

    if "proxy server" in lowered or "代理服务器" in output:
        return False

    return None


def is_residual_system_proxy(
    proxy_enable: int,
    proxy_server: str,
    auto_config_url: str,
    winhttp_direct: Optional[bool],
) -> bool:
    """True when user or WinHTTP proxy settings still look like a leftover."""
    if int(proxy_enable):
        return True
    if (proxy_server or "").strip():
        return True
    if (auto_config_url or "").strip():
        return True
    if winhttp_direct is False:
        return True
    return False


def probe_tcp(host: str, port: int, timeout: float) -> EndpointProbe:
    """TCP connect probe, equivalent to Test-NetConnection -Port for reachability."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return EndpointProbe(host=host, port=port, ok=True)
    except OSError as exc:
        return EndpointProbe(host=host, port=port, ok=False, detail=str(exc))


def detected_flags(snapshot: DiagnosticSnapshot) -> List[DiagnosticFlag]:
    flags = [
        DiagnosticFlag(
            snapshot.internet_reachable,
            "ms.check.internet_ok" if snapshot.internet_reachable else "ms.check.internet_fail",
        ),
        DiagnosticFlag(
            not snapshot.residual_system_proxy,
            "ms.check.proxy_clean" if not snapshot.residual_system_proxy else "ms.check.proxy_residual",
        ),
        DiagnosticFlag(
            snapshot.microsoft_available,
            "ms.check.microsoft_ok" if snapshot.microsoft_available else "ms.check.microsoft_fail",
        ),
    ]
    if snapshot.env_proxies:
        flags.append(DiagnosticFlag(False, "ms.check.env_residual"))
    return flags


def repair_flags(results: Sequence[StepResult]) -> List[DiagnosticFlag]:
    flags = []
    for result in results:
        code = REPAIR_CODES.get(result.title)
        if code is None:
            continue
        flags.append(DiagnosticFlag(result.ok, code))
    return flags


def result_flags(before: DiagnosticSnapshot, after: DiagnosticSnapshot) -> List[DiagnosticFlag]:
    flags = []
    if not before.microsoft_available and after.microsoft_available:
        flags.append(DiagnosticFlag(True, "ms.result.microsoft_restored"))
    elif after.microsoft_available:
        flags.append(DiagnosticFlag(True, "ms.result.microsoft_ok"))
    else:
        flags.append(DiagnosticFlag(False, "ms.result.microsoft_still_down"))

    if before.residual_system_proxy and not after.residual_system_proxy:
        flags.append(DiagnosticFlag(True, "ms.result.proxy_cleared"))
    elif after.residual_system_proxy:
        flags.append(DiagnosticFlag(False, "ms.result.proxy_remains"))

    if after.env_proxies:
        flags.append(DiagnosticFlag(False, "ms.result.env_remains"))
    elif before.env_proxies:
        flags.append(DiagnosticFlag(True, "ms.result.env_cleared"))

    return flags


class MicrosoftServiceDiagnostic:
    """Collect a before/after snapshot of proxy residue and Microsoft endpoints."""

    INTERNET_TARGETS = (
        ("www.msftconnecttest.com", 80),
        ("www.baidu.com", 443),
    )
    MICROSOFT_TARGETS = (
        ("login.live.com", 443),
        ("storeedgefd.dsx.mp.microsoft.com", 443),
    )

    def __init__(
        self,
        executor=None,
        timeout_sec: float = 4.0,
        env_scanner: Optional[ProxyEnvScanner] = None,
        proxy_registry: Optional[ProxyRegistry] = None,
    ):
        self.executor = executor or get_executor()
        self.timeout_sec = timeout_sec
        self.env_scanner = env_scanner or ProxyEnvScanner()
        self.proxy_registry = proxy_registry or ProxyRegistry()

    def collect(self) -> DiagnosticSnapshot:
        proxy_enable, proxy_server, auto_config_url = self.proxy_registry.read_settings()
        winhttp_raw, winhttp_direct = self._read_winhttp()
        env_proxies = self._read_env_proxies()
        internet_ok, endpoints = self._probe_targets()
        microsoft_ok = (
            len(endpoints) == len(self.MICROSOFT_TARGETS)
            and all(item.ok for item in endpoints)
        )
        if any(item.ok for item in endpoints):
            internet_ok = True

        return DiagnosticSnapshot(
            internet_reachable=internet_ok,
            residual_system_proxy=is_residual_system_proxy(
                proxy_enable,
                proxy_server,
                auto_config_url,
                winhttp_direct,
            ),
            microsoft_available=microsoft_ok,
            proxy_enable=proxy_enable,
            proxy_server=proxy_server,
            auto_config_url=auto_config_url,
            winhttp_direct=winhttp_direct,
            winhttp_raw=winhttp_raw,
            env_proxies=env_proxies,
            endpoints=endpoints,
        )

    def _read_winhttp(self) -> Tuple[str, Optional[bool]]:
        result = self.executor.run(
            ["netsh", "winhttp", "show", "proxy"],
            timeout=10,
            check=False,
        )
        raw = result.output or ""
        if not result.ok and not raw:
            raw = "Command failed"
        return raw, parse_winhttp_direct(raw)

    def _read_env_proxies(self) -> List[EnvProxyHit]:
        try:
            found = self.env_scanner.scan_all()
        except Exception as exc:
            logger.error(f"Proxy environment scan failed: {exc}")
            return []

        return [
            EnvProxyHit(scope=item.scope, name=item.name, value=item.value)
            for item in found
        ]

    def _probe_targets(self) -> Tuple[bool, List[EndpointProbe]]:
        internet_results: List[bool] = []
        endpoints: List[EndpointProbe] = []

        with ThreadPoolExecutor(max_workers=4) as pool:
            internet_futures = [
                pool.submit(probe_tcp, host, port, self.timeout_sec)
                for host, port in self.INTERNET_TARGETS
            ]
            microsoft_futures = [
                pool.submit(probe_tcp, host, port, self.timeout_sec)
                for host, port in self.MICROSOFT_TARGETS
            ]
            for future in internet_futures:
                try:
                    internet_results.append(future.result().ok)
                except Exception as exc:
                    logger.error(f"Internet probe failed: {exc}")
            for future in microsoft_futures:
                try:
                    endpoints.append(future.result())
                except Exception as exc:
                    logger.error(f"Microsoft probe failed: {exc}")

        endpoints.sort(key=lambda item: item.host)
        return any(internet_results), endpoints
