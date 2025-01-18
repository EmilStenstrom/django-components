import logging
import sys
from typing import Any, Dict, Literal

DEFAULT_TRACE_LEVEL_NUM = 5  # NOTE: MUST be lower than DEBUG which is 10

logger = logging.getLogger("django_components")
actual_trace_level_num = -1


def setup_logging() -> None:
    # Check if "TRACE" level was already defined. And if so, use its log level.
    # See https://docs.python.org/3/howto/logging.html#custom-levels
    global actual_trace_level_num
    log_levels = _get_log_levels()

    if "TRACE" in log_levels:
        actual_trace_level_num = log_levels["TRACE"]
    else:
        actual_trace_level_num = DEFAULT_TRACE_LEVEL_NUM
        logging.addLevelName(actual_trace_level_num, "TRACE")


def _get_log_levels() -> Dict[str, int]:
    # Use official API if possible
    if sys.version_info >= (3, 11):
        return logging.getLevelNamesMapping()
    else:
        return logging._nameToLevel.copy()


def trace(logger: logging.Logger, message: str, *args: Any, **kwargs: Any) -> None:
    """
    TRACE level logger.

    To display TRACE logs, set the logging level to 5.

    Example:
    ```py
    LOGGING = {
        "version": 1,
        "disable_existing_loggers": False,
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": sys.stdout,
            },
        },
        "loggers": {
            "django_components": {
                "level": 5,
                "handlers": ["console"],
            },
        },
    }
    ```
    """
    if actual_trace_level_num == -1:
        setup_logging()
    if logger.isEnabledFor(actual_trace_level_num):
        logger.log(actual_trace_level_num, message, *args, **kwargs)


def trace_msg(
    action: Literal["PARSE", "RENDR"],
    node_type: str,
    node_id: str,
    msg: str = "",
) -> None:
    """
    TRACE level logger with opinionated format for tracing interaction of components,
    nodes, and slots. Formats messages like so:

    `"PARSE slot ID 0088 ...Done!"`
    """
    full_msg = f"{action} {node_type} ID {node_id} {msg}"

    # NOTE: When debugging tests during development, it may be easier to change
    # this to `print()`
    trace(logger, full_msg)
