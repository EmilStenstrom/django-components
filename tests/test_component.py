from textwrap import dedent

from django.test import SimpleTestCase

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

class MultistyleComponent(SimpleComponent):
    class Media:
        css = {"all": ["style.css", "style2.css"]}
        js = ["script.js", "script2.js"]

class ComponentRegistryTest(SimpleTestCase):
    def test_simple_component(self):
        comp = SimpleComponent()

        self.assertHTMLEqual(comp.render_dependencies(), dedent("""
            <link href="style.css" type="text/css" media="all" rel="stylesheet">
            <script type="text/javascript" src="script.js"></script>
        """).strip())

        self.assertHTMLEqual(comp.render(variable="test"), dedent("""
            Variable: <strong>test</strong>
        """).lstrip())

    def test_component_with_list_of_styles(self):
        comp = MultistyleComponent()

        self.assertHTMLEqual(comp.render_dependencies(), dedent("""
            <link href="style.css" type="text/css" media="all" rel="stylesheet">
            <link href="style2.css" type="text/css" media="all" rel="stylesheet">
            <script type="text/javascript" src="script.js"></script>
            <script type="text/javascript" src="script2.js"></script>
        """).strip())
