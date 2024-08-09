"""Module for interfacing with Django's Library (`django.template.library`)"""

from typing import Callable, List, NamedTuple, Optional

from django.template.base import Node, Parser, Token
from django.template.library import Library

from django_components.tag_formatter import InternalTagFormatter


class TagProtectedError(Exception):
    pass


class Tags(NamedTuple):
    inline_tag: str
    block_tag: str


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


def register_tags(
    library: Library,
    tag_fn: Callable[[Parser, Token, str], Node],
    tags: Tags,
) -> None:
    inline_tag, block_tag = tags.inline_tag, tags.block_tag

    # Register inline tag
    if is_tag_protected(library, inline_tag):
        raise TagProtectedError('Cannot register inline tag "%s", this tag name is protected' % inline_tag)
    else:
        library.tag(inline_tag, lambda parser, token: tag_fn(parser, token, inline_tag))

    if block_tag == inline_tag:
        return

    # Register block tag
    if is_tag_protected(library, block_tag):
        raise TagProtectedError('Cannot register block tag "%s", this tag name is protected' % block_tag)
    else:
        library.tag(block_tag, lambda parser, token: tag_fn(parser, token, block_tag))


def register_tags_from_formatter(
    library: Library,
    tag_fn: Callable[[Parser, Token, str], Node],
    formatter: InternalTagFormatter,
    component_name: str,
) -> Tags:
    inline_tag = formatter.start_inline_tag(component_name)
    block_tag = formatter.start_block_tag(component_name)
    tags = Tags(inline_tag=inline_tag, block_tag=block_tag)
    register_tags(library, tag_fn, tags)
    return tags


def mark_protected_tags(lib: Library, tags: Optional[List[str]] = None) -> None:
    protected_tags = tags if tags is not None else PROTECTED_TAGS
    lib._protected_tags = [*protected_tags]


def is_tag_protected(lib: Library, tag: str) -> bool:
    protected_tags = getattr(lib, "_protected_tags", [])
    return tag in protected_tags
