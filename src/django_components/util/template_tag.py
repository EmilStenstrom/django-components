"""
This file is for logic that focuses on transforming the AST of template tags
(as parsed from tag_parser) into a form that can be used by the Nodes.
"""

import inspect
import sys
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Mapping, NamedTuple, Optional, Set, Tuple, Union

from django.template import Context, NodeList
from django.template.base import Parser, Token
from django.template.exceptions import TemplateSyntaxError

from django_components.expression import process_aggregate_kwargs
from django_components.util.tag_parser import TagAttr, parse_tag


# For details see https://github.com/django-components/django-components/pull/902#discussion_r1913611633
# and following comments
def validate_params(
    tag: str,
    signature: inspect.Signature,
    params: List["TagParam"],
    extra_kwargs: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Validates a list of TagParam objects against this tag's function signature.

    The validation preserves the order of parameters as they appeared in the template.

    Raises `TypeError` if the parameters don't match the tag's signature.
    """

    # Create a function that uses the given signature
    def validator(*args: Any, **kwargs: Any) -> None:
        # Let Python do the signature validation
        bound = signature.bind(*args, **kwargs)
        bound.apply_defaults()

    validator.__signature__ = signature  # type: ignore[attr-defined]

    # Call the validator with our args and kwargs in the same order as they appeared
    # in the template, to let the Python interpreter validate on repeated kwargs.
    try:
        apply_params_in_original_order(validator, params, extra_kwargs)
    except TypeError as e:
        raise TypeError(f"Invalid parameters for tag '{tag}': {str(e)}") from None


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


def resolve_params(
    tag: str,
    params: List[TagAttr],
    context: Context,
) -> List[TagParam]:
    # First, resolve any spread operators. Spreads can introduce both positional
    # args (e.g. `*args`) and kwargs (e.g. `**kwargs`).
    resolved_params: List[TagParam] = []
    for param in params:
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

    if tag == "html_attrs":
        resolved_params = merge_repeated_kwargs(resolved_params)
    resolved_params = process_aggregate_kwargs(resolved_params)

    return resolved_params


# Data obj to give meaning to the parsed tag fields
class ParsedTag(NamedTuple):
    flags: Dict[str, bool]
    params: List[TagAttr]
    parse_body: Callable[[], NodeList]


def parse_template_tag(
    tag: str,
    end_tag: Optional[str],
    allowed_flags: Optional[List[str]],
    parser: Parser,
    token: Token,
) -> ParsedTag:
    _, attrs = parse_tag(token.contents, parser)

    # First token is tag name, e.g. `slot` in `{% slot <name> ... %}`
    tag_name_attr = attrs.pop(0)
    tag_name = tag_name_attr.serialize(omit_key=True)

    # Sanity check
    if tag_name != tag:
        raise TemplateSyntaxError(f"Start tag parser received tag '{tag_name}', expected '{tag}'")

    # There's 3 ways how we tell when a tag ends:
    # 1. If the tag contains `/` at the end, it's a self-closing tag (like `<div />`),
    #    and it doesn't have an end tag. In this case we strip the trailing slash.
    #
    # Otherwise, depending on the end_tag, the tag may be:
    # 2. Block tag - With corresponding end tag, e.g. `{% endslot %}`
    # 3. Inlined tag - Without the end tag.
    last_token = attrs[-1].value if len(attrs) else None
    if last_token and last_token.serialize() == "/":
        attrs.pop()
        is_inline = True
    else:
        is_inline = not end_tag

    raw_params, flags = _extract_flags(tag_name, attrs, allowed_flags or [])

    def _parse_tag_body(parser: Parser, end_tag: str, inline: bool) -> NodeList:
        if inline:
            body = NodeList()
        else:
            body = parser.parse(parse_until=[end_tag])
            parser.delete_first_token()
        return body

    return ParsedTag(
        params=raw_params,
        flags=flags,
        # NOTE: We defer parsing of the body, so we have the chance to call the tracing
        # loggers before the parsing. This is because, if the body contains any other
        # tags, it will trigger their tag handlers. So the code called AFTER
        # `parse_body()` is already after all the nested tags were processed.
        parse_body=lambda: _parse_tag_body(parser, end_tag, is_inline) if end_tag else NodeList(),
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
        # Base state - all flags False
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


def apply_params_in_original_order(
    fn: Callable[..., Any],
    params: List[TagParam],
    extra_kwargs: Optional[Dict[str, Any]] = None,
) -> Any:
    """
    Apply a list of `TagParams` to another function, keeping the order of the params as they
    appeared in the template.

    If a template tag was called like this:

    ```django
    {% component key1=value1 arg1 arg2 key2=value2 key3=value3 %}
    ```

    Then `apply_params_in_original_order()` will call the `fn` like this:
    ```
    component(
        key1=call_params[0], # kwarg 1
        call_params[1], # arg 1
        call_params[2], # arg 2
        key2=call_params[3], # kwarg 2
        key3=call_params[4], # kwarg 3
        ...
        **extra_kwargs,
    )
    ```

    This way, this will be effectively the same as:

    ```python
    component(key1=value1, arg1, arg2, key2=value2, key3=value3, ..., **extra_kwargs)
    ```

    The problem this works around is that, dynamically, args and kwargs in Python
    can be passed only with `*args` and `**kwargs`. But in such case, we're already
    grouping all args and kwargs, which may not represent the original order of the params
    as they appeared in the template tag.

    If you need to pass kwargs that are not valid Python identifiers, e.g. `data-id`, `class`, `:href`,
    you can pass them in via `extra_kwargs`. These kwargs will be exempt from the validation, and will be
    passed to the function as a dictionary spread.
    """
    # Generate a script like so:
    # ```py
    # component(
    #     key1=call_params[0],
    #     call_params[1],
    #     call_params[2],
    #     key2=call_params[3],
    #     key3=call_params[4],
    #     ...
    #     **extra_kwargs,
    # )
    # ```
    #
    # NOTE: Instead of grouping params into args and kwargs, we preserve the original order
    #       of the params as they appeared in the template.
    #
    # NOTE: Because we use `eval()` here, we can't trust neither the param keys nor values.
    #       So we MUST NOT reference them directly in the exec script, otherwise we'd be at risk
    #       of injection attack.
    #
    #       Currently, the use of `eval()` is safe, because we control the input:
    #       - List with indices is used so that we don't have to reference directly or try to print the values.
    #         and instead refer to them as `call_params[0]`, `call_params[1]`, etc.
    #       - List indices are safe, because we generate them.
    #       - Kwarg names come from the user. But Python expects the kwargs to be valid identifiers.
    #         So if a key is not a valid identifier, we'll raise an error. Before passing it to `eval()`
    validator_call_script = "fn("
    call_params: List[Union[List, Dict]] = []
    for index, param in enumerate(params):
        call_params.append(param.value)
        if param.key is None:
            validator_call_script += f"call_params[{index}], "
        else:
            validator_call_script += f"{param.key}=call_params[{index}], "

    validator_call_script += "**extra_kwargs, "
    validator_call_script += ")"

    def applier(fn: Callable[..., Any]) -> Any:
        locals = {
            "fn": fn,
            "call_params": call_params,
            "extra_kwargs": extra_kwargs or {},
        }
        # NOTE: `eval()` changed API in Python 3.13
        if sys.version_info >= (3, 13):
            return eval(validator_call_script, globals={}, locals=locals)
        else:
            return eval(validator_call_script, {}, locals)

    return applier(fn)
