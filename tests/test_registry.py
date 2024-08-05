import unittest

from django.template import Library

from django_components import AlreadyRegistered, Component, ComponentRegistry, NotRegistered, register, registry

from .django_test_setup import setup_test_config

setup_test_config()


class MockComponent(Component):
    pass


class MockComponent2(Component):
    pass


class MockComponentView(Component):
    def get(self, request, *args, **kwargs):
        pass


class ComponentRegistryTest(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.registry = ComponentRegistry()

    def test_register_class_decorator(self):
        @register("decorated_component")
        class TestComponent(Component):
            pass

        self.assertEqual(registry.get("decorated_component"), TestComponent)

        # Cleanup
        registry.unregister("decorated_component")

    def test_register_class_decorator_custom_registry(self):
        my_lib = Library()
        my_reg = ComponentRegistry(library=my_lib)

        self.assertDictEqual(my_reg.all(), {})
        self.assertDictEqual(registry.all(), {})

        @register("decorated_component", registry=my_reg)
        class TestComponent(Component):
            pass

        self.assertDictEqual(my_reg.all(), {"decorated_component": TestComponent})
        self.assertDictEqual(registry.all(), {})

    def test_simple_register(self):
        self.registry.register(name="testcomponent", component=MockComponent)
        self.assertEqual(self.registry.all(), {"testcomponent": MockComponent})

    def test_register_two_components(self):
        self.registry.register(name="testcomponent", component=MockComponent)
        self.registry.register(name="testcomponent2", component=MockComponent)
        self.assertEqual(
            self.registry.all(),
            {
                "testcomponent": MockComponent,
                "testcomponent2": MockComponent,
            },
        )

    def test_unregisters_only_unused_tags(self):
        self.assertDictEqual(self.registry._tags, {})
        # NOTE: We preserve the default component tags
        self.assertIn("component", self.registry.library.tags)

        # Register two components that use the same tag
        self.registry.register(name="testcomponent", component=MockComponent)
        self.registry.register(name="testcomponent2", component=MockComponent)

        self.assertDictEqual(
            self.registry._tags,
            {
                "#component": {"testcomponent", "testcomponent2"},
                "component": {"testcomponent", "testcomponent2"},
            },
        )

        self.assertIn("component", self.registry.library.tags)

        # Unregister only one of the components. The tags should remain
        self.registry.unregister(name="testcomponent")

        self.assertDictEqual(
            self.registry._tags,
            {
                "#component": {"testcomponent2"},
                "component": {"testcomponent2"},
            },
        )

        self.assertIn("component", self.registry.library.tags)

        # Unregister the second components. The tags should be removed
        self.registry.unregister(name="testcomponent2")

        self.assertDictEqual(self.registry._tags, {})
        self.assertIn("component", self.registry.library.tags)

    def test_prevent_registering_different_components_with_the_same_name(self):
        self.registry.register(name="testcomponent", component=MockComponent)
        with self.assertRaises(AlreadyRegistered):
            self.registry.register(name="testcomponent", component=MockComponent2)

    def test_allow_duplicated_registration_of_the_same_component(self):
        try:
            self.registry.register(name="testcomponent", component=MockComponentView)
            self.registry.register(name="testcomponent", component=MockComponentView)
        except AlreadyRegistered:
            self.fail("Should not raise AlreadyRegistered")

    def test_simple_unregister(self):
        self.registry.register(name="testcomponent", component=MockComponent)
        self.registry.unregister(name="testcomponent")
        self.assertEqual(self.registry.all(), {})

    def test_raises_on_failed_unregister(self):
        with self.assertRaises(NotRegistered):
            self.registry.unregister(name="testcomponent")
