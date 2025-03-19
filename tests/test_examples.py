"""
Some basic examples of how to use the `log_calls`, `log_if_modifies`, and
`tally_calls` decorators.
"""

import logging
import time

from funlog import log_calls, log_if_modifies, log_tallies, tally_calls

# This ensures the configuration is applied even if logging was already configured.
logging.basicConfig(level=logging.DEBUG, format="%(levelname)s:%(message)s", force=True)

log = logging.getLogger(__name__)


# Default: info level, show args and return values:
@log_calls()
def add(a: int, b: int) -> int:
    return a + b


# Don't show arguments:
@log_calls(level="debug", show_args=False)
def multiply(a: int, b: int) -> int:
    return a * b


# Don't show return value:
@log_calls(show_return_value=False)
def divide(a: float, b: float) -> float:
    return a / b


# Only log when function is called:
@log_calls(show_calls_only=True)
def subtract(a: int, b: int) -> int:
    return a - b


# Only log when function returns:
@log_calls(show_returns_only=True)
def power(a: int, b: int) -> int:
    return a**b


# Only log if function takes longer than 0.1s:
@log_calls(if_slower_than=0.1)
def slow_function(delay: float) -> str:
    time.sleep(delay)
    return f"Slept for {delay} seconds"


# Example of log_if_modifies decorator:
@log_if_modifies()
def append_if_not_exists(items: list[str], item: str) -> list[str]:
    if item not in items:
        items.append(item)
    return items


# Examples of tally_calls decorator:
@tally_calls()
def fibonacci(n: int) -> int:
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)


@tally_calls(min_total_runtime=0.1, periodic_ratio=1.5)
def slow_counter(n: int) -> int:
    time.sleep(0.01)
    return n + 1


def test_examples():
    """
    Logging should look something like this for the examples below:

    Basic call examples:
    INFO:≫ Call: test_simple_example.add(2, 3)
    INFO:≪ Call done: test_simple_example.add() took 0.00ms: 5
    DEBUG:≫ Call: test_simple_example.multiply
    DEBUG:≪ Call done: test_simple_example.multiply() took 0.00ms: 20
    INFO:≫ Call: test_simple_example.divide(10, 2)
    INFO:≪ Call done: test_simple_example.divide() took 0.00ms
    INFO:≫ Call: test_simple_example.subtract(10, 3)
    INFO:⏱ Call to test_simple_example.power(2, 3) took 0.00ms: 8
    INFO:This should not log (too fast):
    INFO:This should log (slow enough):
    INFO:⏱ Call to test_simple_example.slow_function(0.15) took 153ms
    INFO:This should log (list is modified):
    INFO:This should not log (list is not modified):
    INFO:This will generate many recursive calls that will be tallied:
    INFO:⏱ test_simple_example.fibonacci() took 0.00ms, now called 1 times, 0.00ms avg per call, total time 0.00ms
    INFO:⏱ test_simple_example.fibonacci() took 0.00ms, now called 2 times, 0.00ms avg per call, total time 0.00ms
    INFO:⏱ test_simple_example.fibonacci() took 0.09ms, now called 3 times, 0.03ms avg per call, total time 0.09ms
    INFO:⏱ test_simple_example.fibonacci() took 0.12ms, now called 5 times, 0.04ms avg per call, total time 0.21ms
    INFO:⏱ test_simple_example.fibonacci() took 0.00ms, now called 10 times, 0.04ms avg per call, total time 0.36ms
    INFO:⏱ test_simple_example.fibonacci() took 0.01ms, now called 20 times, 0.03ms avg per call, total time 0.60ms
    INFO:⏱ test_simple_example.fibonacci() took 0.02ms, now called 40 times, 0.02ms avg per call, total time 0.89ms
    INFO:⏱ test_simple_example.fibonacci() took 0.00ms, now called 80 times, 0.02ms avg per call, total time 1.53ms
    INFO:⏱ test_simple_example.fibonacci() took 0.00ms, now called 160 times, 0.01ms avg per call, total time 2.29ms
    INFO:Call multiple times to trigger periodic logging:
    INFO:⏱ test_simple_example.slow_counter() took 12.52ms, now called 9 times, 12.03ms avg per call, total time 108ms
    INFO:Log all tallies at the end:
    INFO:⏱ Function tallies:
        test_simple_example.slow_counter() was called 10 times, total time 121ms, avg per call 12.08ms
        test_simple_example.fibonacci() was called 177 times, total time 2.96ms, avg per call 0.02ms
    """

    log.info("\n\nBasic call examples:")
    result = add(2, 3)
    assert result == 5

    result = multiply(4, 5)
    assert result == 20

    result = divide(10, 2)
    assert result == 5

    result = subtract(10, 3)
    assert result == 7

    result = power(2, 3)
    assert result == 8

    log.info("This should not log (too fast):")
    result = slow_function(0.05)
    assert "Slept for 0.05 seconds" in result

    log.info("This should log (slow enough):")
    result = slow_function(0.15)
    assert "Slept for 0.15 seconds" in result

    log.info("This should log (list is modified):")
    items = ["apple", "banana"]
    result = append_if_not_exists(items, "cherry")
    assert "cherry" in result

    log.info("This should not log (list is not modified):")
    result = append_if_not_exists(items, "banana")
    assert result == items

    log.info("This will generate many recursive calls that will be tallied:")
    result = fibonacci(10)
    assert result == 55

    log.info("Call multiple times to trigger periodic logging:")
    for i in range(10):
        slow_counter(i)

    log.info("Log all tallies at the end:")
    log_tallies()
