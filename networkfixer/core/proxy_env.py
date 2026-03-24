"""
Proxy Ghost Killer (幽灵代理专杀)

Detects and removes residual proxy environment variables that cause network issues
after proxy software is closed.
"""

import os
import socket
import winreg
import logging
from typing import List, Tuple, Optional, Dict
from urllib.parse import urlparse
from dataclasses import dataclass

from ..models.result import StepResult

logger = logging.getLogger(__name__)


@dataclass
class ProxyEnvInfo:
    """Information about a detected proxy environment variable."""
    name: str  # Variable name (e.g., "HTTP_PROXY")
    value: str  # Proxy URL (e.g., "http://127.0.0.1:7890")
    scope: str  # "Process", "User", or "Machine"
    is_alive: Optional[bool] = None  # True if proxy is responding, False if dead, None if not tested


class ProxyEnvScanner:
    """Scanner for proxy environment variables across different scopes."""

    PROXY_VAR_NAMES = [
        "http_proxy", "HTTP_PROXY",
        "https_proxy", "HTTPS_PROXY",
        "all_proxy", "ALL_PROXY",
    ]

    REGISTRY_USER_PATH = r"Environment"
    REGISTRY_MACHINE_PATH = r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"

    def __init__(self):
        self.detected_proxies: List[ProxyEnvInfo] = []

    def scan_all(self) -> List[ProxyEnvInfo]:
        """
        Scan all proxy environment variables across Process, User, and Machine levels.

        Returns:
            List of detected proxy environment variables with their information.
        """
        self.detected_proxies = []

        # Scan Process level (current runtime environment)
        self._scan_process_env()

        # Scan User level (registry HKEY_CURRENT_USER)
        self._scan_user_env()

        # Scan Machine level (registry HKEY_LOCAL_MACHINE)
        self._scan_machine_env()

        logger.info(f"Proxy environment scan complete: found {len(self.detected_proxies)} entries")
        return self.detected_proxies

    def _scan_process_env(self) -> None:
        """Scan process-level environment variables."""
        for var_name in self.PROXY_VAR_NAMES:
            value = os.environ.get(var_name)
            if value:
                logger.debug(f"Found process-level proxy: {var_name}={value}")
                self.detected_proxies.append(ProxyEnvInfo(
                    name=var_name,
                    value=value,
                    scope="Process"
                ))

    def _scan_user_env(self) -> None:
        """Scan user-level environment variables from registry."""
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                self.REGISTRY_USER_PATH,
                0,
                winreg.KEY_READ
            ) as key:
                self._read_registry_vars(key, "User")
        except Exception as e:
            logger.debug(f"Failed to read user environment variables: {e}")

    def _scan_machine_env(self) -> None:
        """Scan machine-level environment variables from registry."""
        try:
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                self.REGISTRY_MACHINE_PATH,
                0,
                winreg.KEY_READ
            ) as key:
                self._read_registry_vars(key, "Machine")
        except PermissionError:
            logger.debug("No permission to read machine environment variables (expected if not admin)")
        except Exception as e:
            logger.debug(f"Failed to read machine environment variables: {e}")

    def _read_registry_vars(self, key, scope: str) -> None:
        """Read proxy variables from a registry key."""
        for var_name in self.PROXY_VAR_NAMES:
            try:
                value, _ = winreg.QueryValueEx(key, var_name)
                if value:
                    logger.debug(f"Found {scope}-level proxy: {var_name}={value}")
                    self.detected_proxies.append(ProxyEnvInfo(
                        name=var_name,
                        value=value,
                        scope=scope
                    ))
            except FileNotFoundError:
                pass
            except Exception as e:
                logger.debug(f"Error reading {var_name} from {scope}: {e}")


class ProxyHealthChecker:
    """TCP-based health checker for proxy endpoints."""

    DEFAULT_TIMEOUT = 2.0  # seconds

    def __init__(self, timeout: float = DEFAULT_TIMEOUT):
        self.timeout = timeout

    def check_proxy(self, proxy_url: str) -> bool:
        """
        Check if a proxy endpoint is alive by attempting TCP connection.

        Args:
            proxy_url: Proxy URL (e.g., "http://127.0.0.1:7890")

        Returns:
            True if proxy is responding, False otherwise
        """
        try:
            parsed = urlparse(proxy_url)
            host = parsed.hostname or "127.0.0.1"
            port = parsed.port or 8080

            return self._tcp_ping(host, port)
        except Exception as e:
            logger.debug(f"Failed to parse/check proxy URL {proxy_url}: {e}")
            return False

    def _tcp_ping(self, host: str, port: int) -> bool:
        """
        Perform TCP connection test to check if port is open.

        Args:
            host: Target hostname/IP
            port: Target port

        Returns:
            True if connection succeeded, False otherwise
        """
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            result = sock.connect_ex((host, port))

            if result == 0:
                logger.debug(f"TCP connection to {host}:{port} succeeded")
                return True
            else:
                logger.debug(f"TCP connection to {host}:{port} failed with code {result}")
                return False
        except socket.timeout:
            logger.debug(f"TCP connection to {host}:{port} timed out")
            return False
        except Exception as e:
            logger.debug(f"TCP connection to {host}:{port} error: {e}")
            return False
        finally:
            if sock:
                try:
                    sock.close()
                except Exception:
                    pass


