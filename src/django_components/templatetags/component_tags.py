from typing import TYPE_CHECKING, Dict, List, Mapping, Optional, Tuple

import django.template
from django.template.base import FilterExpression, Node, NodeList, Parser, TextNode, Token, TokenType
from django.template.exceptions import TemplateSyntaxError
from django.utils.safestring import SafeString, mark_safe

from django_components.app_settings import ContextBehavior, app_settings
from django_components.attributes import HtmlAttrsNode
from django_components.component import RENDERED_COMMENT_TEMPLATE, ComponentNode
from django_components.component_registry import ComponentRegistry
from django_components.component_registry import registry as component_registry
from django_components.logger import trace_msg
from django_components.middleware import (
    CSS_DEPENDENCY_PLACEHOLDER,
    JS_DEPENDENCY_PLACEHOLDER,
    is_dependency_middleware_active,
)
from django_components.slots import FillNode, SlotNode, parse_slot_fill_nodes_from_component_nodelist
from django_components.template_parser import parse_bits
from django_components.utils import gen_id

if TYPE_CHECKING:
    from django_components.component import Component


register = django.template.Library()


SLOT_REQUIRED_OPTION_KEYWORD = "required"
SLOT_DEFAULT_OPTION_KEYWORD = "default"


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
    bits = token.split_contents()
    args = bits[1:]
    # e.g. {% slot <name> %}
    is_required = False
    is_default = False
    if 1 <= len(args) <= 3:
        slot_name, *options = args
        if not is_wrapped_in_quotes(slot_name):
            raise TemplateSyntaxError(f"'{bits[0]}' name must be a string 'literal'.")
        slot_name = strip_quotes(slot_name)
        modifiers_count = len(options)
        if SLOT_REQUIRED_OPTION_KEYWORD in options:
            is_required = True
            modifiers_count -= 1
        if SLOT_DEFAULT_OPTION_KEYWORD in options:
            is_default = True
            modifiers_count -= 1
        if modifiers_count != 0:
            keywords = [
                SLOT_REQUIRED_OPTION_KEYWORD,
                SLOT_DEFAULT_OPTION_KEYWORD,
            ]
            raise TemplateSyntaxError(f"Invalid options passed to 'slot' tag. Valid choices: {keywords}.")
    else:
        raise TemplateSyntaxError(
            "'slot' tag does not match pattern "
            "{% slot <name> ['default'] ['required'] %}. "
            "Order of options is free."
        )

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
    )

    trace_msg("PARSE", "SLOT", slot_name, slot_id, "...Done!")
    return slot_node


@register.tag("fill")
def do_fill(parser: Parser, token: Token) -> FillNode:
    """Block tag whose contents 'fill' (are inserted into) an identically named
    'slot'-block in the component template referred to by a parent component.
    It exists to make component nesting easier.

    This tag is available only within a {% component %}..{% endcomponent %} block.
    Runtime checks should prohibit other usages.
    """
    bits = token.split_contents()
    tag = bits[0]
    args = bits[1:]
    # e.g. {% fill <name> %}
    alias_fexp: Optional[FilterExpression] = None
    if len(args) == 1:
        tgt_slot_name: str = args[0]
    # e.g. {% fill <name> as <alias> %}
    elif len(args) == 3:
        tgt_slot_name, as_keyword, alias = args
        if as_keyword.lower() != "as":
            raise TemplateSyntaxError(f"{tag} tag args do not conform to pattern '<target slot> as <alias>'")
        alias_fexp = FilterExpression(alias, parser)
    else:
        raise TemplateSyntaxError(f"'{tag}' tag takes either 1 or 3 arguments: Received {len(args)}.")

    # Use a unique ID to be able to tie the fill nodes with components and slots
    # NOTE: MUST be called BEFORE `parser.parse()` to ensure predictable numbering
    fill_id = gen_id()
    trace_msg("PARSE", "FILL", tgt_slot_name, fill_id)

    nodelist = parser.parse(parse_until=["endfill"])
    parser.delete_first_token()

    fill_node = FillNode(
        nodelist,
        name_fexp=FilterExpression(tgt_slot_name, tag),
        alias_fexp=alias_fexp,
        node_id=fill_id,
    )

    trace_msg("PARSE", "FILL", tgt_slot_name, fill_id, "...Done!")
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
    bits, isolated_context = check_for_isolated_context_keyword(bits)
    component_name, context_args, context_kwargs = parse_component_with_args(parser, bits, "component")

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
    attributes, default_attrs, append_attrs = parse_html_attrs_args(parser, bits, "html_attrs")
    return HtmlAttrsNode(attributes, default_attrs, append_attrs)


def is_whitespace_node(node: Node) -> bool:
    return isinstance(node, TextNode) and node.s.isspace()


def is_whitespace_token(token: Token) -> bool:
    return token.token_type == TokenType.TEXT and not token.contents.strip()


def is_block_tag_token(token: Token, name: str) -> bool:
    return token.token_type == TokenType.BLOCK and token.split_contents()[0] == name


def check_for_isolated_context_keyword(bits: List[str]) -> Tuple[List[str], bool]:
    """Return True and strip the last word if token ends with 'only' keyword or if CONTEXT_BEHAVIOR is 'isolated'."""

    if bits[-1] == "only":
        return bits[:-1], True

    if app_settings.CONTEXT_BEHAVIOR == ContextBehavior.ISOLATED:
        return bits, True

    return bits, False


def parse_component_with_args(
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


def parse_html_attrs_args(
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


def strip_quotes(s: str) -> str:
    return s.strip("\"'")
