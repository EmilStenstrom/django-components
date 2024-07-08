from typing import Any, Dict, List, Optional

from django.template import Context, Template, TemplateSyntaxError

# isort: off
from .django_test_setup import *  # NOQA
from .testutils import BaseTestCase, parametrize_context_behavior

# isort: on

from django_components import component, types


class SlottedComponent(component.Component):
    template: types.django_html = """
        {% load component_tags %}
        <custom-template>
            <header>{% slot "header" %}Default header{% endslot %}</header>
            <main>{% slot "main" %}Default main{% endslot %}</main>
            <footer>{% slot "footer" %}Default footer{% endslot %}</footer>
        </custom-template>
    """


class SlottedComponentWithContext(SlottedComponent):
    def get_context_data(self, variable):
        return {"variable": variable}


#######################
# TESTS
#######################


class ComponentSlottedTemplateTagTest(BaseTestCase):
    def setUp(self):
        # NOTE: component.registry is global, so need to clear before each test
        component.registry.clear()

    @parametrize_context_behavior(["django", "isolated"])
    def test_slotted_template_basic(self):
        component.registry.register(name="test1", component=SlottedComponent)

        @component.register("test2")
        class SimpleComponent(component.Component):
            template = """Variable: <strong>{{ variable }}</strong>"""

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

    # NOTE: Second arg is the expected output of `{{ variable }}`
    @parametrize_context_behavior([("django", "test456"), ("isolated", "")])
    def test_slotted_template_with_context_var(self, context_behavior_data):
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
            f"""
            <custom-template>
                <header>Default header</header>
                <main>test123 - {context_behavior_data} </main>
                <footer>test321</footer>
            </custom-template>
        """,
        )

    @parametrize_context_behavior(["django", "isolated"])
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

    @parametrize_context_behavior(["django", "isolated"])
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

    @parametrize_context_behavior(["django", "isolated"])
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

    @parametrize_context_behavior(["django", "isolated"])
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

    @parametrize_context_behavior(["django", "isolated"])
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

    @parametrize_context_behavior(["django", "isolated"])
    def test_default_slot_is_fillable_by_implicit_fill_content(self):
        @component.register("test_comp")
        class ComponentWithDefaultSlot(component.Component):
            template: types.django_html = """
                {% load component_tags %}
                <div>
                    <main>{% slot "main" default %}Easy to override{% endslot %}</main>
                </div>
            """

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

    @parametrize_context_behavior(["django", "isolated"])
    def test_default_slot_is_fillable_by_explicit_fill_content(self):
        @component.register("test_comp")
        class ComponentWithDefaultSlot(component.Component):
            template: types.django_html = """
                {% load component_tags %}
                <div>
                    <main>{% slot "main" default %}Easy to override{% endslot %}</main>
                </div>
            """

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

    @parametrize_context_behavior(["django", "isolated"])
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

    @parametrize_context_behavior(["django", "isolated"])
    def test_fill_tag_can_occur_within_component_nested_in_implicit_fill(self):
        component.registry.register("slotted", SlottedComponent)

        @component.register("test_comp")
        class ComponentWithDefaultSlot(component.Component):
            template: types.django_html = """
                {% load component_tags %}
                <div>
                    <main>{% slot "main" default %}Easy to override{% endslot %}</main>
                </div>
            """

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

    @parametrize_context_behavior(["django", "isolated"])
    def test_error_from_mixed_implicit_and_explicit_fill_content(self):
        @component.register("test_comp")
        class ComponentWithDefaultSlot(component.Component):
            template: types.django_html = """
                {% load component_tags %}
                <div>
                    <main>{% slot "main" default %}Easy to override{% endslot %}</main>
                </div>
            """

        with self.assertRaises(TemplateSyntaxError):
            template_str: types.django_html = """
                {% load component_tags %}
                {% component 'test_comp' %}
                  {% fill "main" %}Main content{% endfill %}
                  <p>And add this too!</p>
                {% endcomponent %}
            """
            Template(template_str)

    @parametrize_context_behavior(["django", "isolated"])
    def test_comments_permitted_inside_implicit_fill_content(self):
        @component.register("test_comp")
        class ComponentWithDefaultSlot(component.Component):
            template: types.django_html = """
                {% load component_tags %}
                <div>
                    <main>{% slot "main" default %}Easy to override{% endslot %}</main>
                </div>
            """

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

    @parametrize_context_behavior(["django", "isolated"])
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

    @parametrize_context_behavior(["django", "isolated"])
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

    @parametrize_context_behavior(["django", "isolated"])
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

        with self.assertRaisesMessage(
            TemplateSyntaxError,
            (
                "Component 'test1' passed fill that refers to undefined slot: 'haeder'.\\n"
                "Unfilled slot names are: ['footer', 'header'].\\n"
                "Did you mean 'header'?"
            ),
        ):
            template.render(Context({}))

    # NOTE: This is relevant only for the "isolated" mode
    @parametrize_context_behavior(["isolated"])
    def test_slots_of_top_level_comps_can_access_full_outer_ctx(self):
        class SlottedComponent(component.Component):
            template: types.django_html = """
                {% load component_tags %}
                <div>
                    <main>{% slot "main" default %}Easy to override{% endslot %}</main>
                </div>
            """

            def get_context_data(self, name: Optional[str] = None) -> Dict[str, Any]:
                return {
                    "name": name,
                }

        component.registry.register("test", SlottedComponent)

        template_str: types.django_html = """
            {% load component_tags %}
            <body>
                {% component "test" %}
                    ABC: {{ name }} {{ some }}
                {% endcomponent %}
            </body>
        """
        self.template = Template(template_str)

        nested_ctx = Context()
        # Check that the component can access vars across different context layers
        nested_ctx.push({"some": "var"})
        nested_ctx.push({"name": "carl"})
        rendered = self.template.render(nested_ctx)

        self.assertHTMLEqual(
            rendered,
            """
            <body>
                <div>
                    <main> ABC: carl var </main>
                </div>
            </body>
            """,
        )


