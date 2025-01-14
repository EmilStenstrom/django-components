import functools
import inspect
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Mapping, NamedTuple, Optional, Set, Tuple, cast

from django.template import Context, NodeList
from django.template.base import Parser, Token, TokenType
from django.template.exceptions import TemplateSyntaxError

from django_components.expression import process_aggregate_kwargs
from django_components.util.tag_parser import TagAttr, TagValue, parse_tag


@dataclass
class TagSpec:
    """Definition of args, kwargs, flags, etc, for a template tag."""

    signature: inspect.Signature
    """Input to the tag as a Python function signature."""
    tag: str
    """Tag name. E.g. `"slot"` means the tag is written like so `{% slot ... %}`"""
    end_tag: Optional[str] = None
    """
    End tag.

    E.g. `"endslot"` means anything between the start tag and `{% endslot %}`
    is considered the slot's body.
    """
    flags: Optional[List[str]] = None
    """
    List of allowed flags.

    Flags are like kwargs, but without the value part. E.g. in `{% mytag only required %}`:
    - `only` and `required` are treated as `only=True` and `required=True` if present
    - and treated as `only=False` and `required=False` if omitted
    """

    def copy(self) -> "TagSpec":
        sig_parameters_copy = [param.replace() for param in self.signature.parameters.values()]
        signature = inspect.Signature(sig_parameters_copy)
        flags = self.flags.copy() if self.flags else None
        return self.__class__(
            signature=signature,
            tag=self.tag,
            end_tag=self.end_tag,
            flags=flags,
        )

    # For details see https://github.com/EmilStenstrom/django-components/pull/902
    def validate_params(self, params: List["TagParam"]) -> Tuple[List[Any], Dict[str, Any]]:
        """
        Validates a list of TagParam objects against this tag spec's function signature.

        The validation preserves the order of parameters as they appeared in the template.

        Args:
            params: List of TagParam objects representing the parameters as they appeared
                   in the template tag.

        Returns:
            A tuple of (args, kwargs) containing the validated parameters.

        Raises:
            TypeError: If the parameters don't match the tag spec's rules.
        """

        # Create a function with this signature that captures the input and sorts
        # it into args and kwargs
        def validator(*args: Any, **kwargs: Any) -> Tuple[List[Any], Dict[str, Any]]:
            # Let Python do the signature validation
            bound = self.signature.bind(*args, **kwargs)
            bound.apply_defaults()

            # Extract positional args
            pos_args: List[Any] = []
            for name, param in self.signature.parameters.items():
                # Case: `name` (positional)
                if param.kind == inspect.Parameter.POSITIONAL_ONLY:
                    pos_args.append(bound.arguments[name])
                # Case: `*args`
                elif param.kind == inspect.Parameter.VAR_POSITIONAL:
                    pos_args.extend(bound.arguments[name])

            # Extract kwargs
            kw_args: Dict[str, Any] = {}
            for name, param in self.signature.parameters.items():
                # Case: `name=...`
                if param.kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY):
                    if name in bound.arguments:
                        kw_args[name] = bound.arguments[name]
                # Case: `**kwargs`
                elif param.kind == inspect.Parameter.VAR_KEYWORD:
                    kw_args.update(bound.arguments[name])

            return pos_args, kw_args

        # Set the signature on the function
        validator.__signature__ = self.signature  # type: ignore[attr-defined]

        call_args = []
        call_kwargs = []
        for param in params:
            if param.key is None:
                call_args.append(param.value)
            else:
                call_kwargs.append({param.key: param.value})

        # Call the validator with our args and kwargs, in such a way to
        # let the Python interpreter validate on repeated kwargs.
        #
        # E.g. `args, kwargs = validator(*call_args, **call_kwargs[0], **call_kwargs[1])`
        #
        # NOTE: Although we use `exec()` here, it's safe, because we control the input -
        #       we pass in only the list index.
        validator_call_script = "args, kwargs = validator(*call_args, "
        for kw_index, _ in enumerate(call_kwargs):
            validator_call_script += f"**call_kwargs[{kw_index}], "
        validator_call_script += ")"

        try:
            # Create function namespace
            namespace: Dict[str, Any] = {"validator": validator, "call_args": call_args, "call_kwargs": call_kwargs}
            exec(validator_call_script, namespace)
            new_args, new_kwargs = namespace["args"], namespace["kwargs"]
            return new_args, new_kwargs
        except TypeError as e:
            # Enhance the error message
            raise TypeError(f"Invalid parameters for tag '{self.tag}': {str(e)}") from None


