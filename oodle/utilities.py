import threading
import time
from functools import wraps
from itertools import cycle
from typing import TYPE_CHECKING, Generator, Callable

import oodle
from oodle.exceptions import ExitThread

if TYPE_CHECKING:
    from oodle.threads import Thread


def abort_concurrent_calls[**P](func: Callable[P, None]) -> Callable[P, None]:
    func_lock = threading.Lock()

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs):
        if not func_lock.acquire(blocking=False):
            return

        try:
            func(*args, **kwargs)
        finally:
            func_lock.release()

    return wrapper


def sleep(seconds: float, /):
    if hasattr(oodle.thread_locals, "thread"):
        _sleep_on_thread(seconds, oodle.thread_locals.thread)

    else:
        _sleep_periodically(seconds)


def _sleep_periodically(seconds: float):
    iterations, remainder = divmod(seconds, 0.01)
    for _ in range(int(iterations)):
        time.sleep(0.01)

    if remainder:
        time.sleep(remainder)


def _sleep_on_thread(seconds: float, thread: "Thread"):
    sleep_duration = generate_timeout_durations(seconds)
    try:
        duration = min(0.01, next(sleep_duration))
        while duration > 0 and not thread.stopping and not thread.wait(timeout=duration):
            duration = min(0.01, next(sleep_duration))

    except SystemError:
        exiting = True
    except TimeoutError:
        exiting = False
    else:
        exiting = True # The thread has exited

    if exiting:
        raise ExitThread


def wait_for(thread_or_iterator, /, *threads: "Thread", timeout: float | None = None):
    if hasattr(thread_or_iterator, "__iter__"):
        threads = list(thread_or_iterator)

    else:
        threads = [thread_or_iterator, *threads]

    timeout_duration = generate_timeout_durations(timeout)
    while any(thread.running for thread in threads):
        sleep(min(0.01, next(timeout_duration)))

    if exceptions := [thread.exception for thread in threads if thread.exception]:
        raise ExceptionGroup(
            f"Exceptions encountered in {wait_for}",
            exceptions,
        )


def generate_timeout_durations(
    timeout: float, clock: Callable[[], float] = time.monotonic
) -> Generator[float, None, None]:
    if not timeout:
        yield from cycle([0])
        return

    start = clock()
    while (elapsed := clock() - start) < timeout:
        yield timeout - elapsed

    raise TimeoutError



def safely_acquire(lock: threading.Lock):
    try:
        lock.acquire()
    except (ExitThread, SystemError):
        pass

    lock.acquire(blocking=False)
