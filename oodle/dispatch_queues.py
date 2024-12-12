from concurrent.futures import Future
from functools import partial, wraps
from queue import Queue
from threading import Event, current_thread
from types import MethodType, FunctionType
from typing import Callable, Self, overload, Type, Any

import oodle
from oodle import Thread
from oodle.exceptions import ExitThread


class IllegalDispatchException(Exception):
    ...


class DispatchQueue[**P, R]:
    def __init__(self):
        self._queue: Queue[tuple[Future[R], Callable[P, R]]] = Queue()
        self._started = Event()
        self._thread = Thread.run(self._dispatch)
        self._started.set()

    def dispatch(self, func: Callable[P, R], *args: P.args, **kwargs: P.kwargs) -> R:
        return self.dispatch_future(func, *args, **kwargs).result()

    def dispatch_future(self, func: Callable[P, R], *args: P.args, **kwargs: P.kwargs) -> Future[R]:
        if getattr(oodle.thread_locals, "thread", None) == self._thread:
            raise IllegalDispatchException("Cannot dispatch on dispatch thread, will dead lock")

        future = Future()
        self._queue.put((future, partial(func, *args, **kwargs)))
        return future

    def safe_dispatch(self, func: Callable[P, R], *args, **kwargs: P.kwargs) -> R:
        if getattr(oodle.thread_locals, "thread", None) == self._thread:
            return func(*args, **kwargs)

        return self.dispatch(func, *args, **kwargs)

    def stop(self):
        self._thread.stop()

    def _dispatch(self):
        self._started.wait()
        while self._thread.running:
            future, func = self._queue.get()
            try:
                result = func()
            except Exception as e:
                shutdown_exceptions = ExitThread
                if self._thread.stopping:
                    shutdown_exceptions |= SystemError

                if isinstance(e, shutdown_exceptions):
                    break

                future.set_exception(e)
            else:
                future.set_result(result)


class QueuedDispatcher:
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._dispatch_queue = DispatchQueue()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        for name in dir(cls):
            if name.startswith("_"):
                continue

            attr = getattr(cls, name)
            if isinstance(attr, FunctionType | property):
                setattr(cls, name, QueuedDispatchDescriptor(attr))


class QueuedDispatchDescriptor[**P, R]:
    def __init__(self, func: Callable[P, R]):
        self.func = func

    @overload
    def __get__(self, instance: None, owner: Type) -> Self:
        ...

    @overload
    def __get__(self, instance: QueuedDispatcher, owner: Type) -> Callable[P, R]:
        ...

    def __get__(self, instance: QueuedDispatcher | None, owner: Type) -> Callable[P, R] | Self:
        if instance is None:
            return self

        if isinstance(self.func, property):
            return instance._dispatch_queue.safe_dispatch(self.func.fget, instance)

        return partial(instance._dispatch_queue.safe_dispatch, self.func, instance)

    def __set__(self, instance, value):
        if isinstance(self.func, property):
            instance._dispatch_queue.safe_dispatch(self.func.fset, instance, value)
        else:
            self.func = value


def queued_dispatch[**P, R](func: Callable[P, R]) -> Callable[P, R]:
    queue = DispatchQueue()

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        return queue.safe_dispatch(func, *args, **kwargs)

    return wrapper
