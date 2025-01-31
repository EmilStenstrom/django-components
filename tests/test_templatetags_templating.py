"""This file tests various ways how the individual tags can be combined inside the templates"""

from typing import Any, Dict, Optional

from django.template import Context, Template

from django_components import Component, register, registry, types

from .django_test_setup import setup_test_config
from .testutils import BaseTestCase, parametrize_context_behavior

setup_test_config({"autodiscover": False})


class SlottedComponent(Component):
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


class NestedSlotTests(BaseTestCase):
    class NestedComponent(Component):
        template: types.django_html = """
            {% load component_tags %}
            {% slot 'outer' %}
                <div id="outer">{% slot 'inner' %}Default{% endslot %}</div>
            {% endslot %}
        """

    @parametrize_context_behavior(["django", "isolated"])
    def test_default_slot_contents_render_correctly(self):
        registry.clear()
        registry.register("test", self.NestedComponent)
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test' %}{% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))
        self.assertHTMLEqual(rendered, '<div id="outer" data-djc-id-a1bc3f>Default</div>')

    @parametrize_context_behavior(["django", "isolated"])
    def test_inner_slot_overriden(self):
        registry.clear()
        registry.register("test", self.NestedComponent)
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test' %}
                {% fill 'inner' %}Override{% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))
        self.assertHTMLEqual(rendered, '<div id="outer" data-djc-id-a1bc40>Override</div>')

    @parametrize_context_behavior(["django", "isolated"])
    def test_outer_slot_overriden(self):
        registry.clear()
        registry.register("test", self.NestedComponent)
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test' %}{% fill 'outer' %}<p>Override</p>{% endfill %}{% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))
        self.assertHTMLEqual(rendered, "<p data-djc-id-a1bc40>Override</p>")

    @parametrize_context_behavior(["django", "isolated"])
    def test_both_overriden_and_inner_removed(self):
        registry.clear()
        registry.register("test", self.NestedComponent)
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test' %}
                {% fill 'outer' %}<p>Override</p>{% endfill %}
                {% fill 'inner' %}<p>Will not appear</p>{% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))
        self.assertHTMLEqual(rendered, "<p data-djc-id-a1bc41>Override</p>")

    # NOTE: Second arg in tuple is expected name in nested fill. In "django" mode,
    # the value should be overridden by the component, while in "isolated" it should
    # remain top-level context.
    @parametrize_context_behavior([("django", "Joe2"), ("isolated", "Jannete")])
    def test_fill_inside_fill_with_same_name(self, context_behavior_data):
        class SlottedComponent(Component):
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

        registry.clear()
        registry.register("test", SlottedComponent)

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "test" name='Igor' %}
                {% fill "header" %}
                    {% component "test" name='Joe2' %}
                        {% fill "header" %}
                            Name2: {{ name }}
                        {% endfill %}
                        {% fill "main" %}
                            Day2: {{ day }}
                        {% endfill %}
                        {% fill "footer" %}
                            XYZ
                        {% endfill %}
                    {% endcomponent %}
                {% endfill %}
                {% fill "footer" %}
                    WWW
                {% endfill %}
            {% endcomponent %}
        """
        self.template = Template(template_str)

        rendered = self.template.render(Context({"day": "Monday", "name": "Jannete"}))
        self.assertHTMLEqual(
            rendered,
            f"""
            <custom-template data-djc-id-a1bc45>
                <header>
                    <custom-template data-djc-id-a1bc49>
                        <header>Name2: {context_behavior_data}</header>
                        <main>Day2: Monday</main>
                        <footer>XYZ</footer>
                    </custom-template>
                </header>
                <main>Default main</main>
                <footer>WWW</footer>
            </custom-template>
            """,
        )


# NOTE: This test group are kept for backward compatibility, as the same logic
# as provided by {% if %} tags was previously provided by this library.
class ConditionalSlotTests(BaseTestCase):
    class ConditionalComponent(Component):
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

    def setUp(self):
        super().setUp()
        registry.register("test", self.ConditionalComponent)

    @parametrize_context_behavior(["django", "isolated"])
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

    @parametrize_context_behavior(["django", "isolated"])
    def test_default_content_if_no_slots(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test' branch='a' %}{% endcomponent %}
            {% component 'test' branch='b' %}{% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))
        self.assertHTMLEqual(
            rendered,
            """
            <p id="a" data-djc-id-a1bc40>Default A</p>
            <p id="b" data-djc-id-a1bc43>Default B</p>
            """,
        )

    @parametrize_context_behavior(["django", "isolated"])
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
        self.assertHTMLEqual(
            rendered,
            """
            <p id="a" data-djc-id-a1bc42>Default A</p>
            <p id="b" data-djc-id-a1bc45>Override B</p>
            """,
        )

    @parametrize_context_behavior(["django", "isolated"])
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
        self.assertHTMLEqual(
            rendered,
            """
            <p id="a" data-djc-id-a1bc44>Override A</p>
            <p id="b" data-djc-id-a1bc47>Override B</p>
            """,
        )


class SlotIterationTest(BaseTestCase):
    """Tests a behaviour of {% fill .. %} tag which is inside a template {% for .. %} loop."""

    class ComponentSimpleSlotInALoop(Component):
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

    # NOTE: Second arg in tuple is expected result. In isolated mode, loops should NOT leak.
    @parametrize_context_behavior(
        [
            ("django", "OBJECT1 OBJECT2"),
            ("isolated", ""),
        ]
    )
    def test_inner_slot_iteration_basic(self, context_behavior_data):
        registry.register("slot_in_a_loop", self.ComponentSimpleSlotInALoop)

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

        self.assertHTMLEqual(rendered, context_behavior_data)

    # NOTE: Second arg in tuple is expected result. In isolated mode, while loops should NOT leak,
    # we should still have access to root context (returned from get_context_data)
    @parametrize_context_behavior(
        [
            ("django", "OUTER_SCOPE_VARIABLE OBJECT1 OUTER_SCOPE_VARIABLE OBJECT2"),
            ("isolated", "OUTER_SCOPE_VARIABLE OUTER_SCOPE_VARIABLE"),
        ]
    )
    def test_inner_slot_iteration_with_variable_from_outer_scope(self, context_behavior_data):
        registry.register("slot_in_a_loop", self.ComponentSimpleSlotInALoop)

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

        self.assertHTMLEqual(rendered, context_behavior_data)

    # NOTE: Second arg in tuple is expected result. In isolated mode, loops should NOT leak.
    @parametrize_context_behavior(
        [
            ("django", "ITER1_OBJ1 ITER1_OBJ2 ITER2_OBJ1 ITER2_OBJ2"),
            ("isolated", ""),
        ]
    )
    def test_inner_slot_iteration_nested(self, context_behavior_data):
        registry.register("slot_in_a_loop", self.ComponentSimpleSlotInALoop)

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

        self.assertHTMLEqual(rendered, context_behavior_data)

    # NOTE: Second arg in tuple is expected result. In isolated mode, while loops should NOT leak,
    # we should still have access to root context (returned from get_context_data)
    @parametrize_context_behavior(
        [
            (
                "django",
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
            ),
            ("isolated", "OUTER_SCOPE_VARIABLE1 OUTER_SCOPE_VARIABLE1"),
        ]
    )
    def test_inner_slot_iteration_nested_with_outer_scope_variable(self, context_behavior_data):
        registry.register("slot_in_a_loop", self.ComponentSimpleSlotInALoop)

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

        self.assertHTMLEqual(rendered, context_behavior_data)

    # NOTE: Second arg in tuple is expected result. In isolated mode, loops should NOT leak.
    @parametrize_context_behavior(
        [
            ("django", "ITER1_OBJ1 default ITER1_OBJ2 default ITER2_OBJ1 default ITER2_OBJ2 default"),
            ("isolated", ""),
        ]
    )
    def test_inner_slot_iteration_nested_with_slot_default(self, context_behavior_data):
        registry.register("slot_in_a_loop", self.ComponentSimpleSlotInALoop)

        objects = [
            {"inner": ["ITER1_OBJ1", "ITER1_OBJ2"]},
            {"inner": ["ITER2_OBJ1", "ITER2_OBJ2"]},
        ]

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "slot_in_a_loop" objects=objects %}
                {% fill "slot_inner" %}
                    {% component "slot_in_a_loop" objects=object.inner %}
                        {% fill "slot_inner" default="super_slot_inner" %}
                            {{ super_slot_inner }}
                        {% endfill %}
                    {% endcomponent %}
                {% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"objects": objects}))

        self.assertHTMLEqual(rendered, context_behavior_data)

    # NOTE: Second arg in tuple is expected result. In isolated mode, loops should NOT leak.
    @parametrize_context_behavior(
        [
            (
                "django",
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
            ),
            # NOTE: In this case the `object.inner` in the inner "slot_in_a_loop"
            # should be undefined, so the loop inside the inner `slot_in_a_loop`
            # shouldn't run. Hence even the inner `slot_inner` fill should NOT run.
            ("isolated", "OUTER_SCOPE_VARIABLE1 OUTER_SCOPE_VARIABLE1"),
        ]
    )
    def test_inner_slot_iteration_nested_with_slot_default_and_outer_scope_variable(
        self,
        context_behavior_data,
    ):
        registry.register("slot_in_a_loop", self.ComponentSimpleSlotInALoop)

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
                        {% fill "slot_inner" default="super_slot_inner" %}
                            {{ outer_scope_variable_2 }}
                            {{ super_slot_inner }}
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
        self.assertHTMLEqual(rendered, context_behavior_data)

    @parametrize_context_behavior(["isolated"])
    def test_inner_slot_iteration_nested_with_slot_default_and_outer_scope_variable__isolated_2(
        self,
    ):
        registry.register("slot_in_a_loop", self.ComponentSimpleSlotInALoop)

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
                        {% fill "slot_inner" default="super_slot_inner" %}
                            {{ outer_scope_variable_2|safe }}
                            {{ super_slot_inner }}
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


class ComponentNestingTests(BaseTestCase):
    class CalendarComponent(Component):
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

    class DashboardComponent(Component):
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

    def setUp(self) -> None:
        super().setUp()
        registry.register("dashboard", self.DashboardComponent)
        registry.register("calendar", self.CalendarComponent)

    # NOTE: Second arg in tuple are expected names in nested fills. In "django" mode,
    # the value should be overridden by the component, while in "isolated" it should
    # remain top-level context.
    @parametrize_context_behavior([("django", ("Igor", "Joe2")), ("isolated", ("Jannete", "Jannete"))])
    def test_component_inside_slot(self, context_behavior_data):
        first_name, second_name = context_behavior_data

        class SlottedComponent(Component):
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

        registry.register("test", SlottedComponent)

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
        self.template = Template(template_str)

        rendered = self.template.render(Context({"day": "Monday", "name": "Jannete"}))
        self.assertHTMLEqual(
            rendered,
            f"""
            <custom-template data-djc-id-a1bc45>
                <header>Name: {first_name}</header>
                <main>Day: Monday</main>
                <footer>
                    <custom-template data-djc-id-a1bc49>
                        <header>Name2: {second_name}</header>
                        <main>Day2: Monday</main>
                        <footer>Default footer</footer>
                    </custom-template>
                </footer>
            </custom-template>
            """,
        )

    # NOTE: Second arg in tuple is expected list content. In isolated mode, loops should NOT leak.
    @parametrize_context_behavior(
        [
            ("django", "<li>1</li> <li>2</li> <li>3</li>"),
            ("isolated", ""),
        ]
    )
    def test_component_nesting_component_without_fill(self, context_behavior_data):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component "dashboard" %}{% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"items": [1, 2, 3]}))
        expected = f"""
            <div class="dashboard-component" data-djc-id-a1bc3f>
            <div class="calendar-component" data-djc-id-a1bc44>
                <h1>
                Welcome to your dashboard!
                </h1>
                <main>
                Here are your to-do items for today:
                </main>
            </div>
            <ol>
                {context_behavior_data}
            </ol>
            </div>
        """
        self.assertHTMLEqual(rendered, expected)

    # NOTE: Second arg in tuple is expected list content. In isolated mode, loops should NOT leak.
    @parametrize_context_behavior(
        [
            ("django", "<li>1</li> <li>2</li> <li>3</li>"),
            ("isolated", ""),
        ]
    )
    def test_component_nesting_slot_inside_component_fill(self, context_behavior_data):
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
        expected = f"""
            <div class="dashboard-component" data-djc-id-a1bc40>
            <div class="calendar-component" data-djc-id-a1bc45>
                <h1>
                Whoa!
                </h1>
                <main>
                Here are your to-do items for today:
                </main>
            </div>
            <ol>
                {context_behavior_data}
            </ol>
            </div>
        """
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["django", "isolated"])
    def test_component_nesting_deep_slot_inside_component_fill(self):
        @register("complex_child")
        class ComplexChildComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div>
                {% slot "content" default %}
                    No slot!
                {% endslot %}
                </div>
            """

        @register("complex_parent")
        class ComplexParentComponent(Component):
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

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "complex_parent" items=items %}{% endcomponent %}
        """
        template = Template(template_str)
        items = [{"value": 1}, {"value": 2}, {"value": 3}]
        rendered = template.render(Context({"items": items}))

        expected = """
            ITEMS: [{'value': 1}, {'value': 2}, {'value': 3}]
            <li data-djc-id-a1bc3f>
                <div data-djc-id-a1bc41> 1 </div>
            </li>
            <li data-djc-id-a1bc3f>
                <div data-djc-id-a1bc43> 2 </div>
            </li>
            <li data-djc-id-a1bc3f>
                <div data-djc-id-a1bc44> 3 </div>
            </li>
        """
        self.assertHTMLEqual(rendered, expected)

    # This test is based on real-life example.
    # It ensures that deeply nested slots in fills with same names are resolved correctly.
    # It also ensures that the component_vars.is_filled context is correctly populated.
    @parametrize_context_behavior(["django", "isolated"])
    def test_component_nesting_deep_slot_inside_component_fill_2(self):
        @register("TestPage")
        class TestPage(Component):
            template: types.django_html = """
                {% component "TestLayout" %}
                    {% fill "content" %}
                        <div class="test-page">
                            ------PROJ_LAYOUT_TABBED META ------<br/>
                            component_vars.is_filled: {{ component_vars.is_filled|safe }}<br/>
                            ------------------------<br/>

                            {% if component_vars.is_filled.left_panel %}
                                <div style="background-color: red;">
                                    {% slot "left_panel" / %}
                                </div>
                            {% endif %}

                            {% slot "content" default %}
                                DEFAULT LAYOUT TABBED CONTENT
                            {% endslot %}
                        </div>
                    {% endfill %}
                {% endcomponent %}
            """

        @register("TestLayout")
        class TestLayout(Component):
            template: types.django_html = """
            {% component "TestBase" %}
                {% fill "content" %}
                    ------LAYOUT META ------<br/>
                    component_vars.is_filled: {{ component_vars.is_filled|safe }}<br/>
                    ------------------------<br/>

                    <div class="test-layout">
                        {% slot "content" default / %}
                    </div>
                {% endfill %}
            {% endcomponent %}
            """

        @register("TestBase")
        class TestBase(Component):
            template: types.django_html = """
                <!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <meta http-equiv="X-UA-Compatible" content="IE=edge">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>Test app</title>
                </head>
                <body class="test-base">
                    ------BASE META ------<br/>
                    component_vars.is_filled: {{ component_vars.is_filled|safe }}<br/>
                    ------------------------<br/>

                    {% slot "content" default / %}
                </body>
                </html>
            """

        rendered = TestPage.render(
            slots={
                "left_panel": "LEFT PANEL SLOT FROM FILL",
                "content": "CONTENT SLOT FROM FILL",
            }
        )

        expected = """
            <!DOCTYPE html>
            <html lang="en" data-djc-id-a1bc3e data-djc-id-a1bc43 data-djc-id-a1bc47><head>
                <meta charset="UTF-8">
                <meta http-equiv="X-UA-Compatible" content="IE=edge">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Test app</title>
            </head>
            <body class="test-base">
                ------BASE META ------ <br>
                component_vars.is_filled: {'content': True}<br>
                ------------------------ <br>

                ------LAYOUT META ------<br>
                component_vars.is_filled: {'content': True}<br>
                ------------------------<br>

                <div class="test-layout">
                    <div class="test-page">
                        ------PROJ_LAYOUT_TABBED META ------<br>
                        component_vars.is_filled: {'left_panel': True, 'content': True}<br>
                        ------------------------<br>

                        <div style="background-color: red;">
                            LEFT PANEL SLOT FROM FILL
                        </div>
                        CONTENT SLOT FROM FILL
                    </div>
                </div>
                <script src="django_components/django_components.min.js"></script>
            </body>
            </html>
        """
        self.assertHTMLEqual(rendered, expected)

    # NOTE: Second arg in tuple is expected list content. In isolated mode, loops should NOT leak.
    @parametrize_context_behavior(
        [
            ("django", "<li>1</li> <li>2</li>"),
            ("isolated", ""),
        ]
    )
    def test_component_nesting_component_with_slot_default(self, context_behavior_data):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component "dashboard" %}
              {% fill "header" default="h" %} Hello! {{ h }} {% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"items": [1, 2]}))
        expected = f"""
            <div class="dashboard-component" data-djc-id-a1bc40>
            <div class="calendar-component" data-djc-id-a1bc45>
                <h1>
                Hello! Welcome to your dashboard!
                </h1>
                <main>
                Here are your to-do items for today:
                </main>
            </div>
            <ol>
                {context_behavior_data}
            </ol>
            </div>
        """
        self.assertHTMLEqual(rendered, expected)
