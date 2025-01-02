"""Catch-all for tests that use template tags and don't fit other files"""

from typing import Callable

from django.template import Context, Template

from django_components import Component, register, registry, types

from .django_test_setup import setup_test_config
from .testutils import BaseTestCase, parametrize_context_behavior

setup_test_config({"autodiscover": False})


class SlottedComponent(Component):
    template_file = "slotted_template.html"


def _get_templates_used_to_render(subject_template, render_context=None):
    """Emulate django.test.client.Client (see request method)."""
    from django.test.signals import template_rendered

    templates_used = []

    def receive_template_signal(sender, template, context, **_kwargs):
        templates_used.append(template.name)

    template_rendered.connect(receive_template_signal, dispatch_uid="test_method")
    subject_template.render(render_context or Context({}))
    template_rendered.disconnect(dispatch_uid="test_method")
    return templates_used


class TemplateSignalTest(BaseTestCase):
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

    @parametrize_context_behavior(["django", "isolated"])
    def test_template_rendered(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test_component' %}{% endcomponent %}
        """
        template = Template(template_str, name="root")
        templates_used = _get_templates_used_to_render(template)
        self.assertIn("slotted_template.html", templates_used)

    @parametrize_context_behavior(["django", "isolated"])
    def test_template_rendered_nested_components(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test_component' %}
              {% fill "header" %}
                {% component 'inner_component' variable='foo' %}{% endcomponent %}
              {% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str, name="root")
        templates_used = _get_templates_used_to_render(template)
        self.assertIn("slotted_template.html", templates_used)
        self.assertIn("simple_template.html", templates_used)
