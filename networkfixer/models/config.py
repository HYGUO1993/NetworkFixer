from .result import AppConfig

_config: AppConfig | None = None


def get_config() -> AppConfig:
    global _config
    if _config is None:
        _config = AppConfig()
    return _config


def reset_config() -> None:
    global _config
    _config = None
