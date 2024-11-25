"""Helper types for IDEs."""

from django_components.util.types import Annotated

css = Annotated[str, "css"]
django_html = Annotated[str, "django_html"]
js = Annotated[str, "js"]
