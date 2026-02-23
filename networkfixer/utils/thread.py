import queue
import logging
from typing import Callable
from tkinter import Tk

logger = logging.getLogger(__name__)


class UISafeCaller:
    def __init__(self, root: Tk, poll_interval_ms: int = 50):
        self.root = root
        self.poll_interval_ms = poll_interval_ms
        self._queue: queue.Queue[Callable] = queue.Queue()
        self._running = True
        self._start_polling()

    def _start_polling(self) -> None:
        self._poll()

    def _poll(self) -> None:
        if not self._running:
            return

        while True:
            try:
                callback = self._queue.get_nowait()
                try:
                    callback()
                except Exception as e:
                    logger.error(f"UI callback error: {e}")
            except queue.Empty:
                break

        self.root.after(self.poll_interval_ms, self._poll)

    def call(self, func: Callable, *args, **kwargs) -> None:
        def wrapper():
            func(*args, **kwargs)
        self._queue.put(wrapper)

    def stop(self) -> None:
        self._running = False


class CancellationToken:
    def __init__(self):
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled

    def reset(self) -> None:
        self._cancelled = False
