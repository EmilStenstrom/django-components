from textwrap import dedent

from django.template import Context, Template

from django_components import component

from .django_test_setup import *  # NOQA
from .testutils import Django111CompatibleSimpleTestCase as SimpleTestCase


class SimpleComponent(component.Component):
    def context(self, variable, variable2="default"):
        return {
            "variable": variable,
            "variable2": variable2,
        }

    def template(self, context):
        return "simple_template.html"

    class Media:
        css = {"all": ["style.css"]}
        js = ["script.js"]


class IffedComponent(SimpleComponent):
    def template(self, context):
        return "iffed_template.html"


class SlottedComponent(component.Component):
    def template(self, context):
        return "slotted_template.html"


class SlottedComponentWithMissingVariable(component.Component):
    def template(self, context):
        return "slotted_template_with_missing_variable.html"


class SlottedComponentNoSlots(component.Component):
    def template(self, context):
        return "slotted_template_no_slots.html"


class SlottedComponentWithContext(component.Component):
    def context(self, variable):
        return {"variable": variable}

    def template(self, context):
        return "slotted_template.html"


class ComponentWithProvidedAndDefaultParameters(component.Component):
    def context(self, variable, default_param="default text"):
        return {"variable": variable, 'default_param': default_param}

    def template(self, context):
        return "template_with_provided_and_default_parameters.html"


class ComponentTemplateTagTest(SimpleTestCase):
    def setUp(self):
        # NOTE: component.registry is global, so need to clear before each test
        component.registry.clear()

    def test_single_component_dependencies(self):
        component.registry.register(name="test", component=SimpleComponent)

        template = Template("{% load component_tags %}{% component_dependencies %}")
        rendered = template.render(Context())
        expected_outcome = (
            """<link href="style.css" type="text/css" media="all" rel="stylesheet">\n"""
            """<script src="script.js"></script>"""
        )
        self.assertHTMLEqual(rendered, dedent(expected_outcome))

    def test_single_component_css_dependencies(self):
        component.registry.register(name="test", component=SimpleComponent)

        template = Template("{% load component_tags %}{% component_css_dependencies %}")
        rendered = template.render(Context())
        expected_outcome = (
            """<link href="style.css" type="text/css" media="all" rel="stylesheet">"""
        )
        self.assertHTMLEqual(rendered, dedent(expected_outcome))

    def test_single_component_js_dependencies(self):
        component.registry.register(name="test", component=SimpleComponent)

        template = Template("{% load component_tags %}{% component_js_dependencies %}")
        rendered = template.render(Context())
        expected_outcome = (
            """<script src="script.js"></script>"""
        )
        self.assertHTMLEqual(rendered, dedent(expected_outcome))

    def test_single_component(self):
        component.registry.register(name="test", component=SimpleComponent)

        template = Template(
            '{% load component_tags %}{% component name="test" variable="variable" %}'
        )
        rendered = template.render(Context({}))
        self.assertHTMLEqual(rendered, "Variable: <strong>variable</strong>\n")

    def test_call_component_with_two_variables(self):
        component.registry.register(name="test", component=IffedComponent)

        template = Template(
            "{% load component_tags %}"
            '{% component name="test" variable="variable" variable2="hej" %}'
        )
        rendered = template.render(Context({}))
        expected_outcome = (
            """Variable: <strong>variable</strong>\n"""
            """Variable2: <strong>hej</strong>"""
        )
        self.assertHTMLEqual(rendered, dedent(expected_outcome))

    def test_component_called_with_positional_name(self):
        component.registry.register(name="test", component=SimpleComponent)

        template = Template(
            '{% load component_tags %}{% component "test" variable="variable" %}'
        )
        rendered = template.render(Context({}))
        self.assertHTMLEqual(rendered, "Variable: <strong>variable</strong>\n")

    def test_component_called_with_singlequoted_name(self):
        component.registry.register(name="test", component=SimpleComponent)

        template = Template(
            '{% load component_tags %}{% component \'test\' variable="variable" %}'
        )
        rendered = template.render(Context({}))
        self.assertHTMLEqual(rendered, "Variable: <strong>variable</strong>\n")

    def test_multiple_component_dependencies(self):
        component.registry.register(name="test1", component=SimpleComponent)
        component.registry.register(name="test2", component=SimpleComponent)

        template = Template("{% load component_tags %}{% component_dependencies %}")
        rendered = template.render(Context())
        expected_outcome = (
            """<link href="style.css" type="text/css" media="all" rel="stylesheet">\n"""
            """<script src="script.js"></script>"""
        )
        self.assertHTMLEqual(rendered, dedent(expected_outcome))

    def test_multiple_component_css_dependencies(self):
        component.registry.register(name="test1", component=SimpleComponent)
        component.registry.register(name="test2", component=SimpleComponent)

        template = Template("{% load component_tags %}{% component_css_dependencies %}")
        rendered = template.render(Context())
        expected_outcome = (
            """<link href="style.css" type="text/css" media="all" rel="stylesheet">"""
        )
        self.assertHTMLEqual(rendered, dedent(expected_outcome))

    def test_multiple_component_js_dependencies(self):
        component.registry.register(name="test1", component=SimpleComponent)
        component.registry.register(name="test2", component=SimpleComponent)

        template = Template("{% load component_tags %}{% component_js_dependencies %}")
        rendered = template.render(Context())
        expected_outcome = (
            """<script src="script.js"></script>"""
        )
        self.assertHTMLEqual(rendered, dedent(expected_outcome))


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
        component.registry.register(name="test1", component=SlottedComponentWithContext)

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
        component.registry.register(name="test", component=SlottedComponentNoSlots)
        template = Template(
            """
            {% load component_tags %}
            {% component_block "test" %}{% endcomponent_block %}
        """
        )
        rendered = template.render(Context({}))

        self.assertHTMLEqual(rendered, "<custom-template></custom-template>")

    def test_slotted_template_without_slots_and_single_quotes(self):
        component.registry.register(name="test", component=SlottedComponentNoSlots)
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
        component.registry.register(name="test", component=SlottedComponentWithMissingVariable)
        template = Template(
            """
            {% load component_tags %}
            {% component_block 'test' %}{% endcomponent_block %}
        """
        )
        rendered = template.render(Context({}))

        self.assertHTMLEqual(rendered, """
            <custom-template>
                <header>Default header</header>
                <main>Default main</main>
                <footer>Default footer</footer>
            </custom-template>
        """)

    def test_component_block_accepts_provided_and_default_parameters(self):
        component.registry.register(name="test", component=ComponentWithProvidedAndDefaultParameters)

        template = Template(
            '{% load component_tags %}{% component_block "test" variable="provided value" %}{% endcomponent_block %}'
        )
        rendered = template.render(Context({}))
        self.assertHTMLEqual(rendered,
                             "Provided variable: <strong>provided value</strong>\nDefault: <p>default text</p>")


