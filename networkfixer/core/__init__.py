"""Core functionality for NetworkFixer"""

from .executor import CommandExecutor, get_executor
from .registry import ProxyRegistry
from .adapters import AdapterManager
from .connectivity import ConnectivityTester
from .operations import NetworkOperations, Step
from .proxy_env import ProxyGhostKiller, ProxyEnvScanner, ProxyHealthChecker, ProxyEnvInfo

__all__ = [
    "CommandExecutor",
    "get_executor",
    "ProxyRegistry",
    "AdapterManager",
    "ConnectivityTester",
    "NetworkOperations",
    "Step",
    "ProxyGhostKiller",
    "ProxyEnvScanner",
    "ProxyHealthChecker",
    "ProxyEnvInfo",
]
