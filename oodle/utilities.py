import threading
import time
from functools import wraps
from itertools import cycle
from typing import TYPE_CHECKING, Generator, Callable, Any
from weakref import ref

import oodle
from oodle.exceptions import ExitThread

if TYPE_CHECKING:
    from oodle.threads import Thread


class AbortConcurrentCallsFunctionWrapper[**P]:
    """Decorator that prevents a function from being called concurrently on separate threads. Concurrent calls return
    immediately with a None return. It always returns None and drops any return the function has."""
    def __init__(self, function: Callable[P, None]):
        self.function = function
        self.instances: dict[int | None, tuple[ref | None, Callable[P, None]]] = {}

    def __call__(self, *args, **kwargs):
        function = self._get_instance_function(None)
        if not function:
            function = self._wrap_in_lock(self.function, threading.Lock())
            self._add_instance_function(None, function)

        return function

    def __get__(self, instance, owner):
        if not instance:
            return self

        function = self._get_instance_function(instance)
        if not function:
            function = self._wrap_in_lock(self.function.__get__(instance, owner), threading.Lock())
            self._add_instance_function(instance, function)

        return function

    def _add_instance_function(self, instance: Any, locked_func: Callable[P, None]):
        instance_id = id(instance)
        def del_instance(_):
            del self.instances[instance_id]

        self.instances[instance_id] = (ref(instance, del_instance), locked_func)

    def _get_instance_function(self, instance: Any) -> Callable[P, None] | None:
        if id(instance) in self.instances:
            return self.instances[id(instance)][1]

        return None

    @staticmethod
    def _wrap_in_lock(func: Callable[P, None], lock: threading.Lock) -> Callable[P, None]:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not lock.acquire(blocking=False):
                return

            try:
                func(*args, **kwargs)
            finally:
                lock.release()

        return wrapper


def abort_concurrent_calls[**P](func: Callable[P, None]) -> Callable[P, None]:
    """Decorator that prevents a function from being called concurrently on separate threads. Concurrent calls return
    immediately with a None return. It always returns None and drops any return the function has."""
    return AbortConcurrentCallsFunctionWrapper[P](func)


def sleep(seconds: float, /):
    """Sleep replacement that periodically gives control back to the interpreter to allow thrown exceptions to be
    processed. If used within an Oodle thread it waits on the thread. Otherwise, time.sleep is used with very short
    sleep durations."""
    if hasattr(oodle.thread_locals, "thread"):
        _sleep_on_thread(seconds, oodle.thread_locals.thread)

    else:
        _sleep_periodically(seconds)


def _sleep_periodically(seconds: float):
    sleep_duration = generate_timeout_durations(seconds)
    try:
        duration = min(0.01, next(sleep_duration))
        while duration > 0:
            time.sleep(duration)
            duration = min(0.01, next(sleep_duration))
    except TimeoutError:
        return


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


def wait_for(*threads: "Thread", timeout: float | None = None):
    """Waits for multiple threads to complete. This raises an ExceptionGroup of all errors raised in each thread. It
    does not stop threads for any reason."""
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
    """Yields the remaining time according to the given clock. It defaults to using the time.monotonic clock."""
    if not timeout:
        yield from cycle([0])
        return

    start = clock()
    while (elapsed := clock() - start) < timeout:
        yield timeout - elapsed

    raise TimeoutError



def safely_acquire(lock: threading.Lock):
    """Attempts to acquire a lock without being interrupted by an ExitThread or SystemError."""
    try:
        lock.acquire()
    except (ExitThread, SystemError):
        pass

    lock.acquire(blocking=False)
