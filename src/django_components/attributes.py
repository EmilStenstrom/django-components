# Initial implementation based on attributes.py from django-web-components
# See https://github.com/Xzya/django-web-components/blob/b43eb0c832837db939a6f8c1980334b0adfdd6e4/django_web_components/templatetags/components.py  # noqa: E501
# And https://github.com/Xzya/django-web-components/blob/b43eb0c832837db939a6f8c1980334b0adfdd6e4/django_web_components/attributes.py  # noqa: E501

from typing import Any, Dict, List, Mapping, Optional, Tuple

from django.template import Context, Node
from django.template.base import FilterExpression
from django.utils.html import conditional_escape, format_html
from django.utils.safestring import SafeString, mark_safe

from django_components.template_parser import process_aggregate_kwargs

HTML_ATTRS_DEFAULTS_KEY = "defaults"
HTML_ATTRS_ATTRS_KEY = "attrs"


def _default(val: Any, default_val: Any) -> Any:
    return val if val is not None else default_val


class HtmlAttrsNode(Node):
    def __init__(
        self,
        attributes: Optional[FilterExpression],
        default_attrs: Optional[FilterExpression],
        kwargs: List[Tuple[str, FilterExpression]],
    ):
        self.attributes = attributes
        self.default_attrs = default_attrs
        self.kwargs = kwargs

    def render(self, context: Context) -> str:
        append_attrs: List[Tuple[str, Any]] = []
        attrs_and_defaults_from_kwargs = {}

        # Resolve kwargs, while also extracting attrs and defaults keys
        for key, value in self.kwargs:
            resolved_value = value.resolve(context)
            if key.startswith(f"{HTML_ATTRS_ATTRS_KEY}:") or key.startswith(f"{HTML_ATTRS_DEFAULTS_KEY}:"):
                attrs_and_defaults_from_kwargs[key] = resolved_value
                continue
            # NOTE: These were already extracted into separate variables, so
            # ignore them here.
            elif key == HTML_ATTRS_ATTRS_KEY or key == HTML_ATTRS_DEFAULTS_KEY:
                continue

            append_attrs.append((key, resolved_value))

        # NOTE: Here we delegate validation to `process_aggregate_kwargs`, which should
        # raise error if the dict includes both `attrs` and `attrs:` keys.
        #
        # So by assigning the `attrs` and `defaults` keys, users are forced to use only
        # one approach or the other, but not both simultaneously.
        if self.attributes:
            attrs_and_defaults_from_kwargs[HTML_ATTRS_ATTRS_KEY] = self.attributes.resolve(context)
        if self.default_attrs:
            attrs_and_defaults_from_kwargs[HTML_ATTRS_DEFAULTS_KEY] = self.default_attrs.resolve(context)

        # Turn `{"attrs:blabla": 1}` into `{"attrs": {"blabla": 1}}`
        attrs_and_defaults_from_kwargs = process_aggregate_kwargs(attrs_and_defaults_from_kwargs)

        # NOTE: We want to allow to use `html_attrs` even without `attrs` or `defaults` params
        # Or when they are None
        attrs = _default(attrs_and_defaults_from_kwargs.get(HTML_ATTRS_ATTRS_KEY, None), {})
        default_attrs = _default(attrs_and_defaults_from_kwargs.get(HTML_ATTRS_DEFAULTS_KEY, None), {})

        final_attrs = {**default_attrs, **attrs}
        final_attrs = append_attributes(*final_attrs.items(), *append_attrs)

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
