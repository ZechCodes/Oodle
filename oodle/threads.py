import ctypes
import threading
from functools import wraps, partial
from threading import Thread as _Thread, Event, Lock, RLock
from typing import Callable, Generator, Self

import oodle
from oodle.exceptions import ExitThread
from oodle.utilities import safely_acquire, generate_timeout_durations, abort_concurrent_calls


class Thread:
    def __init__(
        self,
        runner: Callable[[], None],
        *,
        on_done: Callable[[Self], None] | None = None,
        on_exception: Callable[[Exception, Self], None] | None = None,
    ):
        self._internal_lock = Lock()
        self._shield_lock = RLock()

        self._done = Event()
        self._stopping = Event()

        self._on_done = on_done
        self._on_exception = on_exception

        self._runner = runner
        self._thread = _Thread(target=self._run, daemon=True)
        self._thread.start()

    def __repr__(self):
        return f"<oodle.Thread {self._thread.name} {self._thread.ident}>"

    @property
    def running(self):
        return not self._done.is_set()

    @abort_concurrent_calls
    def stop(self, timeout: float = 0, wait: bool = False):
        timeout_duration = generate_timeout_durations(timeout)
        if self._thread.ident == threading.get_ident():
            raise ExitThread

        if not self.running:
            return

        if not self._shield_lock.acquire(timeout=next(timeout_duration)):
            return

        with self._shield_lock:
            self._stopping.set()
            self._throw()
            if wait:
                self.wait(next(timeout_duration))

    def wait(self, timeout: float | None=None):
        self._done.wait(timeout=timeout)

    def _handle_exception(self, e: Exception):
        shutdown_exceptions = ExitThread
        if self._stopping.is_set():
            shutdown_exceptions |= SystemError

        if isinstance(e, shutdown_exceptions):
            return

        if self._on_exception:
            self._on_exception(e, self)

        raise e

    def _run(self):
        oodle.thread_locals.thread = self
        oodle.thread_locals.shield_lock = self._shield_lock
        try:
            try:
                self._runner()
            finally:
                safely_acquire(self._internal_lock)
                self._done.set()

        except Exception as e:
            self._handle_exception(e)

        finally:
            if self._on_done:
                self._on_done(self)

            self._internal_lock.release()

    def _throw(self):
        if self._internal_lock.acquire(blocking=False):
            try:
                ctypes.pythonapi.PyThreadState_SetAsyncExc(
                    ctypes.c_long(self._thread.ident),
                    ctypes.py_object(ExitThread),
                )
            finally:
                self._internal_lock.release()

    @classmethod
    def run[**P](cls, func: Callable[[P], None], *args: P.args, **kwargs: P.kwargs) -> Self:
        return cls(partial(func, *args, **kwargs))
