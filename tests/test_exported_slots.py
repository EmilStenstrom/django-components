from django.template import Context, Template

from .django_test_setup import *  # NOQA
from django_components import component

from .testutils import Django30CompatibleSimpleTestCase as SimpleTestCase


@component.register('inner')
class SlottedComponent(component.Component):
    template_name = "slotted_template.html"


@component.register('outer')
class ExportingComponent(component.Component):
    template_name = "exporting_template.html"


class ExportedSlotTests(SimpleTestCase):
    def test_can_pass_content_slot_to_outer_component(self):
        template = Template(
            """
            {% load component_tags %}
            {% component_block "outer" %}
                {% slot exported_header %}Override header{% endslot %}
            {% endcomponent_block %}
        """
        )

        rendered = template.render(Context({}))

        self.assertHTMLEqual(
            rendered,
            """
            <custom-template>
                <header>Override header</header>
                <main>Replacement main</main>
                <footer>Default footer</footer>
            </custom-template>
        """,
        )

    def test_can_override_new_default_content(self):
        template = Template(
            """
            {% load component_tags %}
            {% component_block "outer" %}
                {% slot exported_main %}Override main{% endslot %}
            {% endcomponent_block %}
        """
        )

        rendered = template.render(Context({}))

        self.assertHTMLEqual(
            rendered,
            """
            <custom-template>
                <header>Default header</header>
                <main>Override main</main>
                <footer>Default footer</footer>
            </custom-template>
        """,
        )

    def test_ignores_attempt_to_fill_unexported_slot(self):
        template = Template(
            """
            {% load component_tags %}
            {% component_block "outer" %}
                {% slot "footer" %}Override main{% endslot %}
            {% endcomponent_block %}
        """
        )

        rendered = template.render(Context({}))

        self.assertHTMLEqual(
            rendered,
            """
            <custom-template>
                <header>Default header</header>
                <main>Replacement main</main>
                <footer>Default footer</footer>
            </custom-template>
        """,
        )
