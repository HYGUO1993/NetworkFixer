from dataclasses import dataclass
from enum import Enum
from typing import Optional


class LogLevel(Enum):
    INFO = "info"
    SUCCESS = "success"
    WARN = "warn"
    ERROR = "error"


@dataclass
class StepResult:
    ok: bool
    title: str
    output: str = ""
    error: Optional[Exception] = None
    return_code: int = 0
    duration_ms: float = 0.0

    def __str__(self) -> str:
        status = "✓" if self.ok else "✗"
        return f"{status} {self.title}"


@dataclass
class ConnectivityResult:
    ping_114: bool = False
    ping_google: bool = False
    http_test: bool = False

    @property
    def all_ok(self) -> bool:
        return self.ping_114 and self.http_test


@dataclass
class AdapterInfo:
    name: str
    is_connected: bool = True


@dataclass
class ProxyStatus:
    enabled: bool
    server: str = ""


@dataclass
class AppConfig:
    ping_timeout_ms: int = 2000
    http_timeout_sec: int = 3
    adapter_cache_ttl_sec: int = 5
    log_to_file: bool = True
    log_file_name: str = "networkfixer.log"
    window_width: int = 560
    window_height: int = 600
    language: str = "zh_CN"
