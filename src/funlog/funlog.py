import functools
import logging
import re
import threading
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import (
    Any,
    Literal,
    ParamSpec,
    TypeAlias,
    TypeVar,
)

EMOJI_CALL_BEGIN = "≫"
EMOJI_CALL_END = "≪"
EMOJI_TIMING = "⏱"

# Support the non-standard "message" log level, if the logger does support message
# level as a higher-priority informative log level.
# Just gracefully fall back to "warning" if not supported.
LogLevelStr: TypeAlias = Literal["debug", "info", "warning", "error", "message"]
LogFunc: TypeAlias = Callable[..., None]


DEFAULT_TRUNCATE = 200

log = logging.getLogger(__name__)

# ------------------------------------------------------------------------------
# strif functions
# ------------------------------------------------------------------------------

# (These functions are simply copied from strif to minimize dependencies.)


def abbrev_str(string: str, max_len: int | None = 80, indicator: str = "…") -> str:
    """
    Abbreviate a string, adding an indicator like an ellipsis if required. Set `max_len` to
    None or 0 not to truncate items.
    """
    if not string or not max_len or len(string) <= max_len:
        return string
    elif max_len <= len(indicator):
        return string[:max_len]
    else:
        return string[: max_len - len(indicator)] + indicator


def single_line(text: str) -> str:
    """
    Convert newlines and other whitespace to spaces.
    """
    return re.sub(r"\s+", " ", text).strip()


def is_quotable(s: str) -> bool:
    """
    Does this string need to be quoted? Same as the logic used by `shlex.quote()`
    but with the addition of ~ since this character isn't generally needed to be quoted.
    """
    return bool(re.compile(r"[^\w@%+=:,./~-]").search(s))


def quote_if_needed(
    arg: Any,
    to_str: Callable[[Any], str] = str,
    quote: Callable[[Any], str] = repr,
    is_quotable: Callable[[str], bool] = is_quotable,
) -> str:
    """
    A friendly way to format a Path or string for display, adding quotes only
    if needed for clarity. Intended for brevity and readability, not as a
    parsable format.

    Quotes strings similarly to `shlex.quote()`, so is mostly compatible with
    shell quoting rules. By default, uses `str()` on non-string objects and
    `repr()` for quoting, so is compatible with Python.
    ```
    print(quote_if_needed("foo")) -> foo
    print(quote_if_needed("item_3")) -> item_3
    print(quote_if_needed("foo bar")) -> 'foo bar'
    print(quote_if_needed("!foo")) -> '!foo'
    print(quote_if_needed("")) -> ''
    print(quote_if_needed(None)) -> None
    print(quote_if_needed(Path("file.txt"))) -> file.txt
    print(quote_if_needed(Path("my file.txt"))) -> 'my file.txt'
    print(quote_if_needed("~/my/path/file.txt")) -> '~/my/path/file.txt'
    ```

    For true shell compatibility, use `shlex.quote()` instead. But note
    `shlex.quote()` can be confusingly ugly because of shell quoting rules:
    ```
    print(quote_if_needed("it's a string")) -> "it's a string"
    print(shlex.quote("it's a string")) -> 'it'"'"'s a string'
    ```

    Can pass in `to_str` and `quote` functions to customize this behavior.
    """
    if not arg:
        return quote(arg)
    if not isinstance(arg, str) and not isinstance(arg, Path):
        return to_str(arg)

    if isinstance(arg, Path):
        arg = str(arg)  # Treat Paths like strings for display.
    if is_quotable(arg):
        return quote(arg)
    else:
        return to_str(arg)


# ------------------------------------------------------------------------------
# Utilities
# ------------------------------------------------------------------------------


def _get_log_func(level: LogLevelStr, log_func: LogFunc | None = None) -> LogFunc:
    if log_func is None:
        log_func = getattr(log, level.lower(), None)
        if level == "message" and log_func is None:
            log_func = log.warning  # Fallback for logger without "message" level.
    if log_func is None:
        raise ValueError(f"Invalid log level: {level!r}")
    return log_func


def balance_quotes(s: str) -> str:
    """
    Ensure balanced single and double quotes in a string, adding any missing quotes.
    This is valuable especially for log file syntax highlighting.
    """
    stack: list[str] = []
    for char in s:
        if char in ("'", '"'):
            if stack and stack[-1] == char:
                stack.pop()
            else:
                stack.append(char)

    if stack:
        for quote in stack:
            s += quote

    return s


