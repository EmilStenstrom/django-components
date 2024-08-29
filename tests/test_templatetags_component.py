import textwrap

from django.template import Context, Template, TemplateSyntaxError

from django_components import AlreadyRegistered, Component, NotRegistered, register, registry, types

from .django_test_setup import setup_test_config
from .testutils import BaseTestCase, parametrize_context_behavior

setup_test_config({"autodiscover": False})


class SlottedComponent(Component):
    template_name = "slotted_template.html"


class SlottedComponentWithContext(Component):
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
    class SimpleComponent(Component):
        template: types.django_html = """
            Variable: <strong>{{ variable }}</strong>
        """

        def get_context_data(self, variable, variable2="default"):
            return {
                "variable": variable,
                "variable2": variable2,
            }

        class Media:
            css = "style.css"
            js = "script.js"

    @parametrize_context_behavior(["django", "isolated"])
    def test_single_component(self):
        registry.register(name="test", component=self.SimpleComponent)

        simple_tag_template: types.django_html = """
            {% load component_tags %}
            {% component name="test" variable="variable" %}{% endcomponent %}
        """

        template = Template(simple_tag_template)
        rendered = template.render(Context({}))
        self.assertHTMLEqual(rendered, "Variable: <strong>variable</strong>\n")

    @parametrize_context_behavior(["django", "isolated"])
    def test_single_component_self_closing(self):
        registry.register(name="test", component=self.SimpleComponent)

        simple_tag_template: types.django_html = """
            {% load component_tags %}
            {% component name="test" variable="variable" /%}
        """

        template = Template(simple_tag_template)
        rendered = template.render(Context({}))
        self.assertHTMLEqual(rendered, "Variable: <strong>variable</strong>\n")

    @parametrize_context_behavior(["django", "isolated"])
    def test_call_with_invalid_name(self):
        registry.register(name="test_one", component=self.SimpleComponent)

        simple_tag_template: types.django_html = """
            {% load component_tags %}
            {% component name="test" variable="variable" %}{% endcomponent %}
        """

        template = Template(simple_tag_template)
        with self.assertRaises(NotRegistered):
            template.render(Context({}))

    @parametrize_context_behavior(["django", "isolated"])
    def test_component_called_with_positional_name(self):
        registry.register(name="test", component=self.SimpleComponent)

        simple_tag_template: types.django_html = """
            {% load component_tags %}
            {% component "test" variable="variable" %}{% endcomponent %}
        """

        template = Template(simple_tag_template)
        rendered = template.render(Context({}))
        self.assertHTMLEqual(rendered, "Variable: <strong>variable</strong>\n")

    @parametrize_context_behavior(["django", "isolated"])
    def test_call_component_with_two_variables(self):
        @register("test")
        class IffedComponent(Component):
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
        registry.register(name="test", component=self.SimpleComponent)

        simple_tag_template: types.django_html = """
            {% load component_tags %}
            {% component 'test' variable="variable" %}{% endcomponent %}
        """

        template = Template(simple_tag_template)
        rendered = template.render(Context({}))
        self.assertHTMLEqual(rendered, "Variable: <strong>variable</strong>\n")

    @parametrize_context_behavior(["django", "isolated"])
    def test_raises_on_component_called_with_variable_as_name(self):
        registry.register(name="test", component=self.SimpleComponent)

        simple_tag_template: types.django_html = """
            {% load component_tags %}
            {% with component_name="test" %}
                {% component component_name variable="variable" %}{% endcomponent %}
            {% endwith %}
        """

        with self.assertRaisesMessage(
            TemplateSyntaxError,
            "Component name must be a string 'literal', got: component_name",
        ):
            Template(simple_tag_template)

    @parametrize_context_behavior(["django", "isolated"])
    def test_component_accepts_provided_and_default_parameters(self):
        @register("test")
        class ComponentWithProvidedAndDefaultParameters(Component):
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


