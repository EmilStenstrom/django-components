try:
    from typing import Annotated  # type: ignore
except ImportError:

    class Annotated:  # type: ignore
        def __init__(self, type_, *args, **kwargs):
            self.type_ = type_
            self.metadata = args, kwargs

        def __repr__(self):
            return f"Annotated[{self.type_}, {self.metadata[0]!r}, {self.metadata[1]!r}]"

        def __getitem__(self, params):
            if not isinstance(params, tuple):
                params = (params,)
            return Annotated(self.type_, *params, **self.metadata[1])  # type: ignore


css = Annotated[str, "css"]
django_html = Annotated[str, "django_html"]
js = Annotated[str, "js"]
