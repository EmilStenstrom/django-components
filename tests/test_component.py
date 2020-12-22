from textwrap import dedent

from django.template import Context

from django_components import component

from .django_test_setup import *  # NOQA
from .testutils import Django111CompatibleSimpleTestCase as SimpleTestCase


class ComponentRegistryTest(SimpleTestCase):
    def test_empty_component(self):
        class EmptyComponent(component.Component):
            pass

        with self.assertRaises(NotImplementedError):
            EmptyComponent().template({})

    def test_simple_component(self):
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

        comp = SimpleComponent()
        context = Context(comp.context(variable="test"))

        self.assertHTMLEqual(comp.render_dependencies(), dedent("""
            <link href="style.css" type="text/css" media="all" rel="stylesheet">
            <script src="script.js"></script>
        """).strip())

        self.assertHTMLEqual(comp.render(context), dedent("""
            Variable: <strong>test</strong>
        """).lstrip())

    def test_component_with_list_of_styles(self):
        class MultistyleComponent(component.Component):
            class Media:
                css = {"all": ["style.css", "style2.css"]}
                js = ["script.js", "script2.js"]

        comp = MultistyleComponent()

        self.assertHTMLEqual(comp.render_dependencies(), dedent("""
            <link href="style.css" type="text/css" media="all" rel="stylesheet">
            <link href="style2.css" type="text/css" media="all" rel="stylesheet">
            <script src="script.js"></script>
            <script src="script2.js"></script>
        """).strip())

    def test_component_with_filtered_template(self):
        class FilteredComponent(component.Component):
            def context(self, var1=None, var2=None):
                return {
                    "var1": var1,
                    "var2": var2,
                }

            def template(self, context):
                return "filtered_template.html"

        comp = FilteredComponent()
        context = Context(comp.context(var1="test1", var2="test2"))

        self.assertHTMLEqual(comp.render(context), dedent("""
            Var1: <strong>test1</strong>
            Var2 (uppercased): <strong>TEST2</strong>
        """).lstrip())