def abbreviate_arg(
    value: Any,
    repr_func: Callable[[Any], str] = quote_if_needed,
    truncate_length: int | None = DEFAULT_TRUNCATE,
) -> str:
    """
    Abbreviate an argument value for logging.
    """
    truncate_length = truncate_length or 0
    if isinstance(value, str) and truncate_length:
        abbreviated = abbrev_str(single_line(value), truncate_length - 2, indicator="…")
        result = repr_func(abbreviated)

        if len(result) >= truncate_length:
            result += f" ({len(value)} chars)"
    elif truncate_length:
        result = abbrev_str(repr_func(value), truncate_length - 2, indicator="…")
    else:
        result = single_line(repr_func(value))

    return balance_quotes(result)


def format_duration(seconds: float) -> str:
    if seconds < 100.0 / 1000.0:
        return f"{seconds * 1000:.2f}ms"
    elif seconds < 1.0:
        return f"{seconds * 1000:.0f}ms"
    elif seconds < 100.0:
        return f"{seconds:.2f}s"
    else:
        return f"{seconds:.0f}s"


def function_name(func: Callable[..., Any], include_module: bool = True) -> str:
    if include_module:
        short_module = func.__module__.split(".")[-1] if func.__module__ else None
        return f"{short_module}.{func.__qualname__}" if short_module else func.__qualname__
    else:
        return func.__qualname__


def default_to_str(value: Any) -> str:
    return abbreviate_arg(value, quote_if_needed, DEFAULT_TRUNCATE)


def format_args(
    args: Iterable[Any],
    kwargs: dict[str, Any],
    to_str: Callable[[Any], str] = default_to_str,
) -> str:
    return ", ".join(
        [to_str(arg) for arg in args] + [f"{k}={to_str(v)}" for k, v in kwargs.items()]
    )


def format_func_call(
    func_name: str,
    args: Iterable[Any],
    kwargs: dict[str, Any],
    to_str: Callable[[Any], str] = default_to_str,
) -> str:
    """
    Format a function call for logging, returning a string in the format
    `some_func(my_value, 'another value', k1=None, k2='some val')`.

    The default `to_str` formats values for readability, abbreviating strings,
    omitting quotes unless needed for readability, truncating long values,
    condensing newlines, and (if necessary when abbreviating quoted strings)
    balancing quotes.

    Use `to_str=repr` to log the exact values passed in.
    """

    return f"{func_name}({format_args(args, kwargs, to_str)})"


# ------------------------------------------------------------------------------
# Logging decorators
# ------------------------------------------------------------------------------

P = ParamSpec("P")
R = TypeVar("R")


