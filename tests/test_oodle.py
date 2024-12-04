from functools import partial
from queue import Queue
from threading import Event, Lock
from unittest.mock import sentinel

import pytest

from oodle import Shield, spawn, ThreadGroup, Channel, sleep


def test_thread_group():
    def add_to_queue(q: Queue, e: Event, value: int):
        print("Waiting")
        e.wait()
        print(f"Adding to queue {i}")
        q.put(value)

    queue = Queue()
    event = Event()
    with ThreadGroup() as group:
        for i in range(10):
            group.spawn[add_to_queue](queue, event, i)

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
        group.spawn[foo](c)
        group.spawn[bar](c)

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

    with pytest.raises(ValueError):
        with ThreadGroup() as group:
            group.spawn[foo_error]()
            group.spawn[foo_event]()
            e1.set()

    assert not e2.is_set()


def test_thread_stopping():
    e = Event()
    def foo(channel: Channel):
        channel.put("World")
        e.set()
        sleep(1000)
        channel.put("!!!")

    c = Channel()
    t = spawn[foo](c)
    e.wait()
    t.stop()

    assert ["World"] == list(c)


def test_thread_lock_release_on_stop():
    l = Lock()
    e = Event()

    def foo():
        with l:
            e.set()
            sleep(100)

    t = spawn[foo]()
    e.wait()
    t.stop()

    assert l.locked() is False


def test_thread_shields():
    def foo():
        with Shield():
            sleep(100)

    t = spawn[foo]()
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
    assert not l1.locked()
    assert not l2.locked()
    assert not l3.locked()


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
    with pytest.raises(ValueError):
        result = Channel.get_first(f1, f2, f3)

    assert not l1.locked()
    assert not l2.locked()
    assert not l3.locked()
    assert result is sentinel
