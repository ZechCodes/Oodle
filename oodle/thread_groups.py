from functools import partial
from threading import Event, Lock
from typing import Callable, Generator
from oodle.threads import Thread


class ThreadGroup:
    """Thread groups manage multiple threads, stopping them all if any raise an exception.

    ThreadGroup can be used as a context manager. All exceptions raised in the threads are then raised in the calling
    thread as an ExceptionGroup."""
    def __init__(self):
        self._threads, self._running_threads = [], []
        self._exception_lock = Lock()
        self._thread_event = Event()
        self._stopping = Event()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.wait()
        return

    @property
    def running(self) -> bool:
        """Returns true as long as there are threads running in the group."""
        return len(self._running_threads) > 0

    def run[**P](self, func: Callable[P, None], *args: P.args, **kwargs: P.kwargs) -> Thread:
        """Runs a function in a thread that belongs to the thread group."""
        return self._create_thread(func, *args, **kwargs)

    def stop(self):
        """Stops the thread group threads."""
        self._stopping.set()
        self._thread_event.set()

    def wait(self):
        """Waits until all threads in the group stop. Raises all exceptions that occurred in the threads in the calling
        thread as an ExceptionGroup."""
        while any(thread.running for thread in self._running_threads):
            self._thread_event.wait()
            self._thread_event.clear()

            if self._stopping.is_set():
                break

        self._stop_threads()
        if exceptions := [thread.exception for thread in self._threads if thread.exception]:
            raise ExceptionGroup(
                f"Exceptions encountered in {self.__class__.__name__}",
                exceptions,
            )

    def _create_thread(self, func, *args, **kwargs):
        ready = Event()
        thread = Thread(
            partial(self._runner, func, ready, *args, **kwargs),
            on_done=self._thread_done,
            on_exception=self._thread_encountered_exception,
        )
        self._threads.append(thread)
        self._running_threads.append(thread)
        ready.set()
        return thread

    def _stop_threads(self):
        for thread in self._threads:
            thread.stop()
            thread.wait()

    def _thread_done(self, thread: Thread):
        self._running_threads.remove(thread)
        self._thread_event.set()

    def _thread_encountered_exception(self, exception: Exception, thread: Thread):
        if not self.running:
            return

        with self._exception_lock:
            self.stop()

    @staticmethod
    def _runner[**P](func: Callable[P, None], ready: Event, *args: P.args, **kwargs: P.kwargs):
        ready.wait()
        func(*args, **kwargs)
