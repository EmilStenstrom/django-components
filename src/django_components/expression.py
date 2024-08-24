import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Mapping, Optional, Tuple, Union

from django.template import Context, TemplateSyntaxError
from django.template.base import FilterExpression, Parser

Expression = Union[FilterExpression]
RuntimeKwargsInput = Dict[str, Union[Expression, "Operator"]]
RuntimeKwargPairsInput = List[Tuple[str, Union[Expression, "Operator"]]]


class Operator(ABC):
    """
    Operator describes something that somehow changes the inputs
    to template tags (the `{% %}`).

    For example, a SpreadOperator inserts one or more kwargs at the
    specified location.
    """

    @abstractmethod
    def resolve(self, context: Context) -> Any: ...  # noqa E704


class SpreadOperator(Operator):
    """Operator that inserts one or more kwargs at the specified location."""

    def __init__(self, expr: Expression) -> None:
        self.expr = expr

    def resolve(self, context: Context) -> Dict[str, Any]:
        return self.expr.resolve(context)


class RuntimeKwargs:
    def __init__(self, kwargs: RuntimeKwargsInput) -> None:
        self.kwargs = kwargs

    def resolve(self, context: Context) -> Dict[str, Any]:
        resolved_kwargs = safe_resolve_dict(context, self.kwargs)
        return process_aggregate_kwargs(resolved_kwargs)


class RuntimeKwargPairs:
    def __init__(self, kwarg_pairs: RuntimeKwargPairsInput) -> None:
        self.kwarg_pairs = kwarg_pairs

    def resolve(self, context: Context) -> List[Tuple[str, Any]]:
        resolved_kwarg_pairs: List[Tuple[str, Any]] = []
        for key, kwarg in self.kwarg_pairs:
            if isinstance(kwarg, SpreadOperator):
                spread_kwargs = kwarg.resolve(context)
                for spread_key, spread_value in spread_kwargs.items():
                    resolved_kwarg_pairs.append((spread_key, spread_value))
            else:
                resolved_kwarg_pairs.append((key, kwarg.resolve(context)))

        return resolved_kwarg_pairs


def is_identifier(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    if not value.isidentifier():
        return False
    return True


def safe_resolve_list(context: Context, args: List[Expression]) -> List:
    return [arg.resolve(context) for arg in args]


def safe_resolve_dict(
    context: Context,
    kwargs: Dict[str, Union[Expression, "Operator"]],
) -> Dict[str, Any]:
    result = {}

    for key, kwarg in kwargs.items():
        # If we've come across a Spread Operator (...), we insert the kwargs from it here
        if isinstance(kwarg, SpreadOperator):
            spread_dict = kwarg.resolve(context)
            if spread_dict is not None:
                for spreadkey, spreadkwarg in spread_dict.items():
                    result[spreadkey] = spreadkwarg
        else:
            result[key] = kwarg.resolve(context)
    return result


def resolve_string(
    s: str,
    parser: Optional[Parser] = None,
    context: Optional[Mapping[str, Any]] = None,
) -> str:
    parser = parser or Parser([])
    context = Context(context or {})
    return parser.compile_filter(s).resolve(context)


def is_kwarg(key: str) -> bool:
    return "=" in key


def is_aggregate_key(key: str) -> bool:
    # NOTE: If we get a key that starts with `:`, like `:class`, we do not split it.
    # This syntax is used by Vue and AlpineJS.
    return ":" in key and not key.startswith(":")


def is_spread_operator(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False

    return value.startswith("...")


# A string that starts with `...1=`, `...29=`, etc.
# We convert the spread syntax to this, so Django parses
# it as a kwarg, so it remains in the original position.
#
# So from `...dict`, we make `...1=dict`
#
# That way it's trivial to merge the kwargs after the spread
# operator is replaced with actual values.
INTERNAL_SPREAD_OPERATOR_RE = re.compile(r"^\.\.\.\d+=")


def is_internal_spread_operator(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False

    return bool(INTERNAL_SPREAD_OPERATOR_RE.match(value))


def process_aggregate_kwargs(kwargs: Mapping[str, Any]) -> Dict[str, Any]:
    """
    This function aggregates "prefixed" kwargs into dicts. "Prefixed" kwargs
    start with some prefix delimited with `:` (e.g. `attrs:`).

    Example:
    ```py
    process_component_kwargs({"abc:one": 1, "abc:two": 2, "def:three": 3, "four": 4})
    # {"abc": {"one": 1, "two": 2}, "def": {"three": 3}, "four": 4}
    ```

    ---

    We want to support a use case similar to Vue's fallthrough attributes.
    In other words, where a component author can designate a prop (input)
    which is a dict and which will be rendered as HTML attributes.

    This is useful for allowing component users to tweak styling or add
    event handling to the underlying HTML. E.g.:

    `class="pa-4 d-flex text-black"` or `@click.stop="alert('clicked!')"`

    So if the prop is `attrs`, and the component is called like so:
    ```django
    {% component "my_comp" attrs=attrs %}
    ```

    then, if `attrs` is:
    ```py
    {"class": "text-red pa-4", "@click": "dispatch('my_event', 123)"}
    ```

    and the component template is:
    ```django
    <div {% html_attrs attrs add:class="extra-class" %}></div>
    ```

    Then this renders:
    ```html
    <div class="text-red pa-4 extra-class" @click="dispatch('my_event', 123)" ></div>
    ```

    However, this way it is difficult for the component user to define the `attrs`
    variable, especially if they want to combine static and dynamic values. Because
    they will need to pre-process the `attrs` dict.

    So, instead, we allow to "aggregate" props into a dict. So all props that start
    with `attrs:`, like `attrs:class="text-red"`, will be collected into a dict
    at key `attrs`.

    This provides sufficient flexiblity to make it easy for component users to provide
    "fallthrough attributes", and sufficiently easy for component authors to process
    that input while still being able to provide their own keys.
    """
    processed_kwargs = {}
    nested_kwargs: Dict[str, Dict[str, Any]] = {}
    for key, val in kwargs.items():
        if not is_aggregate_key(key):
            processed_kwargs[key] = val
            continue

        # NOTE: Trim off the prefix from keys
        prefix, sub_key = key.split(":", 1)
        if prefix not in nested_kwargs:
            nested_kwargs[prefix] = {}
        nested_kwargs[prefix][sub_key] = val

    # Assign aggregated values into normal input
    for key, val in nested_kwargs.items():
        if key in processed_kwargs:
            raise TemplateSyntaxError(
                f"Received argument '{key}' both as a regular input ({key}=...)"
                f" and as an aggregate dict ('{key}:key=...'). Must be only one of the two"
            )
        processed_kwargs[key] = val

    return processed_kwargs
