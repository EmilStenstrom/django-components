"""
This file centralizes various ways we use Django's Context class
pass data across components, nodes, slots, and contexts.

You can think of the Context as our storage system.
"""

from typing import TYPE_CHECKING, Optional

from django.template import Context

from django_components.logger import trace_msg

if TYPE_CHECKING:
    from django_components.slots import FillContent


_FILLED_SLOTS_CONTENT_CONTEXT_KEY = "_DJANGO_COMPONENTS_FILLED_SLOTS"
_OUTER_CONTEXT_CONTEXT_KEY = "_DJANGO_COMPONENTS_OUTER_CONTEXT"
_SLOT_COMPONENT_ASSOC_KEY = "_DJANGO_COMPONENTS_SLOT_COMP_ASSOC"


def prepare_context(context: Context, outer_context: Context) -> None:
    """Initialize the internal context state."""
    # This is supposed to run ALWAYS at Component.render
    set_outer_context(context, outer_context)

    # Initialize a dict that will hold all slot -> component associations
    # within this rendering run.
    # This is shared across the whole render chain, thus we set it only once.
    if _SLOT_COMPONENT_ASSOC_KEY not in context:
        context[_SLOT_COMPONENT_ASSOC_KEY] = {}

    # If we're inside a forloop, we need to make a disposable copy of slot -> comp
    # mapping, which can be modified in the loop. We do so by copying it onto the latest
    # context layer.
    #
    # This is necessary, because otherwise if we have a nested loop with a same
    # component used recursively, the inner slot -> comp mapping would leak into the outer.
    #
    # NOTE: If you ever need to debug this, insert a print/debug statement into
    # `django.template.defaulttags.ForNode.render` to inspect the context object
    # inside the for loop.
    if "forloop" in context:
        context.dicts[-1][_SLOT_COMPONENT_ASSOC_KEY] = context[_SLOT_COMPONENT_ASSOC_KEY].copy()


def make_isolated_context_copy(context: Context) -> Context:
    # Even if contexts are isolated, we still need to pass down the
    # outer context so variables in slots can be rendered using
    # the outer context.
    root_ctx = get_outer_context(context)
    slot_assoc = context.get("_DJANGO_COMPONENTS_SLOT_COMP_ASSOC", {})

    context_copy = context.new()
    context_copy["_DJANGO_COMPONENTS_SLOT_COMP_ASSOC"] = slot_assoc
    set_outer_context(context_copy, root_ctx)

    return context_copy


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
    """
    trace_msg("SET", "FILL", slot_name, component_id)
    slot_key = (_FILLED_SLOTS_CONTENT_CONTEXT_KEY, component_id, slot_name)
    context[slot_key] = value


def get_outer_context(context: Context) -> Optional[Context]:
    """
    Use this function to get the outer context.

    See `set_outer_context` for more details.
    """
    return context.get(_OUTER_CONTEXT_CONTEXT_KEY)


def set_outer_context(context: Context, outer_ctx: Optional[Context]) -> None:
    """
    Use this function to set the outer context.

    When we consider a component's template, then outer context is the context
    that was available just outside of the template. Other way you can think about
    it is that, given that the component is not isolated, then outer context is
    the context that's available at the root of the template.

    We pass through this context to allow to configure how slot fills should be
    rendered using the `SLOT_CONTEXT_BEHAVIOR` setting.
    """
    if outer_ctx and len(outer_ctx.dicts) > 1:
        outer_root_context: Context = outer_ctx.new()
        outer_root_context.push(outer_ctx.dicts[1])
    else:
        outer_root_context = Context()

    context.push({_OUTER_CONTEXT_CONTEXT_KEY: outer_root_context})


def set_slot_component_association(
    context: Context,
    slot_id: str,
    component_id: str,
) -> None:
    """
    Set association between a Slot and a Component in the current context.

    We use SlotNodes to render slot fills. SlotNodes are created only at Template
    parse time.
    However, when we refer to components with slots in (another) template (using
    `{% component %}`), we can render the same component multiple time. So we can
    have multiple FillNodes intended to be used with the same SlotNode.

    So how do we tell the SlotNode which FillNode to render? We do so by tagging
    the ComponentNode and FillNodes with a unique component_id, which ties them
    together. And then we tell SlotNode which component_id to use to be able to
    find the correct Component/Fill.

    We don't want to store this info on the Nodes themselves, as we need to treat
    them as immutable due to caching of Templates by Django.

    Hence, we use the Context to store the associations of SlotNode <-> Component
    for the current context stack.
    """
    context[_SLOT_COMPONENT_ASSOC_KEY][slot_id] = component_id


def get_slot_component_association(context: Context, slot_id: str) -> str:
    """
    Given a slot ID, get the component ID that this slot is associated with
    in this context.

    See `set_slot_component_association` for more details.
    """
    return context[_SLOT_COMPONENT_ASSOC_KEY][slot_id]
