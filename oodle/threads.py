from collections.abc import Callable
from sys import setprofile
from threading import Thread as _Thread, Event


class ExitThread(Exception):
    ...


class InterruptibleThread(_Thread):
    def __init__(
        self,
        *args,
        stop_callback: Callable[[], None] | None = None,
        cancel_callback: Callable[[], None] | None = None,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self._shield_lock = Lock()
        self._cancel_callback = cancel_callback
        self._stop_callback = stop_callback
    @property
    def shield(self) -> Lock:
        return self._shield_lock

    def run(self):
        try:
            super().run()
        except Exception as e:
            if self._cancel_callback:
                self._cancel_callback()

            if not isinstance(e, ExitThread):
                raise
        else:
            if self._stop_callback:
                self._stop_callback()

    def stop(self, timeout: float = 0):




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
    def spawn(cls, target, args, kwargs, stop_callback: Callable[[], None] | None=None, cancel_callback: Callable[[], None] | None=None):
        thread = InterruptibleThread(
            target=target,
            args=args,
            kwargs=kwargs,
            stop_callback=stop_callback,
            cancel_callback=cancel_callback,
            daemon=True
        )
        thread.start()
        return cls(thread)
