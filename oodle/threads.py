from collections.abc import Callable
from sys import setprofile
from threading import Thread as _Thread, Event


class ExitThread(Exception):
    ...


class StoppableThread(_Thread):
    def __init__(
        self,
        *args,
        stop_callback: Callable[[], None] | None = None,
        cancel_callback: Callable[[], None] | None = None,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self._stop_event = Event()
        self.acquired_locks = set()
        self._cancel_callback = cancel_callback
        self._stop_callback = stop_callback

    def run(self):
        setprofile(self._profile_thread)
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
        finally:
            setprofile(None)

    def stop(self):
        self._stop_event.set()

        for lock in self.acquired_locks:
            lock.release()

    def _profile_thread(self, frame, event, obj):
        if self._stop_event.is_set():
            raise ExitThread


class Thread:
    def __init__(self, thread: StoppableThread, stop_callback: Callable[[], None] | None=None):
        self._thread = thread
        self._stop_callback = stop_callback

    @property
    def is_alive(self):
        return self._thread.is_alive()

    def stop(self):
        if not self.is_alive:
            return

        self._thread.stop()

    def wait(self, timeout: float | None=None):
        self._thread.join(timeout)

    @classmethod
    def spawn(cls, target, args, kwargs, stop_callback: Callable[[], None] | None=None, cancel_callback: Callable[[], None] | None=None):
        thread = StoppableThread(
            target=target,
            args=args,
            kwargs=kwargs,
            stop_callback=stop_callback,
            cancel_callback=cancel_callback,
            daemon=True
        )
        thread.start()
        return cls(thread)
