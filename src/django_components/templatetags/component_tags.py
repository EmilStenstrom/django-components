from typing import TYPE_CHECKING, Callable, Dict, List, NamedTuple, Optional, Set, Tuple, Union

import django.template
from django.template.base import FilterExpression, NodeList, Parser, Token
from django.template.exceptions import TemplateSyntaxError
from django.utils.safestring import SafeString, mark_safe

from django_components.app_settings import ContextBehavior, app_settings
from django_components.attributes import HtmlAttrsNode
from django_components.component import RENDERED_COMMENT_TEMPLATE, ComponentNode
from django_components.component_registry import ComponentRegistry
from django_components.component_registry import registry as component_registry
from django_components.expression import AggregateFilterExpression, Expression, resolve_string
from django_components.logger import trace_msg
from django_components.middleware import (
    CSS_DEPENDENCY_PLACEHOLDER,
    JS_DEPENDENCY_PLACEHOLDER,
    is_dependency_middleware_active,
)
from django_components.provide import ProvideNode
from django_components.slots import FillNode, SlotNode, parse_slot_fill_nodes_from_component_nodelist
from django_components.tag_formatter import get_tag_formatter
from django_components.template_parser import is_aggregate_key, parse_bits, process_aggregate_kwargs
from django_components.utils import gen_id, is_str_wrapped_in_quotes

if TYPE_CHECKING:
    from django_components.component import Component


# NOTE: Variable name `register` is required by Django to recognize this as a template tag library
# See https://docs.djangoproject.com/en/dev/howto/custom-template-tags
register = django.template.Library()


SLOT_REQUIRED_OPTION_KEYWORD = "required"
SLOT_DEFAULT_OPTION_KEYWORD = "default"
SLOT_DATA_ATTR = "data"
SLOT_DEFAULT_ATTR = "default"


def _get_components_from_registry(registry: ComponentRegistry) -> List["Component"]:
    """Returns a list unique components from the registry."""

    unique_component_classes = set(registry.all().values())

    components = []
    for component_class in unique_component_classes:
        components.append(component_class(component_class.__name__))

    return components


def _get_components_from_preload_str(preload_str: str) -> List["Component"]:
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
def component_dependencies(preload: str = "") -> SafeString:
    """Marks location where CSS link and JS script tags should be rendered."""

    if is_dependency_middleware_active():
        preloaded_dependencies = []
        for component in _get_components_from_preload_str(preload):
            preloaded_dependencies.append(RENDERED_COMMENT_TEMPLATE.format(name=component.registered_name))
        return mark_safe("\n".join(preloaded_dependencies) + CSS_DEPENDENCY_PLACEHOLDER + JS_DEPENDENCY_PLACEHOLDER)
    else:
        rendered_dependencies = []
        for component in _get_components_from_registry(component_registry):
            rendered_dependencies.append(component.render_dependencies())

        return mark_safe("\n".join(rendered_dependencies))


@register.simple_tag(name="component_css_dependencies")
def component_css_dependencies(preload: str = "") -> SafeString:
    """Marks location where CSS link tags should be rendered."""

    if is_dependency_middleware_active():
        preloaded_dependencies = []
        for component in _get_components_from_preload_str(preload):
            preloaded_dependencies.append(RENDERED_COMMENT_TEMPLATE.format(name=component.registered_name))
        return mark_safe("\n".join(preloaded_dependencies) + CSS_DEPENDENCY_PLACEHOLDER)
    else:
        rendered_dependencies = []
        for component in _get_components_from_registry(component_registry):
            rendered_dependencies.append(component.render_css_dependencies())

        return mark_safe("\n".join(rendered_dependencies))


@register.simple_tag(name="component_js_dependencies")
def component_js_dependencies(preload: str = "") -> SafeString:
    """Marks location where JS script tags should be rendered."""

    if is_dependency_middleware_active():
        preloaded_dependencies = []
        for component in _get_components_from_preload_str(preload):
            preloaded_dependencies.append(RENDERED_COMMENT_TEMPLATE.format(name=component.registered_name))
        return mark_safe("\n".join(preloaded_dependencies) + JS_DEPENDENCY_PLACEHOLDER)
    else:
        rendered_dependencies = []
        for component in _get_components_from_registry(component_registry):
            rendered_dependencies.append(component.render_js_dependencies())

        return mark_safe("\n".join(rendered_dependencies))


