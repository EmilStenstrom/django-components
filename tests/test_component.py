from textwrap import dedent

from django.test import SimpleTestCase

from django_components import component

from .django_test_setup import *  # NOQA


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

        self.assertHTMLEqual(comp.render_dependencies(), dedent("""
            <link href="style.css" type="text/css" media="all" rel="stylesheet">
            <script type="text/javascript" src="script.js"></script>
        """).strip())

        self.assertHTMLEqual(comp.render(variable="test"), dedent("""
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
            <script type="text/javascript" src="script.js"></script>
            <script type="text/javascript" src="script2.js"></script>
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

        self.assertHTMLEqual(comp.render(var1="test1", var2="test2"), dedent("""
            Var1: <strong>test1</strong>
            Var2 (uppercased): <strong>TEST2</strong>
        """).lstrip())
