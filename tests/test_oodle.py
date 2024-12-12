from itertools import islice, cycle, batched
from queue import Queue
from threading import Event, Lock

import pytest

from oodle import Shield, ThreadGroup, Channel, Thread
from oodle.dispatch_queues import DispatchQueue, IllegalDispatchException
from oodle.utilities import sleep, wait_for


def test_thread_group():
    def add_to_queue(q: Queue, e: Event, value: int):
        e.wait()
        q.put(value)

    queue = Queue()
    event = Event()
    with ThreadGroup() as group:
        for i in range(10):
            group.run(add_to_queue, queue, event, i)

        assert queue.qsize() == 0
        event.set()

    assert queue.qsize() == 10


def test_channels():
    e1 = Event()
    e2 = Event()

    def foo(channel: Channel):
        e1.wait()
        channel.put("World")
        e2.set()

    def bar(channel: Channel):
        channel.put("Hello")
        e1.set()
        e2.wait()
        channel.put("!!!")


    with ThreadGroup() as group:
        c = Channel()
        group.run(foo, c)
        group.run(bar, c)

    x, y, z = c
    assert x == "Hello"
    assert y == "World"
    assert z == "!!!"
    assert c.is_empty


def test_thread_group_error():
    e1 = Event()
    e2 = Event()

    def foo_error():
        e1.wait()
        raise ValueError

    def foo_event():
        sleep(0.1)
        e2.set()

    try:
        with ThreadGroup() as group:
            group.run(foo_error)
            group.run(foo_event)
            e1.set()
    except *ValueError:
        raised_value_error = True
    else:
        raised_value_error = False

    assert raised_value_error is True
    assert e2.is_set() is False


def test_thread_stopping():
    e = Event()
    def foo(channel: Channel):
        channel.put("World")
        e.set()
        sleep(1000)
        channel.put("!!!")

    c = Channel()
    t = Thread.run(foo, c)
    assert e.wait(0.1), "Should never timeout"
    t.stop(0.1)

    assert ["World"] == list(c)


def test_thread_lock_release_on_stop():
    l = Lock()
    e = Event()

    def foo():
        with l:
            e.set()
            sleep(100)

    t = Thread.run(foo)
    e.wait()
    t.stop()
    t.wait()

    assert l.locked() is False


def test_thread_shields():
    shields_up = Event()

    def foo():
        with Shield():
            shields_up.set()
            sleep(100)

    t = Thread.run(foo)
    shields_up.wait()
    with pytest.raises(TimeoutError):
        t.stop(0.1)


def test_channel_get_first():
    l1, l2, l3 = Lock(), Lock(), Lock()

    def f1(channel: Channel):
        with l1:
            sleep(1)
            channel.put("f1")

    def f2(channel: Channel):
        with l2:
            sleep(1)
            channel.put("f2")

    def f3(channel: Channel):
        with l3:
            channel.put("f3")

    result = Channel.get_first(f1, f2, f3)
    assert result == "f3"
    assert l1.locked() is False
    assert l2.locked() is False
    assert l3.locked() is False


def test_channel_get_first_error():
    l1, l2, l3 = Lock(), Lock(), Lock()

    def f1(channel: Channel):
        with l1:
            sleep(1)
            channel.put("f1")

    def f2(channel: Channel):
        with l2:
            sleep(1)
            channel.put("f2")

    def f3(channel: Channel):
        with l3:
            raise ValueError

    result = sentinel = object()
    raised_value_error = False
    try:
        result = Channel.get_first(f1, f2, f3)
    except *ValueError:
        raised_value_error = True

    assert raised_value_error is True
    assert not l1.locked()
    assert not l2.locked()
    assert not l3.locked()
    assert result is sentinel


def test_dispatch_queue():
    def foo(delay, message):
        if delay:
            sleep(delay)

        l.append(message)

    l = []
    q = DispatchQueue()
    wait_for(
        [
            Thread.run(q.dispatch, foo, 0.01, "foo"),
            Thread.run(q.dispatch, foo, 0, "bar"),
        ]
    )
    assert l == ["foo", "bar"]


def test_dispatch_queue_doesnt_deadlock_on_own_thread():
    def foo():
        q.dispatch(bar)

    def bar():
        l.append("bar")

    l = []
    q = DispatchQueue()
    with pytest.raises(IllegalDispatchException):
        q.dispatch(foo)

