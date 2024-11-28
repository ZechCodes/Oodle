from queue import Queue
from threading import Lock

from oodle.thread_groups import ThreadGroup
from oodle.channels import Channel


def test_thread_group():
    def add_to_queue(q: Queue, l: Lock, value: int):
        with l:
            q.put(value)

    q = Queue()
    l = Lock()
    with ThreadGroup() as spawn:
        with l:
            for i in range(10):
                spawn[add_to_queue](q, l, i)

            assert q.qsize() == 0

    assert q.qsize() == 10


def test_channels():
    l1 = Lock()
    l2 = Lock()

    l1.acquire()
    l2.acquire()

    def foo(channel: Channel):
        with l1:
            channel.put("World")
            l2.release()

    def bar(channel: Channel):
        channel.put("Hello")
        l1.release()
        with l2:
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
