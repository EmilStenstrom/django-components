from typing import TYPE_CHECKING, List, Mapping, Optional, Tuple

import django.template
from django.template.base import FilterExpression, Node, NodeList, Parser, TextNode, Token, TokenType
from django.template.exceptions import TemplateSyntaxError
from django.template.library import parse_bits
from django.utils.safestring import SafeString, mark_safe

from django_components.app_settings import app_settings
from django_components.component import RENDERED_COMMENT_TEMPLATE, ComponentNode
from django_components.component_registry import ComponentRegistry
from django_components.component_registry import registry as component_registry
from django_components.middleware import (
    CSS_DEPENDENCY_PLACEHOLDER,
    JS_DEPENDENCY_PLACEHOLDER,
    is_dependency_middleware_active,
)
from django_components.slots import (
    IfSlotFilledConditionBranchNode,
    IfSlotFilledElseBranchNode,
    IfSlotFilledNode,
    NamedFillNode,
    SlotNode,
    _IfSlotFilledBranchNode,
    parse_slot_fill_nodes_from_component_nodelist,
)

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

    nodelist = parser.parse(parse_until=["endslot"])
    parser.delete_first_token()
    return SlotNode(
        slot_name,
        nodelist,
        is_required=is_required,
        is_default=is_default,
    )


@register.tag("fill")
def do_fill(parser: Parser, token: Token) -> NamedFillNode:
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
    nodelist = parser.parse(parse_until=["endfill"])
    parser.delete_first_token()

    return NamedFillNode(
        nodelist,
        name_fexp=FilterExpression(tgt_slot_name, tag),
        alias_fexp=alias_fexp,
    )


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
    body: NodeList = parser.parse(parse_until=["endcomponent"])
    parser.delete_first_token()
    fill_nodes = parse_slot_fill_nodes_from_component_nodelist(body, ComponentNode)
    component_node = ComponentNode(
        FilterExpression(component_name, parser),
        context_args,
        context_kwargs,
        isolated_context=isolated_context,
        fill_nodes=fill_nodes,
    )

    return component_node


def is_whitespace_node(node: Node) -> bool:
    return isinstance(node, TextNode) and node.s.isspace()


def is_whitespace_token(token: Token) -> bool:
    return token.token_type == TokenType.TEXT and not token.contents.strip()


def is_block_tag_token(token: Token, name: str) -> bool:
    return token.token_type == TokenType.BLOCK and token.split_contents()[0] == name


@register.tag(name="if_filled")
def do_if_filled_block(parser: Parser, token: Token) -> "IfSlotFilledNode":
    """
    ### Usage

    Example:

    ```
    {% if_filled <slot> (<bool>) %}
        ...
    {% elif_filled <slot> (<bool>) %}
        ...
    {% else_filled %}
        ...
    {% endif_filled %}
    ```

    Notes:

    Optional arg `<bool>` is True by default.
    If a False is provided instead, the effect is a negation of the `if_filled` check:
    The behavior is analogous to `if not is_filled <slot>`.
    This design prevents us having to define a separate `if_unfilled` tag.
    """
    bits = token.split_contents()
    starting_tag = bits[0]
    slot_name, is_positive = parse_if_filled_bits(bits)
    nodelist: NodeList = parser.parse(("elif_filled", "else_filled", "endif_filled"))
    branches: List[_IfSlotFilledBranchNode] = [
        IfSlotFilledConditionBranchNode(
            slot_name=slot_name,  # type: ignore
            nodelist=nodelist,
            is_positive=is_positive,
        )
    ]

    token = parser.next_token()

    # {% elif_filled <slot> (<is_positive>) %} (repeatable)
    while token.contents.startswith("elif_filled"):
        bits = token.split_contents()
        slot_name, is_positive = parse_if_filled_bits(bits)
        nodelist = parser.parse(("elif_filled", "else_filled", "endif_filled"))
        branches.append(
            IfSlotFilledConditionBranchNode(
                slot_name=slot_name,  # type: ignore
                nodelist=nodelist,
                is_positive=is_positive,
            )
        )

        token = parser.next_token()

    # {% else_filled %} (optional)
    if token.contents.startswith("else_filled"):
        bits = token.split_contents()
        _, _ = parse_if_filled_bits(bits)
        nodelist = parser.parse(("endif_filled",))
        branches.append(IfSlotFilledElseBranchNode(nodelist))
        token = parser.next_token()

    # {% endif_filled %}
    if token.contents != "endif_filled":
        raise TemplateSyntaxError(
            f"{{% {starting_tag} %}} missing closing {{% endif_filled %}} tag"
            f" at line {token.lineno}: '{token.contents}'"
        )

    return IfSlotFilledNode(branches)


def parse_if_filled_bits(
    bits: List[str],
) -> Tuple[Optional[str], Optional[bool]]:
    tag, args = bits[0], bits[1:]
    if tag in ("else_filled", "endif_filled"):
        if len(args) != 0:
            raise TemplateSyntaxError(f"Tag '{tag}' takes no arguments. Received '{' '.join(args)}'")
        else:
            return None, None
    if len(args) == 1:
        slot_name = args[0]
        is_positive = True
    elif len(args) == 2:
        slot_name = args[0]
        is_positive = bool_from_string(args[1])
    else:
        raise TemplateSyntaxError(
            f"{bits[0]} tag arguments '{' '.join(args)}' do not match pattern " f"'<slotname> (<is_positive>)'"
        )
    if not is_wrapped_in_quotes(slot_name):
        raise TemplateSyntaxError(f"First argument of '{bits[0]}' must be a quoted string 'literal'.")
    slot_name = strip_quotes(slot_name)
    return slot_name, is_positive


def check_for_isolated_context_keyword(bits: List[str]) -> Tuple[List[str], bool]:
    """Return True and strip the last word if token ends with 'only' keyword or if CONTEXT_BEHAVIOR is 'isolated'."""

    if bits[-1] == "only":
        return bits[:-1], True

    if app_settings.CONTEXT_BEHAVIOR == "isolated":
        return bits, True

    return bits, False


def parse_component_with_args(
    parser: Parser, bits: List[str], tag_name: str
) -> Tuple[str, List[FilterExpression], Mapping[str, FilterExpression]]:
    tag_args, tag_kwargs = parse_bits(
        parser=parser,
        bits=bits,
        params=["tag_name", "name"],
        takes_context=False,
        name=tag_name,
        varargs=True,
        varkw=[],
        defaults=None,
        kwonly=[],
        kwonly_defaults=None,
    )

    if tag_name != tag_args[0].token:
        raise RuntimeError(f"Internal error: Expected tag_name to be {tag_name}, but it was {tag_args[0].token}")
    if len(tag_args) > 1:
        # At least one position arg, so take the first as the component name
        component_name = tag_args[1].token
        context_args = tag_args[2:]
        context_kwargs = tag_kwargs
    else:  # No positional args, so look for component name as keyword arg
        try:
            component_name = tag_kwargs.pop("name").token
            context_args = []
            context_kwargs = tag_kwargs
        except IndexError:
            raise TemplateSyntaxError(f"Call the '{tag_name}' tag with a component name as the first parameter")

    return component_name, context_args, context_kwargs


def is_wrapped_in_quotes(s: str) -> bool:
    return s.startswith(('"', "'")) and s[0] == s[-1]


def strip_quotes(s: str) -> str:
    return s.strip("\"'")


def bool_from_string(s: str) -> bool:
    s = strip_quotes(s.lower())
    if s == "true":
        return True
    elif s == "false":
        return False
    else:
        raise TemplateSyntaxError(f"Expected a bool value. Received: '{s}'")
