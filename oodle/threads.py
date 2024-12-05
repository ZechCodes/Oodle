import ctypes
import time
from threading import Thread as _Thread, Event, Lock
from typing import Any, Callable, TYPE_CHECKING

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
            super().run()
        except Exception as e:
            if not isinstance(e, ExitThread):
                self._run_callback(self._exception_callback, e)
        finally:
            self._done.set()
            self._run_callback(self._stop_callback)

    def stop(self, timeout: float = 0):
        start = time.monotonic()

        def get_timeout_duration():
            elapsed = time.monotonic() - start
            if elapsed < timeout:
                return min(0.01, timeout - elapsed)

            raise TimeoutError("Failed to stop thread within timeout")

        if not timeout:
            get_timeout_duration = lambda: None

        while self.shield.is_held and not self.done.is_set():
            self.shield.acquire(timeout=get_timeout_duration())

        self._stopping.set()
        while not self.done.is_set():
            self.throw(ExitThread())
            self.join(timeout=get_timeout_duration())

    def throw(self, exception: Exception):
        ctypes.pythonapi.PyThreadState_SetAsyncExc(
            ctypes.c_long(self.ident),
            ctypes.py_object(exception),
        )

    def _run_callback[**P](self, callback: Callable[P, None] | None, *args: P.args, **kwargs: P.kwargs):
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

    def stop(self, timeout: float = 0):
        if not self.is_alive:
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
