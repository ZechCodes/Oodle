from threading import Event

from oodle.threads import Thread


def test_thread_run():
    value = 0
    def f():
        nonlocal value
        value = 1

    t = Thread.run(f)
    t.wait()
    assert value == 1


def test_stop():
    e = Event()
    v = 0
    def f():
        nonlocal v
        e.wait()
        v = 1

    t = Thread.run(f)
    t.stop()
    e.set()
    t.wait()
    assert v == 0
