import logging
import sys
from typing import Any, Dict, Literal, Optional

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
    action: Literal["PARSE", "ASSOC", "RENDR", "GET", "SET"],
    node_type: Literal["COMP", "FILL", "SLOT", "PROVIDE", "N/A"],
    node_name: str,
    node_id: str,
    msg: str = "",
    component_id: Optional[str] = None,
) -> None:
    """
    TRACE level logger with opinionated format for tracing interaction of components,
    nodes, and slots. Formats messages like so:

    `"ASSOC SLOT test_slot ID 0088 TO COMP 0087"`
    """
    msg_prefix = ""
    if action == "ASSOC":
        if not component_id:
            raise ValueError("component_id must be set for the ASSOC action")
        msg_prefix = f"TO COMP {component_id}"
    elif action == "RENDR" and node_type == "FILL":
        if not component_id:
            raise ValueError("component_id must be set for the RENDER action")
        msg_prefix = f"FOR COMP {component_id}"

    msg_parts = [f"{action} {node_type} {node_name} ID {node_id}", *([msg_prefix] if msg_prefix else []), msg]
    full_msg = " ".join(msg_parts)

    # NOTE: When debugging tests during development, it may be easier to change
    # this to `print()`
    trace(logger, full_msg)
