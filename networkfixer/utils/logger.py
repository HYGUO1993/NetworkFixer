import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    log_file: Optional[str] = None,
    level: int = logging.DEBUG,
    console: bool = True
) -> logging.Logger:
    root_logger = logging.getLogger("networkfixer")
    root_logger.setLevel(level)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    if console:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    return root_logger


class GUIHandler(logging.Handler):
    LEVEL_TAGS = {
        logging.DEBUG: "info",
        logging.INFO: "info",
        logging.WARNING: "warn",
        logging.ERROR: "error",
        logging.CRITICAL: "error",
    }

    def __init__(self, log_callback):
        super().__init__()
        self.log_callback = log_callback

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            tag = self.LEVEL_TAGS.get(record.levelno, "info")
            self.log_callback(msg, tag)
        except Exception:
            self.handleError(record)
