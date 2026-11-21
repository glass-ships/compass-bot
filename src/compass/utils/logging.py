"""
Custom logging setup for Compass Bot with optional log rotation and enhanced formatting.
Configures the root logger to log to both console and a rotating file,
with a custom format that includes timestamps, log levels, and source modules.

Levels are set on loggers, never on handlers, so a single `setup_logging` call controls
verbosity for both your code and third-party libraries (e.g. quieting a chatty dependency).

Usage:

In the application entry point (e.g. main.py), not in library modules:
```python
from compass.utils.logging import setup_logging
setup_logging(level="DEBUG", rotate=True, logger_levels={"discord": "WARNING"})
```

Then in any module, use the standard logging module to log messages:
```python
import logging
logger = logging.getLogger(__name__)
logger.info("This is an info message.")
```

To temporarily capture all log output to a file:
```python
from compass.utils.logging import log_to_file
with log_to_file("run.log"):
    logger.info("Goes to the console and run.log")
```
"""

import logging
import logging.handlers
import sys
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Literal

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class OriginFormatter(logging.Formatter):
    """Display the source module for root logger records."""

    def format(self, record):
        record.origin = record.module if record.name == "root" else record.name
        return super().format(record)


def _detach_handler(handler: logging.Handler) -> None:
    """Remove a handler from the root logger and release its resources."""
    logging.getLogger().removeHandler(handler)
    handler.close()


_FMT = "%(asctime)s | %(levelname)-4s | %(origin)-12s | %(message)s"
_DATE_FMT = "%Y-%m-%d %H:%M:%S"
LOG_FMT = OriginFormatter(fmt=_FMT, datefmt=_DATE_FMT)


def setup_logging(
    level: LogLevel = "INFO",
    rotate: bool = True,
    num_backups: int = 15,
    log_file: str | Path | None = None,
    reset_handlers: bool = True,
    logger_levels: Mapping[str, LogLevel | int] | None = None,
):
    """Configure logging with a custom format and optional timed rotating file handler.

    Arguments
    ---------
    level: str
        The logging level to set for the root logger. Options are "DEBUG", "INFO", "WARNING", "ERROR", and "CRITICAL".
    rotate: bool
        If True, add a TimedRotatingFileHandler that rotates logs at midnight and keeps N backups.
    num_backups: int
        The number of backup files to keep. Default is 15. Only relevant if `rotate` is True.
    log_file: str | Path | None
        Path of the rotating log file (default: ~/compass.log). Missing parent directories are created.
        Only relevant if `rotate` is True.
    reset_handlers: bool
        If True, remove existing handlers from the root logger before adding new ones.
        This prevents duplicate logs if setup_logging is called multiple times.
    logger_levels: Mapping[str, str | int] | None
        Per-logger level overrides, e.g. {"discord": "WARNING", "my_package": "DEBUG"}.
        These may be more or less verbose than `level`, since handlers do not filter by level.
    """
    root = logging.getLogger()
    root.setLevel(level)
    for name, logger_level in (logger_levels or {}).items():
        logging.getLogger(name).setLevel(logger_level)

    # Shorten level names to 4 characters for better log formatting
    logging.addLevelName(logging.DEBUG, "DBUG")
    logging.addLevelName(logging.INFO, "INFO")
    logging.addLevelName(logging.WARNING, "WARN")
    logging.addLevelName(logging.ERROR, "ERR")
    logging.addLevelName(logging.CRITICAL, "CRIT")

    if reset_handlers:
        # Remove existing handlers to prevent duplicate logs
        for handler in root.handlers[:]:
            _detach_handler(handler)

    # Setup stream handler first, so a file handler failure below is reported in the usual format
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(LOG_FMT)
    root.addHandler(sh)

    if rotate:
        if log_file is None:
            log_file = Path.home() / "compass.log"
        # Setup timed rotating file handler
        try:
            Path(log_file).parent.mkdir(parents=True, exist_ok=True)
            fh = logging.handlers.TimedRotatingFileHandler(
                log_file,
                when="midnight",
                backupCount=num_backups,
            )
        except OSError as e:
            root.error(f"Failed to create log file handler: {e}. Logging will only go to console.")
        else:
            fh.setFormatter(LOG_FMT)
            root.addHandler(fh)


def add_log_fh(log_file: str | Path, mode: Literal["w", "a"] = "w") -> logging.FileHandler:
    """Add a file handler to the root logger, replacing any existing one for the same file.

    Arguments
    ---------
    log_file: str | Path
        Path to the log file. Missing parent directories are created.
    mode: "w" | "a"
        FileHandler mode: "w" to overwrite (default) or "a" to append.

    Returns
    -------
    logging.FileHandler
        The handler that was added.
    """

    resolved_log_file = Path(log_file).resolve()
    resolved_log_file.parent.mkdir(parents=True, exist_ok=True)

    # Keep only one open handler per log_file so callers can toggle logging on/off.
    remove_log_fh(resolved_log_file)

    file_handler = logging.FileHandler(resolved_log_file, mode=mode)
    file_handler.setFormatter(LOG_FMT)
    logging.getLogger().addHandler(file_handler)

    return file_handler


def remove_log_fh(log_file: str | Path) -> int:
    """Close and remove root logger file handlers that write to the given log_file.

    Returns the number of handlers removed.
    """

    resolved_log_file = Path(log_file).resolve()
    removed = 0

    for handler in logging.getLogger().handlers[:]:
        if not isinstance(handler, logging.FileHandler):
            continue

        if Path(handler.baseFilename).resolve() != resolved_log_file:
            continue

        _detach_handler(handler)
        removed += 1

    return removed


@contextmanager
def log_to_file(log_file: str | Path, mode: Literal["w", "a"] = "w") -> Iterator[logging.FileHandler]:
    """Context manager to temporarily add a file handler to the root logger.

    Yields the handler. It is removed when the context exits, even if an exception occurs.
    """

    handler = add_log_fh(log_file, mode=mode)
    try:
        yield handler
    finally:
        _detach_handler(handler)
