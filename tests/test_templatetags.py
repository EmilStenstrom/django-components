import re
import textwrap
from typing import Any, Callable, Dict, Optional

from django.template import Context, Template, TemplateSyntaxError
from django.test import override_settings

# isort: off
from .django_test_setup import *  # NOQA
from .testutils import BaseTestCase

# isort: on

import django_components
import django_components.component_registry
from django_components import component, types


class SlottedComponent(component.Component):
    template_name = "slotted_template.html"


class SlottedComponentWithContext(component.Component):
    template: types.django_html = """
        {% load component_tags %}
        <custom-template>
            <header>{% slot "header" %}Default header{% endslot %}</header>
            <main>{% slot "main" %}Default main{% endslot %}</main>
            <footer>{% slot "footer" %}Default footer{% endslot %}</footer>
        </custom-template>
    """

    def get_context_data(self, variable):
        return {"variable": variable}


#######################
# TESTS
#######################


class ComponentTemplateTagTest(BaseTestCase):
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

    def setUp(self):
        # NOTE: component.registry is global, so need to clear before each test
        component.registry.clear()

    def inline_to_block(self, tag):
        return re.sub(
            r"({% component (.*) %}{% endcomponent %})",
            r"{% component \2 %}{% endcomponent %}",
            tag,
        )

    def test_single_component(self):
        component.registry.register(name="test", component=self.SimpleComponent)

        simple_tag_tempate: types.django_html = """
            {% load component_tags %}
            {% component name="test" variable="variable" %}{% endcomponent %}
        """
        block_tag_template = self.inline_to_block(simple_tag_tempate)

        for tag in [simple_tag_tempate, block_tag_template]:
            template = Template(tag)
            rendered = template.render(Context({}))
            self.assertHTMLEqual(rendered, "Variable: <strong>variable</strong>\n")

    def test_call_with_invalid_name(self):
        # Note: No tag registered

        simple_tag_tempate: types.django_html = """
            {% load component_tags %}
            {% component name="test" variable="variable" %}{% endcomponent %}
        """
        block_tag_template = self.inline_to_block(simple_tag_tempate)

        for tag in [simple_tag_tempate, block_tag_template]:
            template = Template(tag)
            with self.assertRaises(django_components.component_registry.NotRegistered):
                template.render(Context({}))

    def test_component_called_with_positional_name(self):
        component.registry.register(name="test", component=self.SimpleComponent)

        simple_tag_tempate: types.django_html = """
            {% load component_tags %}
            {% component "test" variable="variable" %}{% endcomponent %}
        """
        block_tag_template = self.inline_to_block(simple_tag_tempate)

        for tag in [simple_tag_tempate, block_tag_template]:
            template = Template(tag)
            rendered = template.render(Context({}))
            self.assertHTMLEqual(rendered, "Variable: <strong>variable</strong>\n")

    def test_call_component_with_two_variables(self):
        @component.register("test")
        class IffedComponent(component.Component):
            template: types.django_html = """
                Variable: <strong>{{ variable }}</strong>
                {% if variable2 != "default" %}
                    Variable2: <strong>{{ variable2 }}</strong>
                {% endif %}
            """

            def get_context_data(self, variable, variable2="default"):
                return {
                    "variable": variable,
                    "variable2": variable2,
                }

            class Media:
                css = "style.css"
                js = "script.js"

        simple_tag_tempate: types.django_html = """
            {% load component_tags %}
            {% component name="test" variable="variable" variable2="hej" %}{% endcomponent %}
        """
        block_tag_template = self.inline_to_block(simple_tag_tempate)

        for tag in [simple_tag_tempate, block_tag_template]:
            template = Template(tag)
            rendered = template.render(Context({}))
            expected_outcome = """Variable: <strong>variable</strong>\n""" """Variable2: <strong>hej</strong>"""
            self.assertHTMLEqual(rendered, textwrap.dedent(expected_outcome))

    def test_component_called_with_singlequoted_name(self):
        component.registry.register(name="test", component=self.SimpleComponent)

        simple_tag_tempate: types.django_html = """
            {% load component_tags %}
            {% component 'test' variable="variable" %}{% endcomponent %}
        """
        block_tag_template = self.inline_to_block(simple_tag_tempate)

        for tag in [simple_tag_tempate, block_tag_template]:
            template = Template(tag)
            rendered = template.render(Context({}))
            self.assertHTMLEqual(rendered, "Variable: <strong>variable</strong>\n")

    def test_component_called_with_variable_as_name(self):
        component.registry.register(name="test", component=self.SimpleComponent)

        simple_tag_tempate: types.django_html = """
            {% load component_tags %}
            {% with component_name="test" %}
                {% component component_name variable="variable" %}{% endcomponent %}
            {% endwith %}
        """
        block_tag_template = self.inline_to_block(simple_tag_tempate)

        for tag in [simple_tag_tempate, block_tag_template]:
            template = Template(tag)
            rendered = template.render(Context({}))
            self.assertHTMLEqual(rendered, "Variable: <strong>variable</strong>\n")

    def test_component_called_with_invalid_variable_as_name(self):
        component.registry.register(name="test", component=self.SimpleComponent)

        simple_tag_tempate: types.django_html = """
            {% load component_tags %}
            {% with component_name="BLAHONGA" %}
                {% component component_name variable="variable" %}{% endcomponent %}
            {% endwith %}
        """
        block_tag_template = self.inline_to_block(simple_tag_tempate)

        for tag in [simple_tag_tempate, block_tag_template]:
            template = Template(tag)

        with self.assertRaises(django_components.component_registry.NotRegistered):
            template.render(Context({}))


