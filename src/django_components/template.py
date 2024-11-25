from functools import lru_cache
from typing import Any, Optional, Type, TypeVar

from django.template import Origin, Template
from django.template.base import UNKNOWN_SOURCE

from django_components.app_settings import app_settings
from django_components.util.cache import lazy_cache

TTemplate = TypeVar("TTemplate", bound=Template)


# Lazily initialize the cache. The cached function takes only the parts that can
# affect how the template string is processed - Template class, template string, and engine
@lazy_cache(lambda: lru_cache(maxsize=app_settings.TEMPLATE_CACHE_SIZE))
def _create_template(
    template_cls: Type[TTemplate],
    template_string: str,
    engine: Optional[Any] = None,
) -> TTemplate:
    return template_cls(template_string, engine=engine)


# Central logic for creating Templates from string, so we can cache the results
def cached_template(
    template_string: str,
    template_cls: Optional[Type[Template]] = None,
    origin: Optional[Origin] = None,
    name: Optional[str] = None,
    engine: Optional[Any] = None,
) -> Template:
    """
    Create a Template instance that will be cached as per the
    [`COMPONENTS.template_cache_size`](../settings#django_components.app_settings.ComponentsSettings.template_cache_size)
    setting.

    Args:
        template_string (str): Template as a string, same as the first argument to Django's\
            [`Template`](https://docs.djangoproject.com/en/5.1/topics/templates/#template). Required.
        template_cls (Type[Template], optional): Specify the Template class that should be instantiated.\
            Defaults to Django's [`Template`](https://docs.djangoproject.com/en/5.1/topics/templates/#template) class.
        origin (Type[Origin], optional): Sets \
            [`Template.Origin`](https://docs.djangoproject.com/en/5.1/howto/custom-template-backend/#origin-api-and-3rd-party-integration).
        name (Type[str], optional): Sets `Template.name`
        engine (Type[Any], optional): Sets `Template.engine`

    ```python
    from django_components import cached_template

    template = cached_template("Variable: {{ variable }}")

    # You can optionally specify Template class, and other Template inputs:
    class MyTemplate(Template):
        pass

    template = cached_template(
        "Variable: {{ variable }}",
        template_cls=MyTemplate,
        name=...
        origin=...
        engine=...
    )
    ```
    """  # noqa: E501
    template = _create_template(template_cls or Template, template_string, engine)

    # Assign the origin and name separately, so the caching doesn't depend on them
    # Since we might be accessing a template from cache, we want to define these only once
    if not getattr(template, "_dc_cached", False):
        template.origin = origin or Origin(UNKNOWN_SOURCE)
        template.name = name
        template._dc_cached = True

    return template
