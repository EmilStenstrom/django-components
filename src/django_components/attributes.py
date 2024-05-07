# Initial implementation based on attributes.py from django-web-components
# See https://github.com/Xzya/django-web-components/blob/b43eb0c832837db939a6f8c1980334b0adfdd6e4/django_web_components/templatetags/components.py
# And https://github.com/Xzya/django-web-components/blob/b43eb0c832837db939a6f8c1980334b0adfdd6e4/django_web_components/attributes.py

import re
from typing import Any, Dict, List, Tuple, Union, Mapping

from django.template import Node, Context, TemplateSyntaxError
from django.template.base import FilterExpression, Parser
from django.utils.html import format_html, conditional_escape
from django.utils.regex_helper import _lazy_re_compile
from django.utils.safestring import mark_safe, SafeString

from django_components.utils import FrozenDict


_AttrItem = Tuple[str, FilterExpression]


# When we have the `{% html_attrs %}` tag, we can specify if we want to SET
# a value, or APPEND (merge) it. SET uses `=` while APPEND uses `+=`. E.g.:
# `{% merge_attrs attributes data-value+="some-value" %}>`
attribute_re: re.Pattern = _lazy_re_compile(
    r"""
    (?P<attr>
        [\w\-\:\@\.\_\#]+
    )
    (?P<sign>
        \+?=
    )
    (?P<value>
        ['"]? # start quote
            [^"']*
        ['"]? # end quote
    )
    """,
    re.VERBOSE | re.UNICODE,
)


class HtmlAttributes(FrozenDict):
    def __str__(self) -> str:
        """Convert the attributes into a single HTML string."""
        return attributes_to_string(self)


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
        append_attrs = {key: value.resolve(context) for key, value in self.append_attrs}

        attrs = merge_attributes(default_attrs, bound_attributes)
        attrs = append_attributes(attrs, append_attrs)

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


def merge_attributes(*args: Dict) -> Dict:
    """
    Merges the input dictionaries and returns a new dictionary.

    Notes:
    ------
    The merge process is performed as follows:
    - "class" values are normalized / concatenated
    - Other values are added to the final dictionary as is
    """
    result: Dict = {}

    for to_merge in args:
        for key, value in to_merge.items():
            if key == "class":
                klass = result.get("class")
                if klass != value:
                    result["class"] = normalize_html_class([klass, value])
            elif key != "":
                result[key] = value

    return result


def append_attributes(*args: Dict) -> Dict:
    """
    Merges the input dictionaries and returns a new dictionary.

    If a key is present in multiple dictionaries, its values are concatenated with a space character
    as separator in the final dictionary.
    """
    result: Dict = {}

    for to_merge in args:
        for key, value in to_merge.items():
            if key in result:
                result[key] += " " + value
            else:
                result[key] = value

    return result


def normalize_html_class(value: Union[str, list, tuple, dict]) -> str:
    """
    Normalizes the given class value into a string.

    Notes:
    ------
    The normalization process is performed as follows:
    - If the input value is a string, it is returned as is.
    - If the input value is a list or a tuple, its elements are recursively normalized and concatenated
      with a space character as separator.
    - If the input value is a dictionary, its keys are concatenated with a space character as separator
      only if their corresponding values are truthy.
    """
    result = ""

    if isinstance(value, str):
        result = value
    elif isinstance(value, (list, tuple)):
        for v in value:
            normalized = normalize_html_class(v)
            if normalized:
                result += normalized + " "
    elif isinstance(value, dict):
        for key, val in value.items():
            if val:
                result += key + " "

    return result.strip()


def parse_attributes(
    tag_name: str,
    parser: Parser,
    attr_list: List[str],
) -> Tuple[List[_AttrItem], List[_AttrItem]]:
    default_attrs: List[_AttrItem] = []
    append_attrs: List[_AttrItem] = []
    for pair in attr_list:
        match = attribute_re.match(pair)
        if not match:
            raise TemplateSyntaxError(
                "Malformed arguments to '%s' tag. You must pass the attributes in the form attr=\"value\"." % tag_name
            )
        dct = match.groupdict()
        attr, sign, value = (
            dct["attr"],
            dct["sign"],
            parser.compile_filter(dct["value"]),
        )
        if sign == "=":
            default_attrs.append((attr, value))
        elif sign == "+=":
            append_attrs.append((attr, value))
        else:
            raise TemplateSyntaxError("Unknown sign '%s' for attribute '%s'" % (sign, attr))
    return default_attrs, append_attrs
