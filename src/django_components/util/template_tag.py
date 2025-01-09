import functools
from typing import Any, Callable, Dict, List, Literal, NamedTuple, Optional, Set, Tuple, Union, cast

from django.template import NodeList
from django.template.base import Parser, Token, TokenType
from django.template.exceptions import TemplateSyntaxError

from django_components.expression import (
    DynamicFilterExpression,
    Expression,
    FilterExpression,
    Operator,
    RuntimeKwargPairs,
    RuntimeKwargPairsInput,
    RuntimeKwargs,
    RuntimeKwargsInput,
    SpreadOperator,
    is_aggregate_key,
    is_dynamic_expression,
)
from django_components.util.tag_parser import TagAttr, TagValue, parse_tag


class ParsedTag(NamedTuple):
    id: str
    name: str
    flags: Dict[str, bool]
    args: List[Expression]
    named_args: Dict[str, Expression]
    kwargs: RuntimeKwargs
    kwarg_pairs: RuntimeKwargPairs
    is_inline: bool
    parse_body: Callable[[], NodeList]


class TagArg(NamedTuple):
    name: str
    positional_only: bool


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


def parse_template_tag(
    parser: Parser,
    token: Token,
    tag_spec: TagSpec,
    tag_id: str,
) -> ParsedTag:
    tag_name, raw_args, raw_kwargs, raw_flags, is_inline = _parse_tag_preprocess(parser, token, tag_spec)

    parsed_tag = _parse_tag_process(
        parser=parser,
        tag_id=tag_id,
        tag_name=tag_name,
        tag_spec=tag_spec,
        raw_args=raw_args,
        raw_kwargs=raw_kwargs,
        raw_flags=raw_flags,
        is_inline=is_inline,
    )
    return parsed_tag


class TagKwarg(NamedTuple):
    type: Literal["kwarg", "spread"]
    key: str
    # E.g. `class` in `attrs:class="my-class"`
    inner_key: Optional[str]
    value: str


def _parse_tag_preprocess(
    parser: Parser,
    token: Token,
    tag_spec: TagSpec,
) -> Tuple[str, List[str], List[TagKwarg], Set[str], bool]:
    fix_nested_tags(parser, token)

    _, attrs = parse_tag(token.contents)

    # First token is tag name, e.g. `slot` in `{% slot <name> ... %}`
    tag_name_attr = attrs.pop(0)
    tag_name = tag_name_attr.serialize(omit_key=True)

    # Sanity check
    if tag_name != tag_spec.tag:
        raise TemplateSyntaxError(f"Start tag parser received tag '{tag_name}', expected '{tag_spec.tag}'")

    # There's 3 ways how we tell when a tag ends:
    # 1. If the tag contains `/` at the end, it's a self-closing tag (like `<div />`),
    #    and it doesn't have an end tag. In this case we strip the trailing slash.
    # Otherwise, depending on the tag spec, the tag may be:
    # 2. Block tag - With corresponding end tag, e.g. `{% endslot %}`
    # 3. Inlined tag - Without the end tag.
    last_token = attrs[-1].serialize(omit_key=True) if len(attrs) else None

    if last_token == "/":
        attrs.pop()
        is_inline = True
    else:
        is_inline = not tag_spec.end_tag

    raw_args, raw_kwargs, raw_flags = _parse_tag_input(tag_name, attrs)

    return tag_name, raw_args, raw_kwargs, raw_flags, is_inline


