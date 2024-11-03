"""Module for interfacing with Django's Library (`django.template.library`)"""

from typing import TYPE_CHECKING, Callable, List, Optional

from django.template.base import Node, Parser, Token
from django.template.library import Library

from django_components.tag_formatter import InternalTagFormatter

if TYPE_CHECKING:
    from django_components.component_registry import ComponentRegistry


class TagProtectedError(Exception):
    """
    The way the [`TagFormatter`](../../concepts/advanced/tag_formatter) works is that,
    based on which start and end tags are used for rendering components,
    the [`ComponentRegistry`](../api#django_components.ComponentRegistry) behind the scenes
    [un-/registers the template tags](https://docs.djangoproject.com/en/5.1/howto/custom-template-tags/#registering-the-tag)
    with the associated instance of Django's
    [`Library`](https://docs.djangoproject.com/en/5.1/howto/custom-template-tags/#code-layout).

    In other words, if I have registered a component `"table"`, and I use the shorthand
    syntax:

    ```django
    {% table ... %}
    {% endtable %}
    ```

    Then [`ComponentRegistry`](../api#django_components.ComponentRegistry)
    registers the tag `table` onto the Django's Library instance.

    However, that means that if we registered a component `"slot"`, then we would overwrite
    the [`{% slot %}`](../template_tags#slot) tag from django_components.

    Thus, this exception is raised when a component is attempted to be registered under
    a forbidden name, such that it would overwrite one of django_component's own template tags.
    """  # noqa: E501

    pass


PROTECTED_TAGS = [
    "component_css_dependencies",
    "component_js_dependencies",
    "fill",
    "html_attrs",
    "provide",
    "slot",
]
"""
These are the names that users cannot choose for their components,
as they would conflict with other tags in the Library.
"""


def register_tag(
    registry: "ComponentRegistry",
    tag: str,
    tag_fn: Callable[[Parser, Token, "ComponentRegistry", str], Node],
) -> None:
    # Register inline tag
    if is_tag_protected(registry.library, tag):
        raise TagProtectedError('Cannot register tag "%s", this tag name is protected' % tag)
    else:
        registry.library.tag(tag, lambda parser, token: tag_fn(parser, token, registry, tag))


def register_tag_from_formatter(
    registry: "ComponentRegistry",
    tag_fn: Callable[[Parser, Token, "ComponentRegistry", str], Node],
    formatter: InternalTagFormatter,
    component_name: str,
) -> str:
    tag = formatter.start_tag(component_name)
    register_tag(registry, tag, tag_fn)
    return tag


def mark_protected_tags(lib: Library, tags: Optional[List[str]] = None) -> None:
    protected_tags = tags if tags is not None else PROTECTED_TAGS
    lib._protected_tags = [*protected_tags]


def is_tag_protected(lib: Library, tag: str) -> bool:
    protected_tags = getattr(lib, "_protected_tags", [])
    return tag in protected_tags
