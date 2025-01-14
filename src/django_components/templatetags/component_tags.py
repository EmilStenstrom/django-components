# Notes on documentation:
# - For intuitive use via Python imports, keep the tag names same as the function name.
#   E.g. so if the tag name is `slot`, one can also do
#   `from django_components.templatetags.component_tags import slot`
#
# - All tags are defined using `@register.tag`. Do NOT use `@register.simple_tag`.
#   The reason for this is so that we use `TagSpec` and `parse_template_tag`. When generating
#   documentation, we extract the `TagSpecs` to be able to describe each tag's function signature.
#
# - Use `with_tag_spec` for defining `TagSpecs`. This will make it available to the function
#   as the last argument, and will also set the `TagSpec` instance to `fn._tag_spec`.
#   During documentation generation, we access the `fn._tag_spec`.

import inspect
from typing import Any, Dict, Literal, Optional

import django.template
from django.template.base import Parser, TextNode, Token
from django.template.exceptions import TemplateSyntaxError
from django.utils.safestring import SafeString, mark_safe

from django_components.attributes import HtmlAttrsNode
from django_components.component import COMP_ONLY_FLAG, ComponentNode
from django_components.component_registry import ComponentRegistry
from django_components.dependencies import CSS_DEPENDENCY_PLACEHOLDER, JS_DEPENDENCY_PLACEHOLDER
from django_components.provide import ProvideNode
from django_components.slots import SLOT_DEFAULT_KEYWORD, SLOT_REQUIRED_KEYWORD, FillNode, SlotNode
from django_components.tag_formatter import get_tag_formatter
from django_components.util.logger import trace_msg
from django_components.util.misc import gen_id
from django_components.util.template_tag import TagSpec, fix_nested_tags, parse_template_tag, with_tag_spec

# NOTE: Variable name `register` is required by Django to recognize this as a template tag library
# See https://docs.djangoproject.com/en/dev/howto/custom-template-tags
register = django.template.Library()


def _component_dependencies(type: Literal["js", "css"]) -> SafeString:
    """Marks location where CSS link and JS script tags should be rendered."""
    if type == "css":
        placeholder = CSS_DEPENDENCY_PLACEHOLDER
    elif type == "js":
        placeholder = JS_DEPENDENCY_PLACEHOLDER
    else:
        raise TemplateSyntaxError(
            f"Unknown dependency type in {{% component_dependencies %}}. Must be one of 'css' or 'js', got {type}"
        )

    return TextNode(mark_safe(placeholder))


def component_dependencies_signature() -> None: ...  # noqa: E704


@register.tag("component_css_dependencies")
@with_tag_spec(
    TagSpec(
        tag="component_css_dependencies",
        end_tag=None,  # inline-only
        signature=inspect.Signature.from_callable(component_dependencies_signature),
    )
)
def component_css_dependencies(parser: Parser, token: Token, tag_spec: TagSpec) -> TextNode:
    """
    Marks location where CSS link tags should be rendered after the whole HTML has been generated.

    Generally, this should be inserted into the `<head>` tag of the HTML.

    If the generated HTML does NOT contain any `{% component_css_dependencies %}` tags, CSS links
    are by default inserted into the `<head>` tag of the HTML. (See
    [JS and CSS output locations](../../concepts/advanced/rendering_js_css/#js-and-css-output-locations))

    Note that there should be only one `{% component_css_dependencies %}` for the whole HTML document.
    If you insert this tag multiple times, ALL CSS links will be duplicately inserted into ALL these places.
    """
    # Parse to check that the syntax is valid
    parse_template_tag(parser, token, tag_spec)
    return _component_dependencies("css")


@register.tag("component_js_dependencies")
@with_tag_spec(
    TagSpec(
        tag="component_js_dependencies",
        end_tag=None,  # inline-only
        signature=inspect.Signature.from_callable(component_dependencies_signature),
    )
)
def component_js_dependencies(parser: Parser, token: Token, tag_spec: TagSpec) -> TextNode:
    """
    Marks location where JS link tags should be rendered after the whole HTML has been generated.

    Generally, this should be inserted at the end of the `<body>` tag of the HTML.

    If the generated HTML does NOT contain any `{% component_js_dependencies %}` tags, JS scripts
    are by default inserted at the end of the `<body>` tag of the HTML. (See
    [JS and CSS output locations](../../concepts/advanced/rendering_js_css/#js-and-css-output-locations))

    Note that there should be only one `{% component_js_dependencies %}` for the whole HTML document.
    If you insert this tag multiple times, ALL JS scripts will be duplicately inserted into ALL these places.
    """
    # Parse to check that the syntax is valid
    parse_template_tag(parser, token, tag_spec)
    return _component_dependencies("js")


def slot_signature(name: str, **kwargs: Any) -> None: ...  # noqa: E704


@register.tag("slot")
@with_tag_spec(
    TagSpec(
        tag="slot",
        end_tag="endslot",
        signature=inspect.Signature.from_callable(slot_signature),
        flags=[SLOT_DEFAULT_KEYWORD, SLOT_REQUIRED_KEYWORD],
    )
)
def slot(parser: Parser, token: Token, tag_spec: TagSpec) -> SlotNode:
    """
    Slot tag marks a place inside a component where content can be inserted
    from outside.

    [Learn more](../../concepts/fundamentals/slots) about using slots.

    This is similar to slots as seen in
    [Web components](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/slot),
    [Vue](https://vuejs.org/guide/components/slots.html)
    or [React's `children`](https://react.dev/learn/passing-props-to-a-component#passing-jsx-as-children).

    **Args:**

    - `name` (str, required): Registered name of the component to render
    - `default`: Optional flag. If there is a default slot, you can pass the component slot content
        without using the [`{% fill %}`](#fill) tag. See
        [Default slot](../../concepts/fundamentals/slots#default-slot)
    - `required`: Optional flag. Will raise an error if a slot is required but not given.
    - `**kwargs`: Any extra kwargs will be passed as the slot data.

    **Example:**

    ```python
    @register("child")
    class Child(Component):
        template = \"\"\"
          <div>
            {% slot "content" default %}
              This is shown if not overriden!
            {% endslot %}
          </div>
          <aside>
            {% slot "sidebar" required / %}
          </aside>
        \"\"\"
    ```

    ```python
    @register("parent")
    class Parent(Component):
        template = \"\"\"
          <div>
            {% component "child" %}
              {% fill "content" %}
                🗞️📰
              {% endfill %}

              {% fill "sidebar" %}
                🍷🧉🍾
              {% endfill %}
            {% endcomponent %}
          </div>
        \"\"\"
    ```

    ### Passing data to slots

    Any extra kwargs will be considered as slot data, and will be accessible in the [`{% fill %}`](#fill)
    tag via fill's `data` kwarg:

    ```python
    @register("child")
    class Child(Component):
        template = \"\"\"
          <div>
            {# Passing data to the slot #}
            {% slot "content" user=user %}
              This is shown if not overriden!
            {% endslot %}
          </div>
        \"\"\"
    ```

    ```python
    @register("parent")
    class Parent(Component):
        template = \"\"\"
          {# Parent can access the slot data #}
          {% component "child" %}
            {% fill "content" data="data" %}
              <div class="wrapper-class">
                {{ data.user }}
              </div>
            {% endfill %}
          {% endcomponent %}
        \"\"\"
    ```

    ### Accessing default slot content

    The content between the `{% slot %}..{% endslot %}` tags is the default content that
    will be rendered if no fill is given for the slot.

    This default content can then be accessed from within the [`{% fill %}`](#fill) tag using
    the fill's `default` kwarg.
    This is useful if you need to wrap / prepend / append the original slot's content.

    ```python
    @register("child")
    class Child(Component):
        template = \"\"\"
          <div>
            {% slot "content" %}
              This is default content!
            {% endslot %}
          </div>
        \"\"\"
    ```

    ```python
    @register("parent")
    class Parent(Component):
        template = \"\"\"
          {# Parent can access the slot's default content #}
          {% component "child" %}
            {% fill "content" default="default" %}
              {{ default }}
            {% endfill %}
          {% endcomponent %}
        \"\"\"
    ```
    """
    tag_id = gen_id()
    tag = parse_template_tag(parser, token, tag_spec)

    trace_id = f"slot-id-{tag_id}"
    trace_msg("PARSE", "SLOT", trace_id, tag_id)

    body = tag.parse_body()
    slot_node = SlotNode(
        nodelist=body,
        node_id=tag_id,
        params=tag.params,
        is_required=tag.flags[SLOT_REQUIRED_KEYWORD],
        is_default=tag.flags[SLOT_DEFAULT_KEYWORD],
        trace_id=trace_id,
    )

    trace_msg("PARSE", "SLOT", trace_id, tag_id, "...Done!")
    return slot_node


def fill_signature(name: str, *, data: Optional[str] = None, default: Optional[str] = None) -> None: ...  # noqa: E704


@register.tag("fill")
@with_tag_spec(
    TagSpec(
        tag="fill",
        end_tag="endfill",
        signature=inspect.Signature.from_callable(fill_signature),
    )
)
def fill(parser: Parser, token: Token, tag_spec: TagSpec) -> FillNode:
    """
    Use this tag to insert content into component's slots.

    `{% fill %}` tag may be used only within a `{% component %}..{% endcomponent %}` block.
    Runtime checks should prohibit other usages.

    **Args:**

    - `name` (str, required): Name of the slot to insert this content into. Use `"default"` for
        the default slot.
    - `default` (str, optional): This argument allows you to access the original content of the slot
        under the specified variable name. See
        [Accessing original content of slots](../../concepts/fundamentals/slots#accessing-original-content-of-slots)
    - `data` (str, optional): This argument allows you to access the data passed to the slot
        under the specified variable name. See [Scoped slots](../../concepts/fundamentals/slots#scoped-slots)

    **Examples:**

    Basic usage:
    ```django
    {% component "my_table" %}
      {% fill "pagination" %}
        < 1 | 2 | 3 >
      {% endfill %}
    {% endcomponent %}
    ```

    ### Accessing slot's default content with the `default` kwarg

    ```django
    {# my_table.html #}
    <table>
      ...
      {% slot "pagination" %}
        < 1 | 2 | 3 >
      {% endslot %}
    </table>
    ```

    ```django
    {% component "my_table" %}
      {% fill "pagination" default="default_pag" %}
        <div class="my-class">
          {{ default_pag }}
        </div>
      {% endfill %}
    {% endcomponent %}
    ```

    ### Accessing slot's data with the `data` kwarg

    ```django
    {# my_table.html #}
    <table>
      ...
      {% slot "pagination" pages=pages %}
        < 1 | 2 | 3 >
      {% endslot %}
    </table>
    ```

    ```django
    {% component "my_table" %}
      {% fill "pagination" data="slot_data" %}
        {% for page in slot_data.pages %}
            <a href="{{ page.link }}">
              {{ page.index }}
            </a>
        {% endfor %}
      {% endfill %}
    {% endcomponent %}
    ```

    ### Accessing slot data and default content on the default slot

    To access slot data and the default slot content on the default slot,
    use `{% fill %}` with `name` set to `"default"`:

    ```django
    {% component "button" %}
      {% fill name="default" data="slot_data" default="default_slot" %}
        You clicked me {{ slot_data.count }} times!
        {{ default_slot }}
      {% endfill %}
    {% endcomponent %}
    ```
    """
    tag_id = gen_id()
    tag = parse_template_tag(parser, token, tag_spec)

    trace_id = f"fill-id-{tag_id}"
    trace_msg("PARSE", "FILL", trace_id, tag_id)

    body = tag.parse_body()
    fill_node = FillNode(
        nodelist=body,
        node_id=tag_id,
        params=tag.params,
        trace_id=trace_id,
    )

    trace_msg("PARSE", "FILL", trace_id, tag_id, "...Done!")
    return fill_node


def component_signature(*args: Any, **kwargs: Any) -> None: ...  # noqa: E704


@with_tag_spec(
    TagSpec(
        tag="component",
        end_tag="endcomponent",
        signature=inspect.Signature.from_callable(component_signature),
        flags=[COMP_ONLY_FLAG],
    )
)
def component(
    parser: Parser,
    token: Token,
    registry: ComponentRegistry,
    tag_name: str,
    tag_spec: TagSpec,
) -> ComponentNode:
    """
    Renders one of the components that was previously registered with
    [`@register()`](./api.md#django_components.register)
    decorator.

    **Args:**

    - `name` (str, required): Registered name of the component to render
    - All other args and kwargs are defined based on the component itself.

    If you defined a component `"my_table"`

    ```python
    from django_component import Component, register

    @register("my_table")
    class MyTable(Component):
        template = \"\"\"
          <table>
            <thead>
              {% for header in headers %}
                <th>{{ header }}</th>
              {% endfor %}
            </thead>
            <tbody>
              {% for row in rows %}
                <tr>
                  {% for cell in row %}
                    <td>{{ cell }}</td>
                  {% endfor %}
                </tr>
              {% endfor %}
            <tbody>
          </table>
        \"\"\"

        def get_context_data(self, rows: List, headers: List):
            return {
                "rows": rows,
                "headers": headers,
            }
    ```

    Then you can render this component by referring to `MyTable` via its
    registered name `"my_table"`:

    ```django
    {% component "my_table" rows=rows headers=headers ... / %}
    ```

    ### Component input

    Positional and keyword arguments can be literals or template variables.

    The component name must be a single- or double-quotes string and must
    be either:

    - The first positional argument after `component`:

        ```django
        {% component "my_table" rows=rows headers=headers ... / %}
        ```

    - Passed as kwarg `name`:

        ```django
        {% component rows=rows headers=headers name="my_table" ... / %}
        ```

    ### Inserting into slots

    If the component defined any [slots](../concepts/fundamentals/slots.md), you can
    pass in the content to be placed inside those slots by inserting [`{% fill %}`](#fill) tags,
    directly within the `{% component %}` tag:

    ```django
    {% component "my_table" rows=rows headers=headers ... / %}
      {% fill "pagination" %}
        < 1 | 2 | 3 >
      {% endfill %}
    {% endcomponent %}
    ```

    ### Isolating components

    By default, components behave similarly to Django's
    [`{% include %}`](https://docs.djangoproject.com/en/5.1/ref/templates/builtins/#include),
    and the template inside the component has access to the variables defined in the outer template.

    You can selectively isolate a component, using the `only` flag, so that the inner template
    can access only the data that was explicitly passed to it:

    ```django
    {% component "name" positional_arg keyword_arg=value ... only %}
    ```
    """
    tag_id = gen_id()

    fix_nested_tags(parser, token)
    bits = token.split_contents()

    # Let the TagFormatter pre-process the tokens
    formatter = get_tag_formatter(registry)
    result = formatter.parse([*bits])
    end_tag = formatter.end_tag(result.component_name)

    # NOTE: The tokens returned from TagFormatter.parse do NOT include the tag itself,
    # so we add it back in.
    bits = [bits[0], *result.tokens]
    token.contents = " ".join(bits)

    # Set the component-specific start and end tags
    component_tag_spec = tag_spec.copy()
    component_tag_spec.tag = tag_name
    component_tag_spec.end_tag = end_tag

    tag = parse_template_tag(parser, token, component_tag_spec)

    trace_msg("PARSE", "COMP", result.component_name, tag_id)

    body = tag.parse_body()

    component_node = ComponentNode(
        name=result.component_name,
        params=tag.params,
        isolated_context=tag.flags[COMP_ONLY_FLAG],
        nodelist=body,
        node_id=tag_id,
        registry=registry,
    )

    trace_msg("PARSE", "COMP", result.component_name, tag_id, "...Done!")
    return component_node


def provide_signature(name: str, **kwargs: Any) -> None: ...  # noqa: E704


@register.tag("provide")
@with_tag_spec(
    TagSpec(
        tag="provide",
        end_tag="endprovide",
        signature=inspect.Signature.from_callable(provide_signature),
        flags=[],
    )
)
def provide(parser: Parser, token: Token, tag_spec: TagSpec) -> ProvideNode:
    """
    The "provider" part of the [provide / inject feature](../../concepts/advanced/provide_inject).
    Pass kwargs to this tag to define the provider's data.
    Any components defined within the `{% provide %}..{% endprovide %}` tags will be able to access this data
    with [`Component.inject()`](../api#django_components.Component.inject).

    This is similar to React's [`ContextProvider`](https://react.dev/learn/passing-data-deeply-with-context),
    or Vue's [`provide()`](https://vuejs.org/guide/components/provide-inject).

    **Args:**

    - `name` (str, required): Provider name. This is the name you will then use in
        [`Component.inject()`](../api#django_components.Component.inject).
    - `**kwargs`: Any extra kwargs will be passed as the provided data.

    **Example:**

    Provide the "user_data" in parent component:

    ```python
    @register("parent")
    class Parent(Component):
        template = \"\"\"
          <div>
            {% provide "user_data" user=user %}
              {% component "child" / %}
            {% endprovide %}
          </div>
        \"\"\"

        def get_context_data(self, user: User):
            return {
                "user": user,
            }
    ```

    Since the "child" component is used within the `{% provide %} / {% endprovide %}` tags,
    we can request the "user_data" using `Component.inject("user_data")`:

    ```python
    @register("child")
    class Child(Component):
        template = \"\"\"
          <div>
            User is: {{ user }}
          </div>
        \"\"\"

        def get_context_data(self):
            user = self.inject("user_data").user
            return {
                "user": user,
            }
    ```

    Notice that the keys defined on the `{% provide %}` tag are then accessed as attributes
    when accessing them with [`Component.inject()`](../api#django_components.Component.inject).

    ✅ Do this
    ```python
    user = self.inject("user_data").user
    ```

    ❌ Don't do this
    ```python
    user = self.inject("user_data")["user"]
    ```
    """
    tag_id = gen_id()

    # e.g. {% provide <name> key=val key2=val2 %}
    tag = parse_template_tag(parser, token, tag_spec)

    trace_id = f"fill-id-{tag_id}"
    trace_msg("PARSE", "PROVIDE", trace_id, tag_id)

    body = tag.parse_body()
    provide_node = ProvideNode(
        nodelist=body,
        node_id=tag_id,
        params=tag.params,
        trace_id=trace_id,
    )

    trace_msg("PARSE", "PROVIDE", trace_id, tag_id, "...Done!")
    return provide_node


def html_attrs_signature(  # noqa: E704
    attrs: Optional[Dict] = None, defaults: Optional[Dict] = None, **kwargs: Any
) -> None: ...


@register.tag("html_attrs")
@with_tag_spec(
    TagSpec(
        tag="html_attrs",
        end_tag=None,  # inline-only
        signature=inspect.Signature.from_callable(html_attrs_signature),
        flags=[],
    )
)
def html_attrs(parser: Parser, token: Token, tag_spec: TagSpec) -> HtmlAttrsNode:
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
    tag_id = gen_id()
    tag = parse_template_tag(parser, token, tag_spec)

    return HtmlAttrsNode(
        node_id=tag_id,
        params=tag.params,
    )


__all__ = [
    "component",
    "component_css_dependencies",
    "component_js_dependencies",
    "fill",
    "html_attrs",
    "provide",
    "slot",
]
