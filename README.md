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

In addition to logging function calls, `funlog` decorators can log arguments briefly but
clearly, abbreviating arguments like long strings or dataclasses and also time the
function call (and logs it in a friendly way in milliseconds or seconds).

I'm publishing it standalone since I have found over the years I frequently want to drop
it into projects. It's often even easier to write than a quick print debugging statement
or a single log statement.

In addition to logging calls, it lets you do *very* simple profiling by having warnings
in production when certain functions are take more than a specified amount of time.
Finally, you can use the decorators to get tallies of function calls and runtimes per
function after a program runs a while or at exit.

It deliberately has **zero dependencies** and is a single file with ~500 lines of code.

## Installation

Add the [`funlog`](https://pypi.org/project/funlog/) package to your environment in the
usual way with `pip install funlog`, `poetry add funlog`, or `uv add funlog`.

Or if for some reason you prefer not to change the dependencies of your project at all,
just copy the single file [`funlog.py`](/src/funlog/funlog.py).

## Examples

A more realistic example is the small
[lint script](https://github.com/jlevy/funlog/blob/main/devtools/lint.py) from this
project:

```python
import subprocess
from rich import print as rprint
from funlog import log_calls

@log_calls(level="warning", show_timing_only=True)
def run(cmd: list[str]) -> int:
    rprint()
    rprint(f"[bold green]❯ {' '.join(cmd)}[/bold green]")
    errcount = 0
    try:
        subprocess.run(cmd, text=True, check=True)
    except subprocess.CalledProcessError as e:
        rprint(f"[bold red]Error: {e}[/bold red]")
        errcount = 1

    return errcount
```

It has the output

```
❯ codespell --write-changes src tests devtools README.md
⏱ Call to run took 88.78ms

❯ ruff check --fix src tests devtools
All checks passed!
⏱ Call to run took 310ms

❯ ruff format src tests devtools
4 files left unchanged
⏱ Call to run took 10.81ms

❯ basedpyright src tests devtools
0 errors, 0 warnings, 0 notes
⏱ Call to run took 2.07s
```

Here is a contrived example to illustrate recursive calls and tallies:

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

## Mini FAQ

- **Isn't it better to do real logging?** Decorator-based logging isn't much different
  from regular logging; think of these decorators as simply as a syntactic convenience.
  Also, they are only handy in certain situations, not something to overuse.
  The biggest benefit is it's less typing than a full log statement and worrying about
  formatting: it handles the name of the function, the args and return values, etc and
  it also truncates values so large values aren't logged by accident.

- **If you want to trace function calls, shouldn't you use a debugger?** Decorator
  logging doesn't replace a debugger.
  It's just one more tool where you want some visibility with little effort.

- **Doesn't this create tons of spam in your logs?** Again, this has all the usual
  considerations of regular logging.
  It will spam logs if you use it on functions that are called a lot.
  In production, it tends to be useful either for slower or less frequently called
  functions (like making an API call that takes a few seconds and consumes resources
  anyway) or with the `if_slower_than_sec` option so it only logs unexpectedly slow
  calls or with the tally options.

- **Is this just a poor version of tracing?** The goal is to be as simple as possible,
  even useful on little command-line apps.
  If you're wanting proper visibility into function calls on production cloud-deployed
  apps, you probably want something more appropriate, like OpenTelemetry.

- **What about when you only want to log sometimes, not on every call?** Probably just
  use a regular log statement.
  Or only log tallies or use the `if_slower_than_sec` option.

## Options

The `log_calls()` decorator is simple with reasonable defaults but is also fully
customizable with optional arguments to the decorator.
You can control whether to show arg values and return values:

- `show_args` to log the function arguments (truncating at `truncate_length`)

- `show_return_value` to log the return value (truncating at `truncate_length`)

By default both calls and returns are logged, but this is also customizable:

- `show_calls_only=True` to log only calls

- `show_returns_only=True` to log only returns

- `show_timing_only=True` only logs the timing of the call very briefly

If `if_slower_than_sec` is set, only log calls that take longer than that number of
seconds.

By default, it uses standard logging with the given `level`, but you can pass in a
custom `log_func` to override that.

Also by default, it shows values using `quote_if_needed()`, which is brief and very
readable. You can pass in a custom `repr_func` to change that.

## Alternatives

This is intended to only be a tiny library.
It doesn't replace any other logging framework or telemetry system.

The main alternative that is similarly simple is
[logdecorator](https://github.com/sighalt/logdecorator).
It has similar use cases but a more explicit usage style, where you give the messages to
the decorator itself.
It seems like a good option but personally, I find that if I'm writing the log message,
I'd often rather just use a regular log statement.
(Also it does not offer tallies or timings like `funlog` does.)

[Eliot](https://github.com/itamarst/eliot) is an interesting and more ambitious logging
framework that includes somewhat similar decorator-based logging.

The main benefit of `funlog` is it is very simple to drop into a project when you want
it and it's quick to add or remove a log decoration.

* * *

*This project was built from
[simple-modern-uv](https://github.com/jlevy/simple-modern-uv).*
