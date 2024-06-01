from typing import TYPE_CHECKING, Dict, List, Mapping, Optional, Tuple

import django.template
from django.template.base import FilterExpression, NodeList, Parser, Token
from django.template.exceptions import TemplateSyntaxError
from django.utils.safestring import SafeString, mark_safe

from django_components.app_settings import ContextBehavior, app_settings
from django_components.attributes import HtmlAttrsNode
from django_components.component import RENDERED_COMMENT_TEMPLATE, ComponentNode
from django_components.component_registry import ComponentRegistry
from django_components.component_registry import registry as component_registry
from django_components.expression import resolve_string
from django_components.logger import trace_msg
from django_components.middleware import (
    CSS_DEPENDENCY_PLACEHOLDER,
    JS_DEPENDENCY_PLACEHOLDER,
    is_dependency_middleware_active,
)
from django_components.provide import ProvideNode
from django_components.slots import FillNode, SlotNode, parse_slot_fill_nodes_from_component_nodelist
from django_components.template_parser import parse_bits
from django_components.utils import gen_id

if TYPE_CHECKING:
    from django_components.component import Component


register = django.template.Library()


SLOT_REQUIRED_OPTION_KEYWORD = "required"
SLOT_DEFAULT_OPTION_KEYWORD = "default"
SLOT_DATA_ATTR = "data"
SLOT_DEFAULT_ATTR = "default"


def get_components_from_registry(registry: ComponentRegistry) -> List["Component"]:
    """Returns a list unique components from the registry."""

    unique_component_classes = set(registry.all().values())

    components = []
    for component_class in unique_component_classes:
        components.append(component_class(component_class.__name__))

    return components


def get_components_from_preload_str(preload_str: str) -> List["Component"]:
    """Returns a list of unique components from a comma-separated str"""

    components = []
    for component_name in preload_str.split(","):
        component_name = component_name.strip()
        if not component_name:
            continue
        component_class = component_registry.get(component_name)
        components.append(component_class(component_name))

    return components


@register.simple_tag(name="component_dependencies")
def component_dependencies_tag(preload: str = "") -> SafeString:
    """Marks location where CSS link and JS script tags should be rendered."""

    if is_dependency_middleware_active():
        preloaded_dependencies = []
        for component in get_components_from_preload_str(preload):
            preloaded_dependencies.append(RENDERED_COMMENT_TEMPLATE.format(name=component.registered_name))
        return mark_safe("\n".join(preloaded_dependencies) + CSS_DEPENDENCY_PLACEHOLDER + JS_DEPENDENCY_PLACEHOLDER)
    else:
        rendered_dependencies = []
        for component in get_components_from_registry(component_registry):
            rendered_dependencies.append(component.render_dependencies())

        return mark_safe("\n".join(rendered_dependencies))


@register.simple_tag(name="component_css_dependencies")
def component_css_dependencies_tag(preload: str = "") -> SafeString:
    """Marks location where CSS link tags should be rendered."""

    if is_dependency_middleware_active():
        preloaded_dependencies = []
        for component in get_components_from_preload_str(preload):
            preloaded_dependencies.append(RENDERED_COMMENT_TEMPLATE.format(name=component.registered_name))
        return mark_safe("\n".join(preloaded_dependencies) + CSS_DEPENDENCY_PLACEHOLDER)
    else:
        rendered_dependencies = []
        for component in get_components_from_registry(component_registry):
            rendered_dependencies.append(component.render_css_dependencies())

        return mark_safe("\n".join(rendered_dependencies))


@register.simple_tag(name="component_js_dependencies")
def component_js_dependencies_tag(preload: str = "") -> SafeString:
    """Marks location where JS script tags should be rendered."""

    if is_dependency_middleware_active():
        preloaded_dependencies = []
        for component in get_components_from_preload_str(preload):
            preloaded_dependencies.append(RENDERED_COMMENT_TEMPLATE.format(name=component.registered_name))
        return mark_safe("\n".join(preloaded_dependencies) + JS_DEPENDENCY_PLACEHOLDER)
    else:
        rendered_dependencies = []
        for component in get_components_from_registry(component_registry):
            rendered_dependencies.append(component.render_js_dependencies())

        return mark_safe("\n".join(rendered_dependencies))


@register.tag("slot")
def do_slot(parser: Parser, token: Token) -> SlotNode:
    # e.g. {% slot <name> ... %}
    tag_name, *args = token.split_contents()
    slot_name, is_default, is_required, slot_kwargs = _parse_slot_args(parser, args, tag_name)
    # Use a unique ID to be able to tie the fill nodes with components and slots
    # NOTE: MUST be called BEFORE `parser.parse()` to ensure predictable numbering
    slot_id = gen_id()
    trace_msg("PARSE", "SLOT", slot_name, slot_id)

    nodelist = parser.parse(parse_until=["endslot"])
    parser.delete_first_token()
    slot_node = SlotNode(
        slot_name,
        nodelist,
        is_required=is_required,
        is_default=is_default,
        node_id=slot_id,
        slot_kwargs=slot_kwargs,
    )

    trace_msg("PARSE", "SLOT", slot_name, slot_id, "...Done!")
    return slot_node


@register.tag("fill")
def do_fill(parser: Parser, token: Token) -> FillNode:
    """
    Block tag whose contents 'fill' (are inserted into) an identically named
    'slot'-block in the component template referred to by a parent component.
    It exists to make component nesting easier.

    This tag is available only within a {% component %}..{% endcomponent %} block.
    Runtime checks should prohibit other usages.
    """
    # e.g. {% fill <name> %}
    tag_name, *args = token.split_contents()
    slot_name_fexp, slot_default_var_fexp, slot_data_var_fexp = _parse_fill_args(parser, args, tag_name)

    # Use a unique ID to be able to tie the fill nodes with components and slots
    # NOTE: MUST be called BEFORE `parser.parse()` to ensure predictable numbering
    fill_id = gen_id()
    trace_msg("PARSE", "FILL", str(slot_name_fexp), fill_id)

    nodelist = parser.parse(parse_until=["endfill"])
    parser.delete_first_token()

    fill_node = FillNode(
        nodelist,
        name_fexp=slot_name_fexp,
        slot_default_var_fexp=slot_default_var_fexp,
        slot_data_var_fexp=slot_data_var_fexp,
        node_id=fill_id,
    )

    trace_msg("PARSE", "FILL", str(slot_name_fexp), fill_id, "...Done!")
    return fill_node


@register.tag(name="component")
def do_component(parser: Parser, token: Token) -> ComponentNode:
    """
    To give the component access to the template context:
        {% component "name" positional_arg keyword_arg=value ... %}

    To render the component in an isolated context:
        {% component "name" positional_arg keyword_arg=value ... only %}

    Positional and keyword arguments can be literals or template variables.
    The component name must be a single- or double-quotes string and must
    be either the first positional argument or, if there are no positional
    arguments, passed as 'name'.
    """

    bits = token.split_contents()
    bits, isolated_context = _check_for_isolated_context_keyword(bits)
    component_name, context_args, context_kwargs = _parse_component_with_args(parser, bits, "component")

    # Use a unique ID to be able to tie the fill nodes with components and slots
    # NOTE: MUST be called BEFORE `parser.parse()` to ensure predictable numbering
    component_id = gen_id()
    trace_msg("PARSE", "COMP", component_name, component_id)

    body: NodeList = parser.parse(parse_until=["endcomponent"])
    parser.delete_first_token()
    fill_nodes = parse_slot_fill_nodes_from_component_nodelist(body, ComponentNode)

    # Tag all fill nodes as children of this particular component instance
    for node in fill_nodes:
        trace_msg("ASSOC", "FILL", node.name_fexp, node.node_id, component_id=component_id)
        node.component_id = component_id

    component_node = ComponentNode(
        FilterExpression(component_name, parser),
        context_args,
        context_kwargs,
        isolated_context=isolated_context,
        fill_nodes=fill_nodes,
        component_id=component_id,
    )

    trace_msg("PARSE", "COMP", component_name, component_id, "...Done!")
    return component_node


@register.tag("provide")
def do_provide(parser: Parser, token: Token) -> SlotNode:
    # e.g. {% provide <name> key=val key2=val2 %}
    tag_name, *args = token.split_contents()
    provide_key, kwargs = _parse_provide_args(parser, args, tag_name)

    # Use a unique ID to be able to tie the fill nodes with components and slots
    # NOTE: MUST be called BEFORE `parser.parse()` to ensure predictable numbering
    slot_id = gen_id()
    trace_msg("PARSE", "PROVIDE", provide_key, slot_id)

    nodelist = parser.parse(parse_until=["endprovide"])
    parser.delete_first_token()
    slot_node = ProvideNode(
        provide_key,
        nodelist,
        node_id=slot_id,
        provide_kwargs=kwargs,
    )

    trace_msg("PARSE", "PROVIDE", provide_key, slot_id, "...Done!")
    return slot_node


@register.tag("html_attrs")
def do_html_attrs(parser: Parser, token: Token) -> HtmlAttrsNode:
    """
    This tag takes:
    - Optional dictionary of attributes (`attrs`)
    - Optional dictionary of defaults (`defaults`)
    - Additional kwargs that are appended to the former two

    The inputs are merged and resulting dict is rendered as HTML attributes
    (`key="value"`).

    Rules:
    1. Both `attrs` and `defaults` can be passed as positional args or as kwargs
    2. Both `attrs` and `defaults` are optional (can be omitted)
    3. Both `attrs` and `defaults` are dictionaries, and we can define them the same way
       we define dictionaries for the `component` tag. So either as `attrs=attrs` or
       `attrs:key=value`.
    4. All other kwargs (`key=value`) are appended and can be repeated.

    Normal kwargs (`key=value`) are concatenated to existing keys. So if e.g. key
    "class" is supplied with value "my-class", then adding `class="extra-class"`
    will result in `class="my-class extra-class".

    Example:
    ```django
    {% html_attrs attrs defaults:class="default-class" class="extra-class" data-id="123" %}
    ```
    """
    bits = token.split_contents()
    attributes, default_attrs, append_attrs = _parse_html_attrs_args(parser, bits, "html_attrs")
    return HtmlAttrsNode(attributes, default_attrs, append_attrs)


def _check_for_isolated_context_keyword(bits: List[str]) -> Tuple[List[str], bool]:
    """Return True and strip the last word if token ends with 'only' keyword or if CONTEXT_BEHAVIOR is 'isolated'."""

    if bits[-1] == "only":
        return bits[:-1], True

    if app_settings.CONTEXT_BEHAVIOR == ContextBehavior.ISOLATED:
        return bits, True

    return bits, False


def _parse_component_with_args(
    parser: Parser, bits: List[str], tag_name: str
) -> Tuple[str, List[FilterExpression], Mapping[str, FilterExpression]]:
    tag_args, tag_kwarg_pairs = parse_bits(
        parser=parser,
        bits=bits,
        params=["tag_name", "name"],
        name=tag_name,
    )

    tag_kwargs = {}
    for key, val in tag_kwarg_pairs:
        if key in tag_kwargs:
            # The keyword argument has already been supplied once
            raise TemplateSyntaxError(f"'{tag_name}' received multiple values for keyword argument '{key}'")
        tag_kwargs[key] = val

    if tag_name != tag_args[0].token:
        raise RuntimeError(f"Internal error: Expected tag_name to be {tag_name}, but it was {tag_args[0].token}")

    component_name = _get_positional_param(tag_name, "name", 1, tag_args, tag_kwargs).token
    if len(tag_args) > 1:
        # Positional args given. Skip tag and component name and take the rest
        context_args = tag_args[2:]
    else:  # No positional args
        context_args = []

    return component_name, context_args, tag_kwargs


