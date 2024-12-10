from threading import RLock, current_thread

import oodle


class Shield:
    def __init__(self):
        self.lock = self._get_lock()

    def __enter__(self):
        self.lock.acquire()
        return None

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.lock.release()
        return

    def _get_lock(self) -> RLock:
        if hasattr(oodle.thread_locals, "shield_lock"):
            return oodle.thread_locals.shield_lock

        raise Exception("Shields can only be used with threads created by Oodle")
