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

### Thread Groups

```python
from oodle import ThreadGroup


def foo(message):
    print(message)


with ThreadGroup() as group:
    group.spawn[foo]("Hello World!")
    group.spawn[foo]("Goodbye World!")
```

That spawns two threads, runs the function `foo` with the argument `"Hello World!"` in one thread and `"Goodbye World!"` in the other, and waits for both to finish.

If any thread in a thread group raises an exception, all other threads are stopped and the exception is raised in the calling thread.

### Channels

```python
from oodle import Channel, ThreadGroup

def foo(message, channel):
    channel.put(message)

with Channel() as channel:
    with ThreadGroup() as group:
        group.spawn[foo]("Hello World!", channel)
        group.spawn[foo]("Goodbye World!", channel)

    message_a, message_b = channel
    print(message_a, message_b)
```

Channels also provide a `get` method and an `is_empty` property.

Additionally, the channel type provides a way to select the first message that arrives and stop all threads.

```python
from oodle import Channel
from oodle.utilities import sleep

def foo(channel):
    channel.put("Hello World!")
    
def bar(channel):
    sleep(1)
    channel.put("Goodbye World!")
    
result = Channel.get_first(foo, bar)
print(result)  # "Hello World!"
```

Internally this uses a thread group to spawn the functions and a channel to communicate between them. So if any of the functions raises an exception, all other threads are stopped and the exception is raised in the calling thread. If no exception is raised, all threads will be stopped after the first message arrives.

### Shields

Threads can use shields to protect against interruption during critical sections.

```python
from oodle import Shield, spawn, sleep


def foo():
    with Shield():
        sleep(1)


thread = spawn[foo]()
thread.stop(0.1)  # Raises TimeoutError
```

### Blocking & Patching

To enable thread interruption it is necessary to not use anything that can block the thread indefinitely. A great example is `time.sleep`. To avoid this use `oodle.sleep` instead. It is possible to patch `time.sleep` with `oodle.sleep` by importing `oodle.patches.patch_time` before any other modules.

```python
import oodle.patches
oodle.patches.patch_time()

from time import sleep
```
