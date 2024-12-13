from queue import Queue
from typing import Callable

import oodle


class Channel[T]:
    """A simple wrapper around a queue.Queue to make using them a bit simpler. It is a context manager so that the
    channel can be closed automatically. It is also an iterator that can block while waiting for more results.

    on_put_callback can be used to assign a function that is called when a new item is put into the channel."""
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
        """Puts a value into the channel queue. Raises ValueError if the channel is closed. Calls on_put_callback when a
        value is put."""
        if self._queue is None:
            raise ValueError("Channel is closed")

        self._queue.put(value)
        if self._on_put_callback:
            self._on_put_callback(value)

    def get(self) -> T:
        """Gets a value from the channel queue. Raises ValueError if the channel is closed. Blocks until a value is
        received."""
        if self._queue is None:
            raise ValueError("Channel is closed")

        return self._queue.get()

    @classmethod
    def get_first(cls, *funcs: "Callable[[Channel[T]], None]") -> T:
        """This classmethod runs all functions it is passed in a ThreadGroup and passes them a shared channel. When a
        value is put into the channel the ThreadGroup is stopped and the value is returned from the channel."""
        def on_put_callback(_):
            group.stop()

        with cls(on_put_callback=on_put_callback) as channel:
            with oodle.ThreadGroup() as group:
                for func in funcs:
                    group.run(func, channel)

            result = channel.get()

        return result
