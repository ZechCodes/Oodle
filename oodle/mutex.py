from threading import Semaphore


class Mutex(Semaphore):
    def __init__(self):
        super().__init__(1)
        self._held = False

    def __repr__(self):
        return f"{self.__class__.__name__}(held={self.is_held})"

    @property
    def is_held(self) -> bool:
        return self._held

    def acquire(self, blocking = True, timeout = None):
        super().acquire(blocking, timeout)
        self._held = True

    def release(self, n = 1):
        super().release(n)
        self._held = False
