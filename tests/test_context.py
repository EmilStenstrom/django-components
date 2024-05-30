from django.template import Context, Template

from django_components import component, types

from .django_test_setup import *  # NOQA
from .testutils import BaseTestCase, parametrize_context_behavior

#########################
# COMPONENTS
#########################


class SimpleComponent(component.Component):
    template: types.django_html = """
        Variable: <strong>{{ variable }}</strong>
    """

    def get_context_data(self, variable=None):
        return {"variable": variable} if variable is not None else {}

    @staticmethod
    def expected_output(variable_value):
        return "Variable: < strong > {} < / strong >".format(variable_value)


class VariableDisplay(component.Component):
    template: types.django_html = """
        {% load component_tags %}
        <h1>Shadowing variable = {{ shadowing_variable }}</h1>
        <h1>Uniquely named variable = {{ unique_variable }}</h1>
    """

    def get_context_data(self, shadowing_variable=None, new_variable=None):
        context = {}
        if shadowing_variable is not None:
            context["shadowing_variable"] = shadowing_variable
        if new_variable is not None:
            context["unique_variable"] = new_variable
        return context


class IncrementerComponent(component.Component):
    template: types.django_html = """
        {% load component_tags %}
        <p class="incrementer">value={{ value }};calls={{ calls }}</p>
        {% slot 'content' %}{% endslot %}
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.call_count = 0

    def get_context_data(self, value=0):
        value = int(value)
        if hasattr(self, "call_count"):
            self.call_count += 1
        else:
            self.call_count = 1
        return {"value": value + 1, "calls": self.call_count}


#########################
# TESTS
#########################


class ContextTests(BaseTestCase):
    class ParentComponent(component.Component):
        template: types.django_html = """
            {% load component_tags %}
            <div>
                <h1>Parent content</h1>
                {% component name="variable_display" shadowing_variable='override' new_variable='unique_val' %}
                {% endcomponent %}
            </div>
            <div>
                {% slot 'content' %}
                    <h2>Slot content</h2>
                    {% component name="variable_display" shadowing_variable='slot_default_override' new_variable='slot_default_unique' %}
                    {% endcomponent %}
                {% endslot %}
            </div>
        """  # noqa

        def get_context_data(self):
            return {"shadowing_variable": "NOT SHADOWED"}

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        component.registry.register(name="variable_display", component=VariableDisplay)
        component.registry.register(name="parent_component", component=cls.ParentComponent)

    @parametrize_context_behavior(["django", "isolated"])
    def test_nested_component_context_shadows_parent_with_unfilled_slots_and_component_tag(
        self,
    ):
        template_str: types.django_html = """
            {% load component_tags %}{% component_dependencies %}
            {% component 'parent_component' %}{% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context())

        self.assertIn("<h1>Shadowing variable = override</h1>", rendered, rendered)
        self.assertIn(
            "<h1>Shadowing variable = slot_default_override</h1>",
            rendered,
            rendered,
        )
        self.assertNotIn("<h1>Shadowing variable = NOT SHADOWED</h1>", rendered, rendered)

    @parametrize_context_behavior(["django", "isolated"])
    def test_nested_component_instances_have_unique_context_with_unfilled_slots_and_component_tag(
        self,
    ):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component_dependencies %}
            {% component name='parent_component' %}{% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context())

        self.assertIn("<h1>Uniquely named variable = unique_val</h1>", rendered, rendered)
        self.assertIn(
            "<h1>Uniquely named variable = slot_default_unique</h1>",
            rendered,
            rendered,
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_nested_component_context_shadows_parent_with_filled_slots(self):
        template_str: types.django_html = """
            {% load component_tags %}{% component_dependencies %}
            {% component 'parent_component' %}
                {% fill 'content' %}
                    {% component name='variable_display' shadowing_variable='shadow_from_slot' new_variable='unique_from_slot' %}
                    {% endcomponent %}
                {% endfill %}
            {% endcomponent %}
        """  # NOQA
        template = Template(template_str)
        rendered = template.render(Context())

        self.assertIn("<h1>Shadowing variable = override</h1>", rendered, rendered)
        self.assertIn(
            "<h1>Shadowing variable = shadow_from_slot</h1>",
            rendered,
            rendered,
        )
        self.assertNotIn("<h1>Shadowing variable = NOT SHADOWED</h1>", rendered, rendered)

    @parametrize_context_behavior(["django", "isolated"])
    def test_nested_component_instances_have_unique_context_with_filled_slots(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component_dependencies %}
            {% component 'parent_component' %}
                {% fill 'content' %}
                    {% component name='variable_display' shadowing_variable='shadow_from_slot' new_variable='unique_from_slot' %}
                    {% endcomponent %}
                {% endfill %}
            {% endcomponent %}
        """  # NOQA
        template = Template(template_str)
        rendered = template.render(Context())

        self.assertIn("<h1>Uniquely named variable = unique_val</h1>", rendered, rendered)
        self.assertIn(
            "<h1>Uniquely named variable = unique_from_slot</h1>",
            rendered,
            rendered,
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_nested_component_context_shadows_outer_context_with_unfilled_slots_and_component_tag(
        self,
    ):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component_dependencies %}
            {% component name='parent_component' %}{% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"shadowing_variable": "NOT SHADOWED"}))

        self.assertIn("<h1>Shadowing variable = override</h1>", rendered, rendered)
        self.assertIn(
            "<h1>Shadowing variable = slot_default_override</h1>",
            rendered,
            rendered,
        )
        self.assertNotIn("<h1>Shadowing variable = NOT SHADOWED</h1>", rendered, rendered)

    @parametrize_context_behavior(["django", "isolated"])
    def test_nested_component_context_shadows_outer_context_with_filled_slots(
        self,
    ):
        template_str: types.django_html = """
            {% load component_tags %}{% component_dependencies %}
            {% component 'parent_component' %}
                {% fill 'content' %}
                    {% component name='variable_display' shadowing_variable='shadow_from_slot' new_variable='unique_from_slot' %}
                    {% endcomponent %}
                {% endfill %}
            {% endcomponent %}
        """  # NOQA
        template = Template(template_str)
        rendered = template.render(Context({"shadowing_variable": "NOT SHADOWED"}))

        self.assertIn("<h1>Shadowing variable = override</h1>", rendered, rendered)
        self.assertIn(
            "<h1>Shadowing variable = shadow_from_slot</h1>",
            rendered,
            rendered,
        )
        self.assertNotIn("<h1>Shadowing variable = NOT SHADOWED</h1>", rendered, rendered)


class ParentArgsTests(BaseTestCase):
    class ParentComponentWithArgs(component.Component):
        template: types.django_html = """
            {% load component_tags %}
            <div>
                <h1>Parent content</h1>
                {% component name="variable_display" shadowing_variable=inner_parent_value new_variable='unique_val' %}
                {% endcomponent %}
            </div>
            <div>
                {% slot 'content' %}
                    <h2>Slot content</h2>
                    {% component name="variable_display" shadowing_variable='slot_default_override' new_variable=inner_parent_value %}
                    {% endcomponent %}
                {% endslot %}
            </div>
        """  # noqa

        def get_context_data(self, parent_value):
            return {"inner_parent_value": parent_value}

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        component.registry.register(name="incrementer", component=IncrementerComponent)
        component.registry.register(name="parent_with_args", component=cls.ParentComponentWithArgs)
        component.registry.register(name="variable_display", component=VariableDisplay)

    @parametrize_context_behavior(["django", "isolated"])
    def test_parent_args_can_be_drawn_from_context(self):
        template_str: types.django_html = """
            {% load component_tags %}{% component_dependencies %}
            {% component 'parent_with_args' parent_value=parent_value %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"parent_value": "passed_in"}))

        self.assertHTMLEqual(
            rendered,
            """
            <div>
                <h1>Parent content</h1>
                <h1>Shadowing variable = passed_in</h1>
                <h1>Uniquely named variable = unique_val</h1>
            </div>
            <div>
                <h2>Slot content</h2>
                <h1>Shadowing variable = slot_default_override</h1>
                <h1>Uniquely named variable = passed_in</h1>
            </div>
            """,
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_parent_args_available_outside_slots(self):
        template_str: types.django_html = """
            {% load component_tags %}{% component_dependencies %}
            {% component 'parent_with_args' parent_value='passed_in' %}{%endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context())

        self.assertIn("<h1>Shadowing variable = passed_in</h1>", rendered, rendered)
        self.assertIn("<h1>Uniquely named variable = passed_in</h1>", rendered, rendered)
        self.assertNotIn("<h1>Shadowing variable = NOT SHADOWED</h1>", rendered, rendered)

    # NOTE: Second arg in tuple are expected values passed through components.
    @parametrize_context_behavior(
        [
            ("django", ("passed_in", "passed_in")),
            ("isolated", ("passed_in", "")),
        ]
    )
    def test_parent_args_available_in_slots(self, context_behavior_data):
        first_val, second_val = context_behavior_data

        template_str: types.django_html = """
            {% load component_tags %}{% component_dependencies %}
            {% component 'parent_with_args' parent_value='passed_in' %}
                {% fill 'content' %}
                    {% component name='variable_display' shadowing_variable='value_from_slot' new_variable=inner_parent_value %}
                    {% endcomponent %}
                {% endfill %}
            {% endcomponent %}
            """  # noqa: E501
        template = Template(template_str)
        rendered = template.render(Context())
        self.assertHTMLEqual(
            rendered,
            f"""
            <div>
                <h1>Parent content</h1>
                <h1>Shadowing variable = {first_val}</h1>
                <h1>Uniquely named variable = unique_val</h1>
            </div>
            <div>
                <h1>Shadowing variable = value_from_slot</h1>
                <h1>Uniquely named variable = {second_val}</h1>
            </div>
            """,
        )


class ContextCalledOnceTests(BaseTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        component.registry.register(name="incrementer", component=IncrementerComponent)

    @parametrize_context_behavior(["django", "isolated"])
    def test_one_context_call_with_simple_component(self):
        template_str: types.django_html = """
            {% load component_tags %}{% component_dependencies %}
            {% component name='incrementer' %}{% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context()).strip().replace("\n", "")
        self.assertHTMLEqual(
            rendered,
            '<p class="incrementer">value=1;calls=1</p>',
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_one_context_call_with_simple_component_and_arg(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component name='incrementer' value='2' %}{% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context()).strip()

        self.assertHTMLEqual(rendered, '<p class="incrementer">value=3;calls=1</p>', rendered)

    @parametrize_context_behavior(["django", "isolated"])
    def test_one_context_call_with_component(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'incrementer' %}{% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context()).strip()

        self.assertHTMLEqual(rendered, '<p class="incrementer">value=1;calls=1</p>', rendered)

    @parametrize_context_behavior(["django", "isolated"])
    def test_one_context_call_with_component_and_arg(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'incrementer' value='3' %}{% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context()).strip()

        self.assertHTMLEqual(rendered, '<p class="incrementer">value=4;calls=1</p>', rendered)

    @parametrize_context_behavior(["django", "isolated"])
    def test_one_context_call_with_slot(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'incrementer' %}
                {% fill 'content' %}
                    <p>slot</p>
                {% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context()).strip()

        self.assertHTMLEqual(
            rendered,
            '<p class="incrementer">value=1;calls=1</p>\n<p>slot</p>',
            rendered,
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_one_context_call_with_slot_and_arg(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'incrementer' value='3' %}
                {% fill 'content' %}
                    <p>slot</p>
                {% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context()).strip()

        self.assertHTMLEqual(
            rendered,
            '<p class="incrementer">value=4;calls=1</p>\n<p>slot</p>',
            rendered,
        )


class ComponentsCanAccessOuterContext(BaseTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        component.registry.register(name="simple_component", component=SimpleComponent)

    # NOTE: Second arg in tuple is expected value.
    @parametrize_context_behavior(
        [
            ("django", "outer_value"),
            ("isolated", ""),
        ]
    )
    def test_simple_component_can_use_outer_context(self, context_behavior_data):
        template_str: types.django_html = """
            {% load component_tags %}{% component_dependencies %}
            {% component 'simple_component' %}{% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"variable": "outer_value"}))
        self.assertHTMLEqual(
            rendered,
            f"""
            Variable: <strong> {context_behavior_data} </strong>
            """,
        )


class IsolatedContextTests(BaseTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        component.registry.register(name="simple_component", component=SimpleComponent)

    @parametrize_context_behavior(["django", "isolated"])
    def test_simple_component_can_pass_outer_context_in_args(self):
        template_str: types.django_html = """
            {% load component_tags %}{% component_dependencies %}
            {% component 'simple_component' variable only %}{% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"variable": "outer_value"})).strip()
        self.assertIn("outer_value", rendered, rendered)

    @parametrize_context_behavior(["django", "isolated"])
    def test_simple_component_cannot_use_outer_context(self):
        template_str: types.django_html = """
            {% load component_tags %}{% component_dependencies %}
            {% component 'simple_component' only %}{% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"variable": "outer_value"})).strip()
        self.assertNotIn("outer_value", rendered, rendered)


class IsolatedContextSettingTests(BaseTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        component.registry.register(name="simple_component", component=SimpleComponent)

    @parametrize_context_behavior(["isolated"])
    def test_component_tag_includes_variable_with_isolated_context_from_settings(
        self,
    ):
        template_str: types.django_html = """
            {% load component_tags %}{% component_dependencies %}
            {% component 'simple_component' variable %}{% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"variable": "outer_value"}))
        self.assertIn("outer_value", rendered, rendered)

    @parametrize_context_behavior(["isolated"])
    def test_component_tag_excludes_variable_with_isolated_context_from_settings(
        self,
    ):
        template_str: types.django_html = """
            {% load component_tags %}{% component_dependencies %}
            {% component 'simple_component' %}{% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"variable": "outer_value"}))
        self.assertNotIn("outer_value", rendered, rendered)

    @parametrize_context_behavior(["isolated"])
    def test_component_includes_variable_with_isolated_context_from_settings(
        self,
    ):
        template_str: types.django_html = """
            {% load component_tags %}{% component_dependencies %}
            {% component 'simple_component' variable %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"variable": "outer_value"}))
        self.assertIn("outer_value", rendered, rendered)

    @parametrize_context_behavior(["isolated"])
    def test_component_excludes_variable_with_isolated_context_from_settings(
        self,
    ):
        template_str: types.django_html = """
            {% load component_tags %}{% component_dependencies %}
            {% component 'simple_component' %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"variable": "outer_value"}))
        self.assertNotIn("outer_value", rendered, rendered)


class OuterContextPropertyTests(BaseTestCase):
    class OuterContextComponent(component.Component):
        template: types.django_html = """
            Variable: <strong>{{ variable }}</strong>
        """

        def get_context_data(self):
            return self.outer_context.flatten()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        component.registry.register(name="outer_context_component", component=cls.OuterContextComponent)

    @parametrize_context_behavior(["django", "isolated"])
    def test_outer_context_property_with_component(self):
        template_str: types.django_html = """
            {% load component_tags %}{% component_dependencies %}
            {% component 'outer_context_component' only %}{% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"variable": "outer_value"})).strip()
        self.assertIn("outer_value", rendered, rendered)


class ContextVarsIsFilledTests(BaseTestCase):
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
        component.registry.register("is_filled_vars", cls.IsFilledVarsComponent)
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

    @parametrize_context_behavior(["django", "isolated"])
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

    @parametrize_context_behavior(["django", "isolated"])
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

    @parametrize_context_behavior(["django", "isolated"])
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

    @parametrize_context_behavior(["django", "isolated"])
    def test_component_with_filled_conditional_slot(self):
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

    @parametrize_context_behavior(["django", "isolated"])
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

    @parametrize_context_behavior(["django", "isolated"])
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

    @parametrize_context_behavior(["django", "isolated"])
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
