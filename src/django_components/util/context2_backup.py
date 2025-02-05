from copy import copy
from dataclasses import dataclass
from typing import (
    Any,
    Dict,
    Iterable,
    Iterator,
    List,
    Mapping,
    Optional,
    Set,
    SupportsIndex,
    Tuple,
    Union,
    cast,
)

from django.template.context import BaseContext as DjangoBaseContext


# TODO - ADD ContextLayer.clear
# TODO - ADD ContextLayer.copy
# TODO - ADD ContextLayer.pop
# TODO - ADD ContextLayer.popitem
# TODO - ADD ContextLayer.setdefault


class ContextPopException(Exception):
    "pop() has been called more times than push()"
    pass


DictArg = Union[Mapping[Any, Any], Iterable[Tuple[Any, Any]], "BaseContext"]


class DictsDescriptor:
    """
    Descriptor that handles direct assignments to `BaseContext.dicts`, e.g.

    ```python
    context = BaseContext()
    context.dicts = [{"a": 1}, {"b": 2}]
    ```

    When `BaseContext.dicts` is assigned directly, we need to:
    1. Clean up old dicts by removing their context references
    2. Reset the context's state
    3. Set up the new dicts properly

    Ideally we wouldn't need this and all these mutations would go through
    BaseContext methods. But since we're not in control of the Django templating,
    we need to detect these mutations and handle them.
    """

    def __init__(self) -> None:
        self.private_name = "_dicts"

    def __get__(self, instance: Optional["BaseContext"], owner: type) -> List[Dict]:
        # Accessing the attribute on class should raise AttributeError
        if instance is None:
            return getattr(owner, "dicts")

        # On instance, return the private attribute
        return getattr(instance, self.private_name)

    def __set__(self, instance: "BaseContext", value: List[dict]) -> None:
        # Clean up old layers by removing their context references
        old_layers = cast(List[ContextLayer], getattr(instance, self.private_name, []))
        for layer_dict in old_layers:
            layer_dict._remove_context(instance)

        # Reset the context's state
        instance._key_index.clear()

        # Create new ContextLayersList and populate it
        new_layers = ContextLayersList(instance)
        new_layers.extend(value)

        # Set the new list
        setattr(instance, self.private_name, new_layers)


