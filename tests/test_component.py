from textwrap import dedent

from django.template import Context, Template

from .django_test_setup import *  # NOQA

from django_components import component
from .testutils import Django30CompatibleSimpleTestCase as SimpleTestCase


class ComponentTest(SimpleTestCase):
    def test_empty_component(self):
        class EmptyComponent(component.Component):
            pass

        with self.assertRaises(NotImplementedError):
            EmptyComponent("empty_component").template({})

    def test_simple_component(self):
        class SimpleComponent(component.Component):
            def context(self, variable=None):
                return {
                    "variable": variable,
                }

            def template(self, context):
                return "simple_template.html"

            class Media:
                css = "style.css"
                js = "script.js"

        comp = SimpleComponent("simple_component")
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
                css = ["style.css", "style2.css"]
                js = ["script.js", "script2.js"]

        comp = MultistyleComponent("multistyle_component")

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

        comp = FilteredComponent("filtered_component")
        context = Context(comp.context(var1="test1", var2="test2"))

        self.assertHTMLEqual(comp.render(context), dedent("""
            Var1: <strong>test1</strong>
            Var2 (uppercased): <strong>TEST2</strong>
        """).lstrip())

    def test_component_with_dynamic_template(self):
        class SvgComponent(component.Component):
            def context(self, name, css_class="", title="", **attrs):
                return {"name": name, "css_class": css_class, "title": title, **attrs}

            def template(self, context):
                return f"svg_{context['name']}.svg"

        comp = SvgComponent("svg_component")
        self.assertHTMLEqual(
            comp.render(Context(comp.context(name="dynamic1"))),
            dedent("""\
                <svg>Dynamic1</svg>
            """)
        )
        self.assertHTMLEqual(
            comp.render(Context(comp.context(name="dynamic2"))),
            dedent("""\
                <svg>Dynamic2</svg>
            """)
        )


class ComponentMediaTests(SimpleTestCase):
    def test_component_media_with_strings(self):
        class SimpleComponent(component.Component):
            class Media:
                css = "path/to/style.css"
                js = "path/to/script.js"

        comp = SimpleComponent("")
        self.assertHTMLEqual(
            comp.render_dependencies(),
            dedent("""\
                <link href="path/to/style.css" type="text/css" media="all" rel="stylesheet">
                <script src="path/to/script.js"></script>
            """)
        )

    def test_component_media_with_lists(self):
        class SimpleComponent(component.Component):
            class Media:
                css = ["path/to/style.css", "path/to/style2.css"]
                js = ["path/to/script.js"]

        comp = SimpleComponent("")
        self.assertHTMLEqual(
            comp.render_dependencies(),
            dedent("""\
                <link href="path/to/style.css" type="text/css" media="all" rel="stylesheet">
                <link href="path/to/style2.css" type="text/css" media="all" rel="stylesheet">
                <script src="path/to/script.js"></script>
            """)
        )

    def test_component_media_with_dict_and_list(self):
        class SimpleComponent(component.Component):
            class Media:
                css = {
                    "all": "path/to/style.css",
                    "print": ["path/to/style2.css"],
                    "screen": "path/to/style3.css",
                }
                js = ["path/to/script.js"]

        comp = SimpleComponent("")
        self.assertHTMLEqual(
            comp.render_dependencies(),
            dedent("""\
                <link href="path/to/style.css" type="text/css" media="all" rel="stylesheet">
                <link href="path/to/style2.css" type="text/css" media="print" rel="stylesheet">
                <link href="path/to/style3.css" type="text/css" media="screen" rel="stylesheet">
                <script src="path/to/script.js"></script>
            """)
        )

    def test_component_media_with_dict_with_list_and_list(self):
        class SimpleComponent(component.Component):
            class Media:
                css = {"all": ["path/to/style.css"]}
                js = ["path/to/script.js"]

        comp = SimpleComponent("")
        self.assertHTMLEqual(
            comp.render_dependencies(),
            dedent("""\
                <link href="path/to/style.css" type="text/css" media="all" rel="stylesheet">
                <script src="path/to/script.js"></script>
            """)
        )


class ComponentIsolationTests(SimpleTestCase):
    def setUp(self):
        class SlottedComponent(component.Component):
            def template(self, context):
                return "slotted_template.html"

        component.registry.register('test', SlottedComponent)

    def test_instances_of_component_do_not_share_slots(self):
        template = Template(
            """
            {% load component_tags %}
            {% component_block "test" %}
                {% slot "header" %}Override header{% endslot %}
            {% endcomponent_block %}
            {% component_block "test" %}
                {% slot "main" %}Override main{% endslot %}
            {% endcomponent_block %}
            {% component_block "test" %}
                {% slot "footer" %}Override footer{% endslot %}
            {% endcomponent_block %}
        """
        )

        template.render(Context({}))
        rendered = template.render(Context({}))

        self.assertHTMLEqual(
            rendered,
            """
            <custom-template>
                <header>Override header</header>
                <main>Default main</main>
                <footer>Default footer</footer>
            </custom-template>
            <custom-template>
                <header>Default header</header>
                <main>Override main</main>
                <footer>Default footer</footer>
            </custom-template>
            <custom-template>
                <header>Default header</header>
                <main>Default main</main>
                <footer>Override footer</footer>
            </custom-template>
        """
        )
