import threading

from oodle.threads import InterruptibleThread


class Shield:
    def __init__(self, thread: InterruptibleThread | None = None):
        self._thread = thread if thread else self._get_thread()

    def __enter__(self):
        self._thread.shield.acquire()
        return None

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._thread.shield.release()
        return

    def _get_thread(self) -> InterruptibleThread:
        match threading.current_thread():
            case InterruptibleThread() as thread:
                return thread

            case _:
                raise RuntimeError("Cannot use Shield outside of an InterruptibleThread")
