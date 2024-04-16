import logging
from typing import Literal, Optional

logger = logging.getLogger("django_components")


def trace_msg(
    action: Literal["PARSE", "ASSOC", "RENDR", "GET", "SET"],
    node_type: Literal["COMP", "FILL", "SLOT", "IFSB", "N/A"],
    node_name: str,
    node_id: str,
    msg: str = "",
    component_id: Optional[str] = None,
) -> None:
    """
    Log a tracing statement to `logger.debug` like so:

    `"ASSOC SLOT test_slot ID 0088 TO COMP 0087"`
    """
    msg_prefix = ""
    if action == "ASSOC":
        if not component_id:
            raise ValueError("component_id must be set for the ASSOC action")
        msg_prefix = f"TO COMP {component_id}"
    elif action == "RENDR" and node_type != "COMP":
        if not component_id:
            raise ValueError("component_id must be set for the RENDER action")
        msg_prefix = f"FOR COMP {component_id}"

    msg_parts = [f"{action} {node_type} {node_name} ID {node_id}", *([msg_prefix] if msg_prefix else []), msg]
    full_msg = " ".join(msg_parts)

    # NOTE: When debugging tests during development, it may be easier to change
    # this to `print()`
    logger.debug(full_msg)
