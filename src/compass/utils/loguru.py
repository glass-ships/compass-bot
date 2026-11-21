"""
Custom loguru setup for COMPASS with optional log rotation and enhanced formatting.
Configures loguru to log to both console and a rotating file, with a custom format that
includes timestamps, log levels, and source modules. Records from the standard `logging`
module (i.e. third-party libraries) are intercepted and routed through loguru.

Loguru has a single logger and levels live on sinks, so per-module verbosity is done with a
shared level filter applied to every sink. A single `setup_logging` call still controls
verbosity for both your code and third-party libraries (e.g. quieting a chatty dependency).

Usage:

In the application entry point (e.g. main.py), not in library modules:
```python
from compass.utils.logging_loguru import setup_logging
setup_logging(level="DEBUG", rotate=True, logger_levels={"discord": "WARNING"})
```

Then in any module, import loguru's logger directly:
```python
from loguru import logger
logger.info("This is an info message.")
```

To temporarily capture all log output to a file:
```python
from compass.utils.logging_loguru import log_to_file
with log_to_file("run.log"):
    logger.info("Goes to the console and run.log")
```
"""

import inspect
import logging
import sys
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from loguru import logger

if TYPE_CHECKING:
    from loguru import Record

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

# Loguru levels can't be renamed, so abbreviate them at format time instead
_LEVEL_ABBREV = {"DEBUG": "DBUG", "WARNING": "WARN", "ERROR": "ERR", "CRITICAL": "CRIT"}


def _format(record: "Record") -> str:
    """Build the format string for a record, with a 4-character level name."""
    name = record["level"].name
    record["extra"]["lvl"] = _LEVEL_ABBREV.get(name, name)
    # A callable format must include the newline and exception placeholder itself.
    # Color tags are applied on terminals and stripped automatically for files and pipes.
    return (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{extra[lvl]: <4}</level> | "
        "<cyan>{name: <12}</cyan> | <level>{message}</level>\n{exception}"
    )


_STDLIB_LEVELS = {
    logging.DEBUG: "DEBUG",
    logging.INFO: "INFO",
    logging.WARNING: "WARNING",
    logging.ERROR: "ERROR",
    logging.CRITICAL: "CRITICAL",
}


class InterceptHandler(logging.Handler):
    """Forward standard `logging` records to loguru, keeping the stdlib logger name."""

    def emit(self, record: logging.LogRecord) -> None:
        # Map by number, since stdlib level names may have been renamed (e.g. via addLevelName)
        level: str | int = _STDLIB_LEVELS.get(record.levelno, record.levelno)
        if isinstance(level, int):
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                pass

        # Walk back to the frame that issued the logging call, so loguru reports the right caller
        frame, depth = inspect.currentframe(), 0
        while frame and (depth == 0 or frame.f_code.co_filename == logging.__file__):
            frame = frame.f_back
            depth += 1

        # Use the stdlib logger name so `logger_levels` keys match e.g. "discord" as before
        logger.opt(depth=depth, exception=record.exc_info).patch(lambda r: r.update(name=record.name)).log(
            level, record.getMessage()
        )


# Level filter shared by all sinks, e.g. {"": "INFO", "discord": "WARNING"}.
# The most specific matching module prefix wins, so overrides may be more or less verbose.
_level_filter: dict[str | None, str | int | bool] = {"": "DEBUG"}
# Open file sinks keyed by resolved path, so callers can toggle file logging on/off
_file_sinks: dict[Path, int] = {}


def _remove_sink(sink_id: int) -> None:
    """Remove a sink from loguru (closing its file) and forget it, if still present."""
    try:
        logger.remove(sink_id)
    except ValueError:
        pass  # Already removed, e.g. by setup_logging(reset_handlers=True)
    for path, sid in list(_file_sinks.items()):
        if sid == sink_id:
            del _file_sinks[path]


def setup_logging(
    level: LogLevel = "INFO",
    rotate: bool = True,
    num_backups: int = 15,
    log_file: str | Path | None = None,
    reset_handlers: bool = True,
    logger_levels: Mapping[str, LogLevel | int] | None = None,
):
    """Configure loguru with a custom format and optional rotating file sink.

    Arguments
    ---------
    level: str
        The default logging level. Options are "DEBUG", "INFO", "WARNING", "ERROR", and "CRITICAL".
    rotate: bool
        If True, add a file sink that rotates logs at midnight and keeps N old files.
    num_backups: int
        The number of rotated files to keep. Default is 15. Only relevant if `rotate` is True.
    log_file: str | Path | None
        Path of the rotating log file (default: ~/compass.log). Missing parent directories are created.
        Only relevant if `rotate` is True.
    reset_handlers: bool
        If True, remove all existing loguru sinks (including loguru's default stderr sink)
        before adding new ones. This prevents duplicate logs if setup_logging is called multiple times.
    logger_levels: Mapping[str, str | int] | None
        Per-module level overrides, e.g. {"discord": "WARNING", "my_package": "DEBUG"}.
        These may be more or less verbose than `level`.
    """
    _level_filter.clear()
    _level_filter[""] = level
    _level_filter.update(logger_levels or {})

    if reset_handlers:
        logger.remove()
        _file_sinks.clear()

    # Route stdlib logging (third-party libraries) into loguru; loguru's filter decides what's shown
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # Setup console sink first, so a file sink failure below is reported in the usual format
    logger.add(sys.stdout, format=_format, filter=_level_filter, level=0)

    if rotate:
        # Default log file path is ~/compass.log
        log_path = Path(log_file) if log_file is not None else Path.home() / "compass.log"
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            logger.add(
                log_path,
                format=_format,
                filter=_level_filter,
                level=0,
                rotation="00:00",
                retention=num_backups,
            )
        except OSError as e:
            logger.error(f"Failed to create log file sink: {e}. Logging will only go to console.")


def add_log_fh(log_file: str | Path, mode: Literal["w", "a"] = "w") -> int:
    """Add a file sink, replacing any existing one for the same file.

    Arguments
    ---------
    log_file: str | Path
        Path to the log file. Missing parent directories are created.
    mode: "w" | "a"
        File mode: "w" to overwrite (default) or "a" to append.

    Returns
    -------
    int
        The loguru sink id that was added.
    """

    resolved_log_file = Path(log_file).resolve()
    resolved_log_file.parent.mkdir(parents=True, exist_ok=True)

    # Keep only one open sink per log_file so callers can toggle logging on/off.
    remove_log_fh(resolved_log_file)

    sink_id = logger.add(resolved_log_file, mode=mode, format=_format, filter=_level_filter, level=0)
    _file_sinks[resolved_log_file] = sink_id

    return sink_id


def remove_log_fh(log_file: str | Path) -> int:
    """Close and remove the file sink added by `add_log_fh` for the given log_file.

    Returns the number of sinks removed.
    """

    sink_id = _file_sinks.get(Path(log_file).resolve())
    if sink_id is None:
        return 0

    _remove_sink(sink_id)
    return 1


@contextmanager
def log_to_file(log_file: str | Path, mode: Literal["w", "a"] = "w") -> Iterator[int]:
    """Context manager to temporarily add a file sink.

    Yields the sink id. It is removed when the context exits, even if an exception occurs.
    """

    sink_id = add_log_fh(log_file, mode=mode)
    try:
        yield sink_id
    finally:
        _remove_sink(sink_id)
