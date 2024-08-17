"""Module for interfacing with Django's Library (`django.template.library`)"""

from typing import Callable, List, Optional

from django.template.base import Node, Parser, Token
from django.template.library import Library

from django_components.tag_formatter import InternalTagFormatter


class TagProtectedError(Exception):
    pass


PROTECTED_TAGS = [
    "component_dependencies",
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
    library: Library,
    tag: str,
    tag_fn: Callable[[Parser, Token, str], Node],
) -> None:
    # Register inline tag
    if is_tag_protected(library, tag):
        raise TagProtectedError('Cannot register tag "%s", this tag name is protected' % tag)
    else:
        library.tag(tag, lambda parser, token: tag_fn(parser, token, tag))


def register_tag_from_formatter(
    library: Library,
    tag_fn: Callable[[Parser, Token, str], Node],
    formatter: InternalTagFormatter,
    component_name: str,
) -> str:
    tag = formatter.start_tag(component_name)
    register_tag(library, tag, tag_fn)
    return tag


def mark_protected_tags(lib: Library, tags: Optional[List[str]] = None) -> None:
    protected_tags = tags if tags is not None else PROTECTED_TAGS
    lib._protected_tags = [*protected_tags]


def is_tag_protected(lib: Library, tag: str) -> bool:
    protected_tags = getattr(lib, "_protected_tags", [])
    return tag in protected_tags
