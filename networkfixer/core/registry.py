import winreg
import logging
from typing import Tuple

from ..models.result import StepResult

logger = logging.getLogger(__name__)


class ProxyRegistry:
    REGISTRY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"

    def read_settings(self) -> Tuple[int, str, str]:
        """Return ProxyEnable, ProxyServer, and AutoConfigURL."""
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                self.REGISTRY_PATH,
                0,
                winreg.KEY_READ
            ) as key:
                enable = self._read_value(key, "ProxyEnable", 0)
                server = self._read_value(key, "ProxyServer", "")
                auto_config_url = self._read_value(key, "AutoConfigURL", "")
                return int(enable or 0), str(server or ""), str(auto_config_url or "")

        except Exception as e:
            logger.error(f"Failed to read proxy settings: {e}")
            return 0, "", ""

    def get_status(self) -> Tuple[bool, str]:
        enable, server, _auto_config_url = self.read_settings()
        return bool(enable), server

    @staticmethod
    def _read_value(key, name: str, default):
        try:
            value, _typ = winreg.QueryValueEx(key, name)
            return value
        except FileNotFoundError:
            return default

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
                try:
                    winreg.DeleteValue(key, "AutoConfigURL")
                except FileNotFoundError:
                    pass

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