class MultiComponentTests(SimpleTestCase):
    def setUp(self):
        component.registry.clear()

    def register_components(self):
        component.registry.register('first_component', SlottedComponent)
        component.registry.register('second_component', SlottedComponentWithContext)

    def make_template(self, first_component_slot='', second_component_slot=''):
        return Template('{% load component_tags %}'
                        "{% component_block 'first_component' %}"
                        + first_component_slot + '{% endcomponent_block %}'
                        "{% component_block 'second_component' variable='xyz' %}"
                        + second_component_slot + '{% endcomponent_block %}')

    def expected_result(self, first_component_slot='', second_component_slot=''):
        return ('<custom-template><header>{}</header>'.format(first_component_slot or "Default header")
                + '<main>Default main</main><footer>Default footer</footer></custom-template>'
                + '<custom-template><header>{}</header>'.format(second_component_slot or "Default header")
                + '<main>Default main</main><footer>Default footer</footer></custom-template>')

    def wrap_with_slot_tags(self, s):
        return '{% slot "header" %}' + s + '{% endslot %}'

    def test_both_components_render_correctly_with_no_slots(self):
        self.register_components()
        rendered = self.make_template().render(Context({}))
        self.assertHTMLEqual(rendered, self.expected_result())

    def test_both_components_render_correctly_with_slots(self):
        self.register_components()
        first_slot_content = '<p>Slot #1</p>'
        second_slot_content = '<div>Slot #2</div>'
        first_slot = self.wrap_with_slot_tags(first_slot_content)
        second_slot = self.wrap_with_slot_tags(second_slot_content)
        rendered = self.make_template(first_slot, second_slot).render(Context({}))
        self.assertHTMLEqual(rendered, self.expected_result(first_slot_content, second_slot_content))

    def test_both_components_render_correctly_when_only_first_has_slots(self):
        self.register_components()
        first_slot_content = '<p>Slot #1</p>'
        first_slot = self.wrap_with_slot_tags(first_slot_content)
        rendered = self.make_template(first_slot).render(Context({}))
        self.assertHTMLEqual(rendered, self.expected_result(first_slot_content))

    def test_both_components_render_correctly_when_only_second_has_slots(self):
        self.register_components()
        second_slot_content = '<div>Slot #2</div>'
        second_slot = self.wrap_with_slot_tags(second_slot_content)
        rendered = self.make_template('', second_slot).render(Context({}))
        self.assertHTMLEqual(rendered, self.expected_result('', second_slot_content))
