import unittest
from django_components import component

class MockComponent(object):
    pass

class ComponentRegistryTest(unittest.TestCase):
    def setUp(self):
        self.registry = component.ComponentRegistry()

    def test_simple_register(self):
        self.registry.register(name="testcomponent", component=MockComponent)
        self.assertEqual(
            self.registry._registry.items(),
            [("testcomponent", MockComponent)]
        )

    def test_register_two_components(self):
        self.registry.register(name="testcomponent", component=MockComponent)
        self.registry.register(name="testcomponent2", component=MockComponent)
        self.assertEqual(
            self.registry._registry.items(),
            [("testcomponent", MockComponent), ("testcomponent2", MockComponent)]
        )

    def test_prevent_registering_twice(self):
        self.registry.register(name="testcomponent", component=MockComponent)
        with self.assertRaises(component.AlreadyRegistered):
            self.registry.register(name="testcomponent", component=MockComponent)

    def test_simple_unregister(self):
        self.registry.register(name="testcomponent", component=MockComponent)
        self.registry.unregister(name="testcomponent")
        self.assertEqual(self.registry._registry.items(), [])

    def test_raises_on_failed_unregister(self):
        with self.assertRaises(component.NotRegistered):
            self.registry.unregister(name="testcomponent")
