"""
Tests focusing on the Component class.
For tests focusing on the `component` tag, see `test_templatetags_component.py`
"""

from django.core.exceptions import ImproperlyConfigured
from django.template import Context

# isort: off
from .django_test_setup import *  # NOQA
from .testutils import BaseTestCase, parametrize_context_behavior

# isort: on

from django_components import component, types


class ComponentTest(BaseTestCase):
    class ParentComponent(component.Component):
        template: types.django_html = """
            {% load component_tags %}
            <div>
                <h1>Parent content</h1>
                {% component name="variable_display" shadowing_variable='override' new_variable='unique_val' %}
                {% endcomponent %}
            </div>
            <div>
                {% slot 'content' %}
                    <h2>Slot content</h2>
                    {% component name="variable_display" shadowing_variable='slot_default_override' new_variable='slot_default_unique' %}
                    {% endcomponent %}
                {% endslot %}
            </div>
        """  # noqa

        def get_context_data(self):
            return {"shadowing_variable": "NOT SHADOWED"}

    class VariableDisplay(component.Component):
        template: types.django_html = """
            {% load component_tags %}
            <h1>Shadowing variable = {{ shadowing_variable }}</h1>
            <h1>Uniquely named variable = {{ unique_variable }}</h1>
        """

        def get_context_data(self, shadowing_variable=None, new_variable=None):
            context = {}
            if shadowing_variable is not None:
                context["shadowing_variable"] = shadowing_variable
            if new_variable is not None:
                context["unique_variable"] = new_variable
            return context

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        component.registry.register(name="parent_component", component=cls.ParentComponent)
        component.registry.register(name="variable_display", component=cls.VariableDisplay)

    @parametrize_context_behavior(["django", "isolated"])
    def test_empty_component(self):
        class EmptyComponent(component.Component):
            pass

        with self.assertRaises(ImproperlyConfigured):
            EmptyComponent("empty_component").get_template(Context({}))

    @parametrize_context_behavior(["django", "isolated"])
    def test_simple_component(self):
        class SimpleComponent(component.Component):
            template: types.django_html = """
                Variable: <strong>{{ variable }}</strong>
            """

            def get_context_data(self, variable=None):
                return {
                    "variable": variable,
                }

            class Media:
                css = "style.css"
                js = "script.js"

        comp = SimpleComponent("simple_component")
        context = Context(comp.get_context_data(variable="test"))

        self.assertHTMLEqual(
            comp.render_dependencies(),
            """
                <link href="style.css" media="all" rel="stylesheet">
                <script src="script.js"></script>
            """,
        )

        self.assertHTMLEqual(
            comp.render(context),
            """
            Variable: <strong>test</strong>
            """,
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_component_with_dynamic_template(self):
        class SvgComponent(component.Component):
            def get_context_data(self, name, css_class="", title="", **attrs):
                return {
                    "name": name,
                    "css_class": css_class,
                    "title": title,
                    **attrs,
                }

            def get_template_name(self, context):
                return f"dynamic_{context['name']}.svg"

        comp = SvgComponent("svg_component")
        self.assertHTMLEqual(
            comp.render(Context(comp.get_context_data(name="svg1"))),
            """
            <svg>Dynamic1</svg>
            """,
        )
        self.assertHTMLEqual(
            comp.render(Context(comp.get_context_data(name="svg2"))),
            """
            <svg>Dynamic2</svg>
            """,
        )
