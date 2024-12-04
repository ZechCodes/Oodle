import threading
import time

from oodle.threads import ExitThread


def sleep(seconds: float, /):
    if hasattr(threading.current_thread(), "pending_stop_event"):
        exiting = False
        try:
            threading.current_thread().pending_stop_event.wait(seconds)
        except SystemError:
            exiting = True

        if exiting:
            raise ExitThread
    else:
        iterations, remainder = divmod(seconds, 0.01)
        for _ in range(int(iterations)):
            time.sleep(0.01)

        if remainder:
            time.sleep(remainder)
