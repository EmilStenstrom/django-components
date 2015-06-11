import unittest
from django_components import component

class SimpleComponent(component.Component):
    def context(self, variable):
        return {
            "variable": variable,
        }

    class Media:
        template = "template.html"
        css = {"all": "style.css"}
        js = ("script.js",)

class ComponentRegistryTest(unittest.TestCase):
    def test_simple_component(self):

        comp = SimpleComponent()

        self.assertEqual(comp.context("test"), {"variable": "test"})
        self.assertEqual(comp._media.template, "template.html")
        self.assertEqual(comp._media.css, {"all": "style.css"})
        self.assertEqual(comp._media.js, ("script.js",))
