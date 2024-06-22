from typing import Any, Callable, List


# Global counter to ensure that all IDs generated by `gen_id` WILL be unique
_id = 0


def gen_id(length: int = 5) -> str:
    """Generate a unique ID that can be associated with a Node"""
    # Global counter to avoid conflicts
    global _id
    _id += 1

    # Pad the ID with `0`s up to 4 digits, e.g. `0007`
    return f"{_id:04}"


def find_last_index(lst: List, predicate: Callable[[Any], bool]) -> Any:
    for r_idx, elem in enumerate(reversed(lst)):
        if predicate(elem):
            return len(lst) - 1 - r_idx
    return -1
