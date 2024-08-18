# Initial implementation based on attributes.py from django-web-components
# See https://github.com/Xzya/django-web-components/blob/b43eb0c832837db939a6f8c1980334b0adfdd6e4/django_web_components/templatetags/components.py  # noqa: E501
# And https://github.com/Xzya/django-web-components/blob/b43eb0c832837db939a6f8c1980334b0adfdd6e4/django_web_components/attributes.py  # noqa: E501

from typing import Any, Dict, List, Mapping, Optional, Tuple

from django.template import Context, Node
from django.utils.html import conditional_escape, format_html
from django.utils.safestring import SafeString, mark_safe

from django_components.expression import Expression, safe_resolve

HTML_ATTRS_DEFAULTS_KEY = "defaults"
HTML_ATTRS_ATTRS_KEY = "attrs"


class HtmlAttrsNode(Node):
    def __init__(
        self,
        attributes: Optional[Expression],
        defaults: Optional[Expression],
        kwargs: List[Tuple[str, Expression]],
    ):
        self.attributes = attributes
        self.defaults = defaults
        self.kwargs = kwargs

    def render(self, context: Context) -> str:
        append_attrs: List[Tuple[str, Any]] = []

        # Resolve all data
        for key, value in self.kwargs:
            resolved_value = safe_resolve(value, context)
            append_attrs.append((key, resolved_value))

        defaults = safe_resolve(self.defaults, context) if self.defaults else {}
        attrs = safe_resolve(self.attributes, context) if self.attributes else {}

        # Merge it
        final_attrs = {**defaults, **attrs}
        final_attrs = append_attributes(*final_attrs.items(), *append_attrs)

        # Render to HTML attributes
        return attributes_to_string(final_attrs)


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
