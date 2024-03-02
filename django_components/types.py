try:
    from typing import Annotated
except ImportError:
    from typing_extensions import Annotated

html = Annotated[str, "html"]
css = Annotated[str, "css"]
django_html = Annotated[str, "django_html"]
js = Annotated[str, "js"]
