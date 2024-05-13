from typing import Any, Dict, List, Mapping, Union

from django.template import Context
from django.template.base import FilterExpression


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


def safe_resolve_list(args: List[FilterExpression], context: Context) -> List:
    return [safe_resolve(arg, context) for arg in args]


def safe_resolve_dict(
    kwargs: Union[Mapping[str, FilterExpression], Dict[str, FilterExpression]],
    context: Context,
) -> Dict:
    return {key: safe_resolve(kwarg, context) for key, kwarg in kwargs.items()}


def safe_resolve(context_item: FilterExpression, context: Context) -> Any:
    """Resolve FilterExpressions and Variables in context if possible. Return other items unchanged."""
    return context_item.resolve(context) if hasattr(context_item, "resolve") else context_item