@register.tag("slot")
def slot(parser: Parser, token: Token) -> SlotNode:
    bits = token.split_contents()
    tag = _parse_tag(
        "slot",
        parser,
        bits,
        params=["name"],
        flags=[SLOT_DEFAULT_OPTION_KEYWORD, SLOT_REQUIRED_OPTION_KEYWORD],
        keywordonly_kwargs=True,
        repeatable_kwargs=False,
        end_tag="endslot",
    )
    data = _parse_slot_args(parser, tag)

    trace_msg("PARSE", "SLOT", data.name, tag.id)

    body = tag.parse_body()
    slot_node = SlotNode(
        name=data.name,
        nodelist=body,
        is_required=tag.flags[SLOT_REQUIRED_OPTION_KEYWORD],
        is_default=tag.flags[SLOT_DEFAULT_OPTION_KEYWORD],
        node_id=tag.id,
        slot_kwargs=tag.kwargs,
    )

    trace_msg("PARSE", "SLOT", data.name, tag.id, "...Done!")
    return slot_node


@register.tag("fill")
def fill(parser: Parser, token: Token) -> FillNode:
    """
    Block tag whose contents 'fill' (are inserted into) an identically named
    'slot'-block in the component template referred to by a parent component.
    It exists to make component nesting easier.

    This tag is available only within a {% component %}..{% endcomponent %} block.
    Runtime checks should prohibit other usages.
    """
    bits = token.split_contents()
    tag = _parse_tag(
        "fill",
        parser,
        bits,
        params=["name"],
        keywordonly_kwargs=[SLOT_DATA_ATTR, SLOT_DEFAULT_ATTR],
        repeatable_kwargs=False,
        end_tag="endfill",
    )
    data = _parse_fill_args(parser, tag)

    trace_msg("PARSE", "FILL", str(data.slot_name), tag.id)

    body = tag.parse_body()
    fill_node = FillNode(
        nodelist=body,
        name_fexp=data.slot_name,
        slot_default_var_fexp=data.slot_default_var,
        slot_data_var_fexp=data.slot_data_var,
        node_id=tag.id,
    )

    trace_msg("PARSE", "FILL", str(data.slot_name), tag.id, "...Done!")
    return fill_node


def component(parser: Parser, token: Token, tag_name: str) -> ComponentNode:
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

    # Let the TagFormatter pre-process the tokens
    formatter = get_tag_formatter()
    result = formatter.parse([*bits])
    end_tag = formatter.end_tag(result.component_name)

    # NOTE: The tokens returned from TagFormatter.parse do NOT include the tag itself
    bits = [bits[0], *result.tokens]

    tag = _parse_tag(
        tag_name,
        parser,
        bits,
        params=True,  # Allow many args
        flags=["only"],
        keywordonly_kwargs=True,
        repeatable_kwargs=False,
        end_tag=end_tag,
    )
    data = _parse_component_args(parser, tag)

    trace_msg("PARSE", "COMP", result.component_name, tag.id)

    body = tag.parse_body()
    fill_nodes = parse_slot_fill_nodes_from_component_nodelist(body, ComponentNode)

    # Tag all fill nodes as children of this particular component instance
    for node in fill_nodes:
        trace_msg("ASSOC", "FILL", node.name_fexp, node.node_id, component_id=tag.id)
        node.component_id = tag.id

    component_node = ComponentNode(
        name=result.component_name,
        context_args=tag.args,
        context_kwargs=tag.kwargs,
        isolated_context=data.isolated_context,
        fill_nodes=fill_nodes,
        component_id=tag.id,
    )

    trace_msg("PARSE", "COMP", result.component_name, tag.id, "...Done!")
    return component_node


@register.tag("provide")
def provide(parser: Parser, token: Token) -> ProvideNode:
    # e.g. {% provide <name> key=val key2=val2 %}
    bits = token.split_contents()
    tag = _parse_tag(
        "provide",
        parser,
        bits,
        params=["name"],
        flags=[],
        keywordonly_kwargs=True,
        repeatable_kwargs=False,
        end_tag="endprovide",
    )
    data = _parse_provide_args(parser, tag)

    trace_msg("PARSE", "PROVIDE", data.key, tag.id)

    body = tag.parse_body()
    slot_node = ProvideNode(
        name=data.key,
        nodelist=body,
        node_id=tag.id,
        provide_kwargs=tag.kwargs,
    )

    trace_msg("PARSE", "PROVIDE", data.key, tag.id, "...Done!")
    return slot_node


@register.tag("html_attrs")
def html_attrs(parser: Parser, token: Token) -> HtmlAttrsNode:
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

    tag = _parse_tag(
        "html_attrs",
        parser,
        bits,
        params=["attrs", "defaults"],
        optional_params=["attrs", "defaults"],
        flags=[],
        keywordonly_kwargs=True,
        repeatable_kwargs=True,
    )

    return HtmlAttrsNode(
        attributes=tag.kwargs.get("attrs"),
        defaults=tag.kwargs.get("defaults"),
        kwargs=[(key, val) for key, val in tag.kwarg_pairs if key != "attrs" and key != "defaults"],
    )


