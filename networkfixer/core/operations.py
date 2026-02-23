import logging
from typing import List, Callable, Tuple, Optional

from .executor import get_executor
from .registry import ProxyRegistry
from .adapters import AdapterManager
from .connectivity import ConnectivityTester
from ..models.result import StepResult, AppConfig, ConnectivityResult
from ..models.config import get_config

logger = logging.getLogger(__name__)


class Step:
    def __init__(self, title_key: str, func: Callable[[], StepResult]):
        self.title_key = title_key
        self.func = func


class NetworkOperations:
    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or get_config()
        self.executor = get_executor()
        self.proxy_registry = ProxyRegistry()
        self.adapter_manager = AdapterManager(
            cache_ttl=self.config.adapter_cache_ttl_sec
        )
        self.connectivity_tester = ConnectivityTester(
            ping_timeout_ms=self.config.ping_timeout_ms,
            http_timeout_sec=self.config.http_timeout_sec
        )

    def get_proxy_status(self) -> Tuple[bool, str]:
        return self.proxy_registry.get_status()

    def disable_proxy(self) -> StepResult:
        return self.proxy_registry.disable()

    def flush_dns(self) -> StepResult:
        result = self.executor.run("ipconfig /flushdns")
        result.title = "flush_dns"
        return result

    def reset_winsock(self) -> StepResult:
        result = self.executor.run("netsh winsock reset")
        result.title = "reset_winsock"
        return result

    def reset_ip(self) -> StepResult:
        result = self.executor.run_chain([
            ["ipconfig", "/release"],
            ["ipconfig", "/renew"]
        ])
        result.title = "reset_ip"
        return result

    def reset_tcpip(self) -> StepResult:
        result = self.executor.run("netsh int ip reset")
        result.title = "reset_tcpip"
        return result

    def list_adapters(self) -> List[str]:
        return self.adapter_manager.list_names()

    def refresh_adapters(self, force: bool = False) -> List[str]:
        return self.adapter_manager.refresh(force)

    def restart_adapter(self, adapter_name: str) -> StepResult:
        if not self.adapter_manager.validate_name(adapter_name):
            return StepResult(
                ok=False,
                title="restart_adapter",
                output="Invalid adapter name"
            )

        result = self.executor.run_chain([
            ["netsh", "interface", "set", "interface", adapter_name, "admin=disabled"],
            ["netsh", "interface", "set", "interface", adapter_name, "admin=enabled"]
        ])
        result.title = "restart_adapter"
        return result

    def test_connectivity(self) -> ConnectivityResult:
        return self.connectivity_tester.test()

    def build_steps(
        self,
        do_proxy: bool,
        do_dns: bool,
        do_winsock: bool,
        do_ip: bool,
        do_tcpip: bool,
        do_adapter: bool,
        adapter_name: str = ""
    ) -> List[Step]:
        steps = []

        if do_proxy:
            steps.append(Step("step.disable_proxy", self.disable_proxy))
        if do_dns:
            steps.append(Step("step.flush_dns", self.flush_dns))
        if do_winsock:
            steps.append(Step("step.reset_winsock", self.reset_winsock))
        if do_ip:
            steps.append(Step("step.reset_ip", self.reset_ip))
        if do_tcpip:
            steps.append(Step("step.reset_tcpip", self.reset_tcpip))

        if do_adapter and adapter_name:
            steps.append(Step(
                "step.restart_adapter",
                lambda: self.restart_adapter(adapter_name)
            ))

        return steps

    def execute_steps(
        self,
        steps: List[Step],
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None
    ) -> List[StepResult]:
        results = []
        total = len(steps)

        for i, step in enumerate(steps):
            if cancel_check and cancel_check():
                logger.info("Operation cancelled by user")
                break

            if progress_callback:
                progress_callback(i + 1, total, step.title_key)

            result = step.func()
            results.append(result)

            logger.info(f"Step {i+1}/{total}: {result}")

        return results
