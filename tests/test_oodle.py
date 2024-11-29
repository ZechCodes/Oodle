from queue import Queue
from threading import Event
from time import sleep

from oodle import spawn, ThreadGroup, Channel, Lock


def test_thread_group():
    def add_to_queue(q: Queue, e: Event, value: int):
        e.wait()
        q.put(value)

    queue = Queue()
    event = Event()
    with ThreadGroup() as spawn:
        for i in range(10):
            spawn[add_to_queue](queue, event, i)

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


    with ThreadGroup() as spawn:
        c = Channel()
        spawn[foo](c)
        spawn[bar](c)

    x, y, z = c
    assert x == "Hello"
    assert y == "World"
    assert z == "!!!"
    assert c.is_empty


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
