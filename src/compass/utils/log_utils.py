import sys
import loguru

LOGURU_FORMAT = " ".join(
    [
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green>",
        "<level>{level: <8}</level>",
        "<cyan>{name: <18}</cyan>",
        "<level>{message}</level>",
    ]
)
LOGURU_FORMAT_SIMPLE = "{time:YYYY-MM-DD_HH:mm:ss} | {level: <8} | {name: <16} | {message}"


def get_logger(name: str = "", level: str = "INFO"):  # , verbose: bool = None):
    """Return a loguru logger with a specified name and verbosity level

    Args:
        name (str, optional): Name of the logger. Defaults to None.
        level (str, optional): Logging level. Defaults to "INFO".
    """
    logger = loguru.logger
    logger.remove()
    logger.add(
        sink=sys.stderr,
        level=level,
        format=LOGURU_FORMAT,
        colorize=True,
    )
    if name:
        fp = f"logs/{name}"
        logger.add(
            sink=fp + "_{time:YYYYMMDD_HHmmss}.log",
            level="DEBUG",
            format=LOGURU_FORMAT_SIMPLE,
        )
    return logger
