import threading
import time

from oodle.threads import ExitThread, Thread, InterruptibleThread

def sleep(seconds: float, /):
    match threading.current_thread():
        case InterruptibleThread() as thread:
            _sleep_using_event(seconds, thread)

        case _:
            _sleep_periodically(seconds)


def _sleep_periodically(seconds: float):
        iterations, remainder = divmod(seconds, 0.01)
        for _ in range(int(iterations)):
            time.sleep(0.01)

        if remainder:
            time.sleep(remainder)


def _sleep_using_event(seconds: float, thread: InterruptibleThread):
    try:
        event_set = thread.stopping.wait(seconds)
    except SystemError:
        exiting = True
    else:
        exiting = event_set

    if exiting:
        raise ExitThread


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
