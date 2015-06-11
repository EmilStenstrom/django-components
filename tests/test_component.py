import unittest
from django_components import component

class ComponentRegistryTest(unittest.TestCase):
    def test_simple_component(self):
        class MyComponent(component.Component):
            pass

        comp = MyComponent()

        self.assertEqual(comp.context(), {})
        self.assertEqual(comp._media.template, None)
        self.assertEqual(comp._media.css, {})
        self.assertEqual(comp._media.js, ())
