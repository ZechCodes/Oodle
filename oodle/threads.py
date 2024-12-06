import ctypes
import time
from itertools import cycle
from threading import Thread as _Thread, Event, Lock
from typing import Any, Callable, TYPE_CHECKING, Generator

from oodle.mutex import Mutex

if TYPE_CHECKING:
    from oodle import ThreadGroup


class ExitThread(Exception):
    ...


class InterruptibleThread(_Thread):
    def __init__(
        self,
        *args,
        exception_callback: Callable[[Exception], None] | None = None,
        stop_callback: Callable[[], None] | None = None,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self._stopping = Event()
        self._shield_mutex = Mutex()
        self._exception_callback = exception_callback
        self._stop_callback = stop_callback
        self._done = Event()
        self._internal_lock = Lock()
        self._stop_lock = Lock()

    @property
    def done(self) -> Event:
        return self._done

    @property
    def stopping(self) -> Event:
        return self._stopping

    @property
    def shield(self) -> Mutex:
        return self._shield_mutex

    def is_alive(self):
        if super().is_alive():
            return True

        return not self._done.is_set()

    def run(self):
        try:
            try:
                super().run()
            finally:
                self._safely_acquire_internal_lock()

        except Exception as e:
            exit_exceptions = ExitThread
            if self._stopping.is_set():
                exit_exceptions |= SystemError

            if not isinstance(e, exit_exceptions):
                self._run_callback(self._exception_callback, e)

        finally:
            self.done.set()
            self._run_callback(self._stop_callback)
            self._internal_lock.release()

    def stop(self, timeout: float = 0):
        timeout_duration = generate_timeout_durations(timeout)
        if self.done.is_set() or self._stopping.is_set() or not self._stop_lock.acquire(blocking=False):
            return

        try:
            while self.shield.is_held and not self.done.is_set():
                self.shield.acquire(timeout=next(timeout_duration))

            self._stopping.set()

            try:
                while not self.done.is_set():
                    self.throw(ExitThread())
                    self.join(timeout=next(timeout_duration) or None)

            finally:
                self.shield.release()
        finally:
            self._stop_lock.release()

    def throw(self, exception: Exception):
        if self._done.is_set() or self._stopping.is_set() or not self._internal_lock.acquire(blocking=False):
            return

        try:
            ctypes.pythonapi.PyThreadState_SetAsyncExc(
                ctypes.c_long(self.ident),
                ctypes.py_object(exception),
            )
        finally:
            self._internal_lock.release()

    def _safely_acquire_internal_lock(self):
        try:
            self._internal_lock.acquire()
        except SystemError:
            try:
                self._internal_lock.release()
            except RuntimeError:
                pass

            self._internal_lock.acquire()

    @staticmethod
    def _run_callback[**P](callback: Callable[P, None] | None, *args: P.args, **kwargs: P.kwargs):
        if callback is not None:
            callback(*args, **kwargs)


class Thread:
    def __init__(self, thread: InterruptibleThread):
        self._thread = thread

    def __repr__(self):
        return f"<oodle.Thread {self._thread}>"

    @property
    def is_alive(self):
        return self._thread.is_alive()

    @property
    def is_done(self):
        match self._thread:
            case InterruptibleThread():
                return self._thread.done.is_set()

            case _:
                return not self.is_alive

    def stop(self, timeout: float = 0):
        if self.is_done:
            return

        self._thread.stop(timeout)

    def wait(self, timeout: float | None=None):
        self._thread.join(timeout)

    @classmethod
    def spawn(
        cls,
        target: Callable[[Any, ...], Any],
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        group: "ThreadGroup | None" = None,
    ):
        def group_exception_callback(exception: Exception):
            group.thread_encountered_exception(oodle_thread, exception)

        def group_stop_callback():
            group.thread_stopped(oodle_thread)

        thread = InterruptibleThread(
            target=target,
            args=args,
            kwargs=kwargs,
            daemon=True,
            exception_callback=group_exception_callback if group else None,
            stop_callback=group_stop_callback if group else None,
        )

        oodle_thread = cls(thread)
        thread.start()
        return oodle_thread


def generate_timeout_durations(
    timeout: float, clock: Callable[[], float] = time.monotonic, step: float = 0.1
) -> Generator[float, None, None]:
    if not timeout:
        yield from cycle([0])
        return

    start = clock()
    while (elapsed := clock() - start) < timeout:
        yield min(step, timeout - elapsed)

    raise TimeoutError("Failed to stop thread within timeout")