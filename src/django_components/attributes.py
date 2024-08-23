# Initial implementation based on attributes.py from django-web-components
# See https://github.com/Xzya/django-web-components/blob/b43eb0c832837db939a6f8c1980334b0adfdd6e4/django_web_components/templatetags/components.py  # noqa: E501
# And https://github.com/Xzya/django-web-components/blob/b43eb0c832837db939a6f8c1980334b0adfdd6e4/django_web_components/attributes.py  # noqa: E501

from typing import Any, Dict, List, Mapping, Optional, Tuple

from django.template import Context
from django.utils.html import conditional_escape, format_html
from django.utils.safestring import SafeString, mark_safe

from django_components.expression import RuntimeKwargPairs, RuntimeKwargs
from django_components.node import BaseNode

HTML_ATTRS_DEFAULTS_KEY = "defaults"
HTML_ATTRS_ATTRS_KEY = "attrs"


class HtmlAttrsNode(BaseNode):
    def __init__(
        self,
        kwargs: RuntimeKwargs,
        kwarg_pairs: RuntimeKwargPairs,
        node_id: Optional[str] = None,
    ):
        super().__init__(nodelist=None, args=None, kwargs=kwargs, node_id=node_id)
        self.kwarg_pairs = kwarg_pairs

    def render(self, context: Context) -> str:
        append_attrs: List[Tuple[str, Any]] = []

        # Resolve all data
        kwargs = self.kwargs.resolve(context)
        attrs = kwargs.pop(HTML_ATTRS_ATTRS_KEY, None) or {}
        defaults = kwargs.pop(HTML_ATTRS_DEFAULTS_KEY, None) or {}

        kwarg_pairs = self.kwarg_pairs.resolve(context)

        for key, value in kwarg_pairs:
            if (
                key in [HTML_ATTRS_ATTRS_KEY, HTML_ATTRS_DEFAULTS_KEY]
                or key.startswith(f"{HTML_ATTRS_ATTRS_KEY}:")
                or key.startswith(f"{HTML_ATTRS_DEFAULTS_KEY}:")
            ):
                continue

            append_attrs.append((key, value))

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
