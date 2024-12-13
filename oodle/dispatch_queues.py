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
    """Raised when a dispatch is made on the same thread that the dispatch queue is running on. Allowing such a dispatch
    would result in deadlock."""


class DispatchQueue[**P, R]:
    """Dispatch queues allow function calls to be dispatched all on a single thread in the order they were originally
    called."""
    def __init__(self):
        self._queue: Queue[tuple[Future[R], Callable[P, R]]] = Queue()
        self._started = Event()
        self._thread = Thread.run(self._dispatch)
        self._started.set()

    def dispatch(self, func: Callable[P, R], *args: P.args, **kwargs: P.kwargs) -> R:
        """Dispatches a function call to the queue to be called when all prior dispatches finish. This blocks until the
        function returns and returns the result. Raises IllegalDispatchException if called on the same thread that the
        dispatch queue was created on."""
        return self.dispatch_future(func, *args, **kwargs).result()

    def dispatch_future(self, func: Callable[P, R], *args: P.args, **kwargs: P.kwargs) -> Future[R]:
        """Dispatches a function call to the queue to be called when all prior dispatches finish. This returns a
        concurrent.futures.Future that resolves to the return of the function once it is run. Raises
        IllegalDispatchException if called on the same thread that the dispatch queue was created on."""
        if getattr(oodle.thread_locals, "thread", None) == self._thread:
            raise IllegalDispatchException("Cannot dispatch on dispatch thread, will dead lock")

        future = Future()
        self._queue.put((future, partial(func, *args, **kwargs)))
        return future

    def safe_dispatch(self, func: Callable[P, R], *args, **kwargs: P.kwargs) -> R:
        """Dispatches a function call to the queue to be called when all prior dispatches finish. This blocks until the
        function returns and returns the result. If called on the same thread that the dispatch queue was created on,
        the function is not queued and is instead called immediately."""
        if getattr(oodle.thread_locals, "thread", None) == self._thread:
            return func(*args, **kwargs)

        return self.dispatch(func, *args, **kwargs)

    def stop(self):
        """Stops the dispatch thread. This does not empty the dispatch queue."""
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
    """Base type for types that need their methods to exist in a single thread of execution. This eliminates the need
    for synchronisation primitives to order operations. All public methods (excluding classmethods and staticmethods)
    and properties are wrapped in a dispatch queue. All methods can be called as normal, QueuedDispatch handles calling
    the function in a dispatch queue, blocking until it finishes, and returning the result."""
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
    """This descriptor is used to wrap methods and properties that rely on the dispatch queue."""
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
    """This decorator can be used to wrap a function in a dispatch queue. This queues all calls to the function. Calls
    to the function block until the function is run and returns. The result is returned. This uses safe_dispatch to
    allow the function to be recursive."""
    queue = DispatchQueue()

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        return queue.safe_dispatch(func, *args, **kwargs)

    return wrapper
