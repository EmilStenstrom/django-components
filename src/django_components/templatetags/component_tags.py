from typing import TYPE_CHECKING, Callable, Dict, List, NamedTuple, Optional, Set, Union

import django.template
from django.template.base import NodeList, Parser, Token, TokenType
from django.template.exceptions import TemplateSyntaxError
from django.utils.safestring import SafeString, mark_safe
from django.utils.text import smart_split

from django_components.attributes import HTML_ATTRS_ATTRS_KEY, HTML_ATTRS_DEFAULTS_KEY, HtmlAttrsNode
from django_components.component import COMP_ONLY_FLAG, RENDERED_COMMENT_TEMPLATE, ComponentNode
from django_components.component_registry import ComponentRegistry
from django_components.component_registry import registry as component_registry
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
from django_components.logger import trace_msg
from django_components.middleware import (
    CSS_DEPENDENCY_PLACEHOLDER,
    JS_DEPENDENCY_PLACEHOLDER,
    is_dependency_middleware_active,
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
    parse_slot_fill_nodes_from_component_nodelist,
)
from django_components.tag_formatter import get_tag_formatter
from django_components.template_parser import parse_bits
from django_components.utils import gen_id

if TYPE_CHECKING:
    from django_components.component import Component


# NOTE: Variable name `register` is required by Django to recognize this as a template tag library
# See https://docs.djangoproject.com/en/dev/howto/custom-template-tags
register = django.template.Library()


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
    tag = _parse_tag(
        "slot",
        parser,
        token,
        params=[SLOT_NAME_KWARG],
        optional_params=[SLOT_NAME_KWARG],
        flags=[SLOT_DEFAULT_KEYWORD, SLOT_REQUIRED_KEYWORD],
        keywordonly_kwargs=True,
        repeatable_kwargs=False,
        end_tag="endslot",
    )

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
def fill(parser: Parser, token: Token) -> FillNode:
    """
    Block tag whose contents 'fill' (are inserted into) an identically named
    'slot'-block in the component template referred to by a parent component.
    It exists to make component nesting easier.

    This tag is available only within a {% component %}..{% endcomponent %} block.
    Runtime checks should prohibit other usages.
    """
    tag = _parse_tag(
        "fill",
        parser,
        token,
        params=[SLOT_NAME_KWARG],
        optional_params=[SLOT_NAME_KWARG],
        keywordonly_kwargs=[SLOT_DATA_KWARG, SLOT_DEFAULT_KWARG],
        repeatable_kwargs=False,
        end_tag="endfill",
    )

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


