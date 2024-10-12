import sys
import typing
from typing import Any, Tuple

# See https://peps.python.org/pep-0655/#usage-in-python-3-11
if sys.version_info >= (3, 11):
    from typing import TypedDict
else:
    from typing_extensions import TypedDict as TypedDict  # for Python <3.11 with (Not)Required

try:
    from typing import Annotated  # type: ignore
except ImportError:

    @typing.no_type_check
    class Annotated:  # type: ignore
        def __init__(self, type_: str, *args: Any, **kwargs: Any):
            self.type_ = type_
            self.metadata = args, kwargs

        def __repr__(self) -> str:
            return f"Annotated[{self.type_}, {self.metadata[0]!r}, {self.metadata[1]!r}]"

        def __getitem__(self, params: Any) -> "Annotated[Any, Any, Any]":  # type: ignore
            if not isinstance(params, tuple):
                params = (params,)
            return Annotated(self.type_, *params, **self.metadata[1])  # type: ignore

        def __class_getitem__(self, *params: Any) -> "Annotated[Any, Any, Any]":  # type: ignore
            return Annotated(*params)  # type: ignore


EmptyTuple = Tuple[()]


class EmptyDict(TypedDict):
    pass