class ParsedTag(NamedTuple):
    id: str
    name: str
    bits: List[str]
    flags: Dict[str, bool]
    args: List[FilterExpression]
    named_args: Dict[str, FilterExpression]
    kwargs: Dict[str, Expression]
    kwarg_pairs: List[Tuple[str, Expression]]
    is_inline: bool
    parse_body: Callable[[], NodeList]


def _parse_tag(
    tag: str,
    parser: Parser,
    bits: List[str],
    params: Union[List[str], bool] = False,
    flags: Optional[List[str]] = None,
    end_tag: Optional[str] = None,
    optional_params: Optional[List[str]] = None,
    keywordonly_kwargs: Optional[Union[bool, List[str]]] = False,
    repeatable_kwargs: Optional[Union[bool, List[str]]] = False,
) -> ParsedTag:
    # Use a unique ID to be able to tie the fill nodes with components and slots
    # NOTE: MUST be called BEFORE `parse_body()` to ensure predictable numbering
    tag_id = gen_id()

    params = params or []

    # e.g. {% slot <name> ... %}
    tag_name, *bits = bits
    if tag_name != tag:
        raise TemplateSyntaxError(f"Start tag parser received tag '{tag_name}', expected '{tag}'")

    # Decide if the template tag is inline or block and strip the trailing slash
    last_token = bits[-1] if len(bits) else None
    if last_token == "/":
        bits.pop()
        is_inline = True
    else:
        # If no end tag was given, we assume that the tag is inline-only
        is_inline = not end_tag

    parsed_flags = {flag: False for flag in (flags or [])}
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

    for bit in bits:
        # Extract flags, which are like keywords but without the value part
        if bit in parsed_flags:
            parsed_flags[bit] = True
            continue
        else:
            bits_without_flags.append(bit)

        # Record which kwargs we've seen, to detect if kwargs were passed in
        # as both aggregate and regular kwargs
        if "=" in bit:
            key = bit.split("=")[0]

            # Also pick up on aggregate keys like `attr:key=val`
            if is_aggregate_key(key):
                key = key.split(":")[0]
                mark_kwarg_key(key, True)
            else:
                mark_kwarg_key(key, False)

    bits = bits_without_flags

    # To support optional args, we need to convert these to kwargs, so `parse_bits`
    # can handle them. So we assign the keys to matched positional args,
    # and then move the kwarg AFTER the pos args.
    #
    # TODO: This following section should live in `parse_bits`, but I don't want to
    # modify it much to maintain some sort of compatibility with Django's version of
    # `parse_bits`.
    # Ideally, Django's parser would be expanded to support our use cases.
    if params != True:  # noqa F712
        params_to_sort = [param for param in params if param not in seen_kwargs]
        new_args = []
        new_params = []
        new_kwargs = []
        for index, bit in enumerate(bits):
            if "=" in bit or not len(params_to_sort):
                # Pass all remaining bits (including current one) as kwargs
                new_kwargs.extend(bits[index:])
                break

            param = params_to_sort.pop(0)
            if optional_params and param in optional_params:
                mark_kwarg_key(param, False)
                new_kwargs.append(f"{param}={bit}")
                continue
            new_args.append(bit)
            new_params.append(param)

        bits = [*new_args, *new_kwargs]
        params = [*new_params, *params_to_sort]

        # Remove any remaining optional positional args if they were not given
        if optional_params:
            params = [param for param in params_to_sort if param not in optional_params]

    # Parse args/kwargs that will be passed to the fill
    args, raw_kwarg_pairs = parse_bits(
        parser=parser,
        bits=bits,
        params=[] if isinstance(params, bool) else params,
        name=tag_name,
    )

    # Post-process args/kwargs - Mark special cases like aggregate dicts
    # or dynamic expressions
    pre_aggregate_kwargs: Dict[str, FilterExpression] = {}
    kwarg_pairs: List[Tuple[str, Expression]] = []
    for key, val in raw_kwarg_pairs:
        # NOTE: If a tag allows mutliple kwargs, and we provide a same aggregate key
        # multiple times (e.g. `attr:class="hidden" and `attr:class="another"`), then
        # we take only the last instance.
        if is_aggregate_key(key):
            pre_aggregate_kwargs[key] = val
        else:
            kwarg_pairs.append((key, val))
    aggregate_kwargs: Dict[str, Dict[str, FilterExpression]] = process_aggregate_kwargs(pre_aggregate_kwargs)

    for key, agg_dict in aggregate_kwargs.items():
        entry = (key, AggregateFilterExpression(agg_dict))
        kwarg_pairs.append(entry)

    # Allow only as many positional args as given
    if params != True and len(args) > len(params):  # noqa F712
        raise TemplateSyntaxError(f"Tag '{tag_name}' received unexpected positional arguments: {args[len(params):]}")

    # For convenience, allow to access named args by their name instead of index
    if params != True:  # noqa F712
        named_args = {param: args[index] for index, param in enumerate(params)}
    else:
        named_args = {}

    # Validate kwargs
    kwargs: Dict[str, Expression] = {}
    extra_keywords: Set[str] = set()
    for key, val in kwarg_pairs:
        # Check if key allowed
        if not keywordonly_kwargs:
            is_key_allowed = False
        else:
            is_key_allowed = keywordonly_kwargs == True or key in keywordonly_kwargs  # noqa: E712
        if not is_key_allowed:
            extra_keywords.add(key)

        # Check for repeated keys
        if key in kwargs:
            if not repeatable_kwargs:
                is_key_repeatable = False
            else:
                is_key_repeatable = repeatable_kwargs == True or key in repeatable_kwargs  # noqa: E712
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
        kwargs=kwargs,
        kwarg_pairs=kwarg_pairs,
        # NOTE: We defer parsing of the body, so we have the chance to call the tracing
        # loggers before the parsing. This is because, if the body contains any other
        # tags, it will trigger their tag handlers. So the code called AFTER
        # `parse_body()` is already after all the nested tags were processed.
        parse_body=lambda: _parse_tag_body(parser, end_tag, is_inline) if end_tag else NodeList(),
        is_inline=is_inline,
    )


