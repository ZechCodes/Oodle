from threading import Event, Semaphore

from .spawners import spawn, Spawner


class ThreadGroup:
    def __init__(self):
        self._threads = []
        self._stop_event = Event()
        self._exception_mutex = Mutex()
        self._exception: ThreadExceptionInfo | None = None

        self._spawner = Spawner(self._build_thread)

    @property
    def spawn(self) -> Spawner:
        return self._spawner

    def _build_thread(self, func, *args, **kwargs):
        thread = Spawner(group=self)[func](*args, **kwargs)
        self._threads.append(thread)
        return thread

    def stop(self):
        self._shutdown_event.set()
        self._stop_event.set()


    def __exit__(self, exc_type, exc_val, exc_tb):
    def thread_encountered_exception(self, thread: Thread, exception):
        if self._stop_event.is_set():
            return

        with self._exception_mutex:
            if not self._exception:
                self._exception = ThreadExceptionInfo(thread, exception)
                self.stop()

    def thread_stopped(self, thread: Thread):
        self._stop_event.set()

        while any(thread.is_alive for thread in self._threads):
            self._stop_event.wait()
            self._stop_event.clear()

            if self._cancel_event.is_set():
                break
    def __enter__(self):
        return self

        return
