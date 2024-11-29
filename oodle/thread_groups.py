from threading import Event, Semaphore

from .spawners import spawn, Spawner


class ThreadGroup:
    def __init__(self):
        self._threads = []
        self._cancel_event = Event()
        self._stop_event = Event()

    def _build_thread(self, func, *args, **kwargs):
        thread = Spawner(stop_callback=self._stop_event.set, cancel_callback=self._cancel_event.set)[func](*args, **kwargs)
        self._threads.append(thread)
        return thread

    def __enter__(self):
        return Spawner(self._build_thread)

    def __exit__(self, exc_type, exc_val, exc_tb):
        while any(thread.is_alive for thread in self._threads):
            self._stop_event.wait()
            self._stop_event.clear()

            if self._cancel_event.is_set():
                break

        return
