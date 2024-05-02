import typing
from typing import Any

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

        def __getitem__(self, params: Any) -> "Annotated":  # type: ignore
            if not isinstance(params, tuple):
                params = (params,)
            return Annotated(self.type_, *params, **self.metadata[1])  # type: ignore

        def __class_getitem__(self, *params: Any) -> "Annotated":  # type: ignore
            return Annotated(*params)  # type: ignore


css = Annotated[str, "css"]
django_html = Annotated[str, "django_html"]
js = Annotated[str, "js"]
