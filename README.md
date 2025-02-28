# funlog

`funlog` is a tiny but quite useful package that offers a few Python decorators to log
function calls, with good control over what gets logged and when.
It also times the function call and logs arguments briefly but clearly, abbreviating
arguments like long strings or dataclasses.

It is fully customizable with optional decorator arguments.
You can log only slow calls, only if a function modifies its first argument, or tally
calls and log them later.

I'm publishing it standalone since I often like to drop this into projects and it
simplifies print-debugging a lot of things or lets you do very lightweight profiling
where get logs if certain functions are taking a lot of time, or tallies of function
calls after a program runs a while or at exit.

Minimal dependencies (only the tiny [strif](https://github.com/jlevy/strif)).

## Installation

```shell
pip install funlog
```

## Usage

Suppose you have a few functions:

```python
import time
import logging
from funlog import log_calls, log_if_modifies, log_tallies, tally_calls

logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s:%(message)s",
    force=True,
)

@log_calls()
def add(a, b):
    return a + b

@log_calls(level="warn", if_slower_than=0.1, show_return_value=False)
def slow_function(delay):
    time.sleep(delay)
    return f"Slept for {delay} seconds"

# Now call the functions.
add(2, 3)
slow_function(0.5)
```

Running that gives you:

```
INFO:≫ Call: __main__.add(2, 3)
INFO:≪ Call done: __main__.add() took 0.00ms: 5
WARNING:⏱ Call to __main__.slow_function(0.5) took 503ms
```

See [test_examples.py](tests/test_examples.py) for more examples and docstrings for more
docs on all the options.

* * *

*This project was built from
[simple-modern-poetry](https://github.com/jlevy/simple-modern-poetry).*
