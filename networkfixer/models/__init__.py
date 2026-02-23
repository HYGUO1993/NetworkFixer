"""Data models for NetworkFixer"""

from .result import (
    LogLevel,
    StepResult,
    ConnectivityResult,
    AdapterInfo,
    ProxyStatus,
    AppConfig,
)
from .config import get_config

__all__ = [
    "LogLevel",
    "StepResult",
    "ConnectivityResult",
    "AdapterInfo",
    "ProxyStatus",
    "AppConfig",
    "get_config",
]