def _parse_tag_input(tag_name: str, attrs: List[TagAttr]) -> Tuple[List[str], List[TagKwarg], Set[str]]:
    # Given a list of attributes passed to a tag, categorise them into args, kwargs, and flags.
    # The result of this will be passed to plugins to allow them to modify the tag inputs.
    # And only once we get back the modified inputs, we will parse the data into
    # internal structures like `DynamicFilterExpression`, or `SpreadOperator`.
    #
    # NOTES:
    # - When args end, kwargs start. Positional args cannot follow kwargs
    # - There can be multiple kwargs with same keys
    # - Flags can be anywhere
    # - Each flag can be present only once
    is_args = True
    args_or_flags: List[str] = []
    kwarg_pairs: List[TagKwarg] = []
    flags = set()
    seen_spreads = 0
    for attr in attrs:
        value = attr.serialize(omit_key=True)

        # Spread
        if attr.value.spread:
            if value == "...":
                raise TemplateSyntaxError("Syntax operator is missing a value")

            kwarg = TagKwarg(type="spread", key=f"...{seen_spreads}", inner_key=None, value=value[3:])
            kwarg_pairs.append(kwarg)
            is_args = False
            seen_spreads += 1
            continue

        # Positional or flag
        elif is_args and not attr.key:
            args_or_flags.append(value)
            continue

        # Keyword
        elif attr.key:
            if is_aggregate_key(attr.key):
                key, inner_key = attr.key.split(":", 1)
            else:
                key, inner_key = attr.key, None

            kwarg = TagKwarg(type="kwarg", key=key, inner_key=inner_key, value=value)
            kwarg_pairs.append(kwarg)
            is_args = False
            continue

        # Either flag or a misplaced positional arg
        elif not is_args and not attr.key:
            # NOTE: By definition, dynamic expressions CANNOT be identifiers, because
            # they contain quotes. So we can catch those early.
            if not value.isidentifier():
                raise TemplateSyntaxError(
                    f"'{tag_name}' received positional argument '{value}' after keyword argument(s)"
                )

            # Otherwise, we assume that the token is a flag. It is up to the tag logic
            # to decide whether this is a recognized flag or a misplaced positional arg.
            if value in flags:
                raise TemplateSyntaxError(f"'{tag_name}' received flag '{value}' multiple times")

            flags.add(value)
            continue
    return args_or_flags, kwarg_pairs, flags


