"""
    ANSI codes are a bit weird to decipher if you're unfamiliar with them, so here's a refresher
    It starts off with a format like \x1b[XXXm where XXX is a semicolon separated list of commands
    The important ones here relate to color.
    30-37 are black, red, green, yellow, blue, magenta, cyan and white in that order
    40-47 are the same except for the background
    90-97 are the same but "bright" foreground
    100-107 are the same as the bright ones but for the background.
    1 means bold, 2 means dim, 0 means reset, and 4 means underline.
"""
import os, sys
import logging
from typing import Any


class _MissingSentinel:
    __slots__ = ()

    def __eq__(self, other) -> bool:
        return False

    def __bool__(self) -> bool:
        return False

    def __hash__(self) -> int:
        return 0

    def __repr__(self):
        return '...'

MISSING: Any = _MissingSentinel()
FORMAT = "[%(asctime)s][%(levelname)-7s][%(name)-30s] %(message)s"
DATEFMT = "%Y-%m-%d %H:%M:%S"
COLORS = {
        'reset': '\x1b[0m',
        'purple': '\x1b[35m',
        'red': '\x1b[31m',
        'grey_b': '\x1b[30;1m',
        'blue_b': '\x1b[34;1m',
        'yellow_b': '\x1b[33;1m',
        'red_bk': '\x1b[41m',
        'black_bk': '\x1b[40;1m',
    }
class _ColorFormatter(logging.Formatter):
        
    # ANSI color codes
    # LEVEL_COLORS = [
    #     (logging.DEBUG, COLORS['black_bk']),
    #     (logging.INFO, COLORS['blue_b']),
    #     (logging.WARNING, COLORS['yellow_b']),
    #     (logging.ERROR, COLORS['red']),
    #     (logging.CRITICAL, COLORS['red_bk']),
    # ]
    
    # FORMATS = {
    #     level: logging.Formatter(
    #         "{} [%(asctime)s] {} [%(levelname)-7s] {} [%(name)-30s] {} [%(message)s]".format(
    #             COLORS['grey_b'], color, COLORS['purple'], COLORS['reset']
    #         ),
    #         DATEFMT,
    #     )
    #     for level, color in LEVEL_COLORS
    # }

    FORMATS = {
        logging.DEBUG: COLORS['grey_b'] + FORMAT + COLORS['reset'],
        logging.INFO: COLORS['blue_b'] + FORMAT + COLORS['reset'],
        logging.WARNING: COLORS['yellow_b'] + FORMAT + COLORS['reset'],
        logging.ERROR: COLORS['red'] + FORMAT + COLORS['reset'],
        logging.CRITICAL: COLORS['red_bk'] + FORMAT + COLORS['reset']
    }
    
    def format(self, record):
        formatter = self.FORMATS.get(record.levelno)
        if formatter is None:
            formatter = self.FORMATS[logging.DEBUG]

        # Override the traceback to always print in red
        if record.exc_info:
            text = formatter.formatException(record.exc_info)
            record.exc_text = f'\x1b[31m{text}\x1b[0m'

        output = formatter.format(record)

        # Remove the cache layer
        record.exc_text = None
        return output

    
def stream_supports_color(stream: Any) -> bool:
    # Pycharm and Vscode support color in their inbuilt editors
    if 'PYCHARM_HOSTED' in os.environ or os.environ.get('TERM_PROGRAM') == 'vscode':
        return True

    is_a_tty = hasattr(stream, 'isatty') and stream.isatty()
    if sys.platform != 'win32':
        return is_a_tty

    # ANSICON checks for things like ConEmu, 
    # WT_SESSION checks if this is Windows Terminal
    return is_a_tty and ('ANSICON' in os.environ or 'WT_SESSION' in os.environ)


def setup_logging(
    *,
    handler: logging.Handler = MISSING,
    formatter: logging.Formatter = MISSING,
    level: int = MISSING,
    root: bool = False,
) -> None:
    """A helper function to setup logging.

    Args:
        handler (logging.Handler, optional): The log handler to use for the library's logger. 
            Defaults to `logging.StreamHandler()`.
        formatter (logging.Formatter, optional): The formatter to use with the given log handler.
            Defaults to color based logging if available, else simple logging.
        level (int, optional): Log level for the library's logger. Defaults to `logging.INFO`.
        root (bool, optional): Set up the root logger rather than the library logger. Default False.
    """

    if level is MISSING:
        level = logging.INFO

    if handler is MISSING:
        handler = logging.StreamHandler()

    if formatter is MISSING:
        if isinstance(handler, logging.StreamHandler) and stream_supports_color(handler.stream):
            formatter = _ColorFormatter()
        else:
            formatter = logging.Formatter(fmt=FORMAT, datefmt=DATEFMT)#, style='{')

    if root:
        logger = logging.getLogger()
    else:
        library, _, _ = __name__.partition('.')
        logger = logging.getLogger(library)

    handler.setFormatter(formatter)
    logger.setLevel(level)
    logger.addHandler(handler)