from copy import copy
from typing import List, cast

from django.template.context import BaseContext as DjangoBaseContext
from django_components.util.context2 import BaseContext, ContextBinding, ContextPopException, ContextLayer

from .django_test_setup import setup_test_config
from .testutils import BaseTestCase

setup_test_config({"autodiscover": False})


# TODO - SLICES WHERE FEWER ITEMS BEING INSERTED THAN DELETED
# TODO - SLICES WHERE MORE ITEMS BEING INSERTED THAN DELETED
# TODO - ADD ContextLayer.clear
# TODO - ADD ContextLayer.copy
# TODO - ADD ContextLayer.pop
# TODO - ADD ContextLayer.popitem
# TODO - ADD ContextLayer.setdefault


class DictsAssignmentTests(BaseTestCase):
    """
    Test that, when we assign a list of dicts to a context, the dicts are properly bound to the context.

    ```py
    context = BaseContext()
    context.dicts = [{"a": 1}, {"b": 2, "c": 3}]  # <-- HERE
    ```
    """

    def test_assign_list_of_regular_dicts(self):
        # Create fresh context
        context = BaseContext()
        old_dicts = cast(List[ContextLayer], list(context.dicts))  # Copy of initial dicts

        # Assign new dicts
        new_dicts = [{"a": 1}, {"b": 2, "c": 3}]
        context.dicts = new_dicts

        # Verify conversion to ContextLayers
        self.assertEqual(len(context.dicts), len(new_dicts))
        for i, d in enumerate(cast(List[ContextLayer], context.dicts)):
            self.assertIsInstance(d, ContextLayer)
            self.assertEqual(d.contexts, {id(context): ContextBinding(context, i)})

        # Verify key index
        self.assertIn("a", context._key_index)
        self.assertIn("b", context._key_index)
        self.assertIn("c", context._key_index)
        self.assertEqual(context._key_index["a"], [0])  # Layer 0
        self.assertEqual(context._key_index["b"], [1])  # Layer 1
        self.assertEqual(context._key_index["c"], [1])  # Layer 1

        # Verify old dicts are unbound
        for d in old_dicts:
            self.assertEqual(d.contexts, {})

        # Verify lookups work
        self.assertEqual(context["a"], 1)
        self.assertEqual(context["b"], 2)
        self.assertEqual(context["c"], 3)

    def test_assign_list_context_dict_bound_to_multiple_contexts(self):
        # Create contexts
        context = BaseContext()
        other_context = BaseContext({"x": 1})
        other_context.push({"y": 2})
        other_indexed_dicts = cast(List[ContextLayer], list(other_context.dicts))

        # Assign mix of regular and indexed dicts
        new_dicts = [{"a": 4}, *other_indexed_dicts, {"z": 3}]
        context.dicts = new_dicts

        # Verify dicts of context
        context_dicts = cast(List[ContextLayer], context.dicts)

        self.assertEqual(len(context_dicts), 5)
        for d in context_dicts:
            self.assertIsInstance(d, ContextLayer)

        # Bound only to context
        self.assertEqual(context_dicts[0].contexts, {id(context): ContextBinding(context, 0)})
        # Bound to context AND other_context
        self.assertEqual(
            context_dicts[1].contexts,
            {id(context): ContextBinding(context, 1), id(other_context): ContextBinding(other_context, 0)},
        )
        self.assertEqual(
            context_dicts[2].contexts,
            {id(context): ContextBinding(context, 2), id(other_context): ContextBinding(other_context, 1)},
        )
        self.assertEqual(
            context_dicts[3].contexts,
            {id(context): ContextBinding(context, 3), id(other_context): ContextBinding(other_context, 2)},
        )
        # Bound only to context
        self.assertEqual(context_dicts[4].contexts, {id(context): ContextBinding(context, 4)})

        # Verify dicts of other_context
        # Bound to context AND other_context
        self.assertEqual(
            other_indexed_dicts[0].contexts,
            {id(context): ContextBinding(context, 1), id(other_context): ContextBinding(other_context, 0)},
        )
        self.assertEqual(
            other_indexed_dicts[1].contexts,
            {id(context): ContextBinding(context, 2), id(other_context): ContextBinding(other_context, 1)},
        )
        self.assertEqual(
            other_indexed_dicts[2].contexts,
            {id(context): ContextBinding(context, 3), id(other_context): ContextBinding(other_context, 2)},
        )

        # Verify key index
        self.assertEqual(context._key_index["a"], [0])
        self.assertEqual(context._key_index["True"], [1])
        self.assertEqual(context._key_index["x"], [2])
        self.assertEqual(context._key_index["y"], [3])
        self.assertEqual(context._key_index["z"], [4])

        # Verify lookups work
        self.assertEqual(context["a"], 4)
        self.assertEqual(context["True"], True)
        self.assertEqual(context["x"], 1)
        self.assertEqual(context["y"], 2)
        self.assertEqual(context["z"], 3)

    def test_assign_list_old_context_dict_bound_if_in_new_dicts_list(self):
        # Create contexts
        context = BaseContext({"x": 1})
        context.push({"y": 2})
        old_indexed_dicts = cast(List[ContextLayer], list(context.dicts))

        # Assign mix of regular and indexed dicts
        new_dicts = [{"a": 4}, *old_indexed_dicts, {"z": 3}]
        context.dicts = new_dicts

        # Verify all dicts are properly set up
        context_dicts = cast(List[ContextLayer], context.dicts)
        self.assertEqual(len(context_dicts), len(new_dicts))
        for i, d in enumerate(context_dicts):
            self.assertIsInstance(d, ContextLayer)

        # Bound only to context
        self.assertEqual(context_dicts[0].contexts, {id(context): ContextBinding(context, 0)})
        # Bound to context AND other_context
        self.assertEqual(context_dicts[1].contexts, {id(context): ContextBinding(context, 1)})
        self.assertEqual(context_dicts[2].contexts, {id(context): ContextBinding(context, 2)})
        self.assertEqual(context_dicts[3].contexts, {id(context): ContextBinding(context, 3)})
        # Bound only to context
        self.assertEqual(context_dicts[4].contexts, {id(context): ContextBinding(context, 4)})

        # Verify old reference points to the same dicts
        self.assertEqual(old_indexed_dicts[0].contexts, {id(context): ContextBinding(context, 1)})
        self.assertEqual(old_indexed_dicts[1].contexts, {id(context): ContextBinding(context, 2)})
        self.assertEqual(old_indexed_dicts[2].contexts, {id(context): ContextBinding(context, 3)})

        # Verify key index
        self.assertEqual(context._key_index["a"], [0])
        self.assertEqual(context._key_index["True"], [1])
        self.assertEqual(context._key_index["x"], [2])
        self.assertEqual(context._key_index["y"], [3])
        self.assertEqual(context._key_index["z"], [4])

        # Verify lookups work
        self.assertEqual(context["a"], 4)
        self.assertEqual(context["True"], True)
        self.assertEqual(context["x"], 1)
        self.assertEqual(context["y"], 2)
        self.assertEqual(context["z"], 3)

    def test_assign_empty_list(self):
        # Create context with some data
        context = BaseContext()
        context.push({"a": 1})
        context.push({"b": 2})
        old_dicts = cast(List[ContextLayer], list(context.dicts))

        # Assign empty list
        context.dicts = []

        # Verify only builtins remain
        self.assertEqual(len(context.dicts), 0)

        # Verify old dicts are cleaned up
        for d in old_dicts:
            self.assertEqual(d.contexts, {})

    def test_assign_raises_on_non_iterable(self):
        # Create context with some data
        context = BaseContext()
        context.push({"a": 1})

        with self.assertRaisesMessage(TypeError, "'NoneType' object is not iterable"):
            context.dicts = None  # type: ignore