class ComponentSlottedTemplateTagTest(BaseTestCase):
    class ComponentWithDefaultSlot(component.Component):
        template: types.django_html = """
            {% load component_tags %}
            <div>
                <main>{% slot "main" default %}Easy to override{% endslot %}</main>
            </div>
        """

    def setUp(self):
        # NOTE: component.registry is global, so need to clear before each test
        component.registry.clear()

    def test_slotted_template_basic(self):
        component.registry.register(name="test1", component=SlottedComponent)

        @component.register("test2")
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

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "test1" %}
                {% fill "header" %}
                    Custom header
                {% endfill %}
                {% fill "main" %}
                    {% component "test2" variable="variable" %}{% endcomponent %}
                {% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        self.assertHTMLEqual(
            rendered,
            """
            <custom-template>
                <header>Custom header</header>
                <main>Variable: <strong>variable</strong></main>
                <footer>Default footer</footer>
            </custom-template>
        """,
        )

    @override_settings(COMPONENTS={"context_behavior": "isolated"})
    def test_slotted_template_with_context_var__isolated(self):
        component.registry.register(name="test1", component=SlottedComponentWithContext)

        template_str: types.django_html = """
            {% load component_tags %}
            {% with my_first_variable="test123" %}
                {% component "test1" variable="test456" %}
                    {% fill "main" %}
                        {{ my_first_variable }} - {{ variable }}
                    {% endfill %}
                    {% fill "footer" %}
                        {{ my_second_variable }}
                    {% endfill %}
                {% endcomponent %}
            {% endwith %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"my_second_variable": "test321"}))

        self.assertHTMLEqual(
            rendered,
            """
            <custom-template>
                <header>Default header</header>
                <main>test123 - </main>
                <footer>test321</footer>
            </custom-template>
        """,
        )

    @override_settings(
        COMPONENTS={
            "context_behavior": "django",
        }
    )
    def test_slotted_template_with_context_var__django(self):
        component.registry.register(name="test1", component=SlottedComponentWithContext)

        template_str: types.django_html = """
            {% load component_tags %}
            {% with my_first_variable="test123" %}
                {% component "test1" variable="test456" %}
                    {% fill "main" %}
                        {{ my_first_variable }} - {{ variable }}
                    {% endfill %}
                    {% fill "footer" %}
                        {{ my_second_variable }}
                    {% endfill %}
                {% endcomponent %}
            {% endwith %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"my_second_variable": "test321"}))

        self.assertHTMLEqual(
            rendered,
            """
            <custom-template>
                <header>Default header</header>
                <main>test123 - test456</main>
                <footer>test321</footer>
            </custom-template>
        """,
        )

    def test_slotted_template_no_slots_filled(self):
        component.registry.register(name="test", component=SlottedComponent)

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "test" %}{% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        self.assertHTMLEqual(
            rendered,
            """
            <custom-template>
                <header>Default header</header>
                <main>Default main</main>
                <footer>Default footer</footer>
            </custom-template>
        """,
        )

    def test_slotted_template_without_slots(self):
        @component.register("test")
        class SlottedComponentNoSlots(component.Component):
            template: types.django_html = """
                <custom-template></custom-template>
            """

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "test" %}{% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        self.assertHTMLEqual(rendered, "<custom-template></custom-template>")

    def test_slotted_template_without_slots_and_single_quotes(self):
        @component.register("test")
        class SlottedComponentNoSlots(component.Component):
            template: types.django_html = """
                <custom-template></custom-template>
            """

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test' %}{% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        self.assertHTMLEqual(rendered, "<custom-template></custom-template>")

    def test_variable_fill_name(self):
        component.registry.register(name="test", component=SlottedComponent)
        template_str: types.django_html = """
            {% load component_tags %}
            {% with slotname="header" %}
                {% component 'test' %}
                    {% fill slotname %}Hi there!{% endfill %}
            {% endcomponent %}
            {% endwith %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))
        expected = """
        <custom-template>
            <header>Hi there!</header>
            <main>Default main</main>
            <footer>Default footer</footer>
        </custom-template>
        """
        self.assertHTMLEqual(rendered, expected)

    def test_missing_required_slot_raises_error(self):
        class Component(component.Component):
            template: types.django_html = """
                {% load component_tags %}
                <div class="header-box">
                    <h1>{% slot "title" required %}{% endslot %}</h1>
                    <h2>{% slot "subtitle" %}{% endslot %}</h2>
                </div>
            """

        component.registry.register("test", Component)

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test' %}
            {% endcomponent %}
        """
        template = Template(template_str)
        with self.assertRaises(TemplateSyntaxError):
            template.render(Context({}))

    def test_default_slot_is_fillable_by_implicit_fill_content(self):
        component.registry.register("test_comp", self.ComponentWithDefaultSlot)

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test_comp' %}
              <p>This fills the 'main' slot.</p>
            {% endcomponent %}
        """
        template = Template(template_str)

        expected = """
        <div>
          <main><p>This fills the 'main' slot.</p></main>
        </div>
        """
        rendered = template.render(Context({}))
        self.assertHTMLEqual(rendered, expected)

    def test_default_slot_is_fillable_by_explicit_fill_content(self):
        component.registry.register("test_comp", self.ComponentWithDefaultSlot)

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test_comp' %}
              {% fill "main" %}<p>This fills the 'main' slot.</p>{% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)
        expected = """
            <div>
            <main><p>This fills the 'main' slot.</p></main>
            </div>
        """
        rendered = template.render(Context({}))
        self.assertHTMLEqual(rendered, expected)

    def test_error_raised_when_default_and_required_slot_not_filled(self):
        @component.register("test_comp")
        class ComponentWithDefaultAndRequiredSlot(component.Component):
            template: types.django_html = """
                {% load component_tags %}
                <div>
                    <header>{% slot "header" %}Your Header Here{% endslot %}</header>
                    <main>{% slot "main" default required %}Easy to override{% endslot %}</main>
                </div>
            """

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test_comp' %}
            {% endcomponent %}
        """
        template = Template(template_str)
        with self.assertRaises(TemplateSyntaxError):
            template.render(Context({}))

    def test_fill_tag_can_occur_within_component_nested_in_implicit_fill(
        self,
    ):
        component.registry.register("test_comp", self.ComponentWithDefaultSlot)
        component.registry.register("slotted", SlottedComponent)

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test_comp' %}
              {% component "slotted" %}
                {% fill "header" %}This Is Allowed{% endfill %}
                {% fill "main" %}{% endfill %}
                {% fill "footer" %}{% endfill %}
              {% endcomponent %}
            {% endcomponent %}
        """
        template = Template(template_str)
        expected = """
            <div>
            <main>
                <custom-template>
                <header>This Is Allowed</header>
                <main></main>
                <footer></footer>
                </custom-template>
            </main>
            </div>
        """
        rendered = template.render(Context({}))
        self.assertHTMLEqual(rendered, expected)

    def test_error_from_mixed_implicit_and_explicit_fill_content(self):
        component.registry.register("test_comp", self.ComponentWithDefaultSlot)

        with self.assertRaises(TemplateSyntaxError):
            template_str: types.django_html = """
                {% load component_tags %}
                {% component 'test_comp' %}
                  {% fill "main" %}Main content{% endfill %}
                  <p>And add this too!</p>
                {% endcomponent %}
            """
            Template(template_str)

    def test_comments_permitted_inside_implicit_fill_content(self):
        component.registry.register("test_comp", self.ComponentWithDefaultSlot)
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test_comp' %}
              <p>Main Content</p>
              {% comment %}
              This won't show up in the rendered HTML
              {% endcomment %}
              {# Nor will this #}
            {% endcomponent %}
        """
        Template(template_str)
        self.assertTrue(True)

    def test_component_without_default_slot_refuses_implicit_fill(self):
        component.registry.register("test_comp", SlottedComponent)
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test_comp' %}
              <p>This shouldn't work because the included component doesn't mark
              any of its slots as 'default'</p>
            {% endcomponent %}
        """
        template = Template(template_str)
        with self.assertRaises(TemplateSyntaxError):
            template.render(Context({}))

    def test_component_template_cannot_have_multiple_default_slots(self):
        class BadComponent(component.Component):
            def get_template(self, context, template_name: Optional[str] = None) -> Template:
                template_str: types.django_html = """
                    {% load django_components %}
                    <div>
                        {% slot "icon" %} {% endslot default %}
                        {% slot "description" %} {% endslot default %}
                    </div>
                """
                return Template(template_str)

        c = BadComponent("name")
        with self.assertRaises(TemplateSyntaxError):
            c.render(Context({}))

    def test_slot_name_fill_typo_gives_helpful_error_message(self):
        component.registry.register(name="test1", component=SlottedComponent)

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "test1" %}
                {% fill "haeder" %}
                    Custom header
                {% endfill %}
                {% fill "main" %}
                    main content
                {% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)
        with self.assertRaises(TemplateSyntaxError):
            try:
                template.render(Context({}))
            except TemplateSyntaxError as e:
                self.assertEqual(
                    textwrap.dedent(
                        """\
                        Component 'test1' passed fill that refers to undefined slot: 'haeder'.
                        Unfilled slot names are: ['footer', 'header'].
                        Did you mean 'header'?"""
                    ),
                    str(e),
                )
                raise e


class SlottedTemplateRegressionTests(BaseTestCase):
    def setUp(self):
        # NOTE: component.registry is global, so need to clear before each test
        component.registry.clear()

    def test_slotted_template_that_uses_missing_variable(self):
        @component.register("test")
        class SlottedComponentWithMissingVariable(component.Component):
            template: types.django_html = """
                {% load component_tags %}
                <custom-template>
                    {{ missing_context_variable }}
                    <header>{% slot "header" %}Default header{% endslot %}</header>
                    <main>{% slot "main" %}Default main{% endslot %}</main>
                    <footer>{% slot "footer" %}Default footer{% endslot %}</footer>
                </custom-template>
            """

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test' %}{% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        self.assertHTMLEqual(
            rendered,
            """
            <custom-template>
                <header>Default header</header>
                <main>Default main</main>
                <footer>Default footer</footer>
            </custom-template>
            """,
        )

    def test_component_accepts_provided_and_default_parameters(self):
        @component.register("test")
        class ComponentWithProvidedAndDefaultParameters(component.Component):
            template: types.django_html = """
                Provided variable: <strong>{{ variable }}</strong>
                Default: <p>{{ default_param }}</p>
            """

            def get_context_data(self, variable, default_param="default text"):
                return {"variable": variable, "default_param": default_param}

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "test" variable="provided value" %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))
        self.assertHTMLEqual(
            rendered,
            "Provided variable: <strong>provided value</strong>\nDefault: <p>default text</p>",
        )


class MultiComponentTests(BaseTestCase):
    def setUp(self):
        component.registry.clear()

    def register_components(self):
        component.registry.register("first_component", SlottedComponent)
        component.registry.register("second_component", SlottedComponentWithContext)

    def make_template(self, first_component_slot="", second_component_slot=""):
        template_str: types.django_html = f"""
            {{% load component_tags %}}
            {{% component 'first_component' %}}
                {first_component_slot}
            {{% endcomponent %}}
            {{% component 'second_component' variable='xyz' %}}
                {second_component_slot}
            {{% endcomponent %}}
        """
        return Template(template_str)

    def expected_result(self, first_component_slot="", second_component_slot=""):
        return (
            "<custom-template><header>{}</header>".format(first_component_slot or "Default header")
            + "<main>Default main</main><footer>Default footer</footer></custom-template>"
            + "<custom-template><header>{}</header>".format(second_component_slot or "Default header")
            + "<main>Default main</main><footer>Default footer</footer></custom-template>"
        )

    def wrap_with_slot_tags(self, s):
        return '{% fill "header" %}' + s + "{% endfill %}"

    def test_both_components_render_correctly_with_no_slots(self):
        self.register_components()
        rendered = self.make_template().render(Context({}))
        self.assertHTMLEqual(rendered, self.expected_result())

    def test_both_components_render_correctly_with_slots(self):
        self.register_components()
        first_slot_content = "<p>Slot #1</p>"
        second_slot_content = "<div>Slot #2</div>"
        first_slot = self.wrap_with_slot_tags(first_slot_content)
        second_slot = self.wrap_with_slot_tags(second_slot_content)
        rendered = self.make_template(first_slot, second_slot).render(Context({}))
        self.assertHTMLEqual(
            rendered,
            self.expected_result(first_slot_content, second_slot_content),
        )

    def test_both_components_render_correctly_when_only_first_has_slots(self):
        self.register_components()
        first_slot_content = "<p>Slot #1</p>"
        first_slot = self.wrap_with_slot_tags(first_slot_content)
        rendered = self.make_template(first_slot).render(Context({}))
        self.assertHTMLEqual(rendered, self.expected_result(first_slot_content))

    def test_both_components_render_correctly_when_only_second_has_slots(self):
        self.register_components()
        second_slot_content = "<div>Slot #2</div>"
        second_slot = self.wrap_with_slot_tags(second_slot_content)
        rendered = self.make_template("", second_slot).render(Context({}))
        self.assertHTMLEqual(rendered, self.expected_result("", second_slot_content))


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

    def test_template_shown_as_used(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test_component' %}{% endcomponent %}
        """
        template = Template(template_str, name="root")
        templates_used = self.templates_used_to_render(template)
        self.assertIn("slotted_template.html", templates_used)

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


class NestedSlotTests(BaseTestCase):
    class NestedComponent(component.Component):
        template: types.django_html = """
            {% load component_tags %}
            {% slot 'outer' %}
                <div id="outer">{% slot 'inner' %}Default{% endslot %}</div>
            {% endslot %}
        """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        component.registry.clear()
        component.registry.register("test", cls.NestedComponent)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        component.registry.clear()

    def test_default_slot_contents_render_correctly(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test' %}{% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))
        self.assertHTMLEqual(rendered, '<div id="outer">Default</div>')

    def test_inner_slot_overriden(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test' %}
                {% fill 'inner' %}Override{% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))
        self.assertHTMLEqual(rendered, '<div id="outer">Override</div>')

    def test_outer_slot_overriden(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test' %}{% fill 'outer' %}<p>Override</p>{% endfill %}{% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))
        self.assertHTMLEqual(rendered, "<p>Override</p>")

    def test_both_overriden_and_inner_removed(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test' %}
                {% fill 'outer' %}<p>Override</p>{% endfill %}
                {% fill 'inner' %}<p>Will not appear</p>{% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))
        self.assertHTMLEqual(rendered, "<p>Override</p>")


class ConditionalSlotTests(BaseTestCase):
    class ConditionalComponent(component.Component):
        template: types.django_html = """
            {% load component_tags %}
            {% if branch == 'a' %}
                <p id="a">{% slot 'a' %}Default A{% endslot %}</p>
            {% elif branch == 'b' %}
                <p id="b">{% slot 'b' %}Default B{% endslot %}</p>
            {% endif %}
        """

        def get_context_data(self, branch=None):
            return {"branch": branch}

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        component.registry.clear()
        component.registry.register("test", cls.ConditionalComponent)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        component.registry.clear()

    def test_no_content_if_branches_are_false(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test' %}
                {% fill 'a' %}Override A{% endfill %}
                {% fill 'b' %}Override B{% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))
        self.assertHTMLEqual(rendered, "")

    def test_default_content_if_no_slots(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test' branch='a' %}{% endcomponent %}
            {% component 'test' branch='b' %}{% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))
        self.assertHTMLEqual(rendered, '<p id="a">Default A</p><p id="b">Default B</p>')

    def test_one_slot_overridden(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test' branch='a' %}
                {% fill 'b' %}Override B{% endfill %}
            {% endcomponent %}
            {% component 'test' branch='b' %}
                {% fill 'b' %}Override B{% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))
        self.assertHTMLEqual(rendered, '<p id="a">Default A</p><p id="b">Override B</p>')

    def test_both_slots_overridden(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test' branch='a' %}
                {% fill 'a' %}Override A{% endfill %}
                {% fill 'b' %}Override B{% endfill %}
            {% endcomponent %}
            {% component 'test' branch='b' %}
                {% fill 'a' %}Override A{% endfill %}
                {% fill 'b' %}Override B{% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))
        self.assertHTMLEqual(rendered, '<p id="a">Override A</p><p id="b">Override B</p>')


class SlotSuperTests(BaseTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        component.registry.clear()
        component.registry.register("test", SlottedComponent)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        component.registry.clear()

    def test_basic_super_functionality(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component "test" %}
                {% fill "header" as "header" %}Before: {{ header.default }}{% endfill %}
                {% fill "main" as "main" %}{{ main.default }}{% endfill %}
                {% fill "footer" as "footer" %}{{ footer.default }}, after{% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        self.assertHTMLEqual(
            rendered,
            """
            <custom-template>
                <header>Before: Default header</header>
                <main>Default main</main>
                <footer>Default footer, after</footer>
            </custom-template>
            """,
        )

    def test_multiple_super_calls(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component "test" %}
                {% fill "header" as "header" %}
                    First: {{ header.default }};
                    Second: {{ header.default }}
                {% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        self.assertHTMLEqual(
            rendered,
            """
            <custom-template>
                <header>First: Default header; Second: Default header</header>
                <main>Default main</main>
                <footer>Default footer</footer>
            </custom-template>
        """,
        )

    def test_super_under_if_node(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component "test" %}
                {% fill "header" as "header" %}
                    {% for i in range %}
                        {% if forloop.first %}First {{ header.default }}
                        {% else %}Later {{ header.default }}
                        {% endif %}
                    {% endfor %}
                {% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"range": range(3)}))

        self.assertHTMLEqual(
            rendered,
            """
            <custom-template>
                <header>First Default header Later Default header Later Default header</header>
                <main>Default main</main>
                <footer>Default footer</footer>
            </custom-template>
            """,
        )


class TemplateSyntaxErrorTests(BaseTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        component.registry.register("test", SlottedComponent)

    @classmethod
    def tearDownClass(cls) -> None:
        super().tearDownClass()
        component.registry.clear()

    def test_variable_outside_fill_tag_compiles_w_out_error(self):
        # As of v0.28 this is valid, provided the component registered under "test"
        # contains a slot tag marked as 'default'. This is verified outside
        # template compilation time.
        template_str: types.django_html = """
            {% load component_tags %}
            {% component "test" %}
                {{ anything }}
            {% endcomponent %}
        """
        Template(template_str)

    def test_text_outside_fill_tag_is_not_error(self):
        # As of v0.28 this is valid, provided the component registered under "test"
        # contains a slot tag marked as 'default'. This is verified outside
        # template compilation time.
        template_str: types.django_html = """
            {% load component_tags %}
            {% component "test" %}
                Text
            {% endcomponent %}
        """
        Template(template_str)

    def test_nonfill_block_outside_fill_tag_is_error(self):
        with self.assertRaises(TemplateSyntaxError):
            template_str: types.django_html = """
                {% load component_tags %}
                {% component "test" %}
                    {% if True %}
                        {% fill "header" %}{% endfill %}
                    {% endif %}
                {% endcomponent %}
            """
            Template(template_str)

    def test_unclosed_component_is_error(self):
        with self.assertRaises(TemplateSyntaxError):
            template_str: types.django_html = """
                {% load component_tags %}
                {% component "test" %}
                {% fill "header" %}{% endfill %}
            """
            Template(template_str)

    def test_fill_with_no_parent_is_error(self):
        with self.assertRaises(TemplateSyntaxError):
            template_str: types.django_html = """
                {% load component_tags %}
                {% fill "header" %}contents{% endfill %}
            """
            Template(template_str).render(Context({}))

    def test_isolated_slot_is_error(self):
        @component.register("broken_component")
        class BrokenComponent(component.Component):
            template: types.django_html = """
                {% load component_tags %}
                {% include 'slotted_template.html' with context=None only %}
            """

        with self.assertRaises(KeyError):
            template_str: types.django_html = """
                {% load component_tags %}
                {% component "broken_component" %}
                    {% fill "header" %}Custom header {% endfill %}
                    {% fill "main" %}Custom main{% endfill %}
                    {% fill "footer" %}Custom footer{% endfill %}
                {% endcomponent %}
            """
            Template(template_str).render(Context({}))

    def test_non_unique_fill_names_is_error(self):
        with self.assertRaises(TemplateSyntaxError):
            template_str: types.django_html = """
                {% load component_tags %}
                {% component "test" %}
                    {% fill "header" %}Custom header {% endfill %}
                    {% fill "header" %}Other header{% endfill %}
                {% endcomponent %}
            """
            Template(template_str).render(Context({}))

    def test_non_unique_fill_names_is_error_via_vars(self):
        with self.assertRaises(TemplateSyntaxError):
            template_str: types.django_html = """
                {% load component_tags %}
                {% with var1="header" var2="header" %}
                    {% component "test" %}
                        {% fill var1 %}Custom header {% endfill %}
                        {% fill var2 %}Other header{% endfill %}
                    {% endcomponent %}
                {% endwith %}
            """
            Template(template_str).render(Context({}))


class ComponentNestingTests(BaseTestCase):

    class CalendarComponent(component.Component):
        """Nested in ComponentWithNestedComponent"""

        template: types.django_html = """
            {% load component_tags %}
            <div class="calendar-component">
            <h1>
                {% slot "header" %}Today's date is <span>{{ date }}</span>{% endslot %}
            </h1>
            <main>
            {% slot "body" %}
                You have no events today.
            {% endslot %}
            </main>
            </div>
        """

    class DashboardComponent(component.Component):
        template: types.django_html = """
            {% load component_tags %}
            <div class="dashboard-component">
            {% component "calendar" date="2020-06-06" %}
                {% fill "header" %}  {# fills and slots with same name relate to diff. things. #}
                {% slot "header" %}Welcome to your dashboard!{% endslot %}
                {% endfill %}
                {% fill "body" %}Here are your to-do items for today:{% endfill %}
            {% endcomponent %}
            <ol>
                {% for item in items %}
                <li>{{ item }}</li>
                {% endfor %}
            </ol>
            </div>
        """

    class ComplexChildComponent(component.Component):
        template: types.django_html = """
            {% load component_tags %}
            <div>
            {% slot "content" default %}
                No slot!
            {% endslot %}
            </div>
        """

    class ComplexParentComponent(component.Component):
        template: types.django_html = """
            {% load component_tags %}
            ITEMS: {{ items|safe }}
            {% for item in items %}
            <li>
                {% component "complex_child" %}
                    {{ item.value }}
                {% endcomponent %}
            </li>
            {% endfor %}
        """

        def get_context_data(self, items, *args, **kwargs) -> Dict[str, Any]:
            return {"items": items}

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        component.registry.register("dashboard", cls.DashboardComponent)
        component.registry.register("calendar", cls.CalendarComponent)
        component.registry.register("complex_child", cls.ComplexChildComponent)
        component.registry.register("complex_parent", cls.ComplexParentComponent)

    @classmethod
    def tearDownClass(cls) -> None:
        super().tearDownClass()
        component.registry.clear()

    @override_settings(COMPONENTS={"context_behavior": "django"})
    def test_component_nesting_component_without_fill__django(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component "dashboard" %}{% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"items": [1, 2, 3]}))
        expected = """
            <div class="dashboard-component">
            <div class="calendar-component">
                <h1>
                Welcome to your dashboard!
                </h1>
                <main>
                Here are your to-do items for today:
                </main>
            </div>
            <ol>
                <li>1</li>
                <li>2</li>
                <li>3</li>
            </ol>
            </div>
        """
        self.assertHTMLEqual(rendered, expected)

    @override_settings(COMPONENTS={"context_behavior": "isolated"})
    def test_component_nesting_component_without_fill__isolated(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component "dashboard" %}{% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"items": [1, 2, 3]}))
        expected = """
            <div class="dashboard-component">
            <div class="calendar-component">
                <h1>
                Welcome to your dashboard!
                </h1>
                <main>
                Here are your to-do items for today:
                </main>
            </div>
            <ol>
            </ol>
            </div>
        """
        self.assertHTMLEqual(rendered, expected)

    @override_settings(COMPONENTS={"context_behavior": "isolated"})
    def test_component_nesting_slot_inside_component_fill__isolated(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component "dashboard" %}{% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"items": [1, 2, 3]}))
        expected = """
            <div class="dashboard-component">
            <div class="calendar-component">
                <h1>
                Welcome to your dashboard!
                </h1>
                <main>
                Here are your to-do items for today:
                </main>
            </div>
            <ol>
            </ol>
            </div>
        """
        self.assertHTMLEqual(rendered, expected)

    @override_settings(COMPONENTS={"context_behavior": "isolated"})
    def test_component_nesting_slot_inside_component_fill__isolated_2(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component "dashboard" %}
                {% fill "header" %}
                    Whoa!
                {% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"items": [1, 2, 3]}))
        expected = """
            <div class="dashboard-component">
            <div class="calendar-component">
                <h1>
                Whoa!
                </h1>
                <main>
                Here are your to-do items for today:
                </main>
            </div>
            <ol>
            </ol>
            </div>
        """
        self.assertHTMLEqual(rendered, expected)

    @override_settings(COMPONENTS={"context_behavior": "isolated"})
    def test_component_nesting_deep_slot_inside_component_fill__isolated(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component "complex_parent" items=items %}{% endcomponent %}
        """
        template = Template(template_str)
        items = [{"value": 1}, {"value": 2}, {"value": 3}]
        rendered = template.render(Context({"items": items}))
        expected = """
            ITEMS: [{'value': 1}, {'value': 2}, {'value': 3}]
            <li>
                <div> 1 </div>
            </li>
            <li>
                <div> 2 </div>
            </li>
            <li>
                <div> 3 </div>
            </li>
        """
        self.assertHTMLEqual(rendered, expected)

    @override_settings(COMPONENTS={"context_behavior": "django"})
    def test_component_nesting_component_with_fill_and_super__django(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component "dashboard" %}
              {% fill "header" as "h" %} Hello! {{ h.default }} {% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"items": [1, 2]}))
        expected = """
            <div class="dashboard-component">
            <div class="calendar-component">
                <h1>
                Hello! Welcome to your dashboard!
                </h1>
                <main>
                Here are your to-do items for today:
                </main>
            </div>
            <ol>
                <li>1</li>
                <li>2</li>
            </ol>
            </div>
        """
        self.assertHTMLEqual(rendered, expected)

    @override_settings(COMPONENTS={"context_behavior": "isolated"})
    def test_component_nesting_component_with_fill_and_super__isolated(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component "dashboard" %}
              {% fill "header" as "h" %} Hello! {{ h.default }} {% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"items": [1, 2]}))
        expected = """
            <div class="dashboard-component">
            <div class="calendar-component">
                <h1>
                Hello! Welcome to your dashboard!
                </h1>
                <main>
                Here are your to-do items for today:
                </main>
            </div>
            <ol>
            </ol>
            </div>
        """
        self.assertHTMLEqual(rendered, expected)


class ConditionalIfFilledSlotsTests(BaseTestCase):
    class ComponentWithConditionalSlots(component.Component):
        template: types.django_html = """
            {# Example from django-components/issues/98 #}
            {% load component_tags %}
            <div class="frontmatter-component">
                <div class="title">{% slot "title" %}Title{% endslot %}</div>
                {% if component_vars.is_filled.subtitle %}
                    <div class="subtitle">
                        {% slot "subtitle" %}Optional subtitle
                        {% endslot %}
                    </div>
                {% endif %}
            </div>
        """

    class ComponentWithComplexConditionalSlots(component.Component):
        template: types.django_html = """
            {# Example from django-components/issues/98 #}
            {% load component_tags %}
            <div class="frontmatter-component">
                <div class="title">{% slot "title" %}Title{% endslot %}</div>
                {% if component_vars.is_filled.subtitle %}
                    <div class="subtitle">{% slot "subtitle" %}Optional subtitle{% endslot %}</div>
                {% elif component_vars.is_filled.alt_subtitle %}
                    <div class="subtitle">{% slot "alt_subtitle" %}Why would you want this?{% endslot %}</div>
                {% else %}
                <div class="warning">Nothing filled!</div>
                {% endif %}
            </div>
        """

    class ComponentWithNegatedConditionalSlot(component.Component):
        template: types.django_html = """
            {# Example from django-components/issues/98 #}
            {% load component_tags %}
            <div class="frontmatter-component">
                <div class="title">{% slot "title" %}Title{% endslot %}</div>
                {% if not component_vars.is_filled.subtitle %}
                <div class="warning">Subtitle not filled!</div>
                {% else %}
                    <div class="subtitle">{% slot "alt_subtitle" %}Why would you want this?{% endslot %}</div>
                {% endif %}
            </div>
        """

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        component.registry.register("conditional_slots", cls.ComponentWithConditionalSlots)
        component.registry.register(
            "complex_conditional_slots",
            cls.ComponentWithComplexConditionalSlots,
        )
        component.registry.register("negated_conditional_slot", cls.ComponentWithNegatedConditionalSlot)

    @classmethod
    def tearDownClass(cls) -> None:
        super().tearDownClass()
        component.registry.clear()

    def test_simple_component_with_conditional_slot(self):
        template: types.django_html = """
            {% load component_tags %}
            {% component "conditional_slots" %}{% endcomponent %}
        """
        expected = """
            <div class="frontmatter-component">
            <div class="title">
            Title
            </div>
            </div>
        """
        rendered = Template(template).render(Context({}))
        self.assertHTMLEqual(rendered, expected)

    @override_settings(COMPONENTS={"context_behavior": "django"})
    def test_component_with_filled_conditional_slot__django(self):
        template: types.django_html = """
            {% load component_tags %}
            {% component "conditional_slots" %}
            {% fill "subtitle" %} My subtitle {% endfill %}
            {% endcomponent %}
        """
        expected = """
            <div class="frontmatter-component">
                <div class="title">
                    Title
                </div>
                <div class="subtitle">
                    My subtitle
                </div>
            </div>
        """
        rendered = Template(template).render(Context({}))
        self.assertHTMLEqual(rendered, expected)

    def test_elif_of_complex_conditional_slots(self):
        template: types.django_html = """
            {% load component_tags %}
            {% component "complex_conditional_slots" %}
                {% fill "alt_subtitle" %} A different subtitle {% endfill %}
            {% endcomponent %}
        """
        expected = """
           <div class="frontmatter-component">
             <div class="title">
                Title
             </div>
             <div class="subtitle">
                A different subtitle
             </div>
           </div>
        """
        rendered = Template(template).render(Context({}))
        self.assertHTMLEqual(rendered, expected)

    def test_else_of_complex_conditional_slots(self):
        template: types.django_html = """
           {% load component_tags %}
           {% component "complex_conditional_slots" %}
           {% endcomponent %}
        """
        expected = """
           <div class="frontmatter-component">
             <div class="title">
             Title
             </div>
            <div class="warning">Nothing filled!</div>
           </div>
        """
        rendered = Template(template).render(Context({}))
        self.assertHTMLEqual(rendered, expected)

    def test_component_with_negated_conditional_slot(self):
        template: types.django_html = """
            {% load component_tags %}
            {% component "negated_conditional_slot" %}
                {# Whoops! Forgot to fill a slot! #}
            {% endcomponent %}
        """
        expected = """
            <div class="frontmatter-component">
                <div class="title">
                Title
                </div>
                <div class="warning">Subtitle not filled!</div>
            </div>
        """
        rendered = Template(template).render(Context({}))
        self.assertHTMLEqual(rendered, expected)


class ContextVarsTests(BaseTestCase):
    class IsFilledVarsComponent(component.Component):
        template: types.django_html = """
            {% load component_tags %}
            <div class="frontmatter-component">
                {% slot "title" default %}{% endslot %}
                {% slot "my_title" %}{% endslot %}
                {% slot "my title 1" %}{% endslot %}
                {% slot "my-title-2" %}{% endslot %}
                {% slot "escape this: #$%^*()" %}{% endslot %}
                {{ component_vars.is_filled|safe }}
            </div>
        """

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        component.registry.register("is_filled_vars", cls.IsFilledVarsComponent)

    def test_is_filled_vars(self):
        template: types.django_html = """
            {% load component_tags %}
            {% component "is_filled_vars" %}
                {% fill "title" %}{% endfill %}
                {% fill "my-title-2" %}{% endfill %}
                {% fill "escape this: #$%^*()" %}{% endfill %}
            {% endcomponent %}
        """
        rendered = Template(template).render(Context())
        expected = """
            <div class="frontmatter-component">
                {'title': True,
                'my_title': False,
                'my_title_1': False,
                'my_title_2': True,
                'escape_this_________': True}
            </div>
        """
        self.assertHTMLEqual(rendered, expected)

    def test_is_filled_vars_default(self):
        template: types.django_html = """
            {% load component_tags %}
            {% component "is_filled_vars" %}
                bla bla
            {% endcomponent %}
        """
        rendered = Template(template).render(Context())
        expected = """
            <div class="frontmatter-component">
                bla bla
                {'title': True,
                'my_title': False,
                'my_title_1': False,
                'my_title_2': False,
                'escape_this_________': False}
            </div>
        """
        self.assertHTMLEqual(rendered, expected)


class BlockCompatTests(BaseTestCase):
    def setUp(self):
        component.registry.clear()
        super().setUp()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        component.registry.clear()

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

    def test_slot_inside_block__slot_default_block_override(self):
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


class IterationFillTest(BaseTestCase):
    """Tests a behaviour of {% fill .. %} tag which is inside a template {% for .. %} loop."""

    class ComponentSimpleSlotInALoop(django_components.component.Component):
        template: types.django_html = """
            {% load component_tags %}
            {% for object in objects %}
                {% slot 'slot_inner' %}
                    {{ object }} default
                {% endslot %}
            {% endfor %}
        """

        def get_context_data(self, objects, *args, **kwargs) -> dict:
            return {
                "objects": objects,
            }

    def setUp(self):
        django_components.component.registry.clear()

    @override_settings(COMPONENTS={"context_behavior": "django"})
    def test_inner_slot_iteration_basic__django(self):
        component.registry.register("slot_in_a_loop", self.ComponentSimpleSlotInALoop)

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "slot_in_a_loop" objects=objects %}
                {% fill "slot_inner" %}
                    {{ object }}
                {% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)
        objects = ["OBJECT1", "OBJECT2"]
        rendered = template.render(Context({"objects": objects}))

        self.assertHTMLEqual(
            rendered,
            """
            OBJECT1
            OBJECT2
            """,
        )

    @override_settings(COMPONENTS={"context_behavior": "isolated"})
    def test_inner_slot_iteration_basic__isolated(self):
        component.registry.register("slot_in_a_loop", self.ComponentSimpleSlotInALoop)

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "slot_in_a_loop" objects=objects %}
                {% fill "slot_inner" %}
                    {{ object }}
                {% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)
        objects = ["OBJECT1", "OBJECT2"]
        rendered = template.render(Context({"objects": objects}))

        self.assertHTMLEqual(rendered, "")

    @override_settings(COMPONENTS={"context_behavior": "django"})
    def test_inner_slot_iteration_with_variable_from_outer_scope__django(self):
        component.registry.register("slot_in_a_loop", self.ComponentSimpleSlotInALoop)

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "slot_in_a_loop" objects=objects %}
                {% fill "slot_inner" %}
                    {{ outer_scope_variable }}
                    {{ object }}
                {% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)
        objects = ["OBJECT1", "OBJECT2"]
        rendered = template.render(
            Context(
                {
                    "objects": objects,
                    "outer_scope_variable": "OUTER_SCOPE_VARIABLE",
                }
            )
        )

        self.assertHTMLEqual(
            rendered,
            """
            OUTER_SCOPE_VARIABLE
            OBJECT1
            OUTER_SCOPE_VARIABLE
            OBJECT2
            """,
        )

    @override_settings(COMPONENTS={"context_behavior": "isolated"})
    def test_inner_slot_iteration_with_variable_from_outer_scope__isolated(self):
        component.registry.register("slot_in_a_loop", self.ComponentSimpleSlotInALoop)

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "slot_in_a_loop" objects=objects %}
                {% fill "slot_inner" %}
                    {{ outer_scope_variable }}
                    {{ object }}
                {% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)
        objects = ["OBJECT1", "OBJECT2"]
        rendered = template.render(
            Context(
                {
                    "objects": objects,
                    "outer_scope_variable": "OUTER_SCOPE_VARIABLE",
                }
            )
        )

        self.assertHTMLEqual(
            rendered,
            """
            OUTER_SCOPE_VARIABLE
            OUTER_SCOPE_VARIABLE
            """,
        )

    @override_settings(COMPONENTS={"context_behavior": "django"})
    def test_inner_slot_iteration_nested__django(self):
        component.registry.register("slot_in_a_loop", self.ComponentSimpleSlotInALoop)

        objects = [
            {"inner": ["ITER1_OBJ1", "ITER1_OBJ2"]},
            {"inner": ["ITER2_OBJ1", "ITER2_OBJ2"]},
        ]

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "slot_in_a_loop" objects=objects %}
                {% fill "slot_inner" %}
                    {% component "slot_in_a_loop" objects=object.inner %}
                        {% fill "slot_inner" %}
                            {{ object }}
                        {% endfill %}
                    {% endcomponent %}
                {% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"objects": objects}))

        self.assertHTMLEqual(
            rendered,
            """
            ITER1_OBJ1
            ITER1_OBJ2
            ITER2_OBJ1
            ITER2_OBJ2
            """,
        )

    @override_settings(COMPONENTS={"context_behavior": "isolated"})
    def test_inner_slot_iteration_nested__isolated(self):
        component.registry.register("slot_in_a_loop", self.ComponentSimpleSlotInALoop)

        objects = [
            {"inner": ["ITER1_OBJ1", "ITER1_OBJ2"]},
            {"inner": ["ITER2_OBJ1", "ITER2_OBJ2"]},
        ]

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "slot_in_a_loop" objects=objects %}
                {% fill "slot_inner" %}
                    {% component "slot_in_a_loop" objects=object.inner %}
                        {% fill "slot_inner" %}
                            {{ object }}
                        {% endfill %}
                    {% endcomponent %}
                {% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"objects": objects}))

        self.assertHTMLEqual(rendered, "")

    @override_settings(COMPONENTS={"context_behavior": "django"})
    def test_inner_slot_iteration_nested_with_outer_scope_variable__django(self):
        component.registry.register("slot_in_a_loop", self.ComponentSimpleSlotInALoop)

        objects = [
            {"inner": ["ITER1_OBJ1", "ITER1_OBJ2"]},
            {"inner": ["ITER2_OBJ1", "ITER2_OBJ2"]},
        ]

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "slot_in_a_loop" objects=objects %}
                {% fill "slot_inner" %}
                    {{ outer_scope_variable_1 }}
                    {% component "slot_in_a_loop" objects=object.inner %}
                        {% fill "slot_inner" %}
                            {{ outer_scope_variable_2 }}
                            {{ object }}
                        {% endfill %}
                    {% endcomponent %}
                {% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(
            Context(
                {
                    "objects": objects,
                    "outer_scope_variable_1": "OUTER_SCOPE_VARIABLE1",
                    "outer_scope_variable_2": "OUTER_SCOPE_VARIABLE2",
                }
            )
        )

        self.assertHTMLEqual(
            rendered,
            """
            OUTER_SCOPE_VARIABLE1
            OUTER_SCOPE_VARIABLE2
            ITER1_OBJ1
            OUTER_SCOPE_VARIABLE2
            ITER1_OBJ2
            OUTER_SCOPE_VARIABLE1
            OUTER_SCOPE_VARIABLE2
            ITER2_OBJ1
            OUTER_SCOPE_VARIABLE2
            ITER2_OBJ2
            """,
        )

    @override_settings(COMPONENTS={"context_behavior": "isolated"})
    def test_inner_slot_iteration_nested_with_outer_scope_variable__isolated(self):
        component.registry.register("slot_in_a_loop", self.ComponentSimpleSlotInALoop)

        objects = [
            {"inner": ["ITER1_OBJ1", "ITER1_OBJ2"]},
            {"inner": ["ITER2_OBJ1", "ITER2_OBJ2"]},
        ]

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "slot_in_a_loop" objects=objects %}
                {% fill "slot_inner" %}
                    {{ outer_scope_variable_1 }}
                    {% component "slot_in_a_loop" objects=object.inner %}
                        {% fill "slot_inner" %}
                            {{ outer_scope_variable_2 }}
                            {{ object }}
                        {% endfill %}
                    {% endcomponent %}
                {% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(
            Context(
                {
                    "objects": objects,
                    "outer_scope_variable_1": "OUTER_SCOPE_VARIABLE1",
                    "outer_scope_variable_2": "OUTER_SCOPE_VARIABLE2",
                }
            )
        )

        self.assertHTMLEqual(
            rendered,
            """
            OUTER_SCOPE_VARIABLE1
            OUTER_SCOPE_VARIABLE1
            """,
        )

    @override_settings(COMPONENTS={"context_behavior": "django"})
    def test_inner_slot_iteration_nested_with_slot_default__django(self):
        component.registry.register("slot_in_a_loop", self.ComponentSimpleSlotInALoop)

        objects = [
            {"inner": ["ITER1_OBJ1", "ITER1_OBJ2"]},
            {"inner": ["ITER2_OBJ1", "ITER2_OBJ2"]},
        ]

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "slot_in_a_loop" objects=objects %}
                {% fill "slot_inner" %}
                    {% component "slot_in_a_loop" objects=object.inner %}
                        {% fill "slot_inner" as "super_slot_inner" %}
                            {{ super_slot_inner.default }}
                        {% endfill %}
                    {% endcomponent %}
                {% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"objects": objects}))

        self.assertHTMLEqual(
            rendered,
            """
            ITER1_OBJ1 default
            ITER1_OBJ2 default
            ITER2_OBJ1 default
            ITER2_OBJ2 default
            """,
        )

    @override_settings(COMPONENTS={"context_behavior": "isolated"})
    def test_inner_slot_iteration_nested_with_slot_default__isolated(self):
        component.registry.register("slot_in_a_loop", self.ComponentSimpleSlotInALoop)

        objects = [
            {"inner": ["ITER1_OBJ1", "ITER1_OBJ2"]},
            {"inner": ["ITER2_OBJ1", "ITER2_OBJ2"]},
        ]

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "slot_in_a_loop" objects=objects %}
                {% fill "slot_inner" %}
                    {% component "slot_in_a_loop" objects=object.inner %}
                        {% fill "slot_inner" as "super_slot_inner" %}
                            {{ super_slot_inner.default }}
                        {% endfill %}
                    {% endcomponent %}
                {% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"objects": objects}))
        self.assertHTMLEqual(rendered, "")

    @override_settings(COMPONENTS={"context_behavior": "django"})
    def test_inner_slot_iteration_nested_with_slot_default_and_outer_scope_variable__django(
        self,
    ):
        component.registry.register("slot_in_a_loop", self.ComponentSimpleSlotInALoop)

        objects = [
            {"inner": ["ITER1_OBJ1", "ITER1_OBJ2"]},
            {"inner": ["ITER2_OBJ1", "ITER2_OBJ2"]},
        ]

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "slot_in_a_loop" objects=objects %}
                {% fill "slot_inner" %}
                    {{ outer_scope_variable_1 }}
                    {% component "slot_in_a_loop" objects=object.inner %}
                        {% fill "slot_inner" as "super_slot_inner" %}
                            {{ outer_scope_variable_2 }}
                            {{ super_slot_inner.default }}
                        {% endfill %}
                    {% endcomponent %}
                {% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(
            Context(
                {
                    "objects": objects,
                    "outer_scope_variable_1": "OUTER_SCOPE_VARIABLE1",
                    "outer_scope_variable_2": "OUTER_SCOPE_VARIABLE2",
                }
            )
        )

        self.assertHTMLEqual(
            rendered,
            """
            OUTER_SCOPE_VARIABLE1
            OUTER_SCOPE_VARIABLE2
            ITER1_OBJ1 default
            OUTER_SCOPE_VARIABLE2
            ITER1_OBJ2 default
            OUTER_SCOPE_VARIABLE1
            OUTER_SCOPE_VARIABLE2
            ITER2_OBJ1 default
            OUTER_SCOPE_VARIABLE2
            ITER2_OBJ2 default
            """,
        )

    @override_settings(COMPONENTS={"context_behavior": "isolated"})
    def test_inner_slot_iteration_nested_with_slot_default_and_outer_scope_variable__isolated_1(
        self,
    ):
        component.registry.register("slot_in_a_loop", self.ComponentSimpleSlotInALoop)

        objects = [
            {"inner": ["ITER1_OBJ1", "ITER1_OBJ2"]},
            {"inner": ["ITER2_OBJ1", "ITER2_OBJ2"]},
        ]

        # NOTE: In this case the `object.inner` in the inner "slot_in_a_loop"
        # should be undefined, so the loop inside the inner `slot_in_a_loop`
        # shouldn't run. Hence even the inner `slot_inner` fill should NOT run.
        template_str: types.django_html = """
            {% load component_tags %}
            {% component "slot_in_a_loop" objects=objects %}
                {% fill "slot_inner" %}
                    {{ outer_scope_variable_1 }}
                    {% component "slot_in_a_loop" objects=object.inner %}
                        {% fill "slot_inner" as "super_slot_inner" %}
                            {{ outer_scope_variable_2 }}
                            {{ super_slot_inner.default }}
                        {% endfill %}
                    {% endcomponent %}
                {% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(
            Context(
                {
                    "objects": objects,
                    "outer_scope_variable_1": "OUTER_SCOPE_VARIABLE1",
                    "outer_scope_variable_2": "OUTER_SCOPE_VARIABLE2",
                }
            )
        )

        self.assertHTMLEqual(
            rendered,
            """
            OUTER_SCOPE_VARIABLE1
            OUTER_SCOPE_VARIABLE1
            """,
        )

    @override_settings(COMPONENTS={"context_behavior": "isolated"})
    def test_inner_slot_iteration_nested_with_slot_default_and_outer_scope_variable__isolated_2(
        self,
    ):
        component.registry.register("slot_in_a_loop", self.ComponentSimpleSlotInALoop)

        objects = [
            {"inner": ["ITER1_OBJ1", "ITER1_OBJ2"]},
            {"inner": ["ITER2_OBJ1", "ITER2_OBJ2"]},
        ]

        # NOTE: In this case we use `objects` in the inner "slot_in_a_loop", which
        # is defined in the root context. So the loop inside the inner `slot_in_a_loop`
        # should run.
        template_str: types.django_html = """
            {% load component_tags %}
            {% component "slot_in_a_loop" objects=objects %}
                {% fill "slot_inner" %}
                    {{ outer_scope_variable_1|safe }}
                    {% component "slot_in_a_loop" objects=objects %}
                        {% fill "slot_inner" as "super_slot_inner" %}
                            {{ outer_scope_variable_2|safe }}
                            {{ super_slot_inner.default }}
                        {% endfill %}
                    {% endcomponent %}
                {% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(
            Context(
                {
                    "objects": objects,
                    "outer_scope_variable_1": "OUTER_SCOPE_VARIABLE1",
                    "outer_scope_variable_2": "OUTER_SCOPE_VARIABLE2",
                }
            )
        )

        self.assertHTMLEqual(
            rendered,
            """
            OUTER_SCOPE_VARIABLE1
            OUTER_SCOPE_VARIABLE2
            {'inner': ['ITER1_OBJ1', 'ITER1_OBJ2']} default
            OUTER_SCOPE_VARIABLE2
            {'inner': ['ITER2_OBJ1', 'ITER2_OBJ2']} default
            OUTER_SCOPE_VARIABLE1
            OUTER_SCOPE_VARIABLE2
            {'inner': ['ITER1_OBJ1', 'ITER1_OBJ2']} default
            OUTER_SCOPE_VARIABLE2
            {'inner': ['ITER2_OBJ1', 'ITER2_OBJ2']} default
            """,
        )
