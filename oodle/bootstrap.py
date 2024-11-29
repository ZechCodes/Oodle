import sys
import threading
from functools import cache
import time
from .utilities import sleep


class TimeProxy:
    @cache
    def __getattr__(self, item):
        if item == "sleep":
            return sleep

        return getattr(time, item)


def patch_runtime():
    sys.modules["time"] = TimeProxy()
