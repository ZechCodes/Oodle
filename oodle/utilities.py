import threading
import time


def sleep(seconds: float, /):
    if hasattr(threading.current_thread(), "pending_stop_event"):
        threading.current_thread().pending_stop_event.wait(seconds)
    else:
        iterations, remainder = divmod(seconds, 0.01)
        for _ in range(int(iterations)):
            time.sleep(0.01)

        if remainder:
            time.sleep(remainder)
