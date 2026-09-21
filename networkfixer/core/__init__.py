"""Core functionality for NetworkFixer"""

from .executor import CommandExecutor, get_executor
from .registry import ProxyRegistry
from .adapters import AdapterManager
from .connectivity import ConnectivityTester
from .operations import NetworkOperations, Step
from .proxy_env import ProxyGhostKiller, ProxyEnvScanner, ProxyHealthChecker, ProxyEnvInfo
from .ms_diagnostic import (
    DiagnosticFlag,
    DiagnosticSnapshot,
    MicrosoftServiceDiagnostic,
    detected_flags,
    repair_flags,
    result_flags,
)

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
    "DiagnosticFlag",
    "DiagnosticSnapshot",
    "MicrosoftServiceDiagnostic",
    "detected_flags",
    "repair_flags",
    "result_flags",
]
