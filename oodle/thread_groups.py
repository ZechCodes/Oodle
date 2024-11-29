from threading import Event, Semaphore

from .spawners import spawn, Spawner


class ThreadGroup:
    def __init__(self):
        self._threads = []
        self._cancel_event = Event()
        self._running_threads = Semaphore()

    def _build_thread(self, func, *args, **kwargs):
        thread = Spawner(stop_callback=self._running_threads.release, cancel_callback=self._cancel_event)[func](*args, **kwargs)
        self._threads.append(thread)
        return thread

    def __enter__(self):
        return Spawner(self._build_thread)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._running_threads.
        for thread in self._threads:
            thread.stop()

        return
