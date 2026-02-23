import ctypes
import logging

logger = logging.getLogger(__name__)


def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except (AttributeError, OSError) as e:
        logger.debug(f"Admin check failed: {e}")
        return False
