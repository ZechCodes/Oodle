from .threads import Thread
from typing import Callable


class Spawner[R, **P]:
    def __init__(
        self,
        thread_builder: Callable[P, Thread] | None = None,
        cancel_callback: Callable[[], None] | None = None,
        stop_callback: Callable[[], None] | None = None,
    ):
        self._thread_builder = thread_builder or self._build_thread
        self._cancel_callback = cancel_callback
        self._stop_callback = stop_callback

    def __getitem__(self, func: Callable[P, R]) -> Callable[P, Thread]:
        if not callable(func):
            raise TypeError(f"Cannot spawn a non-callable object {func!r}")

        def runner(*args: P.args, **kwargs: P.kwargs) -> Thread:
            return self._thread_builder(func, *args, *kwargs)

        return runner

    def _build_thread(self, func: Callable[P, R], *args: P.args, **kwargs: P.kwargs) -> Thread:
        return Thread.spawn(func, args, kwargs, stop_callback=self._stop_callback, cancel_callback=self._cancel_callback)


spawn = Spawner()