def log_calls(
    level: LogLevelStr = "info",
    show_args: bool = True,
    show_return_value: bool = True,
    show_calls_only: bool = False,
    show_returns_only: bool = False,
    show_timing_only: bool = False,
    if_slower_than: float = 0.0,
    truncate_length: int | None = DEFAULT_TRUNCATE,
    repr_func: Callable[[Any], str] = quote_if_needed,
    log_func: LogFunc | None = None,
    include_module: bool = True,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Decorator to log function calls and returns and time taken, with optional display of
    arguments and return values.

    You can control whether to show arg values and return values:

    - `show_args` to show the function arguments (truncating at `truncate_length`)
    - `show_return_value` to show the return value (truncating at `truncate_length`)

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
    """

    def to_str(value: Any) -> str:
        return abbreviate_arg(value, repr_func, truncate_length)

    def format_call(func_name: str, args: Any, kwargs: Any):
        if show_args:
            return format_func_call(func_name, args, kwargs, to_str)
        else:
            return func_name

    log_func = _get_log_func(level, log_func)

    show_calls = True
    show_returns = True
    if if_slower_than > 0.0:
        show_calls = False
        show_returns = False
    if show_calls_only:
        show_calls = True
        show_returns = False
    elif show_returns_only or show_timing_only:
        show_calls = False
        show_returns = True
    if show_timing_only:
        show_return_value = False
        show_args = False
        include_module = False

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            func_name = function_name(func, include_module)

            # Capture args now in case they are mutated by the function.
            call_str = format_call(func_name, args, kwargs)

            if show_calls:
                log_func(f"{EMOJI_CALL_BEGIN} Call: {call_str}")

            start_time = time.time()
            exception_info = None
            result = None
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                exception_info = str(e)
                raise  # Re-raise to preserve stack trace.
            finally:
                end_time = time.time()
                elapsed = end_time - start_time

                if show_returns:
                    if exception_info:
                        return_msg = (
                            f"{EMOJI_CALL_END} Exception: {func_name}(): "
                            f"{abbrev_str(exception_info, truncate_length)}"
                        )
                    else:
                        if show_calls:
                            # If we already logged the call, log the return in a corresponding style.
                            return_msg = (
                                f"{EMOJI_CALL_END} Call done: {func_name}() "
                                f"took {format_duration(elapsed)}"
                            )
                        else:
                            return_msg = (
                                f"{EMOJI_TIMING} Call to {call_str} took {format_duration(elapsed)}"
                            )
                    if show_return_value and not exception_info:
                        log_func("%s: %s", return_msg, to_str(result))
                    else:
                        log_func("%s", return_msg)
                elif elapsed > if_slower_than:
                    return_msg = (
                        f"{EMOJI_TIMING} Call to {call_str} took {format_duration(elapsed)}"
                    )
                    log_func("%s", return_msg)

        return wrapper

    return decorator


def log_if_modifies(
    level: LogLevelStr = "info",
    repr_func: Callable[[Any], str] = repr,
    log_func: LogFunc | None = None,
    include_module: bool = True,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Decorator to log function calls if the returned value differs from the first
    argument input. Does not log exceptions.
    """
    log_func = _get_log_func(level, log_func)

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            if not args:
                raise ValueError("Function must have at least one positional argument")

            original_value: Any = args[0]
            result = func(*args, **kwargs)

            if result != original_value:
                func_name = function_name(func, include_module)
                log_func(
                    "%s(%s) -> %s",
                    func_name,
                    repr_func(original_value),
                    repr_func(result),
                )

            return result

        return wrapper

    return decorator


# ------------------------------------------------------------------------------
# Tallying decorators
# ------------------------------------------------------------------------------


@dataclass
class Tally:
    calls: int = 0
    total_time: float = 0.0
    last_logged_count: int = 0
    last_logged_total_time: float = 0.0


_tallies: dict[str, Tally] = {}
_tallies_lock = threading.Lock()


DISABLED = float("inf")


def tally_calls(
    level: LogLevelStr = "info",
    min_total_runtime: float = 0.0,
    periodic_ratio: float = 2.0,
    if_slower_than: float = DISABLED,
    log_func: LogFunc | None = None,
    include_module: bool = True,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Decorator to monitor performance by tallying function calls and total runtime, only logging
    periodically (every time calls exceed `periodic_ratio` more in count or runtime than the last
    time it was logged) or if runtime is greater than `if_slower_than` seconds).

    Currently does not log exceptions.
    """

    log_func = _get_log_func(level, log_func)

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            start_time = time.time()

            result = func(*args, **kwargs)

            end_time = time.time()
            elapsed = end_time - start_time

            func_name = function_name(func, include_module)

            should_log = False
            calls: int = 0
            total_time: float = 0.0

            with _tallies_lock:
                if func_name not in _tallies:
                    _tallies[func_name] = Tally()

                _tallies[func_name].calls += 1
                _tallies[func_name].total_time += elapsed

                should_log = _tallies[func_name].total_time >= min_total_runtime and (
                    elapsed > if_slower_than
                    or _tallies[func_name].calls
                    >= periodic_ratio * _tallies[func_name].last_logged_count
                    or _tallies[func_name].total_time
                    >= periodic_ratio * _tallies[func_name].last_logged_total_time
                )

                if should_log:
                    calls = _tallies[func_name].calls
                    total_time = _tallies[func_name].total_time
                    _tallies[func_name].last_logged_count = calls
                    _tallies[func_name].last_logged_total_time = total_time

            if should_log:
                log_func(
                    "%s %s() took %s, now called %d times, %s avg per call, total time %s",
                    EMOJI_TIMING,
                    func_name,
                    format_duration(elapsed),
                    calls,
                    format_duration(total_time / calls),
                    format_duration(total_time),
                )

            return result

        return wrapper

    return decorator


def log_tallies(
    level: LogLevelStr = "info",
    if_slower_than: float = 0.0,
    log_func: LogFunc | None = None,
):
    """
    Log all tallies and runtimes of tallied functions.
    """
    log_func = _get_log_func(level, log_func)

    with _tallies_lock:
        tallies_copy = {k: replace(t) for k, t in _tallies.items()}

    tallies_to_log = {k: t for k, t in tallies_copy.items() if t.total_time >= if_slower_than}
    if tallies_to_log:
        log_lines: list[str] = []
        log_lines.append(f"{EMOJI_TIMING} Function tallies:")
        for fkey, t in sorted(
            tallies_to_log.items(), key=lambda item: item[1].total_time, reverse=True
        ):
            log_lines.append(
                "    %s() was called %d times, total time %s, avg per call %s"  # noqa: UP031
                % (
                    fkey,
                    t.calls,
                    format_duration(t.total_time),
                    format_duration(t.total_time / t.calls) if t.calls else "N/A",
                )
            )
        log_func("\n".join(log_lines))
