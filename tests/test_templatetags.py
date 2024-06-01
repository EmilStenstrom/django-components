"""Catch-all for tests that use template tags and don't fit other files"""

from typing import Callable

from django.template import Context, Template

# isort: off
from .django_test_setup import *  # NOQA
from .testutils import BaseTestCase, parametrize_context_behavior

# isort: on

from django_components import component, types


class SlottedComponent(component.Component):
    template_name = "slotted_template.html"


#######################
# TESTS
#######################


class TemplateInstrumentationTest(BaseTestCase):
    saved_render_method: Callable  # Assigned during setup.

    @classmethod
    def setUpClass(cls):
        """Emulate Django test instrumentation for TestCase (see setup_test_environment)"""
        from django.test.utils import instrumented_test_render

        cls.saved_render_method = Template._render
        Template._render = instrumented_test_render

    @classmethod
    def tearDownClass(cls):
        Template._render = cls.saved_render_method

    def setUp(self):
        component.registry.clear()
        component.registry.register("test_component", SlottedComponent)

        @component.register("inner_component")
        class SimpleComponent(component.Component):
            template_name = "simple_template.html"

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


class BlockCompatTests(BaseTestCase):
    def setUp(self):
        component.registry.clear()
        super().setUp()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        component.registry.clear()

    @parametrize_context_behavior(["django", "isolated"])
    def test_slots_inside_extends(self):
        component.registry.register("slotted_component", SlottedComponent)

        @component.register("slot_inside_extends")
        class SlotInsideExtendsComponent(component.Component):
            template: types.django_html = """
                {% extends "block_in_slot_in_component.html" %}
            """

        template: types.django_html = """
            {% load component_tags %}
            {% component "slot_inside_extends" %}
                {% fill "body" %}
                    BODY_FROM_FILL
                {% endfill %}
            {% endcomponent %}
        """
        rendered = Template(template).render(Context())
        expected = """
            <!DOCTYPE html>
            <html lang="en">
            <body>
                <custom-template>
                <header></header>
                <main>BODY_FROM_FILL</main>
                <footer>Default footer</footer>
                </custom-template>
            </body>
            </html>
        """
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["django", "isolated"])
    def test_slots_inside_include(self):
        component.registry.register("slotted_component", SlottedComponent)

        @component.register("slot_inside_include")
        class SlotInsideIncludeComponent(component.Component):
            template: types.django_html = """
                {% include "block_in_slot_in_component.html" %}
            """

        template: types.django_html = """
            {% load component_tags %}
            {% component "slot_inside_include" %}
                {% fill "body" %}
                    BODY_FROM_FILL
                {% endfill %}
            {% endcomponent %}
        """
        rendered = Template(template).render(Context())
        expected = """
            <!DOCTYPE html>
            <html lang="en">
            <body>
                <custom-template>
                <header></header>
                <main>BODY_FROM_FILL</main>
                <footer>Default footer</footer>
                </custom-template>
            </body>
            </html>
        """
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["django", "isolated"])
    def test_component_inside_block(self):
        component.registry.register("slotted_component", SlottedComponent)
        template: types.django_html = """
            {% extends "block.html" %}
            {% load component_tags %}
            {% block body %}
            {% component "slotted_component" %}
                {% fill "header" %}{% endfill %}
                {% fill "main" %}
                TEST
                {% endfill %}
                {% fill "footer" %}{% endfill %}
            {% endcomponent %}
            {% endblock %}
        """
        rendered = Template(template).render(Context())
        expected = """
            <!DOCTYPE html>
            <html lang="en">
            <body>
            <main role="main">
            <div class='container main-container'>
                <custom-template>
                <header></header>
                <main>TEST</main>
                <footer></footer>
                </custom-template>
            </div>
            </main>
            </body>
            </html>
        """
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["django", "isolated"])
    def test_block_inside_component(self):
        component.registry.register("slotted_component", SlottedComponent)

        template: types.django_html = """
            {% extends "block_in_component.html" %}
            {% load component_tags %}
            {% block body %}
            <div>
                58 giraffes and 2 pantaloons
            </div>
            {% endblock %}
        """
        rendered = Template(template).render(Context())
        expected = """
            <!DOCTYPE html>
            <html lang="en">
            <body>
                <custom-template>
                <header></header>
                <main>
                    <div> 58 giraffes and 2 pantaloons </div>
                </main>
                <footer>Default footer</footer>
                </custom-template>
            </body>
            </html>
        """
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["django", "isolated"])
    def test_block_inside_component_parent(self):
        component.registry.register("slotted_component", SlottedComponent)

        @component.register("block_in_component_parent")
        class BlockInCompParent(component.Component):
            template_name = "block_in_component_parent.html"

        template: types.django_html = """
            {% load component_tags %}
            {% component "block_in_component_parent" %}{% endcomponent %}
        """
        rendered = Template(template).render(Context())
        expected = """
            <!DOCTYPE html>
            <html lang="en">
            <body>
                <custom-template>
                <header></header>
                <main>
                    <div> 58 giraffes and 2 pantaloons </div>
                </main>
                <footer>Default footer</footer>
                </custom-template>
            </body>
            </html>
        """
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["django", "isolated"])
    def test_block_does_not_affect_inside_component(self):
        """
        Assert that when we call a component with `{% component %}`, that
        the `{% block %}` will NOT affect the inner component.
        """
        component.registry.register("slotted_component", SlottedComponent)

        @component.register("block_inside_slot_v1")
        class BlockInSlotInComponent(component.Component):
            template_name = "block_in_slot_in_component.html"

        template: types.django_html = """
            {% load component_tags %}
            {% component "block_inside_slot_v1" %}
                {% fill "body" %}
                    BODY_FROM_FILL
                {% endfill %}
            {% endcomponent %}
            {% block inner %}
                wow
            {% endblock %}
        """
        rendered = Template(template).render(Context())
        expected = """
            <!DOCTYPE html>
            <html lang="en">
            <body>
                <custom-template>
                <header></header>
                <main>BODY_FROM_FILL</main>
                <footer>Default footer</footer>
                </custom-template>
            </body>
            </html>
            wow
        """
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["django", "isolated"])
    def test_slot_inside_block__slot_default_block_default(self):
        component.registry.register("slotted_component", SlottedComponent)

        @component.register("slot_inside_block")
        class _SlotInsideBlockComponent(component.Component):
            template: types.django_html = """
                {% extends "slot_inside_block.html" %}
            """

        template: types.django_html = """
            {% load component_tags %}
            {% component "slot_inside_block" %}{% endcomponent %}
        """
        rendered = Template(template).render(Context())
        expected = """
            <!DOCTYPE html>
            <html lang="en">
            <body>
                <custom-template>
                <header></header>
                <main>
                    Helloodiddoo
                    Default inner
                </main>
                <footer>Default footer</footer>
                </custom-template>
            </body>
            </html>
        """
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["django", "isolated"])
    def test_slot_inside_block__slot_default_block_override(self):
        component.registry.clear()
        component.registry.register("slotted_component", SlottedComponent)

        @component.register("slot_inside_block")
        class _SlotInsideBlockComponent(component.Component):
            template: types.django_html = """
                {% extends "slot_inside_block.html" %}
                {% block inner %}
                    INNER BLOCK OVERRIDEN
                {% endblock %}
            """

        template: types.django_html = """
            {% load component_tags %}
            {% component "slot_inside_block" %}{% endcomponent %}
        """
        rendered = Template(template).render(Context())
        expected = """
            <!DOCTYPE html>
            <html lang="en">
            <body>
                <custom-template>
                <header></header>
                <main>
                    Helloodiddoo
                    INNER BLOCK OVERRIDEN
                </main>
                <footer>Default footer</footer>
                </custom-template>
            </body>
            </html>
        """
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["isolated", "django"])
    def test_slot_inside_block__slot_overriden_block_default(self):
        component.registry.register("slotted_component", SlottedComponent)

        @component.register("slot_inside_block")
        class _SlotInsideBlockComponent(component.Component):
            template: types.django_html = """
                {% extends "slot_inside_block.html" %}
            """

        template: types.django_html = """
            {% load component_tags %}
            {% component "slot_inside_block" %}
                {% fill "body" %}
                    SLOT OVERRIDEN
                {% endfill %}
            {% endcomponent %}
        """
        rendered = Template(template).render(Context())
        expected = """
            <!DOCTYPE html>
            <html lang="en">
            <body>
                <custom-template>
                <header></header>
                <main>
                    Helloodiddoo
                    SLOT OVERRIDEN
                </main>
                <footer>Default footer</footer>
                </custom-template>
            </body>
            </html>
        """
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["django", "isolated"])
    def test_slot_inside_block__slot_overriden_block_overriden(self):
        component.registry.register("slotted_component", SlottedComponent)

        @component.register("slot_inside_block")
        class _SlotInsideBlockComponent(component.Component):
            template: types.django_html = """
                {% extends "slot_inside_block.html" %}
                {% block inner %}
                    {% load component_tags %}
                    {% slot "new_slot" %}{% endslot %}
                {% endblock %}
                whut
            """

        # NOTE: The "body" fill will NOT show up, because we override the `inner` block
        # with a different slot. But the "new_slot" WILL show up.
        template: types.django_html = """
            {% load component_tags %}
            {% component "slot_inside_block" %}
                {% fill "body" %}
                    SLOT_BODY__OVERRIDEN
                {% endfill %}
                {% fill "new_slot" %}
                    SLOT_NEW__OVERRIDEN
                {% endfill %}
            {% endcomponent %}
        """
        rendered = Template(template).render(Context())
        expected = """
            <!DOCTYPE html>
            <html lang="en">
            <body>
                <custom-template>
                <header></header>
                <main>
                    Helloodiddoo
                    SLOT_NEW__OVERRIDEN
                </main>
                <footer>Default footer</footer>
                </custom-template>
            </body>
            </html>
        """
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["django", "isolated"])
    def test_inject_inside_block(self):
        component.registry.register("slotted_component", SlottedComponent)

        @component.register("injectee")
        class InjectComponent(component.Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_context_data(self):
                var = self.inject("block_provide")
                return {"var": var}

        template: types.django_html = """
            {% extends "block_in_component_provide.html" %}
            {% load component_tags %}
            {% block body %}
                {% component "injectee" %}
                {% endcomponent %}
            {% endblock %}
        """
        rendered = Template(template).render(Context())
        expected = """
            <!DOCTYPE html>
            <html lang="en">
            <body>
                <custom-template>
                <header></header>
                <main>
                    <div> injected: DepInject(hello='from_block') </div>
                </main>
                <footer>Default footer</footer>
                </custom-template>
            </body>
            </html>
        """
        self.assertHTMLEqual(rendered, expected)
