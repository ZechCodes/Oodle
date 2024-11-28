from threading import Thread
from typing import Callable


class Spawner[R, **P]:
    def __init__(self, thread_builder: Callable[P, Thread] | None = None):
        self._thread_builder = thread_builder or self._build_thread

    def __getitem__(self, func: Callable[P, R]) -> Callable[P, Thread]:
        if not callable(func):
            raise TypeError(f"Cannot spawn a non-callable object {func!r}")

        def runner(*args: P.args, **kwargs: P.kwargs) -> Thread:
            return self._thread_builder(func, *args, *kwargs)

        return runner

    def _build_thread(self, func: Callable[P, R], *args: P.args, **kwargs: P.kwargs) -> Thread:
        thread = Thread(target=func, args=args, kwargs=kwargs, daemon=True)
        thread.start()
        return thread