def component(parser: Parser, token: Token, registry: ComponentRegistry, tag_name: str) -> ComponentNode:
    """
    To give the component access to the template context:
        ```#!htmldjango {% component "name" positional_arg keyword_arg=value ... %}```

    To render the component in an isolated context:
        ```#!htmldjango {% component "name" positional_arg keyword_arg=value ... only %}```

    Positional and keyword arguments can be literals or template variables.
    The component name must be a single- or double-quotes string and must
    be either the first positional argument or, if there are no positional
    arguments, passed as 'name'.
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
        tag_name,
        parser,
        token,
        params=[],
        extra_params=True,  # Allow many args
        flags=[COMP_ONLY_FLAG],
        keywordonly_kwargs=True,
        repeatable_kwargs=False,
        end_tag=end_tag,
    )

    # Check for isolated context keyword
    isolated_context = tag.flags[COMP_ONLY_FLAG]

    trace_msg("PARSE", "COMP", result.component_name, tag.id)

    body = tag.parse_body()
    fill_nodes = parse_slot_fill_nodes_from_component_nodelist(tuple(body), ignored_nodes=(ComponentNode,))

    # Tag all fill nodes as children of this particular component instance
    for node in fill_nodes:
        trace_msg("ASSOC", "FILL", node.trace_id, node.node_id, component_id=tag.id)
        node.component_id = tag.id

    component_node = ComponentNode(
        name=result.component_name,
        args=tag.args,
        kwargs=tag.kwargs,
        isolated_context=isolated_context,
        fill_nodes=fill_nodes,
        node_id=tag.id,
        registry=registry,
    )

    trace_msg("PARSE", "COMP", result.component_name, tag.id, "...Done!")
    return component_node


@register.tag("provide")
def provide(parser: Parser, token: Token) -> ProvideNode:
    # e.g. {% provide <name> key=val key2=val2 %}
    tag = _parse_tag(
        "provide",
        parser,
        token,
        params=[PROVIDE_NAME_KWARG],
        optional_params=[PROVIDE_NAME_KWARG],
        flags=[],
        keywordonly_kwargs=True,
        repeatable_kwargs=False,
        end_tag="endprovide",
    )

    name_kwarg = tag.kwargs.kwargs.get(PROVIDE_NAME_KWARG, None)
    trace_id = f"provide-id-{tag.id} ({name_kwarg})" if name_kwarg else f"fill-id-{tag.id}"

    trace_msg("PARSE", "PROVIDE", trace_id, tag.id)

    body = tag.parse_body()
    slot_node = ProvideNode(
        nodelist=body,
        node_id=tag.id,
        kwargs=tag.kwargs,
        trace_id=trace_id,
    )

    trace_msg("PARSE", "PROVIDE", trace_id, tag.id, "...Done!")
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
    ```htmldjango
    {% html_attrs attrs defaults:class="default-class" class="extra-class" data-id="123" %}
    ```
    """
    tag = _parse_tag(
        "html_attrs",
        parser,
        token,
        params=[HTML_ATTRS_ATTRS_KEY, HTML_ATTRS_DEFAULTS_KEY],
        optional_params=[HTML_ATTRS_ATTRS_KEY, HTML_ATTRS_DEFAULTS_KEY],
        flags=[],
        keywordonly_kwargs=True,
        repeatable_kwargs=True,
    )

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
    tag: str,
    parser: Parser,
    token: Token,
    params: Optional[List[str]] = None,
    extra_params: bool = False,
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

    _fix_nested_tags(parser, token)

    # e.g. {% slot <name> ... %}
    tag_name, *bits = token.split_contents()
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
    raw_args, raw_kwarg_pairs = parse_bits(
        parser=parser,
        bits=bits,
        params=[] if extra_params else params,
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
    if not extra_params and len(args) > len(params):  # noqa F712
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
        if not keywordonly_kwargs:
            is_key_allowed = False
        else:
            is_key_allowed = keywordonly_kwargs == True or key in keywordonly_kwargs  # noqa: E712
        if not is_key_allowed:
            is_optional = key in optional_params if optional_params else False
            if not is_optional:
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
        kwargs=RuntimeKwargs(kwargs),
        kwarg_pairs=RuntimeKwargPairs(kwarg_pairs),
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


def _fix_nested_tags(parser: Parser, block_token: Token) -> None:
    # When our template tag contains a nested tag, e.g.:
    # `{% component 'test' "{% lorem var_a w %}"`
    #
    # Django parses this into:
    # `TokenType.BLOCK: 'component 'test'     "{% lorem var_a w'`
    #
    # Above you can see that the token ends at the end of the NESTED tag,
    # and includes `{%`. So that's what we use to identify if we need to fix
    # nested tags or not.
    has_unclosed_tag = block_token.contents.count("{%") > block_token.contents.count("%}")

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
    # There is 3 double quotes, but if the contents get split at the first `%}`
    # then there will be a single unclosed double quote in the last bit.
    # Hence, for this we use Django's `smart_split()`, which can detect quoted text.
    last_bit = list(smart_split(block_token.contents))[-1]
    has_unclosed_quote = last_bit.count("'") % 2 or last_bit.count('"') % 2

    needs_fixing = has_unclosed_tag or has_unclosed_quote

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
