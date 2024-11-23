"""
This file centralizes various ways we use Django's Context class
pass data across components, nodes, slots, and contexts.

You can think of the Context as our storage system.
"""

from collections import namedtuple
from typing import Any, Dict, Optional

from django.template import Context, TemplateSyntaxError

from django_components.util.misc import find_last_index

_COMPONENT_SLOT_CTX_CONTEXT_KEY = "_DJANGO_COMPONENTS_COMPONENT_SLOT_CTX"
_ROOT_CTX_CONTEXT_KEY = "_DJANGO_COMPONENTS_ROOT_CTX"
_REGISTRY_CONTEXT_KEY = "_DJANGO_COMPONENTS_REGISTRY"
_INJECT_CONTEXT_KEY_PREFIX = "_DJANGO_COMPONENTS_INJECT__"


def make_isolated_context_copy(context: Context) -> Context:
    context_copy = context.new()
    copy_forloop_context(context, context_copy)

    # Pass through our internal keys
    context_copy[_REGISTRY_CONTEXT_KEY] = context.get(_REGISTRY_CONTEXT_KEY, None)
    if _ROOT_CTX_CONTEXT_KEY in context:
        context_copy[_ROOT_CTX_CONTEXT_KEY] = context[_ROOT_CTX_CONTEXT_KEY]

    # Make inject/provide to work in isolated mode
    context_keys = context.flatten().keys()
    for key in context_keys:
        if key.startswith(_INJECT_CONTEXT_KEY_PREFIX):
            context_copy[key] = context[key]

    return context_copy


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


def get_injected_context_var(
    component_name: str,
    context: Context,
    key: str,
    default: Optional[Any] = None,
) -> Any:
    """
    Retrieve a 'provided' field. The field MUST have been previously 'provided'
    by the component's ancestors using the `{% provide %}` template tag.
    """
    # NOTE: For simplicity, we keep the provided values directly on the context.
    # This plays nicely with Django's Context, which behaves like a stack, so "newer"
    # values overshadow the "older" ones.
    internal_key = _INJECT_CONTEXT_KEY_PREFIX + key

    # Return provided value if found
    if internal_key in context:
        return context[internal_key]

    # If a default was given, return that
    if default is not None:
        return default

    # Otherwise raise error
    raise KeyError(
        f"Component '{component_name}' tried to inject a variable '{key}' before it was provided."
        f" To fix this, make sure that at least one ancestor of component '{component_name}' has"
        f" the variable '{key}' in their 'provide' attribute."
    )


def set_provided_context_var(
    context: Context,
    key: str,
    provided_kwargs: Dict[str, Any],
) -> None:
    """
    'Provide' given data under given key. In other words, this data can be retrieved
    using `self.inject(key)` inside of `get_context_data()` method of components that
    are nested inside the `{% provide %}` tag.
    """
    # NOTE: We raise TemplateSyntaxError since this func should be called only from
    # within template.
    if not key:
        raise TemplateSyntaxError(
            "Provide tag received an empty string. Key must be non-empty and a valid identifier."
        )
    if not key.isidentifier():
        raise TemplateSyntaxError(
            "Provide tag received a non-identifier string. Key must be non-empty and a valid identifier."
        )

    # We turn the kwargs into a NamedTuple so that the object that's "provided"
    # is immutable. This ensures that the data returned from `inject` will always
    # have all the keys that were passed to the `provide` tag.
    tpl_cls = namedtuple("DepInject", provided_kwargs.keys())  # type: ignore[misc]
    payload = tpl_cls(**provided_kwargs)

    internal_key = _INJECT_CONTEXT_KEY_PREFIX + key
    context[internal_key] = payload
