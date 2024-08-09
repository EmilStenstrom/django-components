from typing import Any, Dict, List, Mapping, Optional, Union

from django.template import Context
from django.template.base import FilterExpression, Parser


class AggregateFilterExpression:
    def __init__(self, dict: Dict[str, FilterExpression]) -> None:
        self.dict = dict


Expression = Union[FilterExpression, AggregateFilterExpression]


def resolve_expression_as_identifier(
    context: Context,
    fexp: FilterExpression,
) -> str:
    resolved = fexp.resolve(context)
    if not isinstance(resolved, str):
        raise ValueError(
            f"FilterExpression '{fexp}' was expected to resolve to string, instead got '{type(resolved)}'"
        )
    if not resolved.isidentifier():
        raise ValueError(
            f"FilterExpression '{fexp}' was expected to resolve to valid identifier, instead got '{resolved}'"
        )
    return resolved


def safe_resolve_list(args: List[Expression], context: Context) -> List:
    return [safe_resolve(arg, context) for arg in args]


def safe_resolve_dict(
    kwargs: Union[Mapping[str, Expression], Dict[str, Expression]],
    context: Context,
) -> Dict:
    return {key: safe_resolve(kwarg, context) for key, kwarg in kwargs.items()}


def safe_resolve(context_item: Expression, context: Context) -> Any:
    """Resolve FilterExpressions and Variables in context if possible. Return other items unchanged."""
    if isinstance(context_item, AggregateFilterExpression):
        return safe_resolve_dict(context_item.dict, context)

    return context_item.resolve(context) if hasattr(context_item, "resolve") else context_item


def resolve_string(
    s: str,
    parser: Optional[Parser] = None,
    context: Optional[Mapping[str, Any]] = None,
) -> str:
    parser = parser or Parser([])
    context = Context(context or {})
    return parser.compile_filter(s).resolve(context)


def is_aggregate_key(key: str) -> bool:
    # NOTE: If we get a key that starts with `:`, like `:class`, we do not split it.
    # This syntax is used by Vue and AlpineJS.
    return ":" in key and not key.startswith(":")
