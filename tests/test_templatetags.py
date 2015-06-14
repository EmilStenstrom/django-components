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
        js = ("script.js",)

class ComponentTemplateTagTest(unittest.TestCase):
    def test_component_dependencies(self):
        component.registry.register(name="test", component=SimpleComponent)

        template = Template('{% load component_tags %}{% component_dependencies %}')
        rendered = template.render(Context())
        self.assertEqual(rendered, dedent("""
            <link href="style.css" type="text/css" media="all" rel="stylesheet" />
            <script type="text/javascript" src="script.js"></script>
        """).strip())
