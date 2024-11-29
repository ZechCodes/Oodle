from .spawners import spawn, Spawner


class ThreadGroup:
    def __init__(self):
        self._threads = []

    def _build_thread(self, func, *args, **kwargs):
        thread = spawn[func](*args, **kwargs)
        self._threads.append(thread)
        return thread

    def __enter__(self):
        return Spawner(self._build_thread)

    def __exit__(self, exc_type, exc_val, exc_tb):
        while self._threads:
            thread = self._threads.pop()
            if thread.is_alive:
                thread.wait()

        return
