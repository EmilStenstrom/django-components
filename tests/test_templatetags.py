"""Catch-all for tests that use template tags and don't fit other files"""

from typing import Callable

from django.template import Context, Template

from django_components import Component, register, registry, types

from .django_test_setup import setup_test_config
from .testutils import BaseTestCase, parametrize_context_behavior

setup_test_config({"autodiscover": False})


class SlottedComponent(Component):
    template_file = "slotted_template.html"


#######################
# TESTS
#######################


class TemplateInstrumentationTest(BaseTestCase):
    saved_render_method: Callable  # Assigned during setup.

    def tearDown(self):
        super().tearDown()
        Template._render = self.saved_render_method

    def setUp(self):
        """Emulate Django test instrumentation for TestCase (see setup_test_environment)"""
        super().setUp()

        from django.test.utils import instrumented_test_render

        self.saved_render_method = Template._render
        Template._render = instrumented_test_render

        registry.clear()
        registry.register("test_component", SlottedComponent)

        @register("inner_component")
        class SimpleComponent(Component):
            template_file = "simple_template.html"

            def get_context_data(self, variable, variable2="default"):
                return {
                    "variable": variable,
                    "variable2": variable2,
                }

            class Media:
                css = "style.css"
                js = "script.js"

    def templates_used_to_render(self, subject_template, render_context=None):
        """Emulate django.test.client.Client (see request method)."""
        from django.test.signals import template_rendered

        templates_used = []

        def receive_template_signal(sender, template, context, **_kwargs):
            templates_used.append(template.name)

        template_rendered.connect(receive_template_signal, dispatch_uid="test_method")
        subject_template.render(render_context or Context({}))
        template_rendered.disconnect(dispatch_uid="test_method")
        return templates_used

    @parametrize_context_behavior(["django", "isolated"])
    def test_template_shown_as_used(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test_component' %}{% endcomponent %}
        """
        template = Template(template_str, name="root")
        templates_used = self.templates_used_to_render(template)
        self.assertIn("slotted_template.html", templates_used)

    @parametrize_context_behavior(["django", "isolated"])
    def test_nested_component_templates_all_shown_as_used(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test_component' %}
              {% fill "header" %}
                {% component 'inner_component' variable='foo' %}{% endcomponent %}
              {% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str, name="root")
        templates_used = self.templates_used_to_render(template)
        self.assertIn("slotted_template.html", templates_used)
        self.assertIn("simple_template.html", templates_used)


class MultilineTagsTests(BaseTestCase):
    @parametrize_context_behavior(["django", "isolated"])
    def test_multiline_tags(self):
        @register("test_component")
        class SimpleComponent(Component):
            template: types.django_html = """
                Variable: <strong>{{ variable }}</strong>
            """

            def get_context_data(self, variable, variable2="default"):
                return {
                    "variable": variable,
                    "variable2": variable2,
                }

        template: types.django_html = """
            {% load component_tags %}
            {% component
                "test_component"
                123
                variable2="abc"
            %}
            {% endcomponent %}
        """
        rendered = Template(template).render(Context())
        expected = """
            Variable: <strong data-djc-id-a1bc3f>123</strong>
        """
        self.assertHTMLEqual(rendered, expected)


class NestedTagsTests(BaseTestCase):
    class SimpleComponent(Component):
        template: types.django_html = """
            Variable: <strong>{{ var }}</strong>
        """

        def get_context_data(self, var):
            return {
                "var": var,
            }

    # See https://github.com/EmilStenstrom/django-components/discussions/671
    @parametrize_context_behavior(["django", "isolated"])
    def test_nested_tags(self):
        registry.register("test", self.SimpleComponent)

        template: types.django_html = """
            {% load component_tags %}
            {% component "test" var="{% lorem 1 w %}" %}{% endcomponent %}
        """
        rendered = Template(template).render(Context())
        expected = """
            Variable: <strong data-djc-id-a1bc3f>lorem</strong>
        """
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["django", "isolated"])
    def test_nested_quote_single(self):
        registry.register("test", self.SimpleComponent)

        template: types.django_html = """
            {% load component_tags %}
            {% component "test" var=_("organisation's") %} {% endcomponent %}
        """
        rendered = Template(template).render(Context())
        expected = """
            Variable: <strong data-djc-id-a1bc3f>organisation&#x27;s</strong>
        """
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["django", "isolated"])
    def test_nested_quote_single_self_closing(self):
        registry.register("test", self.SimpleComponent)

        template: types.django_html = """
            {% load component_tags %}
            {% component "test" var=_("organisation's") / %}
        """
        rendered = Template(template).render(Context())
        expected = """
            Variable: <strong data-djc-id-a1bc3f>organisation&#x27;s</strong>
        """
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["django", "isolated"])
    def test_nested_quote_double(self):
        registry.register("test", self.SimpleComponent)

        template: types.django_html = """
            {% load component_tags %}
            {% component "test" var=_('organisation"s') %} {% endcomponent %}
        """
        rendered = Template(template).render(Context())
        expected = """
            Variable: <strong data-djc-id-a1bc3f>organisation"s</strong>
        """
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["django", "isolated"])
    def test_nested_quote_double_self_closing(self):
        registry.register("test", self.SimpleComponent)

        template: types.django_html = """
            {% load component_tags %}
            {% component "test" var=_('organisation"s') / %}
        """
        rendered = Template(template).render(Context())
        expected = """
            Variable: <strong data-djc-id-a1bc3f>organisation"s</strong>
        """
        self.assertHTMLEqual(rendered, expected)