class ListMutationTests(BaseTestCase):
    def test_append_regular_dict(self):
        context = BaseContext()

        # Append a regular dict
        context.dicts.append({"a": 1, "b": 2})

        # Verify length increased
        self.assertEqual(len(context.dicts), 2)

        # Verify conversion to ContextLayer
        new_dict = cast(ContextLayer, context.dicts[-1])
        self.assertIsInstance(new_dict, ContextLayer)
        self.assertEqual(new_dict.contexts, {id(context): ContextBinding(context, 1)})

        # Verify key index
        self.assertEqual(context._key_index["a"], [1])
        self.assertEqual(context._key_index["b"], [1])

        # Verify lookups work
        self.assertEqual(context["a"], 1)
        self.assertEqual(context["b"], 2)

    def test_append_indexed_dict(self):
        # Create two contexts
        context = BaseContext()
        other = BaseContext()
        other.dicts.append({"x": 1, "y": 2})
        other_indexed_dict = cast(ContextLayer, other.dicts[-1])

        # Append ContextLayer from other context
        context.dicts.append(other_indexed_dict)

        # Verify length increased
        self.assertEqual(len(context.dicts), 2)

        # Verify dict was properly reindexed
        new_dict = cast(ContextLayer, context.dicts[-1])
        self.assertIsInstance(new_dict, ContextLayer)
        self.assertEqual(
            new_dict.contexts,
            {id(context): ContextBinding(context, 1), id(other): ContextBinding(other, 1)},
        )
        self.assertIs(other_indexed_dict, new_dict)

        # Verify key index
        self.assertEqual(context._key_index["x"], [1])
        self.assertEqual(context._key_index["y"], [1])

        # Verify lookups work
        self.assertEqual(context["x"], 1)
        self.assertEqual(context["y"], 2)

    def test_extend_with_regular_dicts(self):
        context = BaseContext()

        # Extend with regular dicts
        new_dicts = [{"a": 1}, {"b": 2, "c": 3}]
        context.dicts.extend(new_dicts)

        # Verify length increased
        self.assertEqual(len(context.dicts), 3)

        # Verify conversion to ContextLayers
        for i, d in enumerate(cast(List[ContextLayer], context.dicts)):
            self.assertIsInstance(d, ContextLayer)
            self.assertEqual(d.contexts, {id(context): ContextBinding(context, i)})

        # Verify key index
        self.assertEqual(context._key_index["True"], [0])
        self.assertEqual(context._key_index["a"], [1])
        self.assertEqual(context._key_index["b"], [2])
        self.assertEqual(context._key_index["c"], [2])

        # Verify lookups work
        self.assertEqual(context["True"], True)
        self.assertEqual(context["a"], 1)
        self.assertEqual(context["b"], 2)
        self.assertEqual(context["c"], 3)

    def test_extend_with_mixed_dicts(self):
        # Create two contexts
        context = BaseContext()
        other = BaseContext()
        other.dicts.append({"x": 1})
        indexed_dict = cast(ContextLayer, other.dicts[-1])

        # Extend with mix of regular and indexed dicts
        mixed_dicts = [{"a": 1}, indexed_dict, {"b": 2}]
        context.dicts.extend(mixed_dicts)

        # Verify length increased
        self.assertEqual(len(context.dicts), 4)

        # Verify all dicts are properly set up
        context_dicts = cast(List[ContextLayer], context.dicts)
        for d in context_dicts:
            self.assertIsInstance(d, ContextLayer)

        # Bound only to context
        self.assertEqual(context_dicts[0].contexts, {id(context): ContextBinding(context, 0)})
        self.assertEqual(context_dicts[1].contexts, {id(context): ContextBinding(context, 1)})
        # Bound to context AND other_context
        self.assertEqual(
            context_dicts[2].contexts,
            {id(context): ContextBinding(context, 2), id(other): ContextBinding(other, 1)},
        )
        # Bound only to context
        self.assertEqual(context_dicts[3].contexts, {id(context): ContextBinding(context, 3)})

        # The dict is shared between contexts
        self.assertIs(indexed_dict, context.dicts[2])

        # Verify key index
        self.assertEqual(context._key_index["True"], [0])
        self.assertEqual(context._key_index["a"], [1])
        self.assertEqual(context._key_index["x"], [2])
        self.assertEqual(context._key_index["b"], [3])

        # Verify lookups work
        self.assertEqual(context["True"], True)
        self.assertEqual(context["a"], 1)
        self.assertEqual(context["x"], 1)
        self.assertEqual(context["b"], 2)

    def test_insert_at_beginning(self):
        # Create context with some data
        context = BaseContext()
        context.dicts.append({"a": 1})
        context.dicts.append({"b": 2})

        # Insert at beginning (after builtins)
        context.dicts.insert(1, {"x": 3})

        # Verify length increased
        self.assertEqual(len(context.dicts), 4)

        # Verify inserted dict is properly set up
        inserted = cast(ContextLayer, context.dicts[1])
        self.assertIsInstance(inserted, ContextLayer)
        self.assertEqual(inserted.contexts, {id(context): ContextBinding(context, 1)})

        # Verify subsequent items were reindexed
        context_dicts = cast(List[ContextLayer], context.dicts)
        self.assertEqual(context_dicts[2].contexts, {id(context): ContextBinding(context, 2)})
        self.assertEqual(context_dicts[3].contexts, {id(context): ContextBinding(context, 3)})

        # Verify key index
        self.assertEqual(context._key_index["True"], [0])
        self.assertEqual(context._key_index["x"], [1])
        self.assertEqual(context._key_index["a"], [2])
        self.assertEqual(context._key_index["b"], [3])

        # Verify lookups work
        self.assertEqual(context["True"], True)
        self.assertEqual(context["x"], 3)
        self.assertEqual(context["a"], 1)
        self.assertEqual(context["b"], 2)

    def test_insert_in_middle(self):
        # Create context with some data
        context = BaseContext()
        context.dicts.append({"a": 1})
        context.dicts.append({"b": 2})

        # Insert in middle
        context.dicts.insert(2, {"x": 3})

        # Verify length increased
        self.assertEqual(len(context.dicts), 4)

        # Verify inserted dict is properly set up
        inserted = cast(ContextLayer, context.dicts[2])
        self.assertIsInstance(inserted, ContextLayer)
        self.assertEqual(inserted.contexts, {id(context): ContextBinding(context, 2)})

        # Verify only subsequent items were reindexed
        context_dicts = cast(List[ContextLayer], context.dicts)
        self.assertEqual(context_dicts[1].contexts, {id(context): ContextBinding(context, 1)})  # Unchanged
        self.assertEqual(context_dicts[3].contexts, {id(context): ContextBinding(context, 3)})  # Reindexed

        # Verify key index
        self.assertEqual(context._key_index["True"], [0])
        self.assertEqual(context._key_index["a"], [1])
        self.assertEqual(context._key_index["x"], [2])
        self.assertEqual(context._key_index["b"], [3])

        # Verify lookups work
        self.assertEqual(context["True"], True)
        self.assertEqual(context["a"], 1)
        self.assertEqual(context["x"], 3)
        self.assertEqual(context["b"], 2)

    def test_insert_from_end(self):
        # Create context with some data
        context = BaseContext()
        context.dicts.append({"a": 1})
        context.dicts.append({"b": 2})

        # Insert at end
        context.dicts.insert(-1, {"x": 3})

        # Verify length increased
        self.assertEqual(len(context.dicts), 4)

        # Verify inserted dict is properly set up
        inserted = cast(ContextLayer, context.dicts[-2])
        self.assertIsInstance(inserted, ContextLayer)
        self.assertEqual(inserted.contexts, {id(context): ContextBinding(context, 2)})

        # Verify only subsequent items were reindexed
        context_dicts = cast(List[ContextLayer], context.dicts)
        self.assertEqual(context_dicts[1].contexts, {id(context): ContextBinding(context, 1)})  # Unchanged
        self.assertEqual(context_dicts[3].contexts, {id(context): ContextBinding(context, 3)})  # Reindexed

        # Verify key index
        self.assertEqual(context._key_index["True"], [0])
        self.assertEqual(context._key_index["a"], [1])
        self.assertEqual(context._key_index["x"], [2])
        self.assertEqual(context._key_index["b"], [3])

        # Verify lookups work
        self.assertEqual(context["True"], True)
        self.assertEqual(context["a"], 1)
        self.assertEqual(context["b"], 2)
        self.assertEqual(context["x"], 3)

    def test_pop_from_end(self):
        # Create context with some data
        context = BaseContext()
        context.dicts.append({"a": 1})
        context.dicts.append({"b": 2})

        # Pop from end
        popped = cast(ContextLayer, context.dicts.pop())

        # Verify length decreased
        self.assertEqual(len(context.dicts), 2)

        # Verify popped dict is cleaned up
        self.assertEqual(popped.contexts, {})

        # Verify no reindexing was needed
        context_dicts = cast(List[ContextLayer], context.dicts)
        self.assertEqual(context_dicts[1].contexts, {id(context): ContextBinding(context, 1)})

        # Verify key index
        self.assertEqual(context._key_index["True"], [0])
        self.assertEqual(context._key_index["a"], [1])
        self.assertNotIn("b", context._key_index)

        # Verify lookups
        self.assertEqual(context["True"], True)
        self.assertEqual(context["a"], 1)
        with self.assertRaises(KeyError):
            _ = context["b"]

    def test_pop_from_middle(self):
        # Create context with some data
        context = BaseContext()
        context.dicts.append({"a": 1})
        context.dicts.append({"b": 2})
        context.dicts.append({"c": 3})

        # Pop from middle
        popped = cast(ContextLayer, context.dicts.pop(2))

        # Verify length decreased
        self.assertEqual(len(context.dicts), 3)

        # Verify popped dict is cleaned up
        self.assertEqual(popped.contexts, {})

        # Verify subsequent items were reindexed
        context_dicts = cast(List[ContextLayer], context.dicts)
        self.assertEqual(context_dicts[1].contexts, {id(context): ContextBinding(context, 1)})  # Unchanged
        self.assertEqual(context_dicts[2].contexts, {id(context): ContextBinding(context, 2)})  # Reindexed

        # Verify key index
        self.assertEqual(context._key_index["True"], [0])
        self.assertEqual(context._key_index["a"], [1])
        self.assertNotIn("b", context._key_index)
        self.assertEqual(context._key_index["c"], [2])  # Reindexed

        # Verify lookups
        self.assertEqual(context["True"], True)
        self.assertEqual(context["a"], 1)
        with self.assertRaises(KeyError):
            _ = context["b"]
        self.assertEqual(context["c"], 3)

    def test_pop_from_beginning(self):
        # Create context with some data
        context = BaseContext()
        context.dicts.append({"a": 1})
        context.dicts.append({"b": 2})
        context.dicts.append({"c": 3})

        # Pop from beginning (after builtins)
        popped = cast(ContextLayer, context.dicts.pop(1))

        # Verify length decreased
        self.assertEqual(len(context.dicts), 3)

        # Verify popped dict is cleaned up
        self.assertEqual(popped.contexts, {})

        # Verify all subsequent items were reindexed
        context_dicts = cast(List[ContextLayer], context.dicts)
        self.assertEqual(context_dicts[1].contexts, {id(context): ContextBinding(context, 1)})  # Reindexed
        self.assertEqual(context_dicts[2].contexts, {id(context): ContextBinding(context, 2)})  # Reindexed

        # Verify key index
        self.assertEqual(context._key_index["True"], [0])
        self.assertNotIn("a", context._key_index)
        self.assertEqual(context._key_index["b"], [1])  # Reindexed
        self.assertEqual(context._key_index["c"], [2])  # Reindexed

        # Verify lookups
        self.assertEqual(context["True"], True)
        with self.assertRaises(KeyError):
            _ = context["a"]
        self.assertEqual(context["b"], 2)
        self.assertEqual(context["c"], 3)

    def test_remove_existing_item(self):
        # Create context with some data
        context = BaseContext()
        context.dicts.append({"a": 1})
        context.dicts.append({"b": 2})
        context.dicts.append({"c": 3})
        to_remove = cast(ContextLayer, context.dicts[2])  # Middle item

        # Remove middle item
        context.dicts.remove(to_remove)

        # Verify length decreased
        self.assertEqual(len(context.dicts), 3)

        # Verify removed dict is cleaned up
        self.assertEqual(to_remove.contexts, {})

        # Verify subsequent items were reindexed
        context_dicts = cast(List[ContextLayer], context.dicts)
        self.assertEqual(context_dicts[1].contexts, {id(context): ContextBinding(context, 1)})  # Unchanged
        self.assertEqual(context_dicts[2].contexts, {id(context): ContextBinding(context, 2)})  # Reindexed

        # Verify key index
        self.assertEqual(context._key_index["True"], [0])
        self.assertEqual(context._key_index["a"], [1])
        self.assertNotIn("b", context._key_index)
        self.assertEqual(context._key_index["c"], [2])  # Reindexed

        # Verify lookups
        self.assertEqual(context["True"], True)
        self.assertEqual(context["a"], 1)
        with self.assertRaises(KeyError):
            _ = context["b"]
        self.assertEqual(context["c"], 3)

    def test_remove_nonexistent_item(self):
        # Create context with some data
        context = BaseContext()
        context.dicts.append({"a": 1})

        # Create a dict that's not in the context
        nonexistent = ContextLayer({"x": 1})
        other_context = BaseContext()
        nonexistent._add_context(other_context, 0)

        # Try to remove non-existent item
        with self.assertRaises(ValueError):
            context.dicts.remove(nonexistent)

        # Verify nothing changed
        self.assertEqual(len(context.dicts), 2)
        self.assertEqual(context._key_index["a"], [1])
        self.assertEqual(context["a"], 1)

        # Verify nonexistent dict still has its original context
        self.assertEqual(nonexistent.contexts, {id(other_context): ContextBinding(other_context, 0)})

    def test_clear(self):
        # Create context with some data
        context = BaseContext()
        context.dicts.append({"a": 1})
        context.dicts.append({"b": 2})
        old_dicts = cast(List[ContextLayer], list(context.dicts))

        # Clear all items
        context.dicts.clear()

        # Verify also builtins removed
        self.assertEqual(len(context.dicts), 0)
        self.assertNotIn("True", context)

        # Verify old dicts are cleaned up
        for d in old_dicts:
            self.assertIsInstance(d, ContextLayer)
            self.assertEqual(d.contexts, {})

        # Verify key index
        self.assertEqual(set(context._key_index.keys()), set())


