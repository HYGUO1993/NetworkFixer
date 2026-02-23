import subprocess
import time
import logging
import shlex
from typing import List, Union, Optional

from ..models.result import StepResult

logger = logging.getLogger(__name__)

CREATE_NO_WINDOW = 0x08000000


class CommandExecutor:
    def __init__(self, hide_window: bool = True):
        self.hide_window = hide_window

    def run(
        self,
        command: Union[str, List[str]],
        shell: bool = False,
        timeout: Optional[float] = None,
        check: bool = True
    ) -> StepResult:
        start_time = time.time()
        creationflags = CREATE_NO_WINDOW if self.hide_window else 0

        try:
            if isinstance(command, str) and not shell:
                args = shlex.split(command)
            else:
                args = command

            logger.debug(f"Executing: {args}")

            proc = subprocess.run(
                args,
                shell=shell,
                check=check,
                creationflags=creationflags,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=timeout,
                text=False
            )

            output = self._decode_output(proc.stdout)
            duration_ms = (time.time() - start_time) * 1000

            return StepResult(
                ok=True,
                title="",
                output=output,
                return_code=proc.returncode,
                duration_ms=duration_ms
            )

        except subprocess.CalledProcessError as e:
            output = self._decode_output(e.stdout) if e.stdout else str(e)
            return StepResult(
                ok=False,
                title="",
                output=output,
                error=e,
                return_code=e.returncode
            )

        except subprocess.TimeoutExpired as e:
            logger.error(f"Command timeout: {command}")
            return StepResult(
                ok=False,
                title="",
                output="Command timed out",
                error=e
            )

        except Exception as e:
            logger.exception(f"Command execution failed: {e}")
            return StepResult(
                ok=False,
                title="",
                output=str(e),
                error=e
            )

    def run_chain(self, commands: List[Union[str, List[str]]]) -> StepResult:
        result = StepResult(ok=True, title="")
        for cmd in commands:
            result = self.run(cmd)
            if not result.ok:
                return result
        return result

    @staticmethod
    def _decode_output(data: bytes) -> str:
        if not data:
            return ""

        for encoding in ['mbcs', 'utf-8', 'gbk']:
            try:
                return data.decode(encoding).strip()
            except (UnicodeDecodeError, LookupError):
                continue

        return data.decode('utf-8', errors='replace').strip()


_executor: Optional[CommandExecutor] = None


def get_executor() -> CommandExecutor:
    global _executor
    if _executor is None:
        _executor = CommandExecutor()
    return _executor
