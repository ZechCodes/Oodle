from queue import Queue
from typing import Callable


class Channel:
    def __init__(self):
        self._queue = Queue()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def __iter__(self):
        return self

    def __next__(self):
        if self.is_empty:
            raise StopIteration

        return self.get()

    @property
    def is_closed(self) -> bool:
        return self._queue is None

    @property
    def is_empty(self) -> bool:
        return self._queue.empty()

    def put(self, value):
    def close(self):
        self._queue.shutdown(True)
        self._queue = None

    def put(self, value: T):
        if self._queue is None:
            raise ValueError("Channel is closed")

        self._queue.put(value)

    def get(self):
        if self._queue is None:
            raise ValueError("Channel is closed")

        return self._queue.get()
