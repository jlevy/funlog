# funlog

`funlog` is a tiny but useful package that offers a few Python decorators to log or
tally function calls, with good control over what gets logged and when.

## Why Decorator Logging?

We all do quick print debugging sometimes.
Sometimes this is via log statements or other times simply with `print()`.

Logging decorators are a nice compromise between the simplicity of print debugging with
more complex or careful log statements:

```python
@log_calls()
def add(a, b):
    return a + b
```

Then in the logs you will have:
```
INFO:≫ Call: __main__.add(5, 5)
INFO:≪ Call done: __main__.add() took 0.00ms: 10
```

In addition to logging function calls, `funlog` decorators also time the function call
and can log arguments briefly but clearly, abbreviating arguments like long strings or
dataclasses.

The decorator is simple with reasonable defaults but is also fully customizable with
optional arguments to the decorator.
You can control whether to show arg values and return values:

- `show_args` to log the function arguments (truncating at `truncate_length`)

- `show_return_value` to log the return value (truncating at `truncate_length`)

By default both calls and returns are logged, but this is also customizable:

- `show_calls_only=True` to log only calls

- `show_returns_only=True` to log only returns

- `show_timing_only=True` only logs the timing of the call very briefly

If `if_slower_than_sec` is set, only log calls that take longer than that number of
seconds.

By default, uses standard logging with the given `level`, but you can pass in a custom
`log_func` to override that.

By default, it shows values using `quote_if_needed()`, which is brief and very readable.
You can pass in a custom `repr_func` to change that.

I'm publishing it standalone since I have found over the years I frequently want to drop
it into projects. It's often even easier to use than quick print debugging.

It also lets you do very lightweight profiling by having warnings in production when
certain functions are taking a lot of time.
Finally, is easy to get tallies of function calls and runtimes per function after a
program runs a while or at exit.

It deliberately has **zero dependencies** and is a single file with ~500 lines of code.

## Installation

Add the [`funlog`](https://pypi.org/project/funlog/) package to your environment in the
usual way with `pip install funlog`, `poetry add funlog`, or `uv add funlog`.

Or if for some reason you prefer not to change the dependencies of your project at all,
just copy the single file [`funlog.py`](/src/funlog/funlog.py).

## Usage

Here is a more complex example with tallies:

```python
import time
import logging
from funlog import log_calls, log_tallies, tally_calls

# Set up logging however you like.
logging.basicConfig(level=logging.DEBUG, format="%(levelname)s:%(message)s", force=True)


@log_calls()
def add(a, b):
    return a + b


@tally_calls()
def sleep(n):
    time.sleep(0.01 * n)


@tally_calls()
def fibonacci(n):
    if n <= 1:
        return n
    sleep(n)
    return fibonacci(n - 1) + fibonacci(n - 2)


@log_calls()
def long_range(n):
    time.sleep(0.01 * n)
    return " ".join(str(i) for i in range(int(n)))


# Now call the functions:
long_range(fibonacci(add(add(5, 5), 2)))

# And then log tallies of all calls:
log_tallies()
```

Running that gives you:

```
INFO:≫ Call: __main__.add(5, 5)
INFO:≪ Call done: __main__.add() took 0.00ms: 10
INFO:≫ Call: __main__.add(10, 2)
INFO:≪ Call done: __main__.add() took 0.00ms: 12
INFO:⏱ __main__.sleep() took 125ms, now called 1 times, 125ms avg per call, total time 125ms
INFO:⏱ __main__.sleep() took 114ms, now called 2 times, 119ms avg per call, total time 239ms
INFO:⏱ __main__.sleep() took 95.03ms, now called 4 times, 109ms avg per call, total time 438ms
INFO:⏱ __main__.sleep() took 55.05ms, now called 8 times, 89.25ms avg per call, total time 714ms
INFO:⏱ __main__.fibonacci() took 0.00ms, now called 1 times, 0.00ms avg per call, total time 0.00ms
INFO:⏱ __main__.fibonacci() took 0.00ms, now called 2 times, 0.00ms avg per call, total time 0.00ms
INFO:⏱ __main__.fibonacci() took 25.22ms, now called 3 times, 8.41ms avg per call, total time 25.22ms
INFO:⏱ __main__.fibonacci() took 59.16ms, now called 5 times, 16.88ms avg per call, total time 84.38ms
INFO:⏱ __main__.fibonacci() took 128ms, now called 9 times, 26.41ms avg per call, total time 238ms
INFO:⏱ __main__.fibonacci() took 243ms, now called 15 times, 37.59ms avg per call, total time 564ms
INFO:⏱ __main__.sleep() took 33.76ms, now called 16 times, 60.92ms avg per call, total time 975ms
INFO:⏱ __main__.fibonacci() took 429ms, now called 25 times, 49.00ms avg per call, total time 1.23s
INFO:⏱ __main__.fibonacci() took 741ms, now called 41 times, 61.40ms avg per call, total time 2.52s
INFO:⏱ __main__.sleep() took 32.68ms, now called 32 times, 48.04ms avg per call, total time 1.54s
INFO:⏱ __main__.fibonacci() took 23.35ms, now called 75 times, 67.37ms avg per call, total time 5.05s
INFO:⏱ __main__.sleep() took 24.54ms, now called 64 times, 43.64ms avg per call, total time 2.79s
INFO:⏱ __main__.fibonacci() took 60.07ms, now called 129 times, 78.67ms avg per call, total time 10.15s
INFO:⏱ __main__.fibonacci() took 55.71ms, now called 223 times, 91.26ms avg per call, total time 20.35s
INFO:⏱ __main__.sleep() took 44.42ms, now called 128 times, 40.64ms avg per call, total time 5.20s
INFO:⏱ __main__.fibonacci() took 2.07s, now called 396 times, 107ms avg per call, total time 42.19s
INFO:≫ Call: __main__.long_range(144)
INFO:≪ Call done: __main__.long_range() took 1.45s: '0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59 60 61 62 63 64 65 66 67 68 …' (465 chars)
INFO:⏱ Function tallies:
    __main__.fibonacci() was called 465 times, total time 59.73s, avg per call 128ms
    __main__.sleep() was called 232 times, total time 9.11s, avg per call 39.25ms
```

There are several other options.
See docstrings and [test_examples.py](tests/test_examples.py) for more docs and examples
on all the options.

* * *

*This project was built from
[simple-modern-uv](https://github.com/jlevy/simple-modern-uv).*
