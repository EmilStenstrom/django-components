# Initial implementation based on attributes.py from django-web-components
# See https://github.com/Xzya/django-web-components/blob/b43eb0c832837db939a6f8c1980334b0adfdd6e4/django_web_components/templatetags/components.py  # noqa: E501
# And https://github.com/Xzya/django-web-components/blob/b43eb0c832837db939a6f8c1980334b0adfdd6e4/django_web_components/attributes.py  # noqa: E501

from typing import Any, Dict, Mapping, Optional, Tuple

from django.template import Context
from django.utils.html import conditional_escape, format_html
from django.utils.safestring import SafeString, mark_safe

from django_components.node import BaseNode


class HtmlAttrsNode(BaseNode):
    """
    Generate HTML attributes (`key="value"`), combining data from multiple sources,
    whether its template variables or static text.

    It is designed to easily merge HTML attributes passed from outside with the internal.
    See how to in [Passing HTML attributes to components](../../guides/howto/passing_html_attrs/).

    **Args:**

    - `attrs` (dict, optional): Optional dictionary that holds HTML attributes. On conflict, overrides
        values in the `default` dictionary.
    - `default` (str, optional): Optional dictionary that holds HTML attributes. On conflict, is overriden
        with values in the `attrs` dictionary.
    - Any extra kwargs will be appended to the corresponding keys

    The attributes in `attrs` and `defaults` are merged and resulting dict is rendered as HTML attributes
    (`key="value"`).

    Extra kwargs (`key=value`) are concatenated to existing keys. So if we have

    ```python
    attrs = {"class": "my-class"}
    ```

    Then

    ```django
    {% html_attrs attrs class="extra-class" %}
    ```

    will result in `class="my-class extra-class"`.

    **Example:**
    ```django
    <div {% html_attrs
        attrs
        defaults:class="default-class"
        class="extra-class"
        data-id="123"
    %}>
    ```

    renders

    ```html
    <div class="my-class extra-class" data-id="123">
    ```

    **See more usage examples in
    [HTML attributes](../../concepts/fundamentals/html_attributes#examples-for-html_attrs).**
    """

    tag = "html_attrs"
    end_tag = None  # inline-only
    allowed_flags = []

    def render(
        self,
        context: Context,
        attrs: Optional[Dict] = None,
        defaults: Optional[Dict] = None,
        **kwargs: Any,
    ) -> SafeString:
        # Merge
        final_attrs = {}
        final_attrs.update(defaults or {})
        final_attrs.update(attrs or {})
        final_attrs = append_attributes(*final_attrs.items(), *kwargs.items())

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
