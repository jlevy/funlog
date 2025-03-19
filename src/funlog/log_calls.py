import functools
import logging
import time
from collections.abc import Callable, Iterable
from typing import (
    Any,
    Literal,
    ParamSpec,
    TypeAlias,
    TypeVar,
)

from strif import abbrev_str, quote_if_needed, single_line

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

    You can control whether to show arg values and return values with `show_args` and
    `show_return_value` (truncating at `truncate_length`).

    By default both calls and returns are logged, but this is also customizable:

    - `show_calls_only=True` to log only calls
    - `show_returns_only=True` to log only returns
    - `show_timing_only=True` only logs the timing of the call very briefly

    If `if_slower_than_sec` is set, only log calls that take longer than that number of
    seconds.

    By default, uses standard logging with the given `level`, but you can pass in a a custom
    `log_func` to override that. By default shows values using `quot
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
