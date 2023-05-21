import re
import textwrap
from typing import Callable, Iterable, Optional

from django.template import Context, Template, TemplateSyntaxError

# isort: off
from .django_test_setup import *  # NOQA
from .testutils import Django30CompatibleSimpleTestCase as SimpleTestCase

# isort: on

import django_components
import django_components.component_registry
from django_components import component


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


class IffedComponent(SimpleComponent):
    template_name = "iffed_template.html"


class SlottedComponent(component.Component):
    template_name = "slotted_template.html"


class BrokenComponent(component.Component):
    template_name = "template_with_illegal_slot.html"


class NonUniqueSlotsComponent(component.Component):
    template_name = "template_with_nonunique_slots.html"


class SlottedComponentWithMissingVariable(component.Component):
    template_name = "slotted_template_with_missing_variable.html"


class SlottedComponentNoSlots(component.Component):
    template_name = "slotted_template_no_slots.html"


class SlottedComponentWithContext(component.Component):
    template_name = "slotted_template.html"

    def get_context_data(self, variable):
        return {"variable": variable}


class ComponentWithProvidedAndDefaultParameters(component.Component):
    template_name = "template_with_provided_and_default_parameters.html"

    def get_context_data(self, variable, default_param="default text"):
        return {"variable": variable, "default_param": default_param}


class _CalendarComponent(component.Component):
    """Nested in ComponentWithNestedComponent"""

    template_name = "slotted_component_nesting_template_pt1_calendar.html"


class _DashboardComponent(component.Component):
    template_name = "slotted_component_nesting_template_pt2_dashboard.html"


class ComponentWithDefaultSlot(component.Component):
    template_name = "template_with_default_slot.html"


class ComponentWithDefaultAndRequiredSlot(component.Component):
    template_name = "template_with_default_and_required_slot.html"


class ComponentTemplateTagTest(SimpleTestCase):
    def setUp(self):
        # NOTE: component.registry is global, so need to clear before each test
        component.registry.clear()

    def inline_to_block(self, tag):
        return re.sub(
            r"({% component (.*) %})",
            r"{% component_block \2 %}{% endcomponent_block %}",
            tag,
        )

    def test_single_component(self):
        component.registry.register(name="test", component=SimpleComponent)

        simple_tag_tempate = '{% load component_tags %}{% component name="test" variable="variable" %}'
        block_tag_template = self.inline_to_block(simple_tag_tempate)

        for tag in [simple_tag_tempate, block_tag_template]:
            template = Template(tag)
            rendered = template.render(Context({}))
            self.assertHTMLEqual(
                rendered, "Variable: <strong>variable</strong>\n"
            )

    def test_call_with_invalid_name(self):
        # Note: No tag registered

        simple_tag_tempate = '{% load component_tags %}{% component name="test" variable="variable" %}'
        block_tag_template = self.inline_to_block(simple_tag_tempate)

        for tag in [simple_tag_tempate, block_tag_template]:
            template = Template(tag)
            with self.assertRaises(
                django_components.component_registry.NotRegistered
            ):
                template.render(Context({}))

    def test_component_called_with_positional_name(self):
        component.registry.register(name="test", component=SimpleComponent)

        simple_tag_tempate = '{% load component_tags %}{% component "test" variable="variable" %}'
        block_tag_template = self.inline_to_block(simple_tag_tempate)

        for tag in [simple_tag_tempate, block_tag_template]:
            template = Template(tag)
            rendered = template.render(Context({}))
            self.assertHTMLEqual(
                rendered, "Variable: <strong>variable</strong>\n"
            )

    def test_call_component_with_two_variables(self):
        component.registry.register(name="test", component=IffedComponent)

        simple_tag_tempate = """
            {% load component_tags %}
            {% component name="test" variable="variable" variable2="hej" %}
        """
        block_tag_template = self.inline_to_block(simple_tag_tempate)

        for tag in [simple_tag_tempate, block_tag_template]:
            template = Template(tag)
            rendered = template.render(Context({}))
            expected_outcome = (
                """Variable: <strong>variable</strong>\n"""
                """Variable2: <strong>hej</strong>"""
            )
            self.assertHTMLEqual(rendered, textwrap.dedent(expected_outcome))

    def test_component_called_with_singlequoted_name(self):
        component.registry.register(name="test", component=SimpleComponent)

        simple_tag_tempate = """{% load component_tags %}{% component 'test' variable="variable" %}"""
        block_tag_template = self.inline_to_block(simple_tag_tempate)

        for tag in [simple_tag_tempate, block_tag_template]:
            template = Template(tag)
            rendered = template.render(Context({}))
            self.assertHTMLEqual(
                rendered, "Variable: <strong>variable</strong>\n"
            )

    def test_component_called_with_variable_as_name(self):
        component.registry.register(name="test", component=SimpleComponent)

        simple_tag_tempate = """
            {% load component_tags %}
            {% with component_name="test" %}
                {% component component_name variable="variable" %}
            {% endwith %}
        """
        block_tag_template = self.inline_to_block(simple_tag_tempate)

        for tag in [simple_tag_tempate, block_tag_template]:
            template = Template(tag)
            rendered = template.render(Context({}))
            self.assertHTMLEqual(
                rendered, "Variable: <strong>variable</strong>\n"
            )

    def test_component_called_with_invalid_variable_as_name(self):
        component.registry.register(name="test", component=SimpleComponent)

        simple_tag_tempate = """
            {% load component_tags %}
            {% with component_name="BLAHONGA" %}
                {% component component_name variable="variable" %}
            {% endwith %}
        """
        block_tag_template = self.inline_to_block(simple_tag_tempate)

        for tag in [simple_tag_tempate, block_tag_template]:
            template = Template(tag)

        with self.assertRaises(
            django_components.component_registry.NotRegistered
        ):
            template.render(Context({}))


