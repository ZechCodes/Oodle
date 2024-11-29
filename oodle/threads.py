import ctypes
from collections.abc import Callable
from threading import Thread as _Thread, Event, Lock
from typing import Any


class ExitThread(Exception):
    ...


class InterruptibleThread(_Thread):
    def __init__(
        self,
        *args,
        cancel_callback: Callable[[], None] | None = None,
        stop_callback: Callable[[], None] | None = None,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self._cancel_callback = cancel_callback
        self._pending_stop_event = Event()
        self._shield_lock = Lock()
        self._stop_callback = stop_callback

    @property
    def pending_stop_event(self) -> Event:
        return self._pending_stop_event

    @property
    def shield(self) -> Lock:
        return self._shield_lock

    def run(self):
        try:
            super().run()
        except Exception as e:
            self._run_callback(self._cancel_callback)
            if not isinstance(e, ExitThread):
                raise
        else:
            self._run_callback(self._stop_callback)

    def stop(self, timeout: float = 0):
        if not self.shield.locked():
            self._pending_stop_event.set()

        counter = 0
        fractional_timeout = timeout / 100 if timeout > 0 else None
        while self.is_alive():
            if self.shield.locked():
                if not self.shield.acquire(timeout=fractional_timeout):
                    break

                self.pending_stop_event.set()
            else:
                self.throw(ExitThread())
                self.join(fractional_timeout)

            counter += 1
            if counter > 100 and timeout > 0:
                break

        else:
            return

        raise TimeoutError("Failed to stop thread")

    def throw(self, exception: Exception):
        ctypes.pythonapi.PyThreadState_SetAsyncExc(
            ctypes.c_long(self.ident),
            ctypes.py_object(exception),
        )

    def _run_callback(self, callback: Callable[[], None] | None):
        if callback is not None:
            callback()


class Thread:
    def __init__(self, thread: InterruptibleThread, stop_callback: Callable[[], None] | None=None):
        self._thread = thread
        self._stop_callback = stop_callback

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
        stop_callback: Callable[[], None] | None=None,
        cancel_callback: Callable[[], None] | None=None
    ):
        thread = InterruptibleThread(
            target=target,
            args=args,
            kwargs=kwargs,
            cancel_callback=cancel_callback,
            stop_callback=stop_callback,
            daemon=True
        )
        thread.start()
        return cls(thread)