class ProxyGhostKiller:
    """Main class for detecting and removing ghost proxy configurations."""

    def __init__(self, health_check_timeout: float = 2.0):
        self.scanner = ProxyEnvScanner()
        self.health_checker = ProxyHealthChecker(timeout=health_check_timeout)

    def scan_and_test(self) -> Tuple[List[ProxyEnvInfo], List[ProxyEnvInfo]]:
        """
        Scan all proxy environment variables and test their health.

        Returns:
            Tuple of (healthy_proxies, dead_proxies)
        """
        proxies = self.scanner.scan_all()

        # Test health for each detected proxy
        for proxy in proxies:
            proxy.is_alive = self.health_checker.check_proxy(proxy.value)

        healthy = [p for p in proxies if p.is_alive]
        dead = [p for p in proxies if p.is_alive is False]

        logger.info(f"Health check complete: {len(healthy)} healthy, {len(dead)} dead proxies")
        return healthy, dead

    def clear_process_env(self, var_names: Optional[List[str]] = None) -> StepResult:
        """
        Clear proxy environment variables from current process.

        Args:
            var_names: List of variable names to clear. If None, clears all known proxy vars.

        Returns:
            StepResult indicating success or failure
        """
        if var_names is None:
            var_names = ProxyEnvScanner.PROXY_VAR_NAMES

        cleared = []
        for var_name in var_names:
            if var_name in os.environ:
                try:
                    del os.environ[var_name]
                    cleared.append(var_name)
                    logger.info(f"Cleared process environment variable: {var_name}")
                except Exception as e:
                    logger.error(f"Failed to clear {var_name}: {e}")

        if cleared:
            return StepResult(
                ok=True,
                title="clear_process_proxy_env",
                output=f"Cleared {len(cleared)} process-level proxy variables: {', '.join(cleared)}"
            )
        else:
            return StepResult(
                ok=True,
                title="clear_process_proxy_env",
                output="No process-level proxy variables to clear"
            )

    def clear_user_env(self, var_names: Optional[List[str]] = None) -> StepResult:
        """
        Clear proxy environment variables from user registry.

        Args:
            var_names: List of variable names to clear. If None, clears all known proxy vars.

        Returns:
            StepResult indicating success or failure
        """
        if var_names is None:
            var_names = ProxyEnvScanner.PROXY_VAR_NAMES

        cleared = []
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                ProxyEnvScanner.REGISTRY_USER_PATH,
                0,
                winreg.KEY_WRITE
            ) as key:
                for var_name in var_names:
                    try:
                        winreg.DeleteValue(key, var_name)
                        cleared.append(var_name)
                        logger.info(f"Deleted user environment variable: {var_name}")
                    except FileNotFoundError:
                        pass  # Variable doesn't exist, no action needed
                    except Exception as e:
                        logger.warning(f"Failed to delete user variable {var_name}: {e}")

            if cleared:
                return StepResult(
                    ok=True,
                    title="clear_user_proxy_env",
                    output=f"Cleared {len(cleared)} user-level proxy variables: {', '.join(cleared)}"
                )
            else:
                return StepResult(
                    ok=True,
                    title="clear_user_proxy_env",
                    output="No user-level proxy variables to clear"
                )
        except Exception as e:
            logger.error(f"Failed to clear user environment variables: {e}")
            return StepResult(
                ok=False,
                title="clear_user_proxy_env",
                error=e,
                output=str(e)
            )

    def clear_machine_env(self, var_names: Optional[List[str]] = None) -> StepResult:
        """
        Clear proxy environment variables from machine registry.
        Requires administrator privileges.

        Args:
            var_names: List of variable names to clear. If None, clears all known proxy vars.

        Returns:
            StepResult indicating success or failure
        """
        if var_names is None:
            var_names = ProxyEnvScanner.PROXY_VAR_NAMES

        cleared = []
        try:
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                ProxyEnvScanner.REGISTRY_MACHINE_PATH,
                0,
                winreg.KEY_WRITE
            ) as key:
                for var_name in var_names:
                    try:
                        winreg.DeleteValue(key, var_name)
                        cleared.append(var_name)
                        logger.info(f"Deleted machine environment variable: {var_name}")
                    except FileNotFoundError:
                        pass  # Variable doesn't exist
                    except Exception as e:
                        logger.warning(f"Failed to delete machine variable {var_name}: {e}")

            if cleared:
                return StepResult(
                    ok=True,
                    title="clear_machine_proxy_env",
                    output=f"Cleared {len(cleared)} machine-level proxy variables: {', '.join(cleared)}"
                )
            else:
                return StepResult(
                    ok=True,
                    title="clear_machine_proxy_env",
                    output="No machine-level proxy variables to clear"
                )
        except PermissionError as e:
            logger.error(f"Permission denied (requires administrator): {e}")
            return StepResult(
                ok=False,
                title="clear_machine_proxy_env",
                error=e,
                output="Permission denied - requires administrator privileges"
            )
        except Exception as e:
            logger.error(f"Failed to clear machine environment variables: {e}")
            return StepResult(
                ok=False,
                title="clear_machine_proxy_env",
                error=e,
                output=str(e)
            )

    def auto_fix(self) -> Dict[str, StepResult]:
        """
        Automatically detect and remove all dead proxy environment variables.

        Returns:
            Dictionary of StepResults for each operation performed
        """
        results = {}

        # Scan and test
        healthy, dead = self.scan_and_test()

        if not dead:
            logger.info("No dead proxies detected, no action needed")
            return results

        # Collect dead proxy variable names by scope
        process_vars = [p.name for p in dead if p.scope == "Process"]
        user_vars = [p.name for p in dead if p.scope == "User"]
        machine_vars = [p.name for p in dead if p.scope == "Machine"]

        # Clear them
        if process_vars:
            results["process"] = self.clear_process_env(process_vars)

        if user_vars:
            results["user"] = self.clear_user_env(user_vars)

        if machine_vars:
            results["machine"] = self.clear_machine_env(machine_vars)

        return results
