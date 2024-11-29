# Oodle

Oodle is a package that makes it easier to manage threads.

## Installation

```bash
pip install oodle
```

## Usage

```python
from oodle import spawn


def foo(message):
    print(message)

    
spawn[foo]("Hello World!").wait()
```

That spawns a thread, runs the function `foo` with the argument `"Hello World!"`, and waits for it to finish.

Spawned threads return an `oodle.threads.Thread` which provides a `wait` method that blocks until the thread finishes and an `is_alive` property that returns `True` if the thread is still running.

```python
from oodle import ThreadGroup


def foo(message):
    print(message)


with ThreadGroup() as spawn:
    spawn[foo]("Hello World!")
    spawn[foo]("Goodbye World!")
```

That spawns two threads, runs the function `foo` with the argument `"Hello World!"` in one thread and `"Goodbye World!"` in the other, and waits for both to finish.

```python
from oodle import Channel, ThreadGroup


def foo(message, channel):
    channel.put(message)


channel = Channel()
with ThreadGroup() as spawn:
    spawn[foo]("Hello World!", channel)
    spawn[foo]("Goodbye World!", channel)

message_a, message_b = channel
print(message_a, message_b)
```

Channels also provide a `get` method and an `is_empty` property.

Threads can use shields to protect against interruption during critical sections.

```python
from oodle import Shield, spawn, sleep


def foo():
    with Shield():
        sleep(1)


thread = spawn[foo]()
thread.stop(0.1)  # Raises TimeoutError
```

To enable thread interruption it is necessary to not use anything that can block the thread indefinitely. A great example is `time.sleep`. To avoid this use `oodle.sleep` instead. It is possible to patch `time.sleep` with `oodle.sleep` by importing `oodle.patches.patch_time` before any other modules.

```python
import oodle.patches.patch_time
from time import sleep
```
