from threading import Thread as _Thread


class Thread:
    def __init__(self, thread: _Thread):
        self._thread = thread

    @property
    def is_alive(self):
        return self._thread.is_alive()

    def wait(self, timeout: float | None=None):
        self._thread.join(timeout)

    @classmethod
    def spawn(cls, target, *args, **kwargs):
        thread = _Thread(target=target, args=args, kwargs=kwargs, daemon=True)
        thread.start()
        return cls(thread)