def with_tag_spec(tag_spec: TagSpec) -> Callable:
    """
    Decorator that binds a `tag_spec` to a template tag function,
    there's a single source of truth for the tag spec, while also:

    1. Making the tag spec available inside the tag function as `tag_spec`.
    2. Making the tag spec accessible from outside as `_tag_spec` for documentation generation.
    """

    def decorator(fn: Callable) -> Any:
        fn._tag_spec = tag_spec  # type: ignore[attr-defined]

        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return fn(*args, **kwargs, tag_spec=tag_spec)

        return wrapper

    return decorator


@dataclass
class TagParam:
    """
    TagParam is practically what `TagAttr` gets resolved to.

    While TagAttr represents an item within template tag call, e.g.:

    {% component key=value ... %}

    TagParam represents an arg or kwarg that was resolved from TagAttr, and will
    be passed to the tag function. E.g.:

    component(key="value", ...)
    """

    # E.g. `attrs:class` in `attrs:class="my-class"`
    key: Optional[str]
    # E.g. `"my-class"` in `attrs:class="my-class"`
    value: Any


class TagParams(NamedTuple):
    """
    TagParams holds the parsed tag attributes and the tag spec, so that, at render time,
    when we are able to resolve the tag inputs with the given Context, we are also able to validate
    the inputs against the tag spec.

    This is done so that the tag's public API (as defined in the tag spec) can be defined
    next to the tag implementation. Otherwise the input validation would have to be defined by
    the internal `Node` classes.
    """

    params: List[TagAttr]
    tag_spec: TagSpec

    def resolve(self, context: Context) -> Tuple[List[Any], Dict[str, Any]]:
        # First, resolve any spread operators. Spreads can introduce both positional
        # args (e.g. `*args`) and kwargs (e.g. `**kwargs`).
        resolved_params: List[TagParam] = []
        for param in self.params:
            resolved = param.value.resolve(context)

            if param.value.spread:
                if param.key:
                    raise ValueError(f"Cannot spread a value onto a key: {param.key}")

                if isinstance(resolved, Mapping):
                    for key, value in resolved.items():
                        resolved_params.append(TagParam(key=key, value=value))
                elif isinstance(resolved, Iterable):
                    for value in resolved:
                        resolved_params.append(TagParam(key=None, value=value))
                else:
                    raise ValueError(
                        f"Cannot spread non-iterable value: '{param.value.serialize()}' resolved to {resolved}"
                    )
            else:
                resolved_params.append(TagParam(key=param.key, value=resolved))

        if self.tag_spec.tag == "html_attrs":
            resolved_params = merge_repeated_kwargs(resolved_params)
        resolved_params = process_aggregate_kwargs(resolved_params)

        args, kwargs = self.tag_spec.validate_params(resolved_params)
        return args, kwargs


# Data obj to give meaning to the parsed tag fields
class ParsedTag(NamedTuple):
    tag_name: str
    flags: Dict[str, bool]
    params: TagParams
    parse_body: Callable[[], NodeList]


