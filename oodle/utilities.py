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


class AbortConcurrentCallsFunctionWrapper[**P, R]:
    def __init__(self, function: Callable[P, R]):
        self.function = function
        self.instances: dict[int | None, tuple[ref | None, Callable[P, R]]] = {}

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

    def _add_instance_function(self, instance: Any, locked_func: Callable[P, R]):
        instance_id = id(instance)
        def del_instance(_):
            del self.instances[instance_id]

        self.instances[instance_id] = (ref(instance, del_instance), locked_func)

    def _get_instance_function(self, instance: Any) -> Callable[P, R] | None:
        if id(instance) in self.instances:
            return self.instances[id(instance)][1]

        return None

    @staticmethod
    def _wrap_in_lock(func, lock):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not lock.acquire(blocking=False):
                return

            try:
                return func(*args, **kwargs)
            finally:
                lock.release()

        return wrapper


def abort_concurrent_calls[**P, R](func: Callable[P, R]) -> Callable[P, R]:
    return AbortConcurrentCallsFunctionWrapper[P, R](func)


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


def wait_for(*threads: "Thread", timeout: float | None = None):
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