class SlottedTemplateRegressionTests(BaseTestCase):
    def setUp(self):
        # NOTE: component.registry is global, so need to clear before each test
        component.registry.clear()

    @parametrize_context_behavior(["django", "isolated"])
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


class SlotDefaultTests(BaseTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        component.registry.clear()
        component.registry.register("test", SlottedComponent)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        component.registry.clear()

    @parametrize_context_behavior(["django", "isolated"])
    def test_basic(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component "test" %}
                {% fill "header" default="header" %}Before: {{ header }}{% endfill %}
                {% fill "main" default="main" %}{{ main }}{% endfill %}
                {% fill "footer" default="footer" %}{{ footer }}, after{% endfill %}
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

    @parametrize_context_behavior(["django", "isolated"])
    def test_multiple_calls(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component "test" %}
                {% fill "header" default="header" %}
                    First: {{ header }};
                    Second: {{ header }}
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

    @parametrize_context_behavior(["django", "isolated"])
    def test_under_if_and_forloop(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component "test" %}
                {% fill "header" default="header" %}
                    {% for i in range %}
                        {% if forloop.first %}
                            First {{ header }}
                        {% else %}
                            Later {{ header }}
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

    @parametrize_context_behavior(["django", "isolated"])
    def test_nested_fills(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component "test" %}
                {% fill "header" default="header1" %}
                    header1_in_header1: {{ header1 }}
                    {% component "test" %}
                        {% fill "header" default="header2" %}
                            header1_in_header2: {{ header1 }}
                            header2_in_header2: {{ header2 }}
                        {% endfill %}
                        {% fill "footer" default="footer2" %}
                            header1_in_footer2: {{ header1 }}
                            footer2_in_footer2: {{ footer2 }}
                        {% endfill %}
                    {% endcomponent %}
                {% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        self.assertHTMLEqual(
            rendered,
            """
            <custom-template>
                <header>
                    header1_in_header1: Default header
                    <custom-template>
                        <header>
                            header1_in_header2: Default header
                            header2_in_header2: Default header
                        </header>
                        <main>Default main</main>
                        <footer>
                            header1_in_footer2: Default header
                            footer2_in_footer2: Default footer
                        </footer>
                    </custom-template>
                </header>
                <main>Default main</main>
                <footer>Default footer</footer>
            </custom-template>
            """,
        )


class ScopedSlotTest(BaseTestCase):
    @parametrize_context_behavior(["django", "isolated"])
    def test_slot_data(self):
        @component.register("test")
        class TestComponent(component.Component):
            template: types.django_html = """
                {% load component_tags %}
                <div>
                    {% slot "my_slot" abc=abc var123=var123 %}Default text{% endslot %}
                </div>
            """

            def get_context_data(self):
                return {
                    "abc": "def",
                    "var123": 456,
                }

        template: types.django_html = """
            {% load component_tags %}
            {% component "test" %}
                {% fill "my_slot" data="slot_data_in_fill" %}
                    {{ slot_data_in_fill.abc }}
                    {{ slot_data_in_fill.var123 }}
                {% endfill %}
            {% endcomponent %}
        """
        rendered = Template(template).render(Context())
        expected = """
            <div>
                def
                456
            </div>
        """
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["django", "isolated"])
    def test_slot_data_with_flags(self):
        @component.register("test")
        class TestComponent(component.Component):
            template: types.django_html = """
                {% load component_tags %}
                <div>
                    {% slot "my_slot" default abc=abc var123=var123 required %}Default text{% endslot %}
                </div>
            """

            def get_context_data(self):
                return {
                    "abc": "def",
                    "var123": 456,
                }

        template: types.django_html = """
            {% load component_tags %}
            {% component "test" %}
                {% fill "my_slot" data="slot_data_in_fill" %}
                    {{ slot_data_in_fill.abc }}
                    {{ slot_data_in_fill.var123 }}
                {% endfill %}
            {% endcomponent %}
        """
        rendered = Template(template).render(Context())
        expected = """
            <div>
                def
                456
            </div>
        """
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["django", "isolated"])
    def test_slot_data_with_slot_default(self):
        @component.register("test")
        class TestComponent(component.Component):
            template: types.django_html = """
                {% load component_tags %}
                <div>
                    {% slot "my_slot" abc=abc var123=var123 %}Default text{% endslot %}
                </div>
            """

            def get_context_data(self):
                return {
                    "abc": "def",
                    "var123": 456,
                }

        template: types.django_html = """
            {% load component_tags %}
            {% component "test" %}
                {% fill "my_slot" data="slot_data_in_fill" default="slot_var" %}
                    {{ slot_var }}
                    {{ slot_data_in_fill.abc }}
                    {{ slot_data_in_fill.var123 }}
                {% endfill %}
            {% endcomponent %}
        """
        rendered = Template(template).render(Context())
        expected = """
            <div>
                Default text
                def
                456
            </div>
        """
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["django", "isolated"])
    def test_slot_data_raises_on_slot_data_and_slot_default_same_var(self):
        @component.register("test")
        class TestComponent(component.Component):
            template: types.django_html = """
                {% load component_tags %}
                <div>
                    {% slot "my_slot" abc=abc var123=var123 %}Default text{% endslot %}
                </div>
            """

            def get_context_data(self):
                return {
                    "abc": "def",
                    "var123": 456,
                }

        template: types.django_html = """
            {% load component_tags %}
            {% component "test" %}
                {% fill "my_slot" data="slot_var" default="slot_var" %}
                    {{ slot_var }}
                {% endfill %}
            {% endcomponent %}
        """
        with self.assertRaisesMessage(
            TemplateSyntaxError,
            "'fill' received the same string for slot default (default=...) and slot data (data=...)",
        ):
            Template(template).render(Context())

    @parametrize_context_behavior(["django", "isolated"])
    def test_slot_data_fill_without_data(self):
        @component.register("test")
        class TestComponent(component.Component):
            template: types.django_html = """
                {% load component_tags %}
                <div>
                    {% slot "my_slot" abc=abc var123=var123 %}Default text{% endslot %}
                </div>
            """

            def get_context_data(self):
                return {
                    "abc": "def",
                    "var123": 456,
                }

        template: types.django_html = """
            {% load component_tags %}
            {% component "test" %}
                {% fill "my_slot" %}
                    overriden
                {% endfill %}
            {% endcomponent %}
        """
        rendered = Template(template).render(Context())
        expected = "<div> overriden </div>"
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["django", "isolated"])
    def test_slot_data_fill_without_slot_data(self):
        @component.register("test")
        class TestComponent(component.Component):
            template: types.django_html = """
                {% load component_tags %}
                <div>
                    {% slot "my_slot" %}Default text{% endslot %}
                </div>
            """

        template: types.django_html = """
            {% load component_tags %}
            {% component "test" %}
                {% fill "my_slot" data="data" %}
                    {{ data|safe }}
                {% endfill %}
            {% endcomponent %}
        """
        rendered = Template(template).render(Context())
        expected = "<div> {} </div>"
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["django", "isolated"])
    def test_slot_data_no_fill(self):
        @component.register("test")
        class TestComponent(component.Component):
            template: types.django_html = """
                {% load component_tags %}
                <div>
                    {% slot "my_slot" abc=abc var123=var123 %}Default text{% endslot %}
                </div>
            """

            def get_context_data(self):
                return {
                    "abc": "def",
                    "var123": 456,
                }

        template: types.django_html = """
            {% load component_tags %}
            {% component "test" %}
            {% endcomponent %}
        """
        rendered = Template(template).render(Context())
        expected = "<div> Default text </div>"
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["django", "isolated"])
    def test_nested_fills(self):
        @component.register("test")
        class TestComponent(component.Component):
            template: types.django_html = """
                {% load component_tags %}
                <div>
                    {% slot "my_slot" abc=abc input=input %}Default text{% endslot %}
                </div>
            """

            def get_context_data(self, input):
                return {
                    "abc": "def",
                    "input": input,
                }

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "test" input=1 %}
                {% fill "my_slot" data="data1" %}
                    data1_in_slot1: {{ data1|safe }}
                    {% component "test" input=2 %}
                        {% fill "my_slot" data="data2" %}
                            data1_in_slot2: {{ data1|safe }}
                            data2_in_slot2: {{ data2|safe }}
                        {% endfill %}
                    {% endcomponent %}
                {% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        self.assertHTMLEqual(
            rendered,
            """
            <div>
                data1_in_slot1: {'abc': 'def', 'input': 1}
                <div>
                    data1_in_slot2: {'abc': 'def', 'input': 1}
                    data2_in_slot2: {'abc': 'def', 'input': 2}
                </div>
            </div>
            """,
        )


class DuplicateSlotTest(BaseTestCase):
    class DuplicateSlotComponent(component.Component):
        template: types.django_html = """
            {% load component_tags %}
            <header>{% slot "header" %}Default header{% endslot %}</header>
             {# Slot name 'header' used twice. #}
            <main>{% slot "header" %}Default main header{% endslot %}</main>
            <footer>{% slot "footer" %}Default footer{% endslot %}</footer>
        """

        def get_context_data(self, name: Optional[str] = None) -> Dict[str, Any]:
            return {
                "name": name,
            }

    class DuplicateSlotNestedComponent(component.Component):
        template: types.django_html = """
            {% load component_tags %}
            {% slot "header" %}START{% endslot %}
            <div class="dashboard-component">
            {% component "calendar" date="2020-06-06" %}
                {% fill "header" %}  {# fills and slots with same name relate to diff. things. #}
                    {% slot "header" %}NESTED{% endslot %}
                {% endfill %}
                {% fill "body" %}Here are your to-do items for today:{% endfill %}
            {% endcomponent %}
            <ol>
                {% for item in items %}
                    <li>{{ item }}</li>
                    {% slot "header" %}LOOP {{ item }} {% endslot %}
                {% endfor %}
            </ol>
            </div>
        """

        def get_context_data(self, items: List) -> Dict[str, Any]:
            return {
                "items": items,
            }

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

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        component.registry.register(name="duplicate_slot", component=cls.DuplicateSlotComponent)
        component.registry.register(name="duplicate_slot_nested", component=cls.DuplicateSlotNestedComponent)
        component.registry.register(name="calendar", component=cls.CalendarComponent)

    # NOTE: Second arg is the input for the "name" component kwarg
    @parametrize_context_behavior(
        [
            # In "django" mode, we MUST pass name as arg through the component
            ("django", "Jannete"),
            # In "isolated" mode, the fill is already using top-level's context, so we pass nothing
            ("isolated", None),
        ]
    )
    def test_duplicate_slots(self, context_behavior_data):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component "duplicate_slot" name=comp_input %}
                {% fill "header" %}
                    Name: {{ name }}
                {% endfill %}
                {% fill "footer" %}
                    Hello
                {% endfill %}
            {% endcomponent %}
        """
        self.template = Template(template_str)

        rendered = self.template.render(Context({"name": "Jannete", "comp_input": context_behavior_data}))
        self.assertHTMLEqual(
            rendered,
            """
            <header>Name: Jannete</header>
            <main>Name: Jannete</main>
            <footer>Hello</footer>
            """,
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_duplicate_slots_fallback(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component "duplicate_slot" %}
            {% endcomponent %}
        """
        self.template = Template(template_str)
        rendered = self.template.render(Context({}))

        # NOTE: Slots should have different fallbacks even though they use the same name
        self.assertHTMLEqual(
            rendered,
            """
            <header>Default header</header>
            <main>Default main header</main>
            <footer>Default footer</footer>
            """,
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_duplicate_slots_nested(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component "duplicate_slot_nested" items=items %}
                {% fill "header" %}
                    OVERRIDDEN!
                {% endfill %}
            {% endcomponent %}
        """
        self.template = Template(template_str)
        rendered = self.template.render(Context({"items": [1, 2, 3]}))

        # NOTE: Slots should have different fallbacks even though they use the same name
        self.assertHTMLEqual(
            rendered,
            """
            OVERRIDDEN!
            <div class="dashboard-component">
                <div class="calendar-component">
                    <h1>
                        OVERRIDDEN!
                    </h1>
                    <main>
                        Here are your to-do items for today:
                    </main>
                </div>

                <ol>
                    <li>1</li>
                    OVERRIDDEN!
                    <li>2</li>
                    OVERRIDDEN!
                    <li>3</li>
                    OVERRIDDEN!
                </ol>
            </div>
            """,
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_duplicate_slots_nested_fallback(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component "duplicate_slot_nested" items=items %}
            {% endcomponent %}
        """
        self.template = Template(template_str)
        rendered = self.template.render(Context({"items": [1, 2, 3]}))

        # NOTE: Slots should have different fallbacks even though they use the same name
        self.assertHTMLEqual(
            rendered,
            """
            START
            <div class="dashboard-component">
                <div class="calendar-component">
                    <h1>
                        NESTED
                    </h1>
                    <main>
                        Here are your to-do items for today:
                    </main>
                </div>

                <ol>
                    <li>1</li>
                    LOOP 1
                    <li>2</li>
                    LOOP 2
                    <li>3</li>
                    LOOP 3
                </ol>
            </div>
            """,
        )


class SlotFillTemplateSyntaxErrorTests(BaseTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        component.registry.register("test", SlottedComponent)

    @classmethod
    def tearDownClass(cls) -> None:
        super().tearDownClass()
        component.registry.clear()

    @parametrize_context_behavior(["django", "isolated"])
    def test_fill_with_no_parent_is_error(self):
        with self.assertRaises(TemplateSyntaxError):
            template_str: types.django_html = """
                {% load component_tags %}
                {% fill "header" %}contents{% endfill %}
            """
            Template(template_str).render(Context({}))

    @parametrize_context_behavior(["django", "isolated"])
    def test_isolated_slot_is_error(self):
        @component.register("broken_component")
        class BrokenComponent(component.Component):
            template: types.django_html = """
                {% load component_tags %}
                {% include 'slotted_template.html' with context=None only %}
            """

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "broken_component" %}
                {% fill "header" %}Custom header {% endfill %}
                {% fill "main" %}Custom main{% endfill %}
                {% fill "footer" %}Custom footer{% endfill %}
            {% endcomponent %}
        """

        with self.assertRaises(KeyError):
            Template(template_str).render(Context({}))

    @parametrize_context_behavior(["django", "isolated"])
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

    @parametrize_context_behavior(["django", "isolated"])
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


class SlotBehaviorTests(BaseTestCase):
    # NOTE: This is standalone function instead of setUp, so we can configure
    # Django settings per test with `@override_settings`
    def make_template(self) -> Template:
        class SlottedComponent(component.Component):
            template: types.django_html = """
                {% load component_tags %}
                <custom-template>
                    <header>{% slot "header" %}Default header{% endslot %}</header>
                    <main>{% slot "main" %}Default main{% endslot %}</main>
                    <footer>{% slot "footer" %}Default footer{% endslot %}</footer>
                </custom-template>
            """

            def get_context_data(self, name: Optional[str] = None) -> Dict[str, Any]:
                return {
                    "name": name,
                }

        component.registry.register("test", SlottedComponent)

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "test" name='Igor' %}
                {% fill "header" %}
                    Name: {{ name }}
                {% endfill %}
                {% fill "main" %}
                    Day: {{ day }}
                {% endfill %}
                {% fill "footer" %}
                    {% component "test" name='Joe2' %}
                        {% fill "header" %}
                            Name2: {{ name }}
                        {% endfill %}
                        {% fill "main" %}
                            Day2: {{ day }}
                        {% endfill %}
                    {% endcomponent %}
                {% endfill %}
            {% endcomponent %}
        """
        return Template(template_str)

    @parametrize_context_behavior(["django"])
    def test_slot_context__django(self):
        template = self.make_template()
        # {{ name }} should be neither Jannete not empty, because overriden everywhere
        rendered = template.render(Context({"day": "Monday", "name": "Jannete"}))
        self.assertHTMLEqual(
            rendered,
            """
            <custom-template>
                <header>Name: Igor</header>
                <main>Day: Monday</main>
                <footer>
                    <custom-template>
                        <header>Name2: Joe2</header>
                        <main>Day2: Monday</main>
                        <footer>Default footer</footer>
                    </custom-template>
                </footer>
            </custom-template>
            """,
        )

        # {{ name }} should be effectively the same as before, because overriden everywhere
        rendered2 = template.render(Context({"day": "Monday"}))
        self.assertHTMLEqual(rendered2, rendered)

    @parametrize_context_behavior(["isolated"])
    def test_slot_context__isolated(self):
        template = self.make_template()
        # {{ name }} should be "Jannete" everywhere
        rendered = template.render(Context({"day": "Monday", "name": "Jannete"}))
        self.assertHTMLEqual(
            rendered,
            """
            <custom-template>
                <header>Name: Jannete</header>
                <main>Day: Monday</main>
                <footer>
                    <custom-template>
                        <header>Name2: Jannete</header>
                        <main>Day2: Monday</main>
                        <footer>Default footer</footer>
                    </custom-template>
                </footer>
            </custom-template>
            """,
        )

        # {{ name }} should be empty everywhere
        rendered2 = template.render(Context({"day": "Monday"}))
        self.assertHTMLEqual(
            rendered2,
            """
            <custom-template>
                <header>Name: </header>
                <main>Day: Monday</main>
                <footer>
                    <custom-template>
                        <header>Name2: </header>
                        <main>Day2: Monday</main>
                        <footer>Default footer</footer>
                    </custom-template>
                </footer>
            </custom-template>
            """,
        )
