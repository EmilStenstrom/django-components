"""
This file centralizes various ways we use Django's Context class
pass data across components, nodes, slots, and contexts.

You can think of the Context as our storage system.
"""

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