def _parse_html_attrs_args(
    parser: Parser, bits: List[str], tag_name: str
) -> Tuple[Optional[FilterExpression], Optional[FilterExpression], List[Tuple[str, FilterExpression]]]:
    tag_args, tag_kwarg_pairs = parse_bits(
        parser=parser,
        bits=bits,
        params=["tag_name"],
        name=tag_name,
    )

    # NOTE: Unlike in the `component` tag, in this case we don't care about duplicates,
    # as we're constructing the dict simply to find the `attrs` kwarg.
    tag_kwargs = {key: val for key, val in tag_kwarg_pairs}

    if tag_name != tag_args[0].token:
        raise RuntimeError(f"Internal error: Expected tag_name to be {tag_name}, but it was {tag_args[0].token}")

    # Allow to optioanlly provide `attrs` as positional arg `{% html_attrs attrs %}`
    try:
        attrs = _get_positional_param(tag_name, "attrs", 1, tag_args, tag_kwargs)
    except TemplateSyntaxError:
        attrs = None

    # Allow to optionally provide `defaults` as positional arg `{% html_attrs attrs defaults %}`
    try:
        defaults = _get_positional_param(tag_name, "defaults", 2, tag_args, tag_kwargs)
    except TemplateSyntaxError:
        defaults = None

    # Allow only up to 2 positional args - [0] == tag name, [1] == attrs, [2] == defaults
    if len(tag_args) > 3:
        raise TemplateSyntaxError(f"Tag '{tag_name}' received unexpected positional arguments: {tag_args[2:]}")

    return attrs, defaults, tag_kwarg_pairs


def _parse_slot_args(
    parser: Parser,
    bits: List[str],
    tag_name: str,
) -> Tuple[str, bool, bool, Dict[str, FilterExpression]]:
    if not len(bits):
        raise TemplateSyntaxError(
            "'slot' tag does not match pattern "
            "{% slot <name> ['default'] ['required'] [key=val, ...] %}. "
            "Order of options is free."
        )

    slot_name, *options = bits
    if not is_wrapped_in_quotes(slot_name):
        raise TemplateSyntaxError(f"'{tag_name}' name must be a string 'literal'.")

    slot_name = resolve_string(slot_name, parser)

    # Parse flags - Since `parse_bits` doesn't handle "shorthand" kwargs
    # (AKA `required` for `required=True`), we have to first get the flags out
    # of the way.
    def extract_value(lst: List[str], value: str) -> bool:
        """Check if value exists in list, and if so, remove it from said list"""
        try:
            lst.remove(value)
            return True
        except ValueError:
            return False

    is_default = extract_value(options, SLOT_DEFAULT_OPTION_KEYWORD)
    is_required = extract_value(options, SLOT_REQUIRED_OPTION_KEYWORD)

    # Parse kwargs that will be passed to the fill
    _, tag_kwarg_pairs = parse_bits(
        parser=parser,
        bits=options,
        params=[],
        name=tag_name,
    )
    tag_kwargs: Dict[str, FilterExpression] = {}
    for key, val in tag_kwarg_pairs:
        if key in tag_kwargs:
            # The keyword argument has already been supplied once
            raise TemplateSyntaxError(f"'{tag_name}' received multiple values for keyword argument '{key}'")
        tag_kwargs[key] = val

    return slot_name, is_default, is_required, tag_kwargs


