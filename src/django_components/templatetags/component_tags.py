# Notes on documentation:
# - For intuitive use via Python imports, keep the tag names same as the function name.
#   E.g. so if the tag name is `slot`, one can also do
#   `from django_components.templatetags.component_tags import slot`
#
# - All tags are defined using `@register.tag`. Do NOT use `@register.simple_tag`.
#   The reason for this is so that we use `TagSpec` and `_parse_tag`. When generating
#   documentation, we extract the `TagSpecs` to be able to describe each tag's function signature.
#
# - Use `with_tag_spec` for defining `TagSpecs`. This will make it available to the function
#   as the last argument, and will also set the `TagSpec` instance to `fn._tag_spec`.
#   During documentation generation, we access the `fn._tag_spec`.

import functools
from typing import Any, Callable, Dict, List, Literal, NamedTuple, Optional, Set, Union

import django.template
from django.template.base import NodeList, Parser, TextNode, Token, TokenType
from django.template.exceptions import TemplateSyntaxError
from django.utils.safestring import SafeString, mark_safe

from django_components.attributes import HTML_ATTRS_ATTRS_KEY, HTML_ATTRS_DEFAULTS_KEY, HtmlAttrsNode
from django_components.component import COMP_ONLY_FLAG, ComponentNode
from django_components.component_registry import ComponentRegistry
from django_components.dependencies import CSS_DEPENDENCY_PLACEHOLDER, JS_DEPENDENCY_PLACEHOLDER
from django_components.expression import (
    DynamicFilterExpression,
    Expression,
    Operator,
    RuntimeKwargPairs,
    RuntimeKwargPairsInput,
    RuntimeKwargs,
    RuntimeKwargsInput,
    SpreadOperator,
    is_aggregate_key,
    is_dynamic_expression,
    is_internal_spread_operator,
    is_kwarg,
    is_spread_operator,
)
from django_components.provide import PROVIDE_NAME_KWARG, ProvideNode
from django_components.slots import (
    SLOT_DATA_KWARG,
    SLOT_DEFAULT_KEYWORD,
    SLOT_DEFAULT_KWARG,
    SLOT_NAME_KWARG,
    SLOT_REQUIRED_KEYWORD,
    FillNode,
    SlotNode,
)
from django_components.tag_formatter import get_tag_formatter
from django_components.template_parser import parse_bits
from django_components.util.logger import trace_msg
from django_components.util.misc import gen_id
from django_components.util.tag_parser import parse_tag_attrs

# NOTE: Variable name `register` is required by Django to recognize this as a template tag library
# See https://docs.djangoproject.com/en/dev/howto/custom-template-tags
register = django.template.Library()


class TagSpec(NamedTuple):
    """Definition of args, kwargs, flags, etc, for a template tag."""

    tag: str
    """Tag name. E.g. `"slot"` means the tag is written like so `{% slot ... %}`"""
    end_tag: Optional[str] = None
    """
    End tag.

    E.g. `"endslot"` means anything between the start tag and `{% endslot %}`
    is considered the slot's body.
    """
    positional_only_args: Optional[List[str]] = None
    """Arguments that MUST be given as positional args."""
    positional_args_allow_extra: bool = False
    """
    If `True`, allows variable number of positional args, e.g. `{% mytag val1 1234 val2 890 ... %}`
    """
    pos_or_keyword_args: Optional[List[str]] = None
    """Like regular Python kwargs, these can be given EITHER as positional OR as keyword arguments."""
    keywordonly_args: Optional[Union[bool, List[str]]] = False
    """
    Parameters that MUST be given only as kwargs (not accounting for `pos_or_keyword_args`).

    - If `False`, NO extra kwargs allowed.
    - If `True`, ANY number of extra kwargs allowed.
    - If a list of strings, e.g. `["class", "style"]`, then only those kwargs are allowed.
    """
    optional_kwargs: Optional[List[str]] = None
    """Specify which kwargs can be optional."""
    repeatable_kwargs: Optional[Union[bool, List[str]]] = False
    """
    Whether this tag allows all or certain kwargs to be repeated.

    - If `False`, NO kwargs can repeat.
    - If `True`, ALL kwargs can repeat.
    - If a list of strings, e.g. `["class", "style"]`, then only those kwargs can repeat.

    E.g. `["class"]` means one can write `{% mytag class="one" class="two" %}`
    """
    flags: Optional[List[str]] = None
    """
    List of allowed flags.

    Flags are like kwargs, but without the value part. E.g. in `{% mytag only required %}`:
    - `only` and `required` are treated as `only=True` and `required=True` if present
    - and treated as `only=False` and `required=False` if omitted
    """


def with_tag_spec(tag_spec: TagSpec) -> Callable:
    """"""

    def decorator(fn: Callable) -> Any:
        fn._tag_spec = tag_spec  # type: ignore[attr-defined]

        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return fn(*args, **kwargs, tag_spec=tag_spec)

        return wrapper

    return decorator


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


@register.tag("component_css_dependencies")
@with_tag_spec(
    TagSpec(
        tag="component_css_dependencies",
        end_tag=None,  # inline-only
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
    _parse_tag(parser, token, tag_spec)
    return _component_dependencies("css")


@register.tag(name="component_js_dependencies")
@with_tag_spec(
    TagSpec(
        tag="component_js_dependencies",
        end_tag=None,  # inline-only
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
    _parse_tag(parser, token, tag_spec)
    return _component_dependencies("js")


@register.tag("slot")
@with_tag_spec(
    TagSpec(
        tag="slot",
        end_tag="endslot",
        positional_only_args=[],
        pos_or_keyword_args=[SLOT_NAME_KWARG],
        keywordonly_args=True,
        repeatable_kwargs=False,
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
    tag = _parse_tag(parser, token, tag_spec)

    slot_name_kwarg = tag.kwargs.kwargs.get(SLOT_NAME_KWARG, None)
    trace_id = f"slot-id-{tag.id} ({slot_name_kwarg})" if slot_name_kwarg else f"slot-id-{tag.id}"

    trace_msg("PARSE", "SLOT", trace_id, tag.id)

    body = tag.parse_body()
    slot_node = SlotNode(
        nodelist=body,
        node_id=tag.id,
        kwargs=tag.kwargs,
        is_required=tag.flags[SLOT_REQUIRED_KEYWORD],
        is_default=tag.flags[SLOT_DEFAULT_KEYWORD],
        trace_id=trace_id,
    )

    trace_msg("PARSE", "SLOT", trace_id, tag.id, "...Done!")
    return slot_node


@register.tag("fill")
@with_tag_spec(
    TagSpec(
        tag="fill",
        end_tag="endfill",
        positional_only_args=[],
        pos_or_keyword_args=[SLOT_NAME_KWARG],
        keywordonly_args=[SLOT_DATA_KWARG, SLOT_DEFAULT_KWARG],
        optional_kwargs=[SLOT_DATA_KWARG, SLOT_DEFAULT_KWARG],
        repeatable_kwargs=False,
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
    tag = _parse_tag(parser, token, tag_spec)

    fill_name_kwarg = tag.kwargs.kwargs.get(SLOT_NAME_KWARG, None)
    trace_id = f"fill-id-{tag.id} ({fill_name_kwarg})" if fill_name_kwarg else f"fill-id-{tag.id}"

    trace_msg("PARSE", "FILL", trace_id, tag.id)

    body = tag.parse_body()
    fill_node = FillNode(
        nodelist=body,
        node_id=tag.id,
        kwargs=tag.kwargs,
        trace_id=trace_id,
    )

    trace_msg("PARSE", "FILL", trace_id, tag.id, "...Done!")
    return fill_node


@with_tag_spec(
    TagSpec(
        tag="component",
        end_tag="endcomponent",
        positional_only_args=[],
        positional_args_allow_extra=True,  # Allow many args
        keywordonly_args=True,
        repeatable_kwargs=False,
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
    _fix_nested_tags(parser, token)
    bits = token.split_contents()

    # Let the TagFormatter pre-process the tokens
    formatter = get_tag_formatter(registry)
    result = formatter.parse([*bits])
    end_tag = formatter.end_tag(result.component_name)

    # NOTE: The tokens returned from TagFormatter.parse do NOT include the tag itself
    bits = [bits[0], *result.tokens]
    token.contents = " ".join(bits)

    tag = _parse_tag(
        parser,
        token,
        TagSpec(
            **{
                **tag_spec._asdict(),
                "tag": tag_name,
                "end_tag": end_tag,
            }
        ),
    )

    # Check for isolated context keyword
    isolated_context = tag.flags[COMP_ONLY_FLAG]

    trace_msg("PARSE", "COMP", result.component_name, tag.id)

    body = tag.parse_body()

    component_node = ComponentNode(
        name=result.component_name,
        args=tag.args,
        kwargs=tag.kwargs,
        isolated_context=isolated_context,
        nodelist=body,
        node_id=tag.id,
        registry=registry,
    )

    trace_msg("PARSE", "COMP", result.component_name, tag.id, "...Done!")
    return component_node


@register.tag("provide")
@with_tag_spec(
    TagSpec(
        tag="provide",
        end_tag="endprovide",
        positional_only_args=[],
        pos_or_keyword_args=[PROVIDE_NAME_KWARG],
        keywordonly_args=True,
        repeatable_kwargs=False,
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
    # e.g. {% provide <name> key=val key2=val2 %}
    tag = _parse_tag(parser, token, tag_spec)

    name_kwarg = tag.kwargs.kwargs.get(PROVIDE_NAME_KWARG, None)
    trace_id = f"provide-id-{tag.id} ({name_kwarg})" if name_kwarg else f"fill-id-{tag.id}"

    trace_msg("PARSE", "PROVIDE", trace_id, tag.id)

    body = tag.parse_body()
    provide_node = ProvideNode(
        nodelist=body,
        node_id=tag.id,
        kwargs=tag.kwargs,
        trace_id=trace_id,
    )

    trace_msg("PARSE", "PROVIDE", trace_id, tag.id, "...Done!")
    return provide_node


@register.tag("html_attrs")
@with_tag_spec(
    TagSpec(
        tag="html_attrs",
        end_tag=None,  # inline-only
        positional_only_args=[],
        pos_or_keyword_args=[HTML_ATTRS_ATTRS_KEY, HTML_ATTRS_DEFAULTS_KEY],
        optional_kwargs=[HTML_ATTRS_ATTRS_KEY, HTML_ATTRS_DEFAULTS_KEY],
        keywordonly_args=True,
        repeatable_kwargs=True,
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
    tag = _parse_tag(parser, token, tag_spec)

    return HtmlAttrsNode(
        kwargs=tag.kwargs,
        kwarg_pairs=tag.kwarg_pairs,
    )


class ParsedTag(NamedTuple):
    id: str
    name: str
    bits: List[str]
    flags: Dict[str, bool]
    args: List[Expression]
    named_args: Dict[str, Expression]
    kwargs: RuntimeKwargs
    kwarg_pairs: RuntimeKwargPairs
    is_inline: bool
    parse_body: Callable[[], NodeList]


def _parse_tag(
    parser: Parser,
    token: Token,
    tag_spec: TagSpec,
) -> ParsedTag:
    # Use a unique ID to be able to tie the fill nodes with components and slots
    # NOTE: MUST be called BEFORE `parse_body()` to ensure predictable numbering
    tag_id = gen_id()

    params = [*(tag_spec.positional_only_args or []), *(tag_spec.pos_or_keyword_args or [])]

    _fix_nested_tags(parser, token)

    # e.g. {% slot <name> ... %}
    tag_name, *bits = token.split_contents()
    if tag_name != tag_spec.tag:
        raise TemplateSyntaxError(f"Start tag parser received tag '{tag_name}', expected '{tag_spec.tag}'")

    # Decide if the template tag is inline or block and strip the trailing slash
    last_token = bits[-1] if len(bits) else None
    if last_token == "/":
        bits.pop()
        is_inline = True
    else:
        # If no end tag was given, we assume that the tag is inline-only
        is_inline = not tag_spec.end_tag

    parsed_flags = {flag: False for flag in (tag_spec.flags or [])}
    bits_without_flags: List[str] = []
    seen_kwargs: Set[str] = set()
    seen_agg_keys: Set[str] = set()

    def mark_kwarg_key(key: str, is_agg_key: bool) -> None:
        if (is_agg_key and key in seen_kwargs) or (not is_agg_key and key in seen_agg_keys):
            raise TemplateSyntaxError(
                f"Received argument '{key}' both as a regular input ({key}=...)"
                f" and as an aggregate dict ('{key}:key=...'). Must be only one of the two"
            )
        if is_agg_key:
            seen_agg_keys.add(key)
        else:
            seen_kwargs.add(key)

    spread_count = 0
    for bit in bits:
        value = bit
        bit_is_kwarg = is_kwarg(bit)

        # Record which kwargs we've seen, to detect if kwargs were passed in
        # as both aggregate and regular kwargs
        if bit_is_kwarg:
            key, value = bit.split("=", 1)

            # Also pick up on aggregate keys like `attr:key=val`
            if is_aggregate_key(key):
                key = key.split(":")[0]
                mark_kwarg_key(key, True)
            else:
                mark_kwarg_key(key, False)

        else:
            # Extract flags, which are like keywords but without the value part
            if value in parsed_flags:
                parsed_flags[value] = True
                continue

            # Extract spread operator (...dict)
            elif is_spread_operator(value):
                if value == "...":
                    raise TemplateSyntaxError("Syntax operator is missing a value")

                # Replace the leading `...` with `...=`, so the parser
                # interprets it as a kwargs, and keeps it in the correct
                # position.
                # Since there can be multiple spread operators, we suffix
                # them with an index, e.g. `...0=`
                internal_spread_bit = f"...{spread_count}={value[3:]}"
                bits_without_flags.append(internal_spread_bit)
                spread_count += 1
                continue

        bits_without_flags.append(bit)

    bits = bits_without_flags

    # To support optional args, we need to convert these to kwargs, so `parse_bits`
    # can handle them. So we assign the keys to matched positional args,
    # and then move the kwarg AFTER the pos args.
    #
    # TODO: This following section should live in `parse_bits`, but I don't want to
    # modify it much to maintain some sort of compatibility with Django's version of
    # `parse_bits`.
    # Ideally, Django's parser would be expanded to support our use cases.
    params_to_sort = [param for param in params if param not in seen_kwargs]
    new_args = []
    new_params = []
    new_kwargs = []
    for index, bit in enumerate(bits):
        if is_kwarg(bit) or not len(params_to_sort):
            # Pass all remaining bits (including current one) as kwargs
            new_kwargs.extend(bits[index:])
            break

        param = params_to_sort.pop(0)
        if tag_spec.pos_or_keyword_args and param in tag_spec.pos_or_keyword_args:
            mark_kwarg_key(param, False)
            new_kwargs.append(f"{param}={bit}")
            continue
        new_args.append(bit)
        new_params.append(param)

    bits = [*new_args, *new_kwargs]
    params = [*new_params, *params_to_sort]

    # Remove any remaining optional positional args if they were not given
    if tag_spec.pos_or_keyword_args:
        params = [param for param in params_to_sort if param not in tag_spec.pos_or_keyword_args]

    # Parse args/kwargs that will be passed to the fill
    raw_args, raw_kwarg_pairs = parse_bits(
        parser=parser,
        bits=bits,
        params=[] if tag_spec.positional_args_allow_extra else params,
        name=tag_name,
    )

    # Post-process args/kwargs - Mark special cases like aggregate dicts
    # or dynamic expressions
    args: List[Expression] = []
    for val in raw_args:
        if is_dynamic_expression(val.token):
            args.append(DynamicFilterExpression(parser, val.token))
        else:
            args.append(val)

    kwarg_pairs: RuntimeKwargPairsInput = []
    for key, val in raw_kwarg_pairs:
        is_spread_op = is_internal_spread_operator(key + "=")

        if is_spread_op:
            # Allow to use dynamic expressions with spread operator, e.g.
            # `..."{{ }}"`
            if is_dynamic_expression(val.token):
                expr = DynamicFilterExpression(parser, val.token)
            else:
                expr = parser.compile_filter(val.token)
            kwarg_pairs.append((key, SpreadOperator(expr)))
        elif is_dynamic_expression(val.token) and not is_spread_op:
            kwarg_pairs.append((key, DynamicFilterExpression(parser, val.token)))
        else:
            kwarg_pairs.append((key, val))

    # Allow only as many positional args as given
    if not tag_spec.positional_args_allow_extra and len(args) > len(params):  # noqa F712
        raise TemplateSyntaxError(f"Tag '{tag_name}' received unexpected positional arguments: {args[len(params):]}")

    # For convenience, allow to access named args by their name instead of index
    named_args = {param: args[index] for index, param in enumerate(params)}

    # Validate kwargs
    kwargs: RuntimeKwargsInput = {}
    extra_keywords: Set[str] = set()
    for key, val in kwarg_pairs:
        # Operators are resolved at render-time, so skip them
        if isinstance(val, Operator):
            kwargs[key] = val
            continue

        # Check if key allowed
        if not tag_spec.keywordonly_args:
            is_key_allowed = False
        else:
            is_key_allowed = (
                tag_spec.keywordonly_args == True or key in tag_spec.keywordonly_args  # noqa: E712
            ) or bool(tag_spec.pos_or_keyword_args and key in tag_spec.pos_or_keyword_args)
        if not is_key_allowed:
            is_optional = key in tag_spec.optional_kwargs if tag_spec.optional_kwargs else False
            if not is_optional:
                extra_keywords.add(key)

        # Check for repeated keys
        if key in kwargs:
            if not tag_spec.repeatable_kwargs:
                is_key_repeatable = False
            else:
                is_key_repeatable = (
                    tag_spec.repeatable_kwargs == True or key in tag_spec.repeatable_kwargs  # noqa: E712
                )
            if not is_key_repeatable:
                # The keyword argument has already been supplied once
                raise TemplateSyntaxError(f"'{tag_name}' received multiple values for keyword argument '{key}'")
        # All ok
        kwargs[key] = val

    if len(extra_keywords):
        extra_keys = ", ".join(extra_keywords)
        raise TemplateSyntaxError(f"'{tag_name}' received unexpected kwargs: {extra_keys}")

    return ParsedTag(
        id=tag_id,
        name=tag_name,
        bits=bits,
        flags=parsed_flags,
        args=args,
        named_args=named_args,
        kwargs=RuntimeKwargs(kwargs),
        kwarg_pairs=RuntimeKwargPairs(kwarg_pairs),
        # NOTE: We defer parsing of the body, so we have the chance to call the tracing
        # loggers before the parsing. This is because, if the body contains any other
        # tags, it will trigger their tag handlers. So the code called AFTER
        # `parse_body()` is already after all the nested tags were processed.
        parse_body=lambda: _parse_tag_body(parser, tag_spec.end_tag, is_inline) if tag_spec.end_tag else NodeList(),
        is_inline=is_inline,
    )


def _parse_tag_body(parser: Parser, end_tag: str, inline: bool) -> NodeList:
    if inline:
        body = NodeList()
    else:
        body = parser.parse(parse_until=[end_tag])
        parser.delete_first_token()
    return body


def _fix_nested_tags(parser: Parser, block_token: Token) -> None:
    # Since the nested tags MUST be wrapped in quotes, e.g.
    # `{% component 'test' "{% lorem var_a w %}" %}`
    # `{% component 'test' key="{% lorem var_a w %}" %}`
    #
    # We can parse the tag's tokens so we can find the last one, and so we consider
    # the unclosed `{%` only for the last bit.
    _, attrs = parse_tag_attrs(block_token.contents)

    # If there are no attributes, then there are no nested tags
    if not attrs:
        return

    last_attr = attrs[-1]
    last_token = last_attr.value

    # User probably forgot to wrap the nested tag in quotes, or this is the end of the input.
    # `{% component ... key={% nested %} %}`
    # `{% component ... key= %}`
    if not last_token:
        return

    # When our template tag contains a nested tag, e.g.:
    # `{% component 'test' "{% lorem var_a w %}" %}`
    #
    # Django parses this into:
    # `TokenType.BLOCK: 'component 'test'     "{% lorem var_a w'`
    #
    # Above you can see that the token ends at the end of the NESTED tag,
    # and includes `{%`. So that's what we use to identify if we need to fix
    # nested tags or not.
    has_unclosed_tag = (
        (last_token.count("{%") > last_token.count("%}"))
        # Moreover we need to also check for unclosed quotes for this edge case:
        # `{% component 'test' "{%}" %}`
        #
        # Which Django parses this into:
        # `TokenType.BLOCK: 'component 'test'  "{'`
        #
        # Here we cannot see any unclosed tags, but there is an unclosed double quote at the end.
        #
        # But we cannot naively search the full contents for unclosed quotes, but
        # only within the last 'bit'. Consider this:
        # `{% component 'test' '"' "{%}" %}`
        #
        or (last_token in ("'{", '"{'))
    )

    # There is 3 double quotes, but if the contents get split at the first `%}`
    # then there will be a single unclosed double quote in the last bit.
    has_unclosed_quote = not last_attr.quoted and last_token and last_token[0] in ('"', "'")

    needs_fixing = has_unclosed_tag and has_unclosed_quote

    if not needs_fixing:
        return

    block_token.contents += "%}" if has_unclosed_quote else " %}"
    expects_text = True
    while True:
        # This is where we need to take parsing in our own hands, because Django parser parsed
        # only up to the first closing tag `%}`, but that closing tag corresponds to a nested tag,
        # and not to the end of the outer template tag.
        #
        # NOTE: If we run out of tokens, this will raise, and break out of the loop
        token = parser.next_token()

        # If there is a nested BLOCK `{% %}`, VAR `{{ }}`, or COMMENT `{# #}` tag inside the template tag,
        # then the way Django parses it results in alternating Tokens of TEXT and non-TEXT types.
        #
        # We use `expects_text` to know which type to handle.
        if expects_text:
            if token.token_type != TokenType.TEXT:
                raise TemplateSyntaxError(f"Template parser received TokenType '{token.token_type}' instead of 'TEXT'")

            expects_text = False

            # Once we come across a closing tag in the text, we know that's our original
            # end tag. Until then, append all the text to the block token and continue
            if "%}" not in token.contents:
                block_token.contents += token.contents
                continue

            # This is the ACTUAL end of the block template tag
            remaining_block_content, text_content = token.contents.split("%}", 1)
            block_token.contents += remaining_block_content

            # We put back into the Parser the remaining bit of the text.
            # NOTE: Looking at the implementation, `parser.prepend_token()` is the opposite
            # of `parser.next_token()`.
            parser.prepend_token(Token(TokenType.TEXT, contents=text_content))
            break

        # In this case we've come across a next block tag `{% %}` inside the template tag
        # This isn't the first occurence, where the `{%` was ignored. And so, the content
        # between the `{% %}` is correctly captured, e.g.
        #
        # `{% firstof False 0 is_active %}`
        # gives
        # `TokenType.BLOCK: 'firstof False 0 is_active'`
        #
        # But we don't want to evaluate this as a standalone BLOCK tag, and instead append
        # it to the block tag that this nested block is part of
        else:
            if token.token_type == TokenType.TEXT:
                raise TemplateSyntaxError(
                    f"Template parser received TokenType '{token.token_type}' instead of 'BLOCK', 'VAR', 'COMMENT'"
                )

            if token.token_type == TokenType.BLOCK:
                block_token.contents += "{% " + token.contents + " %}"
            elif token.token_type == TokenType.VAR:
                block_token.contents += "{{ " + token.contents + " }}"
            elif token.token_type == TokenType.COMMENT:
                pass  # Comments are ignored
            else:
                raise TemplateSyntaxError(f"Unknown token type '{token.token_type}'")

            expects_text = True
            continue


__all__ = [
    "component",
    "component_css_dependencies",
    "component_js_dependencies",
    "fill",
    "html_attrs",
    "provide",
    "slot",
]