class KeyIndexingTests(BaseTestCase):
    def test_key_layer_tracking(self):
        context = BaseContext()

        # Add multiple layers with some shared keys
        context.dicts.append({"a": 1, "b": 2})
        context.dicts.append({"b": 3, "c": 4})
        context.dicts.append({"a": 5, "d": 6})

        # Touch the keys to ensure it's sorted
        context["a"]
        context["b"]
        context["c"]
        context["d"]

        # Verify key index tracks all layers correctly
        self.assertEqual(context._key_index["a"], [3, 1])  # Layers 1 and 3
        self.assertEqual(context._key_index["b"], [2, 1])  # Layers 1 and 2
        self.assertEqual(context._key_index["c"], [2])  # Layer 2 only
        self.assertEqual(context._key_index["d"], [3])  # Layer 3 only

        # Verify builtins are still tracked
        self.assertEqual(context._key_index["True"], [0])
        self.assertEqual(context._key_index["False"], [0])
        self.assertEqual(context._key_index["None"], [0])

    def test_key_shadowing(self):
        context = BaseContext()

        # Create layers with shadowed keys
        context.dicts.append({"x": "layer1"})
        context.dicts.append({"x": "layer2", "y": "only_layer2"})
        context.dicts.append({"x": "layer3"})

        # Verify most recent value is returned
        self.assertEqual(context["x"], "layer3")
        self.assertEqual(context["y"], "only_layer2")

        # Pop top layer and verify shadowing
        context.dicts.pop()
        self.assertEqual(context["x"], "layer2")

        # Pop middle layer and verify shadowing
        context.dicts.pop()
        self.assertEqual(context["x"], "layer1")
        with self.assertRaises(KeyError):
            _ = context["y"]

    def test_key_deletion(self):
        context = BaseContext()

        # Create layers with shared keys
        context.dicts.append({"a": 1, "b": 2})
        context.dicts.append({"a": 3, "c": 4})

        # Delete key from top layer
        del context.dicts[-1]["a"]

        # Verify key index is updated
        self.assertEqual(context._key_index["a"], [1])  # Only layer 1 remains
        self.assertEqual(context["a"], 1)  # Falls back to layer 1

        # Delete key from remaining layer
        del context.dicts[1]["a"]

        # Verify key is completely removed
        self.assertNotIn("a", context._key_index)
        with self.assertRaises(KeyError):
            _ = context["a"]

        # Verify other keys are unaffected
        self.assertEqual(context["b"], 2)
        self.assertEqual(context["c"], 4)

    def test_key_updates(self):
        context = BaseContext()

        # Create initial layer
        context.dicts.append({"x": 1, "y": 2})
        initial_x_layers = list(context._key_index["x"])

        # Update existing key
        context.dicts[1]["x"] = 10

        # Verify key index unchanged but value updated
        self.assertEqual(context._key_index["x"], initial_x_layers)
        self.assertEqual(context["x"], 10)

        # Add new layer with same key
        context.dicts.append({"x": 20})

        # Touch the key to ensure it's sorted
        context["x"]

        # Verify key index updated
        self.assertEqual(context._key_index["x"], [2, 1])
        self.assertEqual(context["x"], 20)

        # Update in lower layer
        context.dicts[1]["x"] = 30

        # Verify shadowing maintained
        self.assertEqual(context["x"], 20)  # Still shadowed by top layer

    def test_key_index_consistency(self):
        context = BaseContext()

        # Add some initial data
        context.dicts.append({"a": 1, "b": 2})
        context.dicts.append({"b": 3, "c": 4})

        # Perform various operations
        context.dicts.insert(2, {"d": 5})
        context.dicts.pop(1)
        context.dicts.append({"a": 6})

        # Verify key index accurately reflects final state
        self.assertEqual(context._key_index["a"], [3])
        self.assertEqual(context._key_index["b"], [2])
        self.assertEqual(context._key_index["c"], [2])
        self.assertEqual(context._key_index["d"], [1])

        # Verify all lookups work correctly
        self.assertEqual(context["a"], 6)
        self.assertEqual(context["b"], 3)
        self.assertEqual(context["c"], 4)
        self.assertEqual(context["d"], 5)


