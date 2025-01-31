import copy

from django.template import Context
from django.template.loader_tags import BlockContext


class CopiedDict(dict):
    """Dict subclass to identify dictionaries that have been copied with `snapshot_context`"""

    pass


def snapshot_context(context: Context) -> Context:
    """
    Make a copy of the Context object, so that it can be used as a snapshot.

    Snapshot here means that the copied Context can leave any scopes that the original
    Context is part of, and the copy will NOT be modified:

    ```py
    ctx = Context({ ... })
    with ctx.render_context.push({}):
        with ctx.update({"a": 1}):
            snapshot = snapshot_context(ctx)

    assert snapshot["a"] == 1  # OK
    assert ctx["a"] == 1       # ERROR
    ```

    This function aims to make a shallow copy, but needs to make deeper copies
    for certain features like forloops or support for `{% block %}` / `{% extends %}`.
    """
    # Using `copy()` should also copy flags like `autoescape`, `use_l10n`, etc.
    context_copy = copy.copy(context)

    # Context is a list of dicts, where the dicts can be thought of as "layers" - when a new
    # layer is added, the keys defined on the latest layer overshadow the previous layers.
    #
    # For some special cases, like when we're inside forloops, we need to make deep copies
    # of the objects created by the forloop, so all forloop metadata (index, first, last, etc.)
    # is preserved for all (potentially nested) forloops.
    #
    # For non-forloop layers, we just make shallow copies.
    dicts_with_copied_forloops = []
    for ctx_dict in context.dicts:
        # This layer is already copied
        if isinstance(ctx_dict, CopiedDict):
            dicts_with_copied_forloops.append(ctx_dict)
            continue

        ctx_dict = CopiedDict(ctx_dict)
        if "forloop" in ctx_dict:
            ctx_dict["forloop"] = ctx_dict["forloop"].copy()

            # Recursively copy the state of potentially nested forloops
            curr_forloop = ctx_dict["forloop"]
            while curr_forloop is not None:
                curr_forloop["parentloop"] = curr_forloop["parentloop"].copy()
                if "parentloop" in curr_forloop["parentloop"]:
                    curr_forloop = curr_forloop["parentloop"]
                else:
                    break

        dicts_with_copied_forloops.append(ctx_dict)

    context_copy.dicts = dicts_with_copied_forloops

    # Make a copy of RenderContext
    render_ctx_copies = []
    for d in context.render_context.dicts:
        # This layer is already copied
        if isinstance(d, CopiedDict):
            render_ctx_copies.append(d)
            continue

        # This holds info on what `{% block %}` blocks are defined
        d_copy = CopiedDict(d)
        if "block_context" in d:
            d_copy["block_context"] = _copy_block_context(d["block_context"])

        # "extends_context" is a list of Origin objects
        if "extends_context" in d:
            d_copy["extends_context"] = d["extends_context"].copy()

        d_copy["_djc_snapshot"] = True
        render_ctx_copies.append(d_copy)

    context_copy.render_context.dicts = render_ctx_copies
    return context_copy


def _copy_block_context(block_context: BlockContext) -> BlockContext:
    """Make a shallow copy of BlockContext"""
    block_context_copy = block_context.__class__()
    for key, val in block_context.blocks.items():
        # Individual dict values should be lists of Nodes. We don't
        # need to modify the Nodes, but we need to make a copy of the lists.
        block_context_copy.blocks[key] = val.copy()
    return block_context_copy