def parse_template_tag(
    parser: Parser,
    token: Token,
    tag_spec: TagSpec,
) -> ParsedTag:
    fix_nested_tags(parser, token)

    _, attrs = parse_tag(token.contents, parser)

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
    last_token = attrs[-1].value if len(attrs) else None
    if last_token and last_token.serialize() == "/":
        attrs.pop()
        is_inline = True
    else:
        is_inline = not tag_spec.end_tag

    raw_params, flags = _extract_flags(tag_name, attrs, tag_spec.flags or [])

    def _parse_tag_body(parser: Parser, end_tag: str, inline: bool) -> NodeList:
        if inline:
            body = NodeList()
        else:
            body = parser.parse(parse_until=[end_tag])
            parser.delete_first_token()
        return body

    return ParsedTag(
        tag_name=tag_name,
        params=TagParams(params=raw_params, tag_spec=tag_spec),
        flags=flags,
        # NOTE: We defer parsing of the body, so we have the chance to call the tracing
        # loggers before the parsing. This is because, if the body contains any other
        # tags, it will trigger their tag handlers. So the code called AFTER
        # `parse_body()` is already after all the nested tags were processed.
        parse_body=lambda: _parse_tag_body(parser, tag_spec.end_tag, is_inline) if tag_spec.end_tag else NodeList(),
    )


def _extract_flags(
    tag_name: str, attrs: List[TagAttr], allowed_flags: List[str]
) -> Tuple[List[TagAttr], Dict[str, bool]]:
    found_flags = set()
    remaining_attrs = []
    for attr in attrs:
        value = attr.serialize(omit_key=True)

        if value not in allowed_flags:
            remaining_attrs.append(attr)
            continue

        if attr.value.spread:
            raise TemplateSyntaxError(f"'{tag_name}' - keyword '{value}' is a reserved flag, and cannot be spread")

        if value in found_flags:
            raise TemplateSyntaxError(f"'{tag_name}' received flag '{value}' multiple times")

        found_flags.add(value)

    flags_dict: Dict[str, bool] = {
        # Base state, as defined in the tag spec
        **{flag: False for flag in (allowed_flags or [])},
        # Flags found on the template tag
        **{flag: True for flag in found_flags},
    }

    return remaining_attrs, flags_dict


# TODO_REMOVE_IN_V1 - Disallow specifying the same key multiple times once in v1.
def merge_repeated_kwargs(params: List[TagParam]) -> List[TagParam]:
    resolved_params: List[TagParam] = []
    params_by_key: Dict[str, TagParam] = {}
    param_indices_by_key: Dict[str, int] = {}
    replaced_param_indices: Set[int] = set()

    for index, param in enumerate(params):
        if param.key is None:
            resolved_params.append(param)
            continue

        # Case: First time we see a kwarg
        if param.key not in params_by_key:
            params_by_key[param.key] = param
            param_indices_by_key[param.key] = index
            resolved_params.append(param)
        # Case: A kwarg is repeated - we merge the values into a single string, with a space in between.
        else:
            # We want to avoid mutating the items of the original list in place.
            # So when it actually comes to merging the values, we create a new TagParam onto
            # which we can merge values of all the repeated params. Thus, we keep track of this
            # with `replaced_param_indices`.
            if index not in replaced_param_indices:
                orig_param = params_by_key[param.key]
                orig_param_index = param_indices_by_key[param.key]
                param_copy = TagParam(key=orig_param.key, value=str(orig_param.value))
                resolved_params[orig_param_index] = param_copy
                params_by_key[param.key] = param_copy
                replaced_param_indices.add(orig_param_index)

            params_by_key[param.key].value += " " + str(param.value)

    return resolved_params


def fix_nested_tags(parser: Parser, block_token: Token) -> None:
    # Since the nested tags MUST be wrapped in quotes, e.g.
    # `{% component 'test' "{% lorem var_a w %}" %}`
    # `{% component 'test' key="{% lorem var_a w %}" %}`
    #
    # We can parse the tag's tokens so we can find the last one, and so we consider
    # the unclosed `{%` only for the last bit.
    _, attrs = parse_tag(block_token.contents, parser)

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
    first_char_index = len(last_token.spread or "")
    has_unclosed_quote = (
        not last_token.quoted
        and last_token.value
        and last_token.value[first_char_index] in ('"', "'")
    )  # fmt: skip

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