class ComponentSlottedTemplateTagTest(SimpleTestCase):
    def setUp(self):
        # NOTE: component.registry is global, so need to clear before each test
        component.registry.clear()

    def test_slotted_template_basic(self):
        component.registry.register(name="test1", component=SlottedComponent)
        component.registry.register(name="test2", component=SimpleComponent)

        template = Template(
            """
            {% load component_tags %}
            {% component_block "test1" %}
                {% fill "header" %}
                    Custom header
                {% endfill %}
                {% fill "main" %}
                    {% component "test2" variable="variable" %}
                {% endfill %}
            {% endcomponent_block %}
        """
        )
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

    def test_slotted_template_with_context_var(self):
        component.registry.register(
            name="test1", component=SlottedComponentWithContext
        )

        template = Template(
            """
            {% load component_tags %}
            {% with my_first_variable="test123" %}
                {% component_block "test1" variable="test456" %}
                    {% fill "main" %}
                        {{ my_first_variable }} - {{ variable }}
                    {% endfill %}
                    {% fill "footer" %}
                        {{ my_second_variable }}
                    {% endfill %}
                {% endcomponent_block %}
            {% endwith %}
        """
        )
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

        template = Template(
            '{% load component_tags %}{% component_block "test" %}{% endcomponent_block %}'
        )
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
        component.registry.register(
            name="test", component=SlottedComponentNoSlots
        )
        template = Template(
            """
            {% load component_tags %}
            {% component_block "test" %}{% endcomponent_block %}
        """
        )
        rendered = template.render(Context({}))

        self.assertHTMLEqual(rendered, "<custom-template></custom-template>")

    def test_slotted_template_without_slots_and_single_quotes(self):
        component.registry.register(
            name="test", component=SlottedComponentNoSlots
        )
        template = Template(
            """
            {% load component_tags %}
            {% component_block 'test' %}{% endcomponent_block %}
        """
        )
        rendered = template.render(Context({}))

        self.assertHTMLEqual(rendered, "<custom-template></custom-template>")

    def test_variable_fill_name(self):
        component.registry.register(name="test", component=SlottedComponent)
        template = Template(
            """
            {% load component_tags %}
            {% with slotname="header" %}
                {% component_block 'test' %}
                    {% fill slotname %}Hi there!{% endfill %}
            {% endcomponent_block %}
            {% endwith %}
            """
        )
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
            template_name = "slotted_template_with_required_slot.html"

        component.registry.register("test", Component)
        template = Template(
            """
            {% load component_tags %}
            {% component_block 'test' %}
            {% endcomponent_block %}
            """
        )
        with self.assertRaises(TemplateSyntaxError):
            template.render(Context({}))

    def test_default_slot_is_fillable_by_implicit_fill_content(self):
        component.registry.register("test_comp", ComponentWithDefaultSlot)

        template = Template(
            """
            {% load component_tags %}
            {% component_block 'test_comp' %}
              <p>This fills the 'main' slot.</p>
            {% endcomponent_block %}
            """
        )

        expected = """
        <div>
          <main><p>This fills the 'main' slot.</p></main>
        </div>
        """
        rendered = template.render(Context({}))
        self.assertHTMLEqual(rendered, expected)

    def test_default_slot_is_fillable_by_explicit_fill_content(self):
        component.registry.register("test_comp", ComponentWithDefaultSlot)

        template = Template(
            """
            {% load component_tags %}
            {% component_block 'test_comp' %}
              {% fill "main" %}<p>This fills the 'main' slot.</p>{% endfill %}
            {% endcomponent_block %}
            """
        )
        expected = """
        <div>
          <main><p>This fills the 'main' slot.</p></main>
        </div>
        """
        rendered = template.render(Context({}))
        self.assertHTMLEqual(rendered, expected)

    def test_error_raised_when_default_and_required_slot_not_filled(self):
        component.registry.register(
            "test_comp", ComponentWithDefaultAndRequiredSlot
        )
        template = Template(
            """
            {% load component_tags %}
            {% component_block 'test_comp' %}
            {% endcomponent_block %}
            """
        )
        with self.assertRaises(TemplateSyntaxError):
            template.render(Context({}))

    def test_fill_tag_can_occur_within_component_block_nested_in_implicit_fill(
        self,
    ):
        component.registry.register("test_comp", ComponentWithDefaultSlot)
        component.registry.register("slotted", SlottedComponent)

        template = Template(
            """
            {% load component_tags %}
            {% component_block 'test_comp' %}
              {% component_block "slotted" %}
                {% fill "header" %}This Is Allowed{% endfill %}
                {% fill "main" %}{% endfill %}
                {% fill "footer" %}{% endfill %}
              {% endcomponent_block %}
            {% endcomponent_block %}
            """
        )
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
        component.registry.register("test_comp", ComponentWithDefaultSlot)

        with self.assertRaises(TemplateSyntaxError):
            Template(
                """
                {% load component_tags %}
                {% component_block 'test_comp' %}
                  {% fill "main" %}Main content{% endfill %}
                  <p>And add this too!</p>
                {% endcomponent_block %}
                """
            )

    def test_comments_permitted_inside_implicit_fill_content(self):
        component.registry.register("test_comp", ComponentWithDefaultSlot)
        Template(
            """
            {% load component_tags %}
            {% component_block 'test_comp' %}
              <p>Main Content</p>
              {% comment %}
              This won't show up in the rendered HTML
              {% endcomment %}
              {# Nor will this #}
            {% endcomponent_block %}
            """
        )
        self.assertTrue(True)

    def test_component_without_default_slot_refuses_implicit_fill(self):
        component.registry.register("test_comp", SlottedComponent)
        template = Template(
            """
            {% load component_tags %}
            {% component_block 'test_comp' %}
              <p>This shouldn't work because the included component doesn't mark
              any of its slots as 'default'</p>
            {% endcomponent_block %}
            """
        )
        with self.assertRaises(TemplateSyntaxError):
            template.render(Context({}))

    def test_component_template_cannot_have_multiple_default_slots(self):
        class BadComponent(component.Component):
            def get_template(
                self, context, template_name: Optional[str] = None
            ) -> Template:
                return Template(
                    """
                    {% load django_components %}
                    <div>
                    {% slot "icon" %} {% endslot default %}
                    {% slot "description" %} {% endslot default %}
                    </div>
                    """
                )

        c = BadComponent("name")
        with self.assertRaises(TemplateSyntaxError):
            c.render(Context({}))

    def test_slot_name_fill_typo_gives_helpful_error_message(self):
        component.registry.register(name="test1", component=SlottedComponent)

        template = Template(
            """
            {% load component_tags %}
            {% component_block "test1" %}
                {% fill "haeder" %}
                    Custom header
                {% endfill %}
                {% fill "main" %}
                    main content
                {% endfill %}
            {% endcomponent_block %}
        """
        )
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


