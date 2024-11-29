import sys
import threading
from oodle.locks import Lock


class ThreadingProxy:
    def __getattr__(self, item):
        if item == "Lock":
            return Lock

        return getattr(threading, item)


def inject_hooks():
    sys.modules["threading"] = ThreadingProxy()
