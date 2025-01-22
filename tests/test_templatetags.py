"""Catch-all for tests that use template tags and don't fit other files"""

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

    # See https://github.com/django-components/django-components/discussions/671
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
