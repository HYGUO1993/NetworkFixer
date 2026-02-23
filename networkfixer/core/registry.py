import winreg
import logging
from typing import Tuple

from ..models.result import StepResult

logger = logging.getLogger(__name__)


class ProxyRegistry:
    REGISTRY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"

    def get_status(self) -> Tuple[bool, str]:
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                self.REGISTRY_PATH,
                0,
                winreg.KEY_READ
            ) as key:
                try:
                    enable, _ = winreg.QueryValueEx(key, "ProxyEnable")
                except FileNotFoundError:
                    enable = 0

                try:
                    server, _ = winreg.QueryValueEx(key, "ProxyServer")
                except FileNotFoundError:
                    server = ""

                return bool(enable), server

        except Exception as e:
            logger.error(f"Failed to get proxy status: {e}")
            return False, ""

    def disable(self) -> StepResult:
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                self.REGISTRY_PATH,
                0,
                winreg.KEY_WRITE
            ) as key:
                winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)
                winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, "")

            logger.info("System proxy disabled")
            return StepResult(ok=True, title="disable_proxy")

        except PermissionError as e:
            logger.error(f"Permission denied: {e}")
            return StepResult(
                ok=False,
                title="disable_proxy",
                error=e,
                output="Permission denied"
            )
        except Exception as e:
            logger.exception(f"Failed to disable proxy: {e}")
            return StepResult(
                ok=False,
                title="disable_proxy",
                error=e,
                output=str(e)
            )