class BaseContext:

    #####################################
    # DJANGO API OVERRIDES
    #####################################

    dicts = DictsDescriptor()

    def __init__(self, dict_: Optional[Union[dict, "BaseContext"]] = None) -> None:
        self._key_index: Dict[str, List[int]] = {}  # Maps keys to layers they appear in
        # We keep track of which key is defined in which layer. However, we only lazily
        # sort the keys when they are accessed.
        self._dirty_keys: Set[str] = set()
        self._dicts = ContextLayersList(self)  # Use ContextLayersList for tracking mutations
        self._reset_dicts(dict_)

    def __hash__(self) -> int:
        return id(self)

    def _reset_dicts(self, *new_dicts: Optional[Union[dict, "BaseContext"]]) -> None:
        # Clear
        self._dicts = ContextLayersList(self)
        self._key_index.clear()

        # Set defaults
        builtins = {"True": True, "False": False, "None": None}
        self.push(builtins)

        for value in new_dicts:
            if value is not None:
                self.push(value)

    def __copy__(self) -> "BaseContext":
        # Create new context instance
        duplicate = cast(BaseContext, copy(super(DjangoBaseContext, self)))

        # Initialize empty state
        duplicate._key_index = {}
        duplicate._dirty_keys = set()
        duplicate._dicts = ContextLayersList(duplicate)

        # Reuse existing ContextLayers by adding the new context to them
        for idx, layer_dict in enumerate(self._dicts):
            layer_dict._add_context(duplicate, idx)
            duplicate._dicts._append(layer_dict)

        return duplicate

    def __getitem__(self, key: str) -> Any:
        "Get a variable's value, starting at the current context and going upward"
        if key in self._key_index:
            return self.get(key)
        raise KeyError(key)

    def __setitem__(self, key: str, value: Any) -> None:
        "Set a variable in the current context"
        self._dicts[-1][key] = value

    def __delitem__(self, key: str) -> None:
        "Delete a variable from the current context"
        del self._dicts[-1][key]

    def set_upward(self, key: str, value: Any) -> None:
        """
        Set a variable in one of the higher contexts if it exists there,
        otherwise in the current context.
        """
        if key in self._key_index:
            latest_layer = self._get_latest_layer(key)
            latest_layer[key] = value
        else:
            self[key] = value

    def get(self, key: str, otherwise: Any = None) -> Any:
        if key in self._key_index:
            latest_layer = self._get_latest_layer(key)
            return latest_layer[key]
        return otherwise

    def flatten(self) -> dict:
        """Return self.dicts as one dictionary."""
        flat: Dict[str, Any] = {}
        # Use the key index to get the latest value for each key
        for key in self._key_index:
            latest_layer = self._get_latest_layer(key)
            flat[key] = latest_layer[key]
        return flat

    def push(self, *args: DictArg, **kwargs: Any) -> "ContextDict":
        new_layer = ContextLayer(*args, **kwargs)
        new_layer._add_context(self, len(self._dicts))
        self._dicts._append(new_layer)
        return ContextDict(self, new_layer)

    def pop(self) -> "ContextLayer":
        if len(self._dicts) == 1:
            raise ContextPopException
        return self._dicts.pop()

    def __repr__(self) -> str:
        return repr(self._dicts)

    def __iter__(self) -> Iterator[dict]:
        return reversed(self._dicts)

    def __contains__(self, key: str) -> bool:
        return key in self._key_index

    #####################################
    # CUSTOM METHODS
    #####################################

    def _remap_layer_indices(self, index_map: Dict[int, int]) -> None:
        """
        Remap layer indices after a reordering operation.

        Args:
            index_map: old_layer_index -> new_layer_index mapping
        """
        # Create new key index with remapped layers
        new_key_index: Dict[str, List[int]] = {}
        for key, layer_indices in self._key_index.items():
            # Map each layer to its new position and maintain reverse sort
            new_layers = [
                # NOTE: Some indices may not be in the index_map, in which case we assume
                #       that they didn't move.
                index_map[layer] if layer in index_map else layer
                for layer in layer_indices
            ]
            self._dirty_keys.add(key)
            new_key_index[key] = new_layers

        self._key_index = new_key_index

    def _register_key(self, key: str, layer: int) -> None:
        """When a key is added to a layer, add it to the key index."""
        if key not in self._key_index:
            self._key_index[key] = []
        if layer not in self._key_index[key]:
            self._key_index[key].append(layer)
            self._dirty_keys.add(key)

    def _unregister_key(self, key: str, layer: int) -> None:
        """When a key is removed from a layer, remove it from the key index."""
        if key not in self._key_index:
            return

        try:
            self._key_index[key].remove(layer)
            if not self._key_index[key]:
                del self._key_index[key]
        except ValueError:
            pass

    def _get_latest_layer(self, key: str) -> "ContextLayer":
        """Get the latest layer that contains the key."""
        # Should raise KeyError if key not found
        key_layers = self._key_index[key]

        if key in self._dirty_keys:
            key_layers.sort(reverse=True)  # Keep highest layers first
            self._dirty_keys.remove(key)

        latest_layer_index = key_layers[0]
        return self._dicts[latest_layer_index]


# TODO - API CHANGE FROM Django:
#        Updated ContextDict not to subclass from dict. So that means that people
#        will no longer be able to do `context.push({"d": 1})["d"]`.
#        Instead, they should do `context.push({"d": 1}); context["d"]`
class ContextDict:
    """A context manager that adds and removes a dictionary from the context."""

    def __init__(self, context: "BaseContext", dict_: "ContextLayer"):
        self.context = context
        self.dict = dict_

    def __enter__(self) -> "ContextLayer":
        return self.dict

    def __exit__(self, *args: Any, **kwargs: Any) -> None:
        self.context.pop()