class ContextOperationTests(BaseTestCase):
    def test_push_pop_behavior(self):
        context = BaseContext()

        # Test basic push/pop
        context.push({"a": 1})
        self.assertEqual(context["a"], 1)

        context.push({"a": 2, "b": 3})
        self.assertEqual(context["a"], 2)  # Shadowed
        self.assertEqual(context["b"], 3)

        # Test pop returns correct dict
        popped = context.pop()
        self.assertIsInstance(popped, dict)
        self.assertEqual(popped, {"a": 2, "b": 3})

        # Verify state after pop
        self.assertEqual(context["a"], 1)  # Original value
        with self.assertRaises(KeyError):
            _ = context["b"]  # No longer exists

        # Test pop with empty context (except builtins)
        context.pop()
        with self.assertRaises(KeyError):
            _ = context["a"]

        # Verify builtins remain
        self.assertTrue(context["True"])
        self.assertFalse(context["False"])
        self.assertIsNone(context["None"])

    def test_flatten_multiple_layers(self):
        context = BaseContext()

        # Create multiple layers with overlapping keys
        context.push({"a": 1, "b": 2})
        context.push({"b": 3, "c": 4})
        context.push({"a": 5, "d": 6})

        initial_len = len(context.dicts)

        # Flatten the context
        flattened = context.flatten()

        self.assertIsInstance(flattened, dict)

        # Verify flattened has correct values (most recent values)
        self.assertEqual(flattened["a"], 5)
        self.assertEqual(flattened["b"], 3)
        self.assertEqual(flattened["c"], 4)
        self.assertEqual(flattened["d"], 6)

        # Verify original context is unchanged
        self.assertEqual(len(context.dicts), initial_len)
        self.assertEqual(context["a"], 5)

        # Verify builtins are preserved in flattened context
        self.assertTrue(flattened["True"])
        self.assertFalse(flattened["False"])
        self.assertIsNone(flattened["None"])

    def test_set_upward_existing_key(self):
        context = BaseContext()

        # Create multiple layers
        context.push({"x": 1})
        context.push({"y": 2})
        context.push({"z": 3})

        # Set upward for key in bottom layer
        context.set_upward("x", 10)
        self.assertEqual(context["x"], 10)

        # Set upward for key in middle layer
        context.set_upward("y", 20)
        self.assertEqual(context["y"], 20)

        # Verify layers below modification point are unchanged
        self.assertEqual(context.dicts[1]["x"], 10)
        self.assertEqual(context.dicts[2]["y"], 20)

        # Verify key indices are unchanged
        self.assertEqual(context._key_index["x"], [1])
        self.assertEqual(context._key_index["y"], [2])

    def test_set_upward_new_key(self):
        context = BaseContext()

        # Create multiple layers
        context.push({"a": 1})
        context.push({"b": 2})

        # Try to set upward for non-existent key
        context.set_upward("c", 3)

        # Verify key was added to top layer
        self.assertEqual(context["c"], 3)
        self.assertEqual(context._key_index["c"], [2])

        # Verify existing keys are unchanged
        self.assertEqual(context["a"], 1)
        self.assertEqual(context["b"], 2)

        # Verify key indices are unchanged for existing keys
        self.assertEqual(context._key_index["a"], [1])
        self.assertEqual(context._key_index["b"], [2])

    def test_key_lookup_order(self):
        context = BaseContext()

        # Create layers with various patterns
        context.push({"a": 1, "b": 1, "c": 1})  # Layer 1
        context.push({"b": 2, "c": 2})  # Layer 2
        context.push({"c": 3})  # Layer 3

        # Test lookup order
        self.assertEqual(context["a"], 1)  # Only in layer 1
        self.assertEqual(context["b"], 2)  # Layer 2 shadows layer 1
        self.assertEqual(context["c"], 3)  # Layer 3 shadows layer 2

        # Pop top layer and verify new lookup order
        context.pop()
        self.assertEqual(context["c"], 2)  # Now from layer 2

        # Pop middle layer and verify final lookup order
        context.pop()
        self.assertEqual(context["c"], 1)  # Now from layer 1

    def test_copy_behavior(self):
        # To test `copy`, the __copy__ method must be called from within
        # a class that subclasses Django's BaseContext.
        class ContextSubclass(BaseContext, DjangoBaseContext):
            pass

        context = ContextSubclass()

        # Create original context with multiple layers
        context.push({"a": 1, "b": {"nested": 2}})
        context.push({"c": 3})
        original_len = len(context.dicts)

        # Create copy
        copied = copy(context)

        # Verify copy is a new context
        self.assertIsInstance(copied, ContextSubclass)
        self.assertIsNot(copied, context)

        # Verify all layers are copied
        self.assertEqual(len(copied.dicts), original_len)

        # Verify values are equal but distinct
        self.assertEqual(copied["a"], 1)
        self.assertEqual(copied["b"]["nested"], 2)
        self.assertEqual(copied["c"], 3)

        # Verify each layer is properly bound to both contexts
        for i, d in enumerate(cast(List[ContextLayer], context.dicts)):
            self.assertEqual(
                d.contexts, {id(context): ContextBinding(context, i), id(copied): ContextBinding(copied, i)}
            )

        # Verify nested dicts are only shallow copied
        self.assertIs(copied.dicts[1]["b"], context.dicts[1]["b"])

        # Modify original and verify copy is affected (since they share the same dicts)
        context.dicts[1]["a"] = 10
        context.dicts[1]["b"]["nested"] = 20
        self.assertEqual(copied["a"], 10)  # Changed from 1 to 10 since dicts are shared
        self.assertEqual(copied["b"]["nested"], 20)

        # Verify builtins are present too
        self.assertTrue(copied["True"])

    def test_push_none_behavior(self):
        context = BaseContext()

        # Test pushing None
        context.push(None)  # type: ignore

        # Verify it creates an empty layer
        self.assertEqual(len(context.dicts), 2)  # Builtins + empty layer
        self.assertEqual(len(context.dicts[-1]), 0)

        # Verify we can add to the empty layer
        context.dicts[-1]["a"] = 1
        self.assertEqual(context["a"], 1)

    def test_push_empty_dict_behavior(self):
        context = BaseContext()

        # Test pushing empty dict
        context.push({})

        # Verify it creates an empty layer
        self.assertEqual(len(context.dicts), 2)  # Builtins + empty layer
        self.assertEqual(len(context.dicts[-1]), 0)

        # Verify we can add to the empty layer
        context.dicts[-1]["a"] = 1
        self.assertEqual(context["a"], 1)

    def test_pop_to_builtins(self):
        context = BaseContext()

        # Create multiple layers
        context.push({"a": 1})
        context.push({"b": 2})

        # Pop all layers except builtins
        while len(context.dicts) > 1:
            context.pop()

        # Verify only builtins remain
        self.assertEqual(len(context.dicts), 1)
        self.assertTrue(context["True"])

        # Verify can't pop builtins layer
        with self.assertRaises(ContextPopException):
            context.pop()

    def test_flatten_empty_layers(self):
        context = BaseContext()

        # Create context with empty layers
        context.push({})
        context.push({"a": 1})
        context.push({})
        context.push({"b": 2})
        context.push({})

        # Flatten context
        flattened = context.flatten()

        # Verify all data is preserved
        self.assertEqual(flattened["a"], 1)
        self.assertEqual(flattened["b"], 2)


