"""
This file cetralizes various ways we use Django's Context class
pass data across components, nodes, slots, and contexts.

You can think of the Context as our storage system.
"""

from copy import copy
from typing import TYPE_CHECKING, Optional

from django.template import Context

from django_components.logger import trace_msg

if TYPE_CHECKING:
    from django_components.slots import FillContent


_FILLED_SLOTS_CONTENT_CONTEXT_KEY = "_DJANGO_COMPONENTS_FILLED_SLOTS"
_OUTER_CONTEXT_CONTEXT_KEY = "_DJANGO_COMPONENTS_OUTER_CONTEXT"
_SLOT_COMPONENT_ASSOC_KEY = "_DJANGO_COMPONENTS_SLOT_COMP_ASSOC"


def get_slot_fill(context: Context, component_id: str, slot_name: str) -> Optional["FillContent"]:
    """
    Use this function to obtain a slot fill from the current context.

    See `set_slot_fill` for more details.
    """
    trace_msg("GET", "FILL", slot_name, component_id)
    slot_key = (_FILLED_SLOTS_CONTENT_CONTEXT_KEY, component_id, slot_name)
    return context.get(slot_key, None)


def set_slot_fill(context: Context, component_id: str, slot_name: str, value: "FillContent") -> None:
    """
    Use this function to set a slot fill for the current context.

    Note that we make use of the fact that Django's Context is a stack - we can push and pop
    extra contexts on top others.

    For the slot fills to be pushed/popped wth stack layer, they need to have keys defined
    directly on the Context object.
    """
    trace_msg("SET", "FILL", slot_name, component_id)
    slot_key = (_FILLED_SLOTS_CONTENT_CONTEXT_KEY, component_id, slot_name)
    context[slot_key] = value


def get_root_context(context: Context) -> Optional[Context]:
    """
    Use this function to get the root context.

    Root context is the top-most context, AKA the context that was passed to
    the initial `Template.render()`.
    We pass through the root context to allow configure how slot fills should be rendered.

    See the `SLOT_CONTEXT_BEHAVIOR` setting.
    """
    return context.get(_OUTER_CONTEXT_CONTEXT_KEY)


def set_root_context(context: Context, root_ctx: Context) -> None:
    """
    Use this function to set the root context.

    Root context is the top-most context, AKA the context that was passed to
    the initial `Template.render()`.
    We pass through the root context to allow configure how slot fills should be rendered.

    See the `SLOT_CONTEXT_BEHAVIOR` setting.
    """
    context.push({_OUTER_CONTEXT_CONTEXT_KEY: root_ctx})


def capture_root_context(context: Context) -> None:
    """
    Set the root context if it was not set before.

    Root context is the top-most context, AKA the context that was passed to
    the initial `Template.render()`.
    We pass through the root context to allow configure how slot fills should be rendered.

    See the `SLOT_CONTEXT_BEHAVIOR` setting.
    """
    root_ctx_already_defined = _OUTER_CONTEXT_CONTEXT_KEY in context
    if not root_ctx_already_defined:
        set_root_context(context, copy(context))


def set_slot_component_association(context: Context, slot_id: str, component_id: str) -> None:
    """
    Set association between a Slot and a Component in the current context.

    We use SlotNodes to render slot fills. SlotNodes are created only at Template parse time.
    However, when we are using components with slots in (another) template, we can render
    the same component multiple time. So we can have multiple FillNodes intended to be used
    with the same SlotNode.

    So how do we tell the SlotNode which FillNode to render? We do so by tagging the ComponentNode
    and FillNodes with a unique component_id, which ties them together. And then we tell SlotNode
    which component_id to use to be able to find the correct Component/Fill.

    We don't want to store this info on the Nodes themselves, as we need to treat them as
    immutable due to caching of Templates by Django.

    Hence, we use the Context to store the associations of SlotNode <-> Component for
    the current context stack.
    """
    key = (_SLOT_COMPONENT_ASSOC_KEY, slot_id)
    context[key] = component_id


def get_slot_component_association(context: Context, slot_id: str) -> str:
    """
    Given a slot ID, get the component ID that this slot is associated with
    in this context.

    See `set_slot_component_association` for more details.
    """
    key = (_SLOT_COMPONENT_ASSOC_KEY, slot_id)
    return context[key]
