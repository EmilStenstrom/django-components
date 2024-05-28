import textwrap

from django.template import Context, Template, TemplateSyntaxError

# isort: off
from .django_test_setup import *  # NOQA
from .testutils import BaseTestCase, parametrize_context_behavior

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

    @parametrize_context_behavior(["django", "isolated"])
    def test_single_component(self):
        component.registry.register(name="test", component=self.SimpleComponent)

        simple_tag_template: types.django_html = """
            {% load component_tags %}
            {% component name="test" variable="variable" %}{% endcomponent %}
        """

        template = Template(simple_tag_template)
        rendered = template.render(Context({}))
        self.assertHTMLEqual(rendered, "Variable: <strong>variable</strong>\n")

    @parametrize_context_behavior(["django", "isolated"])
    def test_call_with_invalid_name(self):
        # Note: No tag registered

        simple_tag_template: types.django_html = """
            {% load component_tags %}
            {% component name="test" variable="variable" %}{% endcomponent %}
        """

        template = Template(simple_tag_template)
        with self.assertRaises(django_components.component_registry.NotRegistered):
            template.render(Context({}))

    @parametrize_context_behavior(["django", "isolated"])
    def test_component_called_with_positional_name(self):
        component.registry.register(name="test", component=self.SimpleComponent)

        simple_tag_template: types.django_html = """
            {% load component_tags %}
            {% component "test" variable="variable" %}{% endcomponent %}
        """

        template = Template(simple_tag_template)
        rendered = template.render(Context({}))
        self.assertHTMLEqual(rendered, "Variable: <strong>variable</strong>\n")

    @parametrize_context_behavior(["django", "isolated"])
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

        simple_tag_template: types.django_html = """
            {% load component_tags %}
            {% component name="test" variable="variable" variable2="hej" %}{% endcomponent %}
        """

        template = Template(simple_tag_template)
        rendered = template.render(Context({}))
        expected_outcome = """Variable: <strong>variable</strong>\n""" """Variable2: <strong>hej</strong>"""
        self.assertHTMLEqual(rendered, textwrap.dedent(expected_outcome))

    @parametrize_context_behavior(["django", "isolated"])
    def test_component_called_with_singlequoted_name(self):
        component.registry.register(name="test", component=self.SimpleComponent)

        simple_tag_template: types.django_html = """
            {% load component_tags %}
            {% component 'test' variable="variable" %}{% endcomponent %}
        """

        template = Template(simple_tag_template)
        rendered = template.render(Context({}))
        self.assertHTMLEqual(rendered, "Variable: <strong>variable</strong>\n")

    @parametrize_context_behavior(["django", "isolated"])
    def test_component_called_with_variable_as_name(self):
        component.registry.register(name="test", component=self.SimpleComponent)

        simple_tag_template: types.django_html = """
            {% load component_tags %}
            {% with component_name="test" %}
                {% component component_name variable="variable" %}{% endcomponent %}
            {% endwith %}
        """

        template = Template(simple_tag_template)
        rendered = template.render(Context({}))
        self.assertHTMLEqual(rendered, "Variable: <strong>variable</strong>\n")

    @parametrize_context_behavior(["django", "isolated"])
    def test_component_called_with_invalid_variable_as_name(self):
        component.registry.register(name="test", component=self.SimpleComponent)

        simple_tag_template: types.django_html = """
            {% load component_tags %}
            {% with component_name="BLAHONGA" %}
                {% component component_name variable="variable" %}{% endcomponent %}
            {% endwith %}
        """

        template = Template(simple_tag_template)
        with self.assertRaises(django_components.component_registry.NotRegistered):
            template.render(Context({}))

    @parametrize_context_behavior(["django", "isolated"])
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

    def make_template(self, first_slot: str = "", second_slot: str = "") -> Template:
        template_str: types.django_html = f"""
            {{% load component_tags %}}
            {{% component 'first_component' %}}
                {first_slot}
            {{% endcomponent %}}
            {{% component 'second_component' variable='xyz' %}}
                {second_slot}
            {{% endcomponent %}}
        """
        return Template(template_str)

    def expected_result(self, first_slot: str = "", second_slot: str = "") -> str:
        first_slot = first_slot or "Default header"
        second_slot = second_slot or "Default header"
        return f"""
            <custom-template>
                <header>{first_slot}</header>
                <main>Default main</main>
                <footer>Default footer</footer>
            </custom-template>
            <custom-template>
                <header>{second_slot}</header>
                <main>Default main</main>
                <footer>Default footer</footer>
            </custom-template>
        """

    def wrap_with_slot_tags(self, s):
        return '{% fill "header" %}' + s + "{% endfill %}"

    @parametrize_context_behavior(["django", "isolated"])
    def test_both_components_render_correctly_with_no_slots(self):
        self.register_components()
        rendered = self.make_template().render(Context({}))
        self.assertHTMLEqual(rendered, self.expected_result())

    @parametrize_context_behavior(["django", "isolated"])
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

    @parametrize_context_behavior(["django", "isolated"])
    def test_both_components_render_correctly_when_only_first_has_slots(self):
        self.register_components()
        first_slot_content = "<p>Slot #1</p>"
        first_slot = self.wrap_with_slot_tags(first_slot_content)
        rendered = self.make_template(first_slot).render(Context({}))
        self.assertHTMLEqual(rendered, self.expected_result(first_slot_content))

    @parametrize_context_behavior(["django", "isolated"])
    def test_both_components_render_correctly_when_only_second_has_slots(self):
        self.register_components()
        second_slot_content = "<div>Slot #2</div>"
        second_slot = self.wrap_with_slot_tags(second_slot_content)
        rendered = self.make_template("", second_slot).render(Context({}))
        self.assertHTMLEqual(rendered, self.expected_result("", second_slot_content))


class ComponentIsolationTests(BaseTestCase):
    def setUp(self):
        class SlottedComponent(component.Component):
            template: types.django_html = """
                {% load component_tags %}
                <custom-template>
                    <header>{% slot "header" %}Default header{% endslot %}</header>
                    <main>{% slot "main" %}Default main{% endslot %}</main>
                    <footer>{% slot "footer" %}Default footer{% endslot %}</footer>
                </custom-template>
            """

        component.registry.register("test", SlottedComponent)

    @parametrize_context_behavior(["django", "isolated"])
    def test_instances_of_component_do_not_share_slots(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component "test" %}
                {% fill "header" %}Override header{% endfill %}
            {% endcomponent %}
            {% component "test" %}
                {% fill "main" %}Override main{% endfill %}
            {% endcomponent %}
            {% component "test" %}
                {% fill "footer" %}Override footer{% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)

        template.render(Context({}))
        rendered = template.render(Context({}))

        self.assertHTMLEqual(
            rendered,
            """
            <custom-template>
                <header>Override header</header>
                <main>Default main</main>
                <footer>Default footer</footer>
            </custom-template>
            <custom-template>
                <header>Default header</header>
                <main>Override main</main>
                <footer>Default footer</footer>
            </custom-template>
            <custom-template>
                <header>Default header</header>
                <main>Default main</main>
                <footer>Override footer</footer>
            </custom-template>
        """,
        )


class AggregateInputTests(BaseTestCase):
    @parametrize_context_behavior(["django", "isolated"])
    def test_agg_input_accessible_in_get_context_data(self):
        @component.register("test")
        class AttrsComponent(component.Component):
            template: types.django_html = """
                {% load component_tags %}
                <div>
                    attrs: {{ attrs|safe }}
                    my_dict: {{ my_dict|safe }}
                </div>
            """

            def get_context_data(self, *args, attrs, my_dict):
                return {"attrs": attrs, "my_dict": my_dict}

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "test" attrs:@click.stop="dispatch('click_event')" attrs:x-data="{hello: 'world'}" attrs:class=class_var my_dict:one=2 %}
            {% endcomponent %}
        """  # noqa: E501
        template = Template(template_str)
        rendered = template.render(Context({"class_var": "padding-top-8"}))
        self.assertHTMLEqual(
            rendered,
            """
            <div>
                attrs: {'@click.stop': "dispatch('click_event')", 'x-data': "{hello: 'world'}", 'class': 'padding-top-8'}
                my_dict: {'one': 2}
            </div>
            """,  # noqa: E501
        )


class ComponentTemplateSyntaxErrorTests(BaseTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        component.registry.register("test", SlottedComponent)

    @classmethod
    def tearDownClass(cls) -> None:
        super().tearDownClass()
        component.registry.clear()

    @parametrize_context_behavior(["django", "isolated"])
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

    @parametrize_context_behavior(["django", "isolated"])
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

    @parametrize_context_behavior(["django", "isolated"])
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

    @parametrize_context_behavior(["django", "isolated"])
    def test_unclosed_component_is_error(self):
        with self.assertRaises(TemplateSyntaxError):
            template_str: types.django_html = """
                {% load component_tags %}
                {% component "test" %}
                {% fill "header" %}{% endfill %}
            """
            Template(template_str)
