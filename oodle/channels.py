from queue import Queue


class Channel:
    def __init__(self):
        self._queue = Queue()

    def __iter__(self):
        return self

    def __next__(self):
        if self.is_empty:
            raise StopIteration

        return self.get()

    @property
    def is_empty(self):
        return self._queue.empty()

    def put(self, value):
        self._queue.put(value)

    def get(self):
        return self._queue.get()
