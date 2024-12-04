from queue import Queue
from typing import Callable



class Channel[T]:
    def __init__(self, *, on_put_callback: Callable[[T], None] | None = None):
        self._queue = Queue()
        self._on_put_callback = on_put_callback

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

    def close(self):
        self._queue.shutdown(True)
        self._queue = None

    def put(self, value: T):
        if self._queue is None:
            raise ValueError("Channel is closed")

        self._queue.put(value)
        if self._on_put_callback:
            self._on_put_callback(value)

    def get(self) -> T:
        if self._queue is None:
            raise ValueError("Channel is closed")

        return self._queue.get()
