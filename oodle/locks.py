import threading

from oodle.threads import StoppableThread


class Lock:
    def __init__(self):
        self._lock = threading.Lock()

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()

    def locked(self):
        return self._lock.locked()

    def acquire(self):
        self._lock.acquire()
        if isinstance(threading.current_thread(), StoppableThread):
            threading.current_thread().acquired_locks.add(self)


    def release(self):
        self._lock.release()
        if isinstance(threading.current_thread(), StoppableThread):
            threading.current_thread().acquired_locks.remove(self)
