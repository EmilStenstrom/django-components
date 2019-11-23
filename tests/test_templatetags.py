from textwrap import dedent
import unittest
from django.template import Template, Context
from django_components import component
from .django_test_setup import *  # NOQA

class SimpleComponent(component.Component):
    def context(self, variable):
        return {
            "variable": variable,
        }

    class Media:
        template = "simple_template.html"
        css = {"all": "style.css"}
        js = ["script.js"]

class ComponentTemplateTagTest(unittest.TestCase):
    def setUp(self):
        # NOTE: component.registry is global, so need to clear before each test
        component.registry._registry = {}

    def test_single_component_dependencies(self):
        component.registry.register(name="test", component=SimpleComponent)

        template = Template('{% load component_tags %}{% component_dependencies %}')
        rendered = template.render(Context())
        self.assertEqual(rendered, dedent("""
            <link href="style.css" type="text/css" media="all" rel="stylesheet" />
            <script type="text/javascript" src="script.js"></script>
        """).strip())

    def test_single_component(self):
        component.registry.register(name="test", component=SimpleComponent)

        template = Template('{% load component_tags %}{% component name="test" variable="variable" %}')
        rendered = template.render(Context({}))
        self.assertEqual(rendered, "Variable: <strong>variable</strong>\n")

    def test_multiple_component_dependencies(self):
        component.registry.register(name="test1", component=SimpleComponent)
        component.registry.register(name="test2", component=SimpleComponent)

        template = Template('{% load component_tags %}{% component_dependencies %}')
        rendered = template.render(Context())
        self.assertEqual(rendered, dedent("""
            <link href="style.css" type="text/css" media="all" rel="stylesheet" />
            <script type="text/javascript" src="script.js"></script>
        """).strip())
