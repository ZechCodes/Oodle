from threading import Event

import oodle
from oodle.shields import Shield
from oodle.threads import Thread
from oodle.utilities import sleep


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


def test_stop_sleep():
    v = 0
    def f():
        nonlocal v
        sleep(100)
        v = 1

    t = Thread.run(f)
    t.stop(wait=True)
    assert v == 0


def test_stop_sleep_with_shield():
    v = 0
    e = Event()
    def f():
        nonlocal v
        with Shield():
            e.set()
            sleep(0.01)
            v = 1

    t = Thread.run(f)
    e.wait()
    t.stop(wait=True)
    assert v == 1
