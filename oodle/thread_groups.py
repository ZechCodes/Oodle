from dataclasses import dataclass
from threading import Event, Semaphore, Thread

from .mutex import Mutex
from .spawners import Spawner


@dataclass
class ThreadExceptionInfo:
    thread: Thread
    exception: Exception


class ThreadGroup:
    def __init__(self):
        self._threads, self._running_threads = [], []
        self._stop_event = Event()
        self._exception_mutex = Mutex()
        self._exception: ThreadExceptionInfo | None = None
        self._shutdown_event = Event()

        self._spawner = Spawner(self._build_thread)

    @property
    def spawn(self) -> Spawner:
        return self._spawner

    def _build_thread(self, func, *args, **kwargs):
        thread = Spawner(group=self)[func](*args, **kwargs)
        self._threads.append(thread)
        self._running_threads.append(thread)
        return thread

    def stop(self):
        self._shutdown_event.set()
        self._stop_event.set()

    def _stop_threads(self):
        for thread in self._threads:
            if thread.is_alive:
                thread.stop()

    def thread_encountered_exception(self, thread: Thread, exception):
        if self._stop_event.is_set():
            return

        with self._exception_mutex:
            if not self._exception:
                self._exception = ThreadExceptionInfo(thread, exception)
                self.stop()

    def thread_stopped(self, thread: Thread):
        try:
            self._running_threads.remove(thread)
        except ValueError:
            pass

        self._stop_event.set()

    def wait(self):
        while any(thread.is_alive for thread in self._running_threads):
            self._stop_event.wait()

            if self._shutdown_event.is_set():
                self._stop_threads()

                if self._exception:
                    raise self._exception.exception

            self._stop_event.clear()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.wait()
        return
