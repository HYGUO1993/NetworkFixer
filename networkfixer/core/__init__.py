"""Core functionality for NetworkFixer"""

from .executor import CommandExecutor, get_executor
from .registry import ProxyRegistry
from .adapters import AdapterManager
from .connectivity import ConnectivityTester
from .operations import NetworkOperations, Step

__all__ = [
    "CommandExecutor",
    "get_executor",
    "ProxyRegistry",
    "AdapterManager",
    "ConnectivityTester",
    "NetworkOperations",
    "Step",
]
