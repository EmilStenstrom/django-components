from textwrap import dedent
import unittest
from django_components import component
from .django_test_setup import *  # NOQA

class SimpleComponent(component.Component):
    def context(self, variable=None):
        return {
            "variable": variable,
        }

    def template(self, context):
        return "simple_template.html"

    class Media:
        css = {"all": ["style.css"]}
        js = ["script.js"]

class ComponentRegistryTest(unittest.TestCase):
    def test_simple_component(self):
        comp = SimpleComponent()

        self.assertEqual(comp.render_dependencies(), dedent("""
            <link href="style.css" type="text/css" media="all" rel="stylesheet" />
            <script type="text/javascript" src="script.js"></script>
        """).strip())

        self.assertEqual(comp.render(variable="test"), dedent("""
            Variable: <strong>test</strong>
        """).lstrip())