class EdgeCaseTests(BaseTestCase):
    def test_negative_indices(self):
        context = BaseContext()

        # Setup test data
        context.push({"a": 1})
        context.push({"b": 2})
        context.push({"c": 3})

        # Test negative index access
        self.assertEqual(context.dicts[-1]["c"], 3)
        self.assertEqual(context.dicts[-2]["b"], 2)
        self.assertEqual(context.dicts[-3]["a"], 1)

        # Test negative index insertion
        context.push({"d": 4})
        context.dicts.insert(-1, {"x": 5})
        self.assertEqual(context.dicts[-2]["x"], 5)
        self.assertEqual(context.dicts[-1]["d"], 4)

        # Test negative index deletion
        popped = context.dicts.pop(-2)
        self.assertEqual(popped["x"], 5)
        self.assertEqual(context.dicts[-1]["d"], 4)

        # Test out of bounds negative index
        with self.assertRaises(IndexError):
            _ = context.dicts[-10]

    def test_invalid_operations(self):
        # Test popping from empty context (except builtins)
        context = BaseContext()
        with self.assertRaises(ContextPopException):
            context.pop()

        # Test popping builtins layer
        context = BaseContext()
        context.dicts.pop(0)

        # Test inserting before builtins layer
        context = BaseContext()
        context.dicts.insert(0, {"x": 1})

        # Test deleting builtins layer
        context = BaseContext()
        del context.dicts[0]

        # Test assigning to builtins layer
        context = BaseContext()
        context.dicts[0] = {"x": 1}

        # Test clearing builtins
        context = BaseContext()
        context.dicts.clear()
        self.assertEqual(len(context.dicts), 0)

        # Test non-string keys
        context = BaseContext({123: "a", None: "b"})
        self.assertEqual(context[123], "a")  # type: ignore
        self.assertEqual(context[None], "b")  # type: ignore

        # Test modifying read-only builtins
        context = BaseContext()
        context.dicts[0]["True"] = False
        self.assertEqual(context["True"], False)

    def test_slice_operations(self):
        context = BaseContext()

        # Setup test data
        context.push({"a": 1})
        context.push({"b": 2})
        context.push({"c": 3})
        context.push({"d": 4})
        context.push({"e": 5})
        initial_len = len(context.dicts)

        # Test basic slicing
        slice_view = context.dicts[2:4]
        self.assertEqual(len(slice_view), 2)
        self.assertEqual(slice_view[0]["b"], 2)
        self.assertEqual(slice_view[1]["c"], 3)

        # Test slice with step
        slice_view = context.dicts[1::2]  # Every other layer
        self.assertEqual(len(slice_view), 3)
        self.assertEqual(slice_view[0]["a"], 1)
        self.assertEqual(slice_view[1]["c"], 3)
        self.assertEqual(slice_view[2]["e"], 5)

        # Test negative slice indices
        slice_view = context.dicts[-3:-1]
        self.assertEqual(len(slice_view), 2)
        self.assertEqual(slice_view[0]["c"], 3)
        self.assertEqual(slice_view[1]["d"], 4)

        # Test slice deletion
        del context.dicts[2:4]
        self.assertEqual(len(context.dicts), initial_len - 2)
        self.assertEqual(context.dicts[1]["a"], 1)
        self.assertEqual(context.dicts[2]["d"], 4)
        self.assertEqual(context.dicts[3]["e"], 5)

        # Test slice assignment
        context.dicts[1:3] = [{"x": 6}, {"y": 7}]
        self.assertEqual(context.dicts[1]["x"], 6)
        self.assertEqual(context.dicts[2]["y"], 7)

        # Test SIMPLE slice with different length assignment is OK
        context.dicts[1:2] = [{"p": 8}, {"q": 9}]
        self.assertEqual(context.dicts[1]["p"], 8)
        self.assertEqual(context.dicts[2]["q"], 9)

        # Test EXTENDED slice (with step) with different length assignment
        with self.assertRaises(ValueError):
            context.dicts[1:2:3] = [{"p": 8}, {"q": 9}]  # Too many items

        # Test slice including builtins
        del context.dicts[0:2]  # Can't delete builtins
