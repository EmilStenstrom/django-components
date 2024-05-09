# Initial implementation based on attributes.py from django-web-components
# See https://github.com/Xzya/django-web-components/blob/b43eb0c832837db939a6f8c1980334b0adfdd6e4/django_web_components/templatetags/components.py
# And https://github.com/Xzya/django-web-components/blob/b43eb0c832837db939a6f8c1980334b0adfdd6e4/django_web_components/attributes.py

import re
from typing import Any, Dict, List, Mapping, Tuple

from django.template import Context, Node, TemplateSyntaxError
from django.template.base import FilterExpression, Parser
from django.utils.html import conditional_escape, format_html
from django.utils.regex_helper import _lazy_re_compile
from django.utils.safestring import SafeString, mark_safe

_AttrItem = Tuple[str, FilterExpression]


_ATTR_ADD_PREFIX = "add::"


# When we have the `{% html_attrs %}` tag, we can specify if we want to SET
# a value, or APPEND (merge) it. SET uses plain `key=val` while APPEND uses
# `add:key=val`. E.g.:
# `{% html_attrs attributes data-id="123" add:class="some-class" %}>`
attribute_re: re.Pattern = _lazy_re_compile(
    r"""
    (?P<attr>
        [\w\-\:\@\.\_\#]+
    )
    =
    (?P<value>
        ['"]? # start quote
            [^"']*
        ['"]? # end quote
    )
    """,
    re.VERBOSE | re.UNICODE,
)


class HtmlAttrsNode(Node):
    def __init__(
        self,
        attributes: FilterExpression,
        default_attrs: List[_AttrItem],
        append_attrs: List[_AttrItem],
    ):
        self.attributes = attributes
        self.default_attrs = default_attrs
        self.append_attrs = append_attrs

    def render(self, context: Context) -> str:
        bound_attributes: dict = self.attributes.resolve(context)

        default_attrs = {key: value.resolve(context) for key, value in self.default_attrs}
        append_attrs = [(key, value.resolve(context)) for key, value in self.append_attrs]

        attrs = {**default_attrs, **bound_attributes}
        attrs = append_attributes(*attrs.items(), *append_attrs)

        return attributes_to_string(attrs)


def attributes_to_string(attributes: Mapping[str, Any]) -> str:
    """Convert a dict of attributes to a string."""
    attr_list = []

    for key, value in attributes.items():
        if value is None or value is False:
            continue
        if value is True:
            attr_list.append(conditional_escape(key))
        else:
            attr_list.append(format_html('{}="{}"', key, value))

    return mark_safe(SafeString(" ").join(attr_list))


def append_attributes(*args: Tuple[str, Any]) -> Dict:
    """
    Merges the key-value pairs and returns a new dictionary.

    If a key is present multiple times, its values are concatenated with a space
    character as separator in the final dictionary.
    """
    result: Dict = {}

    for key, value in args:
        if key in result:
            result[key] += " " + value
        else:
            result[key] = value

    return result


def parse_attributes(
    tag_name: str,
    parser: Parser,
    attr_list: List[str],
) -> Tuple[List[_AttrItem], List[_AttrItem]]:
    """Process dict and extra kwargs passed to `html_attr` tag."""
    default_attrs: List[_AttrItem] = []
    append_attrs: List[_AttrItem] = []
    for pair in attr_list:
        match = attribute_re.match(pair)
        if not match:
            raise TemplateSyntaxError(
                "Malformed arguments to '%s' tag. You must pass the attributes in the form attr=\"value\"." % tag_name
            )
        dct = match.groupdict()
        raw_attr, value = (
            dct["attr"],
            parser.compile_filter(dct["value"]),
        )

        # For those kwargs where keyword starts with 'add::', we assume that these
        # keys should be concatenated. For the rest, we don't do any special processing.
        if raw_attr.startswith(_ATTR_ADD_PREFIX):
            attr = raw_attr[len(_ATTR_ADD_PREFIX) :]
            append_attrs.append((attr, value))
        else:
            default_attrs.append((raw_attr, value))

    return default_attrs, append_attrs