@dataclass
class ContextBinding:
    context: "BaseContext"
    layer_index: int


class ContextLayer(dict):
    """A dictionary that notifies its parent Contexts of any changes."""

    # NOTE: Although this accepts `*args`, it only uses the first argument.
    #       The rest is passed to `dict.__init__()` and will raise an error.
    def __init__(self, *args: DictArg, **kwargs: Any) -> None:
        # It might happen that a single layer dictionary is pushed to multiple Contexts.
        # And in those Contexts, it may be at different positions.
        #
        # Thus, we store which Contexts the the layer is "connected" to.
        # And if we update this dict, we will update all contexts that have it.
        #
        # NOTE: If `Context.dicts` is reassigned manually, then `DictsDescriptor` will
        #       remove the `context` from this dict
        # NOTE: For easier access, the data is keyed by their ID
        self.contexts: Dict[int, ContextBinding] = {}

        arg = args[0] if args else None
        new_dict: Dict[Any, Any] = {}
        if arg is not None:
            if isinstance(arg, (DjangoBaseContext, BaseContext)):
                new_dict.update(arg.flatten())
            else:
                # NOTE: This should raise if arg is not a dict nor mapping / iterable
                new_dict.update(arg)

        # Let `dict` raise error if it received more than 1 positional argument
        updated_args = (new_dict, *args[1:])
        super().__init__(*updated_args, **kwargs)

    #####################################
    # CUSTOM METHODS
    #####################################

    def _get_context_binding(self, context: "BaseContext") -> Optional[ContextBinding]:
        """Get the context binding for a specific context."""
        context_id = id(context)
        if context_id not in self.contexts:
            return None

        return self.contexts[context_id]

    def _set_context_binding(self, context: "BaseContext", layer_index: int) -> None:
        """Set the context binding for a specific context."""
        context_id = id(context)
        self.contexts[context_id] = ContextBinding(context, layer_index)

    def _delete_context_binding(self, context: "BaseContext") -> None:
        """Delete the context binding for a specific context."""
        context_id = id(context)
        del self.contexts[context_id]

    def _add_context(self, context: "BaseContext", layer_index: int) -> None:
        """Add a new context binding to this dict's contexts."""
        context_binding = self._get_context_binding(context)
        if context_binding is not None:
            return

        self._set_context_binding(context, layer_index)

        # Register all keys in the new context
        for key in self:
            context._register_key(key, layer_index)

    def _remove_context(self, context: "BaseContext") -> None:
        """Remove a context binding from this dict's contexts."""
        context_binding = self._get_context_binding(context)
        if context_binding is None:
            return

        # Unregister all keys from the context that is being removed
        for key in self:
            context._unregister_key(key, context_binding.layer_index)

        self._delete_context_binding(context)

    def _get_cached_layer_index(self, context: "BaseContext") -> int:
        """Get the index of the layer for a specific context."""
        context_binding = self._get_context_binding(context)
        if context_binding is None:
            raise ValueError(f"Context {context} not found in this ContextLayer")

        return context_binding.layer_index

    def _cache_layer_index(self, context: "BaseContext", new_index: int) -> None:
        """Set the index of the layer for a specific context."""
        context_binding = self._get_context_binding(context)
        if context_binding is None:
            self._set_context_binding(context, new_index)
        else:
            context_binding.layer_index = new_index

    #########################
    # DICT API OVERRIDES
    #########################

    # dict[key] = value
    def __setitem__(self, key: str, value: Any) -> None:
        is_new_key = key not in self
        super().__setitem__(key, value)
        if is_new_key:
            # Register new key in all contexts
            for context_binding in self.contexts.values():
                context_binding.context._register_key(key, context_binding.layer_index)

    # del dict[key]
    def __delitem__(self, key: str) -> None:
        # NOTE: Raises KeyError if key not found
        super().__delitem__(key)
        # Unregister deleted key from all contexts
        for context_binding in self.contexts.values():
            context_binding.context._unregister_key(key, context_binding.layer_index)

    # TODO - API CHANGE FROM DJANGO - If BaseContext is passed as arg, then it is flattened
    def update(  # type: ignore[override]
        self,
        *args: DictArg,
        **kwargs: Any,
    ) -> None:
        # Get new keys before update
        self_keys: Set[str] = set(self.keys())
        new_keys: Set[str] = set()

        if args:
            other = args[0]
            if isinstance(other, (DjangoBaseContext, BaseContext)):
                other = other.flatten()

            if isinstance(other, dict):
                new_keys = set(other.keys())
            else:
                new_keys = {k for k, v in other}  # Creates Set

        new_keys.update(set(kwargs.keys()))
        new_keys = new_keys - self_keys

        super().update(*args, **kwargs)

        # Register new keys in all contexts
        if new_keys:
            for context_binding in self.contexts.values():
                for key in new_keys:
                    context_binding.context._register_key(key, context_binding.layer_index)


