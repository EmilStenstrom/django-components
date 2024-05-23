"""
This file centralizes various ways we use Django's Context class
pass data across components, nodes, slots, and contexts.

You can think of the Context as our storage system.
"""

from typing import Any, Dict, List

from django.template import Context

from django_components.utils import find_last_index

_FILLED_SLOTS_CONTENT_CONTEXT_KEY = "_DJANGO_COMPONENTS_FILLED_SLOTS"
_ROOT_CTX_CONTEXT_KEY = "_DJANGO_COMPONENTS_ROOT_CTX"
_PARENT_COMP_CONTEXT_KEY = "_DJANGO_COMPONENTS_PARENT_COMP"
_CURRENT_COMP_CONTEXT_KEY = "_DJANGO_COMPONENTS_CURRENT_COMP"


def prepare_context(
    context: Context,
    component_id: str,
) -> None:
    """Initialize the internal context state."""
    # Initialize mapping dicts within this rendering run.
    # This is shared across the whole render chain, thus we set it only once.
    if _FILLED_SLOTS_CONTENT_CONTEXT_KEY not in context:
        context[_FILLED_SLOTS_CONTENT_CONTEXT_KEY] = {}

    set_component_id(context, component_id)


def make_isolated_context_copy(context: Context) -> Context:
    context_copy = context.new()
    copy_forloop_context(context, context_copy)

    # Pass through our internal keys
    context_copy[_FILLED_SLOTS_CONTENT_CONTEXT_KEY] = context.get(_FILLED_SLOTS_CONTENT_CONTEXT_KEY, {})
    if _ROOT_CTX_CONTEXT_KEY in context:
        context_copy[_ROOT_CTX_CONTEXT_KEY] = context.get(_ROOT_CTX_CONTEXT_KEY, {})

    return context_copy


def set_component_id(context: Context, component_id: str) -> None:
    """
    We use the Context object to pass down info on inside of which component
    we are currently rendering.
    """
    # Store the previous component so we can detect if the current component
    # is the top-most or not. If it is, then "_parent_component_id" is None
    context[_PARENT_COMP_CONTEXT_KEY] = context.get(_CURRENT_COMP_CONTEXT_KEY, None)
    context[_CURRENT_COMP_CONTEXT_KEY] = component_id


def copy_forloop_context(from_context: Context, to_context: Context) -> None:
    """Forward the info about the current loop"""
    # Note that the ForNode (which implements for loop behavior) does not
    # only add the `forloop` key, but also keys corresponding to the loop elements
    # So if the loop syntax is `{% for my_val in my_lists %}`, then ForNode also
    # sets a `my_val` key.
    # For this reason, instead of copying individual keys, we copy the whole stack layer
    # set by ForNode.
    if "forloop" in from_context:
        forloop_dict_index = find_last_index(from_context.dicts, lambda d: "forloop" in d)
        to_context.update(from_context.dicts[forloop_dict_index])


def get_injected_context_vars(
    context: Context,
    inject: List[str] | None,
    component_name: str,
) -> Dict[str, Any]:
    """
    Collect 'injected' fields so they can be made available inside `get_context_data`
    and the component's template. These fields MUST have been previously 'provided'
    by the component's ancestors using the `provide` class attribute.
    """
    injected = {}
    for key in inject or []:
        # NOTE: For simplicity, we keep the provided values directly on the context.
        # This plays nicely with Django's Context, which behaves like a stack, so "newer"
        # values overshadow the "older" ones.
        internal_key = _INJECT_CONTEXT_KEY_PREFIX + key
        if internal_key not in context:
            raise RuntimeError(
                f"Component '{component_name}' tried to inject a variable '{key}' before it was provided."
                f"To fix this, make sure that at least one ancestor of component '{component_name}' has"
                f" the variable '{key}' in their 'provide' attribute."
            )
        injected[key] = context[internal_key]
    return injected


def set_provided_context_vars(
    context: Context,
    provide: List[str] | None,
    context_data: Dict[str, Any],
    component_name: str,
) -> None:
    """
    'Provide' specific fields from the context data. In other words, these fields
    can be retrieved by the component's descendants using the `inject` class attribute.
    """
    for key in provide or []:
        if key not in context_data:
            raise RuntimeError(
                f"Component '{component_name}' tried to provide a variable '{key}' but"
                " the variable was not exported from get_context_data."
            )
        internal_key = _INJECT_CONTEXT_KEY_PREFIX + key
        context[internal_key] = context_data[key]