class DynamicComponentTemplateTagTest(BaseTestCase):
    class SimpleComponent(Component):
        template: types.django_html = """
            Variable: <strong>{{ variable }}</strong>
        """

        def get_context_data(self, variable, variable2="default"):
            return {
                "variable": variable,
                "variable2": variable2,
            }

        class Media:
            css = "style.css"
            js = "script.js"

    def setUp(self):
        super().setUp()

        # Run app installation so the `dynamic` component is defined
        from django_components.apps import ComponentsConfig

        ComponentsConfig.ready(None)  # type: ignore[arg-type]

    @parametrize_context_behavior(["django", "isolated"])
    def test_basic(self):
        registry.register(name="test", component=self.SimpleComponent)

        simple_tag_template: types.django_html = """
            {% load component_tags %}
            {% component "dynamic" is="test" variable="variable" %}{% endcomponent %}
        """

        template = Template(simple_tag_template)
        rendered = template.render(Context({}))
        self.assertHTMLEqual(rendered, "Variable: <strong>variable</strong>\n")

    @parametrize_context_behavior(["django", "isolated"])
    def test_call_with_invalid_name(self):
        registry.register(name="test", component=self.SimpleComponent)

        simple_tag_template: types.django_html = """
            {% load component_tags %}
            {% component "dynamic" is="haber_der_baber" variable="variable" %}{% endcomponent %}
        """

        template = Template(simple_tag_template)
        with self.assertRaisesMessage(NotRegistered, "The component 'haber_der_baber' was not found"):
            template.render(Context({}))

    @parametrize_context_behavior(["django", "isolated"])
    def test_component_called_with_variable_as_name(self):
        registry.register(name="test", component=self.SimpleComponent)

        simple_tag_template: types.django_html = """
            {% load component_tags %}
            {% with component_name="test" %}
                {% component "dynamic" is=component_name variable="variable" %}{% endcomponent %}
            {% endwith %}
        """

        template = Template(simple_tag_template)
        rendered = template.render(Context({}))
        self.assertHTMLEqual(rendered, "Variable: <strong>variable</strong>\n")

    @parametrize_context_behavior(["django", "isolated"])
    def test_component_called_with_variable_as_spread(self):
        registry.register(name="test", component=self.SimpleComponent)

        simple_tag_template: types.django_html = """
            {% load component_tags %}
            {% component "dynamic" ...props %}{% endcomponent %}
        """

        template = Template(simple_tag_template)
        rendered = template.render(
            Context(
                {
                    "props": {
                        "is": "test",
                        "variable": "variable",
                    },
                }
            )
        )
        self.assertHTMLEqual(rendered, "Variable: <strong>variable</strong>\n")

    @parametrize_context_behavior(["django", "isolated"])
    def test_component_as_class(self):
        registry.register(name="test", component=self.SimpleComponent)

        simple_tag_template: types.django_html = """
            {% load component_tags %}
            {% component "dynamic" is=comp_cls variable="variable" %}{% endcomponent %}
        """

        template = Template(simple_tag_template)
        rendered = template.render(
            Context(
                {
                    "comp_cls": self.SimpleComponent,
                }
            )
        )
        self.assertHTMLEqual(rendered, "Variable: <strong>variable</strong>\n")

    @parametrize_context_behavior(
        ["django", "isolated"],
        settings={
            "COMPONENTS": {
                "tag_formatter": "django_components.component_shorthand_formatter",
                "autodiscover": False,
            },
        },
    )
    def test_shorthand_formatter(self):
        from django_components.apps import ComponentsConfig

        ComponentsConfig.ready(None)  # type: ignore[arg-type]

        registry.register(name="test", component=self.SimpleComponent)

        simple_tag_template: types.django_html = """
            {% load component_tags %}
            {% dynamic is="test" variable="variable" %}{% enddynamic %}
        """

        template = Template(simple_tag_template)
        rendered = template.render(Context({}))
        self.assertHTMLEqual(rendered, "Variable: <strong>variable</strong>\n")

    @parametrize_context_behavior(
        ["django", "isolated"],
        settings={
            "COMPONENTS": {
                "dynamic_component_name": "uno_reverse",
                "tag_formatter": "django_components.component_shorthand_formatter",
                "autodiscover": False,
            },
        },
    )
    def test_component_name_is_configurable(self):
        from django_components.apps import ComponentsConfig

        ComponentsConfig.ready(None)  # type: ignore[arg-type]

        registry.register(name="test", component=self.SimpleComponent)

        simple_tag_template: types.django_html = """
            {% load component_tags %}
            {% uno_reverse is="test" variable="variable" %}{% enduno_reverse %}
        """

        template = Template(simple_tag_template)
        rendered = template.render(Context({}))
        self.assertHTMLEqual(rendered, "Variable: <strong>variable</strong>\n")

    @parametrize_context_behavior(["django", "isolated"])
    def test_raises_already_registered_on_name_conflict(self):
        with self.assertRaisesMessage(AlreadyRegistered, 'The component "dynamic" has already been registered'):
            registry.register(name="dynamic", component=self.SimpleComponent)

    @parametrize_context_behavior(["django", "isolated"])
    def test_component_called_with_default_slot(self):
        class SimpleSlottedComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                Variable: <strong>{{ variable }}</strong>
                Slot: {% slot "default" default / %}
            """

            def get_context_data(self, variable, variable2="default"):
                return {
                    "variable": variable,
                    "variable2": variable2,
                }

        registry.register(name="test", component=SimpleSlottedComponent)

        simple_tag_template: types.django_html = """
            {% load component_tags %}
            {% with component_name="test" %}
                {% component "dynamic" is=component_name variable="variable" %}
                    HELLO_FROM_SLOT
                {% endcomponent %}
            {% endwith %}
        """

        template = Template(simple_tag_template)
        rendered = template.render(Context({}))
        self.assertHTMLEqual(
            rendered,
            """
            Variable: <strong>variable</strong>
            Slot: HELLO_FROM_SLOT
            """,
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_component_called_with_named_slots(self):
        class SimpleSlottedComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                Variable: <strong>{{ variable }}</strong>
                Slot 1: {% slot "default" default / %}
                Slot 2: {% slot "two" / %}
            """

            def get_context_data(self, variable, variable2="default"):
                return {
                    "variable": variable,
                    "variable2": variable2,
                }

        registry.register(name="test", component=SimpleSlottedComponent)

        simple_tag_template: types.django_html = """
            {% load component_tags %}
            {% with component_name="test" %}
                {% component "dynamic" is=component_name variable="variable" %}
                    {% fill "default" %}
                        HELLO_FROM_SLOT_1
                    {% endfill %}
                    {% fill "two" %}
                        HELLO_FROM_SLOT_2
                    {% endfill %}
                {% endcomponent %}
            {% endwith %}
        """

        template = Template(simple_tag_template)
        rendered = template.render(Context({}))
        self.assertHTMLEqual(
            rendered,
            """
            Variable: <strong>variable</strong>
            Slot 1: HELLO_FROM_SLOT_1
            Slot 2: HELLO_FROM_SLOT_2
            """,
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_raises_on_invalid_slots(self):
        class SimpleSlottedComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                Variable: <strong>{{ variable }}</strong>
                Slot 1: {% slot "default" default / %}
                Slot 2: {% slot "two" / %}
            """

            def get_context_data(self, variable, variable2="default"):
                return {
                    "variable": variable,
                    "variable2": variable2,
                }

        registry.register(name="test", component=SimpleSlottedComponent)

        simple_tag_template: types.django_html = """
            {% load component_tags %}
            {% with component_name="test" %}
                {% component "dynamic" is=component_name variable="variable" %}
                    {% fill "default" %}
                        HELLO_FROM_SLOT_1
                    {% endfill %}
                    {% fill "three" %}
                        HELLO_FROM_SLOT_2
                    {% endfill %}
                {% endcomponent %}
            {% endwith %}
        """

        template = Template(simple_tag_template)

        with self.assertRaisesMessage(
            TemplateSyntaxError, "Component \\'dynamic\\' passed fill that refers to undefined slot: \\'three\\'"
        ):
            template.render(Context({}))

    @parametrize_context_behavior(["django", "isolated"])
    def test_raises_on_invalid_args(self):
        registry.register(name="test", component=self.SimpleComponent)

        simple_tag_template: types.django_html = """
            {% load component_tags %}
            {% with component_name="test" %}
                {% component "dynamic" is=component_name invalid_variable="variable" %}{% endcomponent %}
            {% endwith %}
        """

        template = Template(simple_tag_template)
        with self.assertRaisesMessage(TypeError, "got an unexpected keyword argument \\'invalid_variable\\'"):
            template.render(Context({}))


class MultiComponentTests(BaseTestCase):
    def register_components(self):
        registry.register("first_component", SlottedComponent)
        registry.register("second_component", SlottedComponentWithContext)

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
    class SlottedComponent(Component):
        template: types.django_html = """
            {% load component_tags %}
            <custom-template>
                <header>{% slot "header" %}Default header{% endslot %}</header>
                <main>{% slot "main" %}Default main{% endslot %}</main>
                <footer>{% slot "footer" %}Default footer{% endslot %}</footer>
            </custom-template>
        """

    def setUp(self):
        super().setUp()
        registry.register("test", self.SlottedComponent)

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
        @register("test")
        class AttrsComponent(Component):
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
    def setUp(self):
        super().setUp()
        registry.register("test", SlottedComponent)

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