def _parse_fill_args(
    parser: Parser,
    bits: List[str],
    tag_name: str,
) -> Tuple[FilterExpression, Optional[FilterExpression], Optional[FilterExpression]]:
    if not len(bits):
        raise TemplateSyntaxError(
            "'fill' tag does not match pattern "
            f"{{% fill <name> [{SLOT_DATA_ATTR}=val] [{SLOT_DEFAULT_ATTR}=slot_var] %}} "
        )

    slot_name = bits.pop(0)
    slot_name_fexp = parser.compile_filter(slot_name)

    # Even tho we want to parse only single kwarg, we use the same logic for parsing
    # as we use for other tags, for consistency.
    _, tag_kwarg_pairs = parse_bits(
        parser=parser,
        bits=bits,
        params=[],
        name=tag_name,
    )

    tag_kwargs: Dict[str, FilterExpression] = {}
    for key, val in tag_kwarg_pairs:
        if key in tag_kwargs:
            raise TemplateSyntaxError(f"'{tag_name}' received multiple values for keyword argument '{key}'")
        tag_kwargs[key] = val

    # Extract known kwargs
    slot_data_var_fexp: Optional[FilterExpression] = None
    if SLOT_DATA_ATTR in tag_kwargs:
        slot_data_var_fexp = tag_kwargs.pop(SLOT_DATA_ATTR)
        if not is_wrapped_in_quotes(slot_data_var_fexp.token):
            raise TemplateSyntaxError(
                f"Value of '{SLOT_DATA_ATTR}' in '{tag_name}' tag must be a string literal, got '{slot_data_var_fexp}'"
            )

    slot_default_var_fexp: Optional[FilterExpression] = None
    if SLOT_DEFAULT_ATTR in tag_kwargs:
        slot_default_var_fexp = tag_kwargs.pop(SLOT_DEFAULT_ATTR)
        if not is_wrapped_in_quotes(slot_default_var_fexp.token):
            raise TemplateSyntaxError(
                f"Value of '{SLOT_DEFAULT_ATTR}' in '{tag_name}' tag must be a string literal,"
                f" got '{slot_default_var_fexp}'"
            )

    # data and default cannot be bound to the same variable
    if slot_data_var_fexp and slot_default_var_fexp and slot_data_var_fexp.token == slot_default_var_fexp.token:
        raise TemplateSyntaxError(
            f"'{tag_name}' received the same string for slot default ({SLOT_DEFAULT_ATTR}=...)"
            f" and slot data ({SLOT_DATA_ATTR}=...)"
        )

    if len(tag_kwargs):
        extra_keywords = tag_kwargs.keys()
        extra_keys = ", ".join(extra_keywords)
        raise TemplateSyntaxError(f"'{tag_name}' received unexpected kwargs: {extra_keys}")

    return slot_name_fexp, slot_default_var_fexp, slot_data_var_fexp


def _parse_provide_args(
    parser: Parser,
    bits: List[str],
    tag_name: str,
) -> Tuple[str, Dict[str, FilterExpression]]:
    if not len(bits):
        raise TemplateSyntaxError("'provide' tag does not match pattern {% provide <key> [key=val, ...] %}. ")

    provide_key, *options = bits
    if not is_wrapped_in_quotes(provide_key):
        raise TemplateSyntaxError(f"'{tag_name}' key must be a string 'literal'.")

    provide_key = resolve_string(provide_key, parser)

    # Parse kwargs that will be 'provided' under the given key
    _, tag_kwarg_pairs = parse_bits(parser=parser, bits=options, params=[], name=tag_name)
    tag_kwargs: Dict[str, FilterExpression] = {}
    for key, val in tag_kwarg_pairs:
        if key in tag_kwargs:
            # The keyword argument has already been supplied once
            raise TemplateSyntaxError(f"'{tag_name}' received multiple values for keyword argument '{key}'")
        tag_kwargs[key] = val

    return provide_key, tag_kwargs


def _get_positional_param(
    tag_name: str,
    param_name: str,
    param_index: int,
    args: List[FilterExpression],
    kwargs: Dict[str, FilterExpression],
) -> FilterExpression:
    # Param is given as positional arg, e.g. `{% tag param %}`
    if len(args) > param_index:
        param = args[param_index]
        return param
    # Check if param was given as kwarg, e.g. `{% tag param_name=param %}`
    elif param_name in kwargs:
        param = kwargs.pop(param_name)
        return param

    raise TemplateSyntaxError(f"Param '{param_name}' not found in '{tag_name}' tag")


def is_wrapped_in_quotes(s: str) -> bool:
    return s.startswith(('"', "'")) and s[0] == s[-1]
