"""
This file is for logic that focuses on transforming the AST of template tags
(as parsed from tag_parser) into a form that can be used by the Nodes.
"""

import inspect
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Mapping, NamedTuple, Optional, Set, Tuple

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
) -> Tuple[Tuple[Any, ...], Dict[str, Any]]:
    """
    Validates a list of TagParam objects against this tag's function signature.

    The validation preserves the order of parameters as they appeared in the template.

    Raises `TypeError` if the parameters don't match the tag's signature.
    """

    # Create a function that uses the given signature
    def validator(*args: Any, **kwargs: Any) -> Tuple[Tuple[Any, ...], Dict[str, Any]]:
        return args, kwargs

    validator.__signature__ = signature  # type: ignore[attr-defined]

    # Call the validator with our args and kwargs in the same order as they appeared
    # in the template, to let the Python interpreter validate on repeated kwargs.
    try:
        # Returns args, kwargs
        return apply_params_in_original_order(validator, params, extra_kwargs)
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

    Then it will be as if the given function was called like this:

    ```python
    fn(key1=value1, arg1, arg2, key2=value2, key3=value3)
    ```

    This function validates that the template tag's parameters match the function's signature
    and follow Python's function calling conventions. It will raise appropriate TypeError exceptions
    for invalid parameter combinations, such as:
    - Too few/many arguments (for non-variadic functions)
    - Duplicate keyword arguments
    - Mixed positional/keyword argument errors
    - Positional args after kwargs

    Returns the result of calling fn with the validated parameters
    """
    signature = inspect.signature(fn)

    # Track state as we process parameters
    seen_kwargs = False  # To detect positional args after kwargs
    used_param_names = set()  # To detect duplicate kwargs
    validated_args = []
    validated_kwargs = {}

    # Get list of valid parameter names and analyze signature
    params_by_name = signature.parameters
    valid_params = list(params_by_name.keys())

    # Check if function accepts variable arguments (*args, **kwargs)
    has_var_positional = any(param.kind == inspect.Parameter.VAR_POSITIONAL for param in params_by_name.values())
    has_var_keyword = any(param.kind == inspect.Parameter.VAR_KEYWORD for param in params_by_name.values())

    # Find the last positional parameter index (excluding *args)
    max_positional_index = 0
    for i, signature_param in enumerate(params_by_name.values()):
        if signature_param.kind in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        ):
            max_positional_index = i + 1
        elif signature_param.kind == inspect.Parameter.VAR_POSITIONAL:
            # Don't count *args in max_positional_index
            break
        # Parameter.KEYWORD_ONLY
        # Parameter.VAR_KEYWORD
        else:
            break

    next_positional_index = 0

    # Process parameters in their original order
    for param in params:
        if param.key is None:
            # This is a positional argument
            if seen_kwargs:
                raise TypeError("positional argument follows keyword argument")

            # Only check position limit for non-variadic functions
            if not has_var_positional and next_positional_index >= max_positional_index:
                if max_positional_index == 0:
                    raise TypeError(f"takes 0 positional arguments but {next_positional_index + 1} was given")
                raise TypeError(f"takes {max_positional_index} positional argument(s) but more were given")

            # For non-variadic arguments, get the parameter name this maps to
            if next_positional_index < max_positional_index:
                param_name = valid_params[next_positional_index]
                # Check if this parameter was already provided as a kwarg
                if param_name in used_param_names:
                    raise TypeError(f"got multiple values for argument '{param_name}'")
                used_param_names.add(param_name)

            validated_args.append(param.value)
            next_positional_index += 1
        else:
            # This is a keyword argument
            seen_kwargs = True

            # Check for duplicate kwargs
            if param.key in used_param_names:
                raise TypeError(f"got multiple values for argument '{param.key}'")

            # Only validate kwarg names if the function doesn't accept **kwargs
            if not has_var_keyword and param.key not in valid_params:
                raise TypeError(f"got an unexpected keyword argument '{param.key}'")

            validated_kwargs[param.key] = param.value
            used_param_names.add(param.key)

    # Add any extra kwargs
    if extra_kwargs:
        validated_kwargs.update(extra_kwargs)

    # Final validation using signature.bind()
    bound_args = signature.bind(*validated_args, **validated_kwargs)
    bound_args.apply_defaults()

    # Actually call the function with validated parameters
    return fn(*bound_args.args, **bound_args.kwargs)
