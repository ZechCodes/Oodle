from sys import setprofile
from threading import Thread as _Thread, Event


class ExitThread(Exception):
    ...


class StoppableThread(_Thread):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._stop_event = Event()
        self.acquired_locks = set()

    def run(self):
        setprofile(self._profile_thread)
        try:
            super().run()
        except ExitThread:
            pass

    def stop(self):
        self._stop_event.set()

        for lock in self.acquired_locks:
            lock.release()

    def _profile_thread(self, frame, event, obj):
        if self._stop_event.is_set():
            raise ExitThread


class Thread:
    def __init__(self, thread: StoppableThread):
        self._thread = thread

    @property
    def is_alive(self):
        return self._thread.is_alive()

    def stop(self):
        if self.is_alive:
            self._thread.stop()

    def wait(self, timeout: float | None=None):
        self._thread.join(timeout)

    @classmethod
    def spawn(cls, target, *args, **kwargs):
        thread = StoppableThread(target=target, args=args, kwargs=kwargs, daemon=True)
        thread.start()
        return cls(thread)
