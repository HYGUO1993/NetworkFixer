import urllib.request
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..models.result import ConnectivityResult

logger = logging.getLogger(__name__)


class ConnectivityTester:
    PING_TARGETS = [
        ("ping_114", "114.114.114.114"),
        ("ping_google", "8.8.8.8"),
    ]
    HTTP_TARGET = "http://www.msftconnecttest.com/redirect"

    def __init__(
        self,
        ping_timeout_ms: int = 2000,
        http_timeout_sec: int = 3
    ):
        self.ping_timeout_ms = ping_timeout_ms
        self.http_timeout_sec = http_timeout_sec

    def test(self, parallel: bool = True) -> ConnectivityResult:
        if parallel:
            return self._test_parallel()
        else:
            return self._test_sequential()

    def _test_sequential(self) -> ConnectivityResult:
        result = ConnectivityResult()
        result.ping_114 = self._ping(self.PING_TARGETS[0][1])
        result.ping_google = self._ping(self.PING_TARGETS[1][1])
        result.http_test = self._http_test()
        return result

    def _test_parallel(self) -> ConnectivityResult:
        result = ConnectivityResult()

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {}

            for key, target in self.PING_TARGETS:
                future = executor.submit(self._ping, target)
                futures[future] = key

            future = executor.submit(self._http_test)
            futures[future] = "http"

            for future in as_completed(futures):
                key = futures[future]
                try:
                    value = future.result()
                    if key == "ping_114":
                        result.ping_114 = value
                    elif key == "ping_google":
                        result.ping_google = value
                    elif key == "http":
                        result.http_test = value
                except Exception as e:
                    logger.error(f"Test {key} failed: {e}")

        return result

    def _ping(self, target: str) -> bool:
        from .executor import get_executor
        executor = get_executor()
        
        cmd = [
            "ping",
            "-n", "1",
            "-w", str(self.ping_timeout_ms),
            target
        ]

        result = executor.run(cmd, check=False)
        return result.return_code == 0

    def _http_test(self) -> bool:
        try:
            with urllib.request.urlopen(
                self.HTTP_TARGET,
                timeout=self.http_timeout_sec
            ) as response:
                return 200 <= response.getcode() < 400
        except Exception as e:
            logger.debug(f"HTTP test failed: {e}")
            return False