def _parse_tag_body(parser: Parser, end_tag: str, inline: bool) -> NodeList:
    if inline:
        body = NodeList()
    else:
        body = parser.parse(parse_until=[end_tag])
        parser.delete_first_token()
    return body


class ParsedComponentTag(NamedTuple):
    isolated_context: bool


def _parse_component_args(
    parser: Parser,
    tag: ParsedTag,
) -> ParsedComponentTag:
    # Check for isolated context keyword
    isolated_context = tag.flags["only"] or app_settings.CONTEXT_BEHAVIOR == ContextBehavior.ISOLATED

    return ParsedComponentTag(isolated_context=isolated_context)


class ParsedSlotTag(NamedTuple):
    name: str


def _parse_slot_args(
    parser: Parser,
    tag: ParsedTag,
) -> ParsedSlotTag:
    slot_name = tag.named_args["name"].token
    if not is_str_wrapped_in_quotes(slot_name):
        raise TemplateSyntaxError(f"'{tag.name}' name must be a string 'literal', got {slot_name}.")

    slot_name = resolve_string(slot_name, parser)

    return ParsedSlotTag(name=slot_name)


class ParsedFillTag(NamedTuple):
    slot_name: FilterExpression
    slot_default_var: Optional[FilterExpression]
    slot_data_var: Optional[FilterExpression]


def _parse_fill_args(
    parser: Parser,
    tag: ParsedTag,
) -> ParsedFillTag:
    slot_name_fexp = tag.named_args["name"]

    # Extract known kwargs
    slot_data_var_fexp: Optional[FilterExpression] = tag.kwargs.get(SLOT_DATA_ATTR)
    if slot_data_var_fexp and not is_str_wrapped_in_quotes(slot_data_var_fexp.token):
        raise TemplateSyntaxError(
            f"Value of '{SLOT_DATA_ATTR}' in '{tag.name}' tag must be a string literal, got '{slot_data_var_fexp}'"
        )

    slot_default_var_fexp: Optional[FilterExpression] = tag.kwargs.get(SLOT_DEFAULT_ATTR)
    if slot_default_var_fexp and not is_str_wrapped_in_quotes(slot_default_var_fexp.token):
        raise TemplateSyntaxError(
            f"Value of '{SLOT_DEFAULT_ATTR}' in '{tag.name}' tag must be a string literal,"
            f" got '{slot_default_var_fexp}'"
        )

    # data and default cannot be bound to the same variable
    if slot_data_var_fexp and slot_default_var_fexp and slot_data_var_fexp.token == slot_default_var_fexp.token:
        raise TemplateSyntaxError(
            f"'{tag.name}' received the same string for slot default ({SLOT_DEFAULT_ATTR}=...)"
            f" and slot data ({SLOT_DATA_ATTR}=...)"
        )

    return ParsedFillTag(
        slot_name=slot_name_fexp,
        slot_default_var=slot_default_var_fexp,
        slot_data_var=slot_data_var_fexp,
    )


class ParsedProvideTag(NamedTuple):
    key: str


def _parse_provide_args(
    parser: Parser,
    tag: ParsedTag,
) -> ParsedProvideTag:
    provide_key = tag.named_args["name"].token
    if not is_str_wrapped_in_quotes(provide_key):
        raise TemplateSyntaxError(f"'{tag.name}' key must be a string 'literal'.")

    provide_key = resolve_string(provide_key, parser)

    return ParsedProvideTag(key=provide_key)
