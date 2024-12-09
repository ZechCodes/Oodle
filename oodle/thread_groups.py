from dataclasses import dataclass
from threading import Event, Thread
from typing import Callable, TYPE_CHECKING

from .mutex import Mutex
from .spawners import Spawner

if TYPE_CHECKING:
    from oodle.tasks import Task


@dataclass
class TaskExceptionInfo:
    task: "Task"
    exception: Exception


class ThreadGroup:
    def __init__(self):
        self._tasks, self._running_tasks = [], []
        self._stop_event = Event()
        self._exception_mutex = Mutex()
        self._exception: TaskExceptionInfo | None = None
        self._shutdown_event = Event()

        self._spawner = Spawner(self._build_task)

    @property
    def spawn(self) -> Spawner:
        return self._spawner

    def _build_task(self, func, *args, **kwargs):
        ready = Event()
        task = Spawner(group=self)[self._runner](func, ready, *args, **kwargs)
        self._tasks.append(task)
        self._running_tasks.append(task)
        ready.set()
        return task

    def _runner[**P](self, func: Callable[P, None], ready: Event, *args: P.args, **kwargs: P.kwargs):
        ready.wait()
        func(*args, **kwargs)

    def stop(self):
        self._shutdown_event.set()
        self._stop_event.set()

    def _stop_tasks(self):
        for task in self._tasks:
            if task.is_running:
                task.stop()

    def task_encountered_exception(self, task: "Task", exception):
        if self._stop_event.is_set():
            return

        with self._exception_mutex:
            if not self._exception:
                self._exception = TaskExceptionInfo(task, exception)
                self.stop()

    def task_stopped(self, task: "Task"):
        self._running_tasks.remove(task)
        self._stop_event.set()

    def wait(self):
        while any(thread.is_alive for thread in self._running_tasks):
            self._stop_event.wait()

            if self._shutdown_event.is_set():
                self._stop_tasks()

                if self._exception:
                    raise self._exception.exception

            self._stop_event.clear()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.wait()
        return