class SlottedTemplateRegressionTests(SimpleTestCase):
    def setUp(self):
        # NOTE: component.registry is global, so need to clear before each test
        component.registry.clear()

    def test_slotted_template_that_uses_missing_variable(self):
        component.registry.register(
            name="test", component=SlottedComponentWithMissingVariable
        )
        template = Template(
            """
            {% load component_tags %}
            {% component_block 'test' %}{% endcomponent_block %}
            """
        )
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

    def test_component_block_accepts_provided_and_default_parameters(self):
        component.registry.register(
            name="test", component=ComponentWithProvidedAndDefaultParameters
        )

        template = Template(
            """
            {% load component_tags %}
            {% component_block "test" variable="provided value" %}
            {% endcomponent_block %}
            """
        )
        rendered = template.render(Context({}))
        self.assertHTMLEqual(
            rendered,
            "Provided variable: <strong>provided value</strong>\nDefault: <p>default text</p>",
        )


class MultiComponentTests(SimpleTestCase):
    def setUp(self):
        component.registry.clear()

    def register_components(self):
        component.registry.register("first_component", SlottedComponent)
        component.registry.register(
            "second_component", SlottedComponentWithContext
        )

    def make_template(self, first_component_slot="", second_component_slot=""):
        return Template(
            "{% load component_tags %}"
            "{% component_block 'first_component' %}"
            + first_component_slot
            + "{% endcomponent_block %}"
            "{% component_block 'second_component' variable='xyz' %}"
            + second_component_slot
            + "{% endcomponent_block %}"
        )

    def expected_result(
        self, first_component_slot="", second_component_slot=""
    ):
        return (
            "<custom-template><header>{}</header>".format(
                first_component_slot or "Default header"
            )
            + "<main>Default main</main><footer>Default footer</footer></custom-template>"
            + "<custom-template><header>{}</header>".format(
                second_component_slot or "Default header"
            )
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
        rendered = self.make_template(first_slot, second_slot).render(
            Context({})
        )
        self.assertHTMLEqual(
            rendered,
            self.expected_result(first_slot_content, second_slot_content),
        )

    def test_both_components_render_correctly_when_only_first_has_slots(self):
        self.register_components()
        first_slot_content = "<p>Slot #1</p>"
        first_slot = self.wrap_with_slot_tags(first_slot_content)
        rendered = self.make_template(first_slot).render(Context({}))
        self.assertHTMLEqual(
            rendered, self.expected_result(first_slot_content)
        )

    def test_both_components_render_correctly_when_only_second_has_slots(self):
        self.register_components()
        second_slot_content = "<div>Slot #2</div>"
        second_slot = self.wrap_with_slot_tags(second_slot_content)
        rendered = self.make_template("", second_slot).render(Context({}))
        self.assertHTMLEqual(
            rendered, self.expected_result("", second_slot_content)
        )


class TemplateInstrumentationTest(SimpleTestCase):
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
        component.registry.register("inner_component", SimpleComponent)

    def templates_used_to_render(self, subject_template, render_context=None):
        """Emulate django.test.client.Client (see request method)."""
        from django.test.signals import template_rendered

        templates_used = []

        def receive_template_signal(sender, template, context, **_kwargs):
            templates_used.append(template.name)

        template_rendered.connect(
            receive_template_signal, dispatch_uid="test_method"
        )
        subject_template.render(render_context or Context({}))
        template_rendered.disconnect(dispatch_uid="test_method")
        return templates_used

    def test_template_shown_as_used(self):
        template = Template(
            """
            {% load component_tags %}
            {% component 'test_component' %}
            """,
            name="root",
        )
        templates_used = self.templates_used_to_render(template)
        self.assertIn("slotted_template.html", templates_used)

    def test_nested_component_templates_all_shown_as_used(self):
        template = Template(
            """
            {% load component_tags %}
            {% component_block 'test_component' %}
              {% fill "header" %}
                {% component 'inner_component' variable='foo' %}
              {% endfill %}
            {% endcomponent_block %}
            """,
            name="root",
        )
        templates_used = self.templates_used_to_render(template)
        self.assertIn("slotted_template.html", templates_used)
        self.assertIn("simple_template.html", templates_used)


class NestedSlotTests(SimpleTestCase):
    class NestedComponent(component.Component):
        template_name = "nested_slot_template.html"

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
        template = Template(
            """
            {% load component_tags %}
            {% component_block 'test' %}{% endcomponent_block %}
        """
        )
        rendered = template.render(Context({}))
        self.assertHTMLEqual(rendered, '<div id="outer">Default</div>')

    def test_inner_slot_overriden(self):
        template = Template(
            """
            {% load component_tags %}
            {% component_block 'test' %}{% fill 'inner' %}Override{% endfill %}{% endcomponent_block %}
        """
        )
        rendered = template.render(Context({}))
        self.assertHTMLEqual(rendered, '<div id="outer">Override</div>')

    def test_outer_slot_overriden(self):
        template = Template(
            """
            {% load component_tags %}
            {% component_block 'test' %}{% fill 'outer' %}<p>Override</p>{% endfill %}{% endcomponent_block %}
        """
        )
        rendered = template.render(Context({}))
        self.assertHTMLEqual(rendered, "<p>Override</p>")

    def test_both_overriden_and_inner_removed(self):
        template = Template(
            """
            {% load component_tags %}
            {% component_block 'test' %}
                {% fill 'outer' %}<p>Override</p>{% endfill %}
                {% fill 'inner' %}<p>Will not appear</p>{% endfill %}
            {% endcomponent_block %}
        """
        )
        rendered = template.render(Context({}))
        self.assertHTMLEqual(rendered, "<p>Override</p>")


class ConditionalSlotTests(SimpleTestCase):
    class ConditionalComponent(component.Component):
        template_name = "conditional_template.html"

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
        template = Template(
            """
            {% load component_tags %}
            {% component_block 'test' %}
                {% fill 'a' %}Override A{% endfill %}
                {% fill 'b' %}Override B{% endfill %}
            {% endcomponent_block %}
        """
        )
        rendered = template.render(Context({}))
        self.assertHTMLEqual(rendered, "")

    def test_default_content_if_no_slots(self):
        template = Template(
            """
            {% load component_tags %}
            {% component 'test' branch='a' %}
            {% component 'test' branch='b' %}
        """
        )
        rendered = template.render(Context({}))
        self.assertHTMLEqual(
            rendered, '<p id="a">Default A</p><p id="b">Default B</p>'
        )

    def test_one_slot_overridden(self):
        template = Template(
            """
            {% load component_tags %}
            {% component_block 'test' branch='a' %}
                {% fill 'b' %}Override B{% endfill %}
            {% endcomponent_block %}
            {% component_block 'test' branch='b' %}
                {% fill 'b' %}Override B{% endfill %}
            {% endcomponent_block %}
        """
        )
        rendered = template.render(Context({}))
        self.assertHTMLEqual(
            rendered, '<p id="a">Default A</p><p id="b">Override B</p>'
        )

    def test_both_slots_overridden(self):
        template = Template(
            """
            {% load component_tags %}
            {% component_block 'test' branch='a' %}
                {% fill 'a' %}Override A{% endfill %}
                {% fill 'b' %}Override B{% endfill %}
            {% endcomponent_block %}
            {% component_block 'test' branch='b' %}
                {% fill 'a' %}Override A{% endfill %}
                {% fill 'b' %}Override B{% endfill %}
            {% endcomponent_block %}
        """
        )
        rendered = template.render(Context({}))
        self.assertHTMLEqual(
            rendered, '<p id="a">Override A</p><p id="b">Override B</p>'
        )


class SlotSuperTests(SimpleTestCase):
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
        template = Template(
            """
            {% load component_tags %}
            {% component_block "test" %}
                {% fill "header" as "header" %}Before: {{ header.default }}{% endfill %}
                {% fill "main" as "main" %}{{ main.default }}{% endfill %}
                {% fill "footer" as "footer" %}{{ footer.default }}, after{% endfill %}
            {% endcomponent_block %}
        """
        )
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
        template = Template(
            """
            {% load component_tags %}
            {% component_block "test" %}
                {% fill "header" as "header" %}First: {{ header.default }}; Second: {{ header.default }}{% endfill %}
            {% endcomponent_block %}
        """
        )
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
        template = Template(
            """
            {% load component_tags %}
            {% component_block "test" %}
                {% fill "header" as "header" %}
                    {% for i in range %}
                        {% if forloop.first %}First {{ header.default }}
                        {% else %}Later {{ header.default }}
                        {% endif %}
                    {% endfor %}
                {% endfill %}
            {% endcomponent_block %}
        """
        )
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


class TemplateSyntaxErrorTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        component.registry.register("test", SlottedComponent)
        component.registry.register("broken_component", BrokenComponent)
        component.registry.register(
            "nonunique_slot_component", NonUniqueSlotsComponent
        )

    @classmethod
    def tearDownClass(cls) -> None:
        super().tearDownClass()
        component.registry.clear()

    def test_variable_outside_fill_tag_compiles_w_out_error(self):
        # As of v0.28 this is valid, provided the component registered under "test"
        # contains a slot tag marked as 'default'. This is verified outside
        # template compilation time.
        Template(
            """
            {% load component_tags %}
            {% component_block "test" %}
                {{ anything }}
            {% endcomponent_block %}
            """
        )

    def test_text_outside_fill_tag_is_not_error(self):
        # As of v0.28 this is valid, provided the component registered under "test"
        # contains a slot tag marked as 'default'. This is verified outside
        # template compilation time.
        Template(
            """
            {% load component_tags %}
            {% component_block "test" %}
                Text
            {% endcomponent_block %}
            """
        )

    def test_nonfill_block_outside_fill_tag_is_error(self):
        with self.assertRaises(TemplateSyntaxError):
            Template(
                """
                {% load component_tags %}
                {% component_block "test" %}
                    {% if True %}
                        {% fill "header" %}{% endfill %}
                    {% endif %}
                {% endcomponent_block %}
            """
            )

    def test_unclosed_component_block_is_error(self):
        with self.assertRaises(TemplateSyntaxError):
            Template(
                """
                {% load component_tags %}
                {% component_block "test" %}
                {% fill "header" %}{% endfill %}
            """
            )

    def test_fill_with_no_parent_is_error(self):
        with self.assertRaises(TemplateSyntaxError):
            Template(
                """
                {% load component_tags %}
                {% fill "header" %}contents{% endfill %}
            """
            ).render(Context({}))

    def test_isolated_slot_is_error(self):
        with self.assertRaises(TemplateSyntaxError):
            Template(
                """
                {% load component_tags %}
                {% component_block "broken_component" %}
                    {% fill "header" %}Custom header {% endfill %}
                    {% fill "main" %}Custom main{% endfill %}
                    {% fill "footer" %}Custom footer{% endfill %}
                {% endcomponent_block %}
                """
            ).render(Context({}))

    def test_non_unique_fill_names_is_error(self):
        with self.assertRaises(TemplateSyntaxError):
            Template(
                """
                {% load component_tags %}
                {% component_block "broken_component" %}
                    {% fill "header" %}Custom header {% endfill %}
                    {% fill "header" %}Other header{% endfill %}
                {% endcomponent_block %}
                """
            ).render(Context({}))

    def test_non_unique_slot_names_is_error(self):
        with self.assertRaises(TemplateSyntaxError):
            Template(
                """
                {% load component_tags %}
                {% component_block "nonunique_slot_component" %}
                {% endcomponent_block %}
                """
            ).render(Context({}))


class ComponentNestingTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        component.registry.register("dashboard", _DashboardComponent)
        component.registry.register("calendar", _CalendarComponent)

    @classmethod
    def tearDownClass(cls) -> None:
        super().tearDownClass()
        component.registry.clear()

    def test_component_nesting_component_without_fill(self):
        template = Template(
            """
            {% load component_tags %}
            {% component "dashboard" %}
            """
        )
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

    def test_component_nesting_component_with_fill_and_super(self):
        template = Template(
            """
            {% load component_tags %}
            {% component_block "dashboard" %}
              {% fill "header" as "h" %} Hello! {{ h.default }} {% endfill %}
            {% endcomponent_block %}
            """
        )
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


class ConditionalIfFilledSlotsTests(SimpleTestCase):
    class ComponentWithConditionalSlots(component.Component):
        template_name = "template_with_conditional_slots.html"

    class ComponentWithComplexConditionalSlots(component.Component):
        template_name = "template_with_if_elif_else_conditional_slots.html"

    class ComponentWithNegatedConditionalSlot(component.Component):
        template_name = "template_with_negated_conditional_slots.html"

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        component.registry.register(
            "conditional_slots", cls.ComponentWithConditionalSlots
        )
        component.registry.register(
            "complex_conditional_slots",
            cls.ComponentWithComplexConditionalSlots,
        )
        component.registry.register(
            "negated_conditional_slot", cls.ComponentWithNegatedConditionalSlot
        )

    @classmethod
    def tearDownClass(cls) -> None:
        super().tearDownClass()
        component.registry.clear()

    def test_simple_component_with_conditional_slot(self):
        template = """
        {% load component_tags %}
        {% component "conditional_slots" %}
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

    def test_component_block_with_filled_conditional_slot(self):
        template = """
        {% load component_tags %}
        {% component_block "conditional_slots" %}
          {% fill "subtitle" %} My subtitle {% endfill %}
        {% endcomponent_block %}
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
        template = """
        {% load component_tags %}
        {% component_block "complex_conditional_slots" %}
            {% fill "alt_subtitle" %} A different subtitle {% endfill %}
        {% endcomponent_block %}
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
        template = """
           {% load component_tags %}
           {% component_block "complex_conditional_slots" %}
           {% endcomponent_block %}
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

    def test_component_block_with_negated_conditional_slot(self):
        template = """
        {% load component_tags %}
        {% component_block "negated_conditional_slot" %}
            {# Whoops! Forgot to fill a slot! #}
        {% endcomponent_block %}
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


class RegressionTests(SimpleTestCase):
    """Ensure we don't break the same thing AGAIN."""

    def setUp(self):
        component.registry.clear()
        super().setUp()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        component.registry.clear()

    def test_block_and_extends_tag_works(self):
        component.registry.register("slotted_component", SlottedComponent)
        template = """
        {% extends "extendable_template_with_blocks.html" %}
        {% load component_tags %}
        {% block body %}
          {% component_block "slotted_component" %}
            {% fill "header" %}{% endfill %}
            {% fill "main" %}
              TEST
            {% endfill %}
            {% fill "footer" %}{% endfill %}
          {% endcomponent_block %}
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


class IterationFillTest(SimpleTestCase):
    """Tests a behaviour of {% fill .. %} tag which is inside a template {% for .. %} loop."""

    class ComponentSimpleSlotInALoop(django_components.component.Component):
        template_name = "template_with_slot_in_a_loop.html"

        def get_context_data(self, objects: Iterable) -> dict:
            return {
                "objects": objects,
            }

    def setUp(self):
        django_components.component.registry.clear()

    def test_inner_slot_iteration_basic(self):
        component.registry.register(
            "slot_in_a_loop", self.ComponentSimpleSlotInALoop
        )

        template = Template(
            """
            {% load component_tags %}
            {% component_block "slot_in_a_loop" objects=objects %}
                {% fill "slot_inner" %}
                    {{ object }}
                {% endfill %}
            {% endcomponent_block %}
        """
        )
        objects = ["OBJECT1", "OBJECT2"]
        rendered = template.render(Context({"objects": objects}))

        self.assertHTMLEqual(
            rendered,
            """
            OBJECT1
            OBJECT2
            """,
        )

    def test_inner_slot_iteration_with_variable_from_outer_scope(self):
        component.registry.register(
            "slot_in_a_loop", self.ComponentSimpleSlotInALoop
        )

        template = Template(
            """
            {% load component_tags %}
            {% component_block "slot_in_a_loop" objects=objects %}
                {% fill "slot_inner" %}
                    {{ outer_scope_variable }}
                    {{ object }}
                {% endfill %}
            {% endcomponent_block %}
        """
        )
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

    def test_inner_slot_iteration_nested(self):
        component.registry.register(
            "slot_in_a_loop", self.ComponentSimpleSlotInALoop
        )

        objects = [
            {"inner": ["OBJECT1_ITER1", "OBJECT2_ITER1"]},
            {"inner": ["OBJECT1_ITER2", "OBJECT2_ITER2"]},
        ]

        template = Template(
            """
            {% load component_tags %}
            {% component_block "slot_in_a_loop" objects=objects %}
                {% fill "slot_inner" %}
                    {% component_block "slot_in_a_loop" objects=object.inner %}
                        {% fill "slot_inner" %}
                            {{ object }}
                        {% endfill %}
                    {% endcomponent_block %}
                {% endfill %}
            {% endcomponent_block %}
        """
        )
        rendered = template.render(Context({"objects": objects}))

        self.assertHTMLEqual(
            rendered,
            """
            OBJECT1_ITER1
            OBJECT2_ITER1
            OBJECT1_ITER2
            OBJECT2_ITER2
            """,
        )

    def test_inner_slot_iteration_nested_with_outer_scope_variable(self):
        component.registry.register(
            "slot_in_a_loop", self.ComponentSimpleSlotInALoop
        )

        objects = [
            {"inner": ["OBJECT1_ITER1", "OBJECT2_ITER1"]},
            {"inner": ["OBJECT1_ITER2", "OBJECT2_ITER2"]},
        ]

        template = Template(
            """
            {% load component_tags %}
            {% component_block "slot_in_a_loop" objects=objects %}
                {% fill "slot_inner" %}
                    {{ outer_scope_variable_1 }}
                    {% component_block "slot_in_a_loop" objects=object.inner %}
                        {% fill "slot_inner" %}
                            {{ outer_scope_variable_2 }}
                            {{ object }}
                        {% endfill %}
                    {% endcomponent_block %}
                {% endfill %}
            {% endcomponent_block %}
        """
        )
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
            OBJECT1_ITER1
            OUTER_SCOPE_VARIABLE2
            OBJECT2_ITER1
            OUTER_SCOPE_VARIABLE1
            OUTER_SCOPE_VARIABLE2
            OBJECT1_ITER2
            OUTER_SCOPE_VARIABLE2
            OBJECT2_ITER2
            """,
        )

    def test_inner_slot_iteration_nested_with_slot_default(self):
        component.registry.register(
            "slot_in_a_loop", self.ComponentSimpleSlotInALoop
        )

        objects = [
            {"inner": ["OBJECT1_ITER1", "OBJECT2_ITER1"]},
            {"inner": ["OBJECT1_ITER2", "OBJECT2_ITER2"]},
        ]

        template = Template(
            """
            {% load component_tags %}
            {% component_block "slot_in_a_loop" objects=objects %}
                {% fill "slot_inner" %}
                    {% component_block "slot_in_a_loop" objects=object.inner %}
                        {% fill "slot_inner" as "super_slot_inner" %}
                            {{ super_slot_inner.default }}
                        {% endfill %}
                    {% endcomponent_block %}
                {% endfill %}
            {% endcomponent_block %}
        """
        )
        rendered = template.render(Context({"objects": objects}))

        self.assertHTMLEqual(
            rendered,
            """
            OBJECT1_ITER1 default
            OBJECT2_ITER1 default
            OBJECT1_ITER2 default
            OBJECT2_ITER2 default
            """,
        )

    def test_inner_slot_iteration_nested_with_slot_default_and_outer_scope_variable(
        self,
    ):
        component.registry.register(
            "slot_in_a_loop", self.ComponentSimpleSlotInALoop
        )

        objects = [
            {"inner": ["OBJECT1_ITER1", "OBJECT2_ITER1"]},
            {"inner": ["OBJECT1_ITER2", "OBJECT2_ITER2"]},
        ]

        template = Template(
            """
            {% load component_tags %}
            {% component_block "slot_in_a_loop" objects=objects %}
                {% fill "slot_inner" %}
                    {{ outer_scope_variable_1 }}
                    {% component_block "slot_in_a_loop" objects=object.inner %}
                        {% fill "slot_inner" as "super_slot_inner" %}
                            {{ outer_scope_variable_2 }}
                            {{ super_slot_inner.default }}
                        {% endfill %}
                    {% endcomponent_block %}
                {% endfill %}
            {% endcomponent_block %}
        """
        )
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
            OBJECT1_ITER1 default
            OUTER_SCOPE_VARIABLE2
            OBJECT2_ITER1 default
            OUTER_SCOPE_VARIABLE1
            OUTER_SCOPE_VARIABLE2
            OBJECT1_ITER2 default
            OUTER_SCOPE_VARIABLE2
            OBJECT2_ITER2 default
            """,
        )
