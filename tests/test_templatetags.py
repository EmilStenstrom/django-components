import re
from textwrap import dedent

from django.template import Context, Template, TemplateSyntaxError

import django_components
from django_components import component

from .django_test_setup import *  # NOQA
from .testutils import Django30CompatibleSimpleTestCase as SimpleTestCase


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
            self.assertHTMLEqual(rendered, dedent(expected_outcome))

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
                {% slot "header" %}
                    Custom header
                {% endslot %}
                {% slot "main" %}
                    {% component "test2" variable="variable" %}
                {% endslot %}
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
                    {% slot "main" %}
                        {{ my_first_variable }} - {{ variable }}
                    {% endslot %}
                    {% slot "footer" %}
                        {{ my_second_variable }}
                    {% endslot %}
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
            '{% load component_tags %}{% component_block "test" variable="provided value" %}{% endcomponent_block %}'
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
        return '{% slot "header" %}' + s + "{% endslot %}"

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
            "{% load component_tags %}{% component 'test_component' %}",
            name="root",
        )
        templates_used = self.templates_used_to_render(template)
        self.assertIn("slotted_template.html", templates_used)

    def test_nested_component_templates_all_shown_as_used(self):
        template = Template(
            "{% load component_tags %}{% component_block 'test_component' %}"
            "{% slot \"header\" %}{% component 'inner_component' variable='foo' %}{% endslot %}"
            "{% endcomponent_block %}",
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

    def test_default_slots_render_correctly(self):
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
            {% component_block 'test' %}{% slot 'inner' %}Override{% endslot %}{% endcomponent_block %}
        """
        )
        rendered = template.render(Context({}))
        self.assertHTMLEqual(rendered, '<div id="outer">Override</div>')

    def test_outer_slot_overriden(self):
        template = Template(
            """
            {% load component_tags %}
            {% component_block 'test' %}{% slot 'outer' %}<p>Override</p>{% endslot %}{% endcomponent_block %}
        """
        )
        rendered = template.render(Context({}))
        self.assertHTMLEqual(rendered, "<p>Override</p>")

    def test_both_overriden_and_inner_removed(self):
        template = Template(
            """
            {% load component_tags %}
            {% component_block 'test' %}
                {% slot 'outer' %}<p>Override</p>{% endslot %}
                {% slot 'inner' %}<p>Will not appear</p>{% endslot %}
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
                {% slot 'a' %}Override A{% endslot %}
                {% slot 'b' %}Override B{% endslot %}
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
                {% slot 'b' %}Override B{% endslot %}
            {% endcomponent_block %}
            {% component_block 'test' branch='b' %}
                {% slot 'b' %}Override B{% endslot %}
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
                {% slot 'a' %}Override A{% endslot %}
                {% slot 'b' %}Override B{% endslot %}
            {% endcomponent_block %}
            {% component_block 'test' branch='b' %}
                {% slot 'a' %}Override A{% endslot %}
                {% slot 'b' %}Override B{% endslot %}
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
                {% slot "header" %}Before: {{ slot.super }}{% endslot %}
                {% slot "main" %}{{ slot.super }}{% endslot %}
                {% slot "footer" %}{{ slot.super }}, after{% endslot %}
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
                {% slot "header" %}First: {{ slot.super }}; Second: {{ slot.super }}{% endslot %}
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
                {% slot "header" %}
                    {% for i in range %}
                        {% if forloop.first %}First {{slot.super}}
                        {% else %}Later {{ slot.super }}
                        {% endif %}
                    {%endfor %}
                {% endslot %}
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

    def test_variable_outside_slot_tag_is_error(self):
        with self.assertRaises(TemplateSyntaxError):
            Template(
                """
                {% load component_tags %}
                {% component_block "test" %}
                    {{ slot.super }}
                {% endcomponent_block %}
            """
            )

    def test_text_outside_slot_tag_is_error(self):
        with self.assertRaises(TemplateSyntaxError):
            Template(
                """
                {% load component_tags %}
                {% component_block "test" %}
                    Text
                {% endcomponent_block %}
            """
            )

    def test_nonslot_block_outside_slot_tag_is_error(self):
        with self.assertRaises(TemplateSyntaxError):
            Template(
                """
                {% load component_tags %}
                {% component_block "test" %}
                    {% if True %}
                        {% slot "header" %}{% endslot %}
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
                    {% slot "header" %}{% endslot %}
            """
            )

    def test_slot_with_no_parent_is_error(self):
        with self.assertRaises(TemplateSyntaxError):
            Template(
                """
                {% load component_tags %}
                {% slot "header" %}contents{% endslot %}
            """
            ).render(Context({}))

    def test_isolated_slot_is_error(self):
        with self.assertRaises(TemplateSyntaxError):
            Template(
                """
                {% load component_tags %}
                {% component_block "broken_component" %}
                    {% slot "header" %}Custom header{% endslot %}
                    {% slot "main" %}Custom main{% endslot %}
                    {% slot "footer" %}Custom footer{% endslot %}
                {% endcomponent_block %}
            """
            ).render(Context({}))