class ContextLayersList(List["ContextLayer"]):
    """
    A list subclass that notifies its parent context of any modifications.

    This is used to track modifications to `BaseContext.dicts` when they happen
    directly on the list object rather than through BaseContext's methods.

    Ideally we wouldn't need this and all these mutations would go through
    BaseContext methods. But since we're not in control of the Django templating,
    we need to detect these mutations and handle them.
    """

    def __init__(self, owner: "BaseContext", *args: Any, **kwargs: Any) -> None:
        self.owner = owner
        super().__init__(*args, **kwargs)

    #####################################
    # CUSTOM METHODS
    #####################################

    def _disconnect_layer(self, layer_dict: "ContextLayer") -> None:
        """Disconnect a layer from its context. This means the Context will no longer track this layer."""
        layer_dict._remove_context(self.owner)

    def _reindex_from(self, start: int) -> None:
        """Update indices of all layers from start onwards."""
        for new_layer_index, layer_dict in enumerate(self):
            # Update the layer index in place
            layer_dict._cache_layer_index(self.owner, new_layer_index)

    def _create_index_map(self) -> Dict[int, int]:
        """Create a mapping of current indices to track reordering."""
        index_map = {}
        for curr_layer_index, layer_dict in enumerate(self):
            # Get the value as stored in the layer.
            old_cached_index = layer_dict._get_cached_layer_index(self.owner)
            # This mapping basically says:
            # "The old index that's stored in the layer should be updated to the new index of this layer"
            index_map[old_cached_index] = curr_layer_index
        return index_map

    def _apply_index_map(self, index_map: Dict[int, int]) -> None:
        """Apply new indices to ContextLayers and update context's key index."""
        for layer_dict in self:
            # Get the value as stored in the layer. This is the value we want to update.
            # NOTE: This may raise ValueError if the layer is no longer connected to the context
            try:
                old_index = layer_dict._get_cached_layer_index(self.owner)
            except ValueError:
                continue

            # NOTE: Some indices may not be in the index_map, in which case we assume
            # that they didn't move.
            if old_index in index_map:
                new_index = index_map[old_index]
                layer_dict._cache_layer_index(self.owner, new_index)

        # Update context's key index
        self.owner._remap_layer_indices(index_map)

    # The original `append()` method
    def _append(self, value: Union[dict, "ContextLayer"]) -> None:
        super().append(value)  # type: ignore[arg-type]

    # The original `extend()` method
    def _extend(self, values: Iterable[Union[dict, "ContextLayer"]]) -> None:
        super().extend(values)  # type: ignore[arg-type]

    ##################################################
    # LIST API OVERRIDES
    ##################################################

    # For `sort()` and `reverse()`, there's no addition / removal. Also,
    # the order of dicts can totally change.
    # One approach could be to clear the Context, and then push the new list.
    #
    # But instead, in hopes of being more efficient, we'll just update the indices
    # after the sort / reverse.
    #
    # 1. Store indices of each item as they were before,
    # 2. Sort/reverse
    # 3. Get updated indices
    # 4. With the before and after, we can construct a map of old_index -> new_index.
    # 5. Tell `BaseContext` to remap the key indices based on this transformation map.
    def sort(self, *args: Any, **kwargs: Any) -> None:
        """Sort the list in place and update indices."""
        # Store current indices
        old_indices = self._create_index_map()

        # Perform the sort
        super().sort(*args, **kwargs)

        # Create mapping of old indices to new positions
        new_indices = self._create_index_map()
        index_map = {old: new_indices[old] for old in old_indices}

        # Apply the new indices
        self._apply_index_map(index_map)

    def reverse(self) -> None:
        """Reverse the list in place and update indices."""
        # Store current indices
        old_indices = self._create_index_map()

        # Perform the reverse
        super().reverse()

        # Create mapping of old indices to new positions
        new_indices = self._create_index_map()
        index_map = {old: new_indices[old] for old in old_indices}

        # Apply the new indices
        self._apply_index_map(index_map)

    # For `append()` and `extend()`, there's no removal, only addition
    # at the end of the list. So we only need to make sure that the new
    # dicts are indexed by creating new ContextLayers.
    def append(self, value: Union[dict, "ContextLayer"]) -> None:
        """Append a new dict, converting to ContextLayer if needed."""
        if not isinstance(value, ContextLayer):
            value = ContextLayer(value)

        # Add this context to the layer
        value._add_context(self.owner, len(self))
        super().append(value)

    def extend(self, values: Iterable[Union[dict, "ContextLayer"]]) -> None:
        """Extend list with new layers, converting each to ContextLayer if needed."""
        start_idx = len(self)
        for idx, value in enumerate(values, start_idx):
            if not isinstance(value, ContextLayer):
                value = ContextLayer(value)

            # Add this context to the layer
            value._add_context(self.owner, idx)
            super().append(value)

    def insert(self, index: SupportsIndex, value: Union[dict, "ContextLayer"]) -> None:
        """Insert a new layer at index, shifting other layers right."""
        index = index.__index__()

        # Normalize negative indices
        if index < 0:
            index = max(0, len(self) + index)

        # Shift indices by +1 for all items AFTER the insertion point (inclusive)
        index_map = {}
        for layer_index in range(index, len(self)): # NOTE: This is the insertion point
            layer_dict = self[layer_index]
            old_cached_index = layer_dict._get_cached_layer_index(self.owner)
            # Shift indices by +1
            index_map[old_cached_index] = layer_index + 1

        self._apply_index_map(index_map)

        if not isinstance(value, ContextLayer):
            value = ContextLayer(value)

        # Insert the new value
        value._add_context(self.owner, index)
        super().insert(index, value)

    def pop(self, index: SupportsIndex = -1) -> "ContextLayer":
        """Remove and return layer at index (default last)."""
        index = index.__index__()

        # Normalize negative indices
        if index < 0:
            index = len(self) + index

        # Get the layer we'll remove
        layer_to_remove = self[index]
        layer_to_remove_index = layer_to_remove._get_cached_layer_index(self.owner)

        # Unregister from Context all keys that were defined on this layer
        for key in list(layer_to_remove.keys()):
            self.owner._unregister_key(key, layer_to_remove_index)

        # Disconnect the layer from the Context
        self._disconnect_layer(layer_to_remove)

        # Shift indices by -1 for all items AFTER the popped one.
        if index != len(self) - 1:  # If not popping from end
            index_map = {}

            # NOTE: +1 Because we want to update indices of items AFTER the popped one
            for layer_index in range(index + 1, len(self)):
                layer_dict = self[layer_index]
                old_cached_index = layer_dict._get_cached_layer_index(self.owner)
                # Shift indices by -1
                index_map[old_cached_index] = layer_index - 1

            self._apply_index_map(index_map)

        # Do the pop
        return super().pop(index)

    def remove(self, value: "ContextLayer") -> None:
        """Remove first occurrence of value."""
        # Raises ValueError if value not found
        index = self.index(value)
        self.pop(index)

    def clear(self) -> None:
        """Remove all items from the list."""
        for layer_dict in self:
            # Unregister from Context all keys that were defined on this layer
            for key in list(layer_dict.keys()):
                layer_index = layer_dict._get_cached_layer_index(self.owner)
                self.owner._unregister_key(key, layer_index)

            # Disconnect the layer from the Context
            self._disconnect_layer(layer_dict)

        super().clear()

    # dicts[index] = value
    #
    # Handles both single item and slice assignment.
    def __setitem__(self, index: Union[SupportsIndex, slice], value: Any) -> None:
        raw_values = []

        # Convert index or slice to a list of indices
        if isinstance(index, slice):
            start = index.start or 0
            stop = index.stop if index.stop is not None else len(self)
            indices = list(range(start, stop, index.step or 1))

            if not isinstance(value, Iterable):
                # Error message based on Python's error message
                raise TypeError("can only assign an iterable to a slice")

            raw_values = list(value)

            # "Extended slice" is when the slice has a step that's not 1, e.g `my_list[3:4:2]`.
            # In that case, Python requires that the length of the values matches
            # the length of the indices. Even if the slice is empty, and even if
            # the step is -1.
            is_extended_slice: Optional[bool] = index.step is not None and index.step != 1
            if is_extended_slice and len(raw_values) != len(indices):
                # Error message based on Python's error message
                raise ValueError(
                    f"attempted to assign sequence of size {len(raw_values)} to extended slice of size {len(indices)}"
                )
        else:
            # Case: Single item case - convert to list of one
            indices = [index.__index__()]
            raw_values = [value]
            is_extended_slice = False

        # Disconnect from Context those layers that will be overwritten
        for layer_index in indices:
            layer_dict = self[layer_index]
            self._disconnect_layer(layer_dict)

        # These are items that will be inserted in their place
        new_layers: List[ContextLayer] = []
        for raw_value in raw_values:
            if isinstance(raw_value, ContextLayer):
                new_layers.append(raw_value)
            else:
                new_layers.append(ContextLayer(raw_value))

        if is_extended_slice:
            # If this IS an extended slice, then this is a one-for-one replacement
            # of the old layers with the new layers. So other indices don't shift.
            for layer_index, new_layer in zip(indices, new_layers):
                new_layer._add_context(self.owner, layer_index)
                super().__setitem__(layer_index, new_layer)
        else:
            # However, if this is NOT an extended slice, then the number of added layers
            # may not match the number of indices. So in this case the slice behaves like
            # JavaScript's `Array.prototype.splice()`.
            #
            # In this case, we need to shift the indices of the layers AFTER the insertion point.
            #
            # For example, if we have `[1, 2, 3]` and we do `my_list[1:2] = [4, 5, 6]`,
            # then we need to shift the indices of `[3]` to the right by 2.
            index_shift = len(new_layers) - len(indices)

            # First shift the indices of the layers AFTER the insertion point (inclusive)
            # In this case the replacement indices MUST be continuous, so we can find
            # the last affected index and shift all layers after it.
            for layer_index in range(max(indices) + 1, len(self)):
                layer_dict = self[layer_index]
                layer_dict._cache_layer_index(self.owner, layer_index + index_shift)

            # Then insert the new layers - These are added one after another, practically
            # at the position of the first replaced index.
            for layer_index, new_layer in enumerate(new_layers, start=min(indices)):
                new_layer._add_context(self.owner, layer_index)
                super().__setitem__(layer_index, new_layer)

    def __delitem__(self, index: Union[SupportsIndex, slice]) -> None:
        """Handle both single item deletion and slice deletion."""
        # Convert index or slice to a list of indices and values
        if isinstance(index, slice):
            start = index.start or 0
            stop = index.stop if index.stop is not None else len(self)
            indices = list(range(start, stop, index.step or 1))
        else:
            # Single item case - convert to list of one
            index = index.__index__()
            indices = [index]

        # Delete in reverse order to avoid the indices shifting
        for idx in reversed(indices):
            # TODO - POTENTIALLY OPTIMIZE BY DEFINING `_pop` that accepts a list of items
            self.pop(idx)
