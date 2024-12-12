from concurrent.futures import Future
from functools import partial
from queue import Queue
from threading import Event, current_thread
from typing import Callable

import oodle
from oodle import Thread
from oodle.exceptions import ExitThread


class IllegalDispatchException(Exception):
    ...


class DispatchQueue[**P, R]:
    def __init__(self):
        self._queue: Queue[tuple[Future[R], Callable[P, R]]] = Queue()
        self._started = Event()
        self._thread = Thread.run(self._dispatch)
        self._started.set()

    def dispatch(self, func: Callable[P, R], *args: P.args, **kwargs: P.kwargs) -> R:
        return self.dispatch_future(func, *args, **kwargs).result()

    def dispatch_future(self, func: Callable[P, R], *args: P.args, **kwargs: P.kwargs) -> Future[R]:
        if getattr(oodle.thread_locals, "thread", None) == self._thread:
            raise IllegalDispatchException("Cannot dispatch on dispatch thread, will dead lock")

        future = Future()
        self._queue.put((future, partial(func, *args, **kwargs)))
        return future

    def stop(self):
        self._thread.stop()

    def _dispatch(self):
        self._started.wait()
        while self._thread.running:
            future, func = self._queue.get()
            try:
                result = func()
            except Exception as e:
                shutdown_exceptions = ExitThread
                if self._thread.stopping:
                    shutdown_exceptions |= SystemError

                if isinstance(e, shutdown_exceptions):
                    break

                future.set_exception(e)
            else:
                future.set_result(result)

