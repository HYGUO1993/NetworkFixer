import time
import logging
from typing import List, Optional

from .executor import get_executor

logger = logging.getLogger(__name__)

DANGEROUS_CHARS = set('"\'&|;()`$\n\r')


class AdapterManager:
    def __init__(self, cache_ttl: int = 5):
        self.cache_ttl = cache_ttl
        self._cache: Optional[List[str]] = None
        self._cache_time: float = 0
        self.executor = get_executor()

    def list_names(self) -> List[str]:
        result = self.executor.run(["netsh", "interface", "show", "interface"])

        if not result.ok:
            logger.error(f"Failed to list adapters: {result.output}")
            return []

        return self._parse_output(result.output)

    def refresh(self, force: bool = False) -> List[str]:
        current_time = time.time()

        if not force and self._cache:
            if current_time - self._cache_time < self.cache_ttl:
                return self._cache

        self._cache = self.list_names()
        self._cache_time = current_time

        return self._cache

    def validate_name(self, name: str) -> bool:
        if not name:
            return False

        if any(c in DANGEROUS_CHARS for c in name):
            logger.warning(f"Invalid adapter name: {name}")
            return False

        return True

    @staticmethod
    def _parse_output(output: str) -> List[str]:
        names = []

        for line in output.splitlines():
            stripped = line.strip()
            if not stripped:
                continue

            if stripped.startswith('-'):
                continue
            if 'Admin' in stripped or '管理员' in stripped:
                continue

            parts = stripped.split()
            if len(parts) >= 4:
                name = ' '.join(parts[3:])
                names.append(name)

        logger.debug(f"Parsed adapters: {names}")
        return names
