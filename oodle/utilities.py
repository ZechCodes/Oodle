import threading
import time

from oodle.threads import ExitThread, Thread


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


def wait_for(thread_or_iterator, /, *threads: Thread, timeout: float | None = None):
    if hasattr(thread_or_iterator, "__iter__"):
        threads = list(thread_or_iterator)

    else:
        threads = [thread_or_iterator, *threads]

    start = time.monotonic()
    while any(thread.is_alive for thread in threads):
        if timeout is not None and time.monotonic() - start > timeout:
            break

        sleep(0.01)
    else:
        return

    raise TimeoutError("Failed to wait for threads")