def _parse_tag_process(
    parser: Parser,
    tag_id: str,
    tag_name: str,
    tag_spec: TagSpec,
    raw_args: List[str],
    raw_kwargs: List[TagKwarg],
    raw_flags: Set[str],
    is_inline: bool,
) -> ParsedTag:
    seen_kwargs = set([kwarg.key for kwarg in raw_kwargs if kwarg.key and kwarg.type == "kwarg"])

    seen_regular_kwargs = set()
    seen_agg_kwargs = set()

    def check_kwarg_for_agg_conflict(kwarg: TagKwarg) -> None:
        # Skip spread operators
        if kwarg.type == "spread":
            return

        is_agg_kwarg = kwarg.inner_key
        if (
            (is_agg_kwarg and (kwarg.key in seen_regular_kwargs))
            or (not is_agg_kwarg and (kwarg.key in seen_agg_kwargs))
        ):  # fmt: skip
            raise TemplateSyntaxError(
                f"Received argument '{kwarg.key}' both as a regular input ({kwarg.key}=...)"
                f" and as an aggregate dict ('{kwarg.key}:key=...'). Must be only one of the two"
            )

        if is_agg_kwarg:
            seen_agg_kwargs.add(kwarg.key)
        else:
            seen_regular_kwargs.add(kwarg.key)

    for raw_kwarg in raw_kwargs:
        check_kwarg_for_agg_conflict(raw_kwarg)

    # Params that may be passed as positional args
    pos_params: List[TagArg] = [
        *[TagArg(name=name, positional_only=True) for name in (tag_spec.positional_only_args or [])],
        *[TagArg(name=name, positional_only=False) for name in (tag_spec.pos_or_keyword_args or [])],
    ]

    args: List[Expression] = []
    # For convenience, allow to access named args by their name instead of index
    named_args: Dict[str, Expression] = {}
    kwarg_pairs: RuntimeKwargPairsInput = []
    flags = set()
    # When we come across a flag within positional args, we need to remember
    # the offset, so we can correctly assign the args to the correct params
    flag_offset = 0

    for index, arg_input in enumerate(raw_args):
        # Flags may be anywhere, so we need to check if the arg is a flag
        if tag_spec.flags and arg_input in tag_spec.flags:
            if arg_input in raw_flags or arg_input in flags:
                raise TemplateSyntaxError(f"'{tag_name}' received flag '{arg_input}' multiple times")
            flags.add(arg_input)
            flag_offset += 1
            continue

        # Allow to use dynamic expressions as args, e.g. `"{{ }}"`
        if is_dynamic_expression(arg_input):
            arg = DynamicFilterExpression(parser, arg_input)
        else:
            arg = FilterExpression(arg_input, parser)

        if (index - flag_offset) >= len(pos_params):
            if tag_spec.positional_args_allow_extra:
                args.append(arg)
                continue
            else:
                # Allow only as many positional args as given
                raise TemplateSyntaxError(
                    f"Tag '{tag_name}' received too many positional arguments: {raw_args[index:]}"
                )

        param = pos_params[index - flag_offset]
        if param.positional_only:
            args.append(arg)
            named_args[param.name] = arg
        else:
            kwarg = TagKwarg(type="kwarg", key=param.name, inner_key=None, value=arg_input)
            check_kwarg_for_agg_conflict(kwarg)
            if param.name in seen_kwargs:
                raise TemplateSyntaxError(
                    f"'{tag_name}' received argument '{param.name}' both as positional and keyword argument"
                )

            kwarg_pairs.append((param.name, arg))

    if len(raw_args) - flag_offset < len(tag_spec.positional_only_args or []):
        raise TemplateSyntaxError(
            f"Tag '{tag_name}' received too few positional arguments. "
            f"Expected {len(tag_spec.positional_only_args or [])}, got {len(raw_args) - flag_offset}"
        )

    for kwarg_input in raw_kwargs:
        # Allow to use dynamic expressions with spread operator, e.g.
        # `..."{{ }}"` or as kwargs values `key="{{ }}"`
        if is_dynamic_expression(kwarg_input.value):
            expr: Union[Expression, Operator] = DynamicFilterExpression(parser, kwarg_input.value)
        else:
            expr = FilterExpression(kwarg_input.value, parser)

        if kwarg_input.type == "spread":
            expr = SpreadOperator(expr)

        if kwarg_input.inner_key:
            full_key = f"{kwarg_input.key}:{kwarg_input.inner_key}"
        else:
            full_key = kwarg_input.key

        kwarg_pairs.append((full_key, expr))

    # Flags
    flags_dict: Dict[str, bool] = {
        # Base state, as defined in the tag spec
        **{flag: False for flag in (tag_spec.flags or [])},
        # Flags found among positional args
        **{flag: True for flag in flags},
    }

    # Flags found among kwargs
    for flag in raw_flags:
        if flag in flags:
            raise TemplateSyntaxError(f"'{tag_name}' received flag '{flag}' multiple times")
        if flag not in (tag_spec.flags or []):
            raise TemplateSyntaxError(f"'{tag_name}' received unknown flag '{flag}'")
        flags.add(flag)
        flags_dict[flag] = True

    # Validate that there are no name conflicts between kwargs and flags
    if flags.intersection(seen_kwargs):
        raise TemplateSyntaxError(
            f"'{tag_name}' received flags that conflict with keyword arguments: {flags.intersection(seen_kwargs)}"
        )

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
        flags=flags_dict,
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


def fix_nested_tags(parser: Parser, block_token: Token) -> None:
    # Since the nested tags MUST be wrapped in quotes, e.g.
    # `{% component 'test' "{% lorem var_a w %}" %}`
    # `{% component 'test' key="{% lorem var_a w %}" %}`
    #
    # We can parse the tag's tokens so we can find the last one, and so we consider
    # the unclosed `{%` only for the last bit.
    _, attrs = parse_tag(block_token.contents)

    # If there are no attributes, then there are no nested tags
    if not attrs:
        return

    last_attr = attrs[-1]

    # TODO: Currently, using a nested template inside a list or dict
    #    e.g. `{% component ... key=["{% nested %}"] %}` is NOT supported.
    #    Hence why we leave if value is not "simple" (which means the value is list or dict).
    if last_attr.value.type != "simple":
        return

    last_attr_value = cast(TagValue, last_attr.value.entries[0])
    last_token = last_attr_value.parts[-1]

    # User probably forgot to wrap the nested tag in quotes, or this is the end of the input.
    # `{% component ... key={% nested %} %}`
    # `{% component ... key= %}`
    if not last_token.value:
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
        (last_token.value.count("{%") > last_token.value.count("%}"))
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
        or (last_token.value in ("'{", '"{'))
    )

    # There is 3 double quotes, but if the contents get split at the first `%}`
    # then there will be a single unclosed double quote in the last bit.
    has_unclosed_quote = not last_token.quoted and last_token.value and last_token.value[0] in ('"', "'")

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
