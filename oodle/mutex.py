from threading import Semaphore


class Mutex(Semaphore):
    def __init__(self):
        super().__init__(1)

    def __repr__(self):
        return f"{self.__class__.__name__}(held={self._value == 1})"
