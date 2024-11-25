from typing import Any, Dict, List, Optional

from django.template import Context, Template, TemplateSyntaxError

from django_components import Component, Slot, register, registry, types

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


class ComponentSlotTests(BaseTestCase):
    @parametrize_context_behavior(["django", "isolated"])
    def test_slotted_template_basic(self):
        registry.register(name="test1", component=SlottedComponent)

        @register("test2")
        class SimpleComponent(Component):
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

    @parametrize_context_behavior(["django", "isolated"])
    def test_slotted_template_basic_self_closing(self):
        @register("test1")
        class SlottedComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                <custom-template>
                    <header>{% slot "header" / %}</header>
                    <main>{% slot "main" %}Default main{% endslot %}</main>
                    <footer>{% slot "footer" / %}</footer>
                </custom-template>
            """

        registry.register(name="test1", component=SlottedComponent)

        @register("test2")
        class SimpleComponent(Component):
            template = """Variable: <strong>{{ variable }}</strong>"""

            def get_context_data(self, variable, variable2="default"):
                return {
                    "variable": variable,
                    "variable2": variable2,
                }

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "test1" %}
                {% fill "header" %}
                    {% component "test2" variable="variable" / %}
                {% endfill %}
                {% fill "main" / %}
                {% fill "footer" / %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        # NOTE: <main> is empty, because the fill is provided, even if empty
        self.assertHTMLEqual(
            rendered,
            """
            <custom-template>
                <header> Variable: <strong>variable</strong> </header>
                <main></main>
                <footer></footer>
            </custom-template>
        """,
        )

    # NOTE: Second arg is the expected output of `{{ variable }}`
    @parametrize_context_behavior([("django", "test456"), ("isolated", "")])
    def test_slotted_template_with_context_var(self, context_behavior_data):
        registry.register(name="test1", component=SlottedComponentWithContext)

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
        registry.register(name="test", component=SlottedComponent)

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
        @register("test")
        class SlottedComponentNoSlots(Component):
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
        @register("test")
        class SlottedComponentNoSlots(Component):
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
        registry.register(name="test", component=SlottedComponent)
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
        class Comp(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div class="header-box">
                    <h1>{% slot "title" required %}{% endslot %}</h1>
                    <h2>{% slot "subtitle" %}{% endslot %}</h2>
                </div>
            """

        registry.register("test", Comp)

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test' %}
            {% endcomponent %}
        """
        template = Template(template_str)

        with self.assertRaisesMessage(TemplateSyntaxError, "Slot 'title' is marked as 'required'"):
            template.render(Context())

    # NOTE: This is relevant only for the "isolated" mode
    @parametrize_context_behavior(["isolated"])
    def test_slots_of_top_level_comps_can_access_full_outer_ctx(self):
        class SlottedComponent(Component):
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

        registry.register("test", SlottedComponent)

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

    @parametrize_context_behavior(["django", "isolated"])
    def test_target_default_slot_as_named(self):
        @register("test")
        class Comp(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div>
                    <h1>{% slot "title" default %}Default title{% endslot %}</h1>
                    <h2>{% slot "subtitle" %}Default subtitle{% endslot %}</h2>
                </div>
            """

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test' %}
                {% fill "default" %}Custom title{% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)

        rendered = template.render(Context())
        self.assertHTMLEqual(
            rendered,
            """
            <div>
                <h1> Custom title </h1>
                <h2> Default subtitle </h2>
            </div>
            """,
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_raises_on_doubly_filled_slot__same_name(self):
        @register("test")
        class Comp(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div class="header-box">
                    <h1>{% slot "title" default %}Default title{% endslot %}</h1>
                    <h2>{% slot "subtitle" %}Default subtitle{% endslot %}</h2>
                </div>
            """

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test' %}
                {% fill "title" %}Custom title{% endfill %}
                {% fill "title" %}Another title{% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)

        with self.assertRaisesMessage(
            TemplateSyntaxError,
            "Multiple fill tags cannot target the same slot name in component 'test': "
            "Detected duplicate fill tag name 'title'",
        ):
            template.render(Context())

    @parametrize_context_behavior(["django", "isolated"])
    def test_raises_on_doubly_filled_slot__named_and_default(self):
        @register("test")
        class Comp(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div class="header-box">
                    <h1>{% slot "title" default %}Default title{% endslot %}</h1>
                    <h2>{% slot "subtitle" %}Default subtitle{% endslot %}</h2>
                </div>
            """

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test' %}
                {% fill "default" %}Custom title{% endfill %}
                {% fill "title" %}Another title{% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)

        with self.assertRaisesMessage(
            TemplateSyntaxError,
            "Slot 'title' of component 'test' was filled twice: once explicitly and once implicitly as 'default'",
        ):
            template.render(Context())

    @parametrize_context_behavior(["django", "isolated"])
    def test_raises_on_doubly_filled_slot__named_and_default_2(self):
        @register("test")
        class Comp(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div class="header-box">
                    <h1>{% slot "default" default %}Default title{% endslot %}</h1>
                    <h2>{% slot "subtitle" %}Default subtitle{% endslot %}</h2>
                </div>
            """

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test' %}
                {% fill "default" %}Custom title{% endfill %}
                {% fill "default" %}Another title{% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)

        with self.assertRaisesMessage(
            TemplateSyntaxError,
            "Multiple fill tags cannot target the same slot name in component 'test': "
            "Detected duplicate fill tag name 'default'",
        ):
            template.render(Context())

    @parametrize_context_behavior(["django", "isolated"])
    def test_multiple_slots_with_same_name_different_flags(self):
        class TestComp(Component):
            def get_context_data(self, required: bool) -> Any:
                return {"required": required}

            template: types.django_html = """
                {% load component_tags %}
                <div>
                    {% if required %}
                        <main>{% slot "main" required %}1{% endslot %}</main>
                    {% endif %}
                    <div>{% slot "main" default %}2{% endslot %}</div>
                </div>
            """

        # 1. Specify the non-required slot by its name
        rendered1 = TestComp.render(
            kwargs={"required": False},
            slots={
                "main": "MAIN",
            },
            render_dependencies=False,
        )

        # 2. Specify the non-required slot by the "default" name
        rendered2 = TestComp.render(
            kwargs={"required": False},
            slots={
                "default": "MAIN",
            },
            render_dependencies=False,
        )

        self.assertInHTML(rendered1, "<div><div>MAIN</div></div>")
        self.assertInHTML(rendered2, "<div><div>MAIN</div></div>")

        # 3. Specify the required slot by its name
        rendered3 = TestComp.render(
            kwargs={"required": True},
            slots={
                "main": "MAIN",
            },
            render_dependencies=False,
        )
        self.assertInHTML(rendered3, "<div><main>MAIN</main><div>MAIN</div></div>")

        # 4. RAISES: Specify the required slot by the "default" name
        #    This raises because the slot that is marked as 'required' is NOT marked as 'default'.
        with self.assertRaisesMessage(
            TemplateSyntaxError,
            "Slot 'main' is marked as 'required'",
        ):
            TestComp.render(
                kwargs={"required": True},
                slots={
                    "default": "MAIN",
                },
                render_dependencies=False,
            )

    @parametrize_context_behavior(["django", "isolated"])
    def test_slot_in_include(self):
        @register("slotted")
        class SlottedWithIncludeComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                {% include 'slotted_template.html' %}
            """

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "slotted" %}
                {% fill "header" %}Custom header{% endfill %}
                {% fill "main" %}Custom main{% endfill %}
                {% fill "footer" %}Custom footer{% endfill %}
            {% endcomponent %}
        """

        rendered = Template(template_str).render(Context({}))

        expected = """
            <custom-template>
                <header>Custom header</header>
                <main>Custom main</main>
                <footer>Custom footer</footer>
            </custom-template>
        """
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["django", "isolated"])
    def test_slot_in_include_raises_if_isolated(self):
        @register("broken_component")
        class BrokenComponent(Component):
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

        with self.assertRaisesMessage(
            TemplateSyntaxError,
            "Encountered a SlotNode outside of a ComponentNode context.",
        ):
            Template(template_str).render(Context({}))


class ComponentSlotDefaultTests(BaseTestCase):
    @parametrize_context_behavior(["django", "isolated"])
    def test_default_slot_is_fillable_by_implicit_fill_content(self):
        @register("test_comp")
        class ComponentWithDefaultSlot(Component):
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
        @register("test_comp")
        class ComponentWithDefaultSlot(Component):
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
    def test_multiple_default_slots_with_same_name(self):
        @register("test_comp")
        class ComponentWithDefaultSlot(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div>
                    <main>{% slot "main" default %}1{% endslot %}</main>
                    <div>{% slot "main" default %}2{% endslot %}</div>
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
            <div><p>This fills the 'main' slot.</p></div>
            </div>
        """
        rendered = template.render(Context({}))
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["django", "isolated"])
    def test_multiple_default_slots_with_different_names(self):
        @register("test_comp")
        class ComponentWithDefaultSlot(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div>
                    <main>{% slot "main" default %}1{% endslot %}</main>
                    <div>{% slot "other" default %}2{% endslot %}</div>
                </div>
            """

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test_comp' %}
              {% fill "main" %}<p>This fills the 'main' slot.</p>{% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)

        with self.assertRaisesMessage(
            TemplateSyntaxError, "Only one component slot may be marked as 'default', found 'main' and 'other'"
        ):
            template.render(Context({}))

    @parametrize_context_behavior(["django", "isolated"])
    def test_error_raised_when_default_and_required_slot_not_filled(self):
        @register("test_comp")
        class ComponentWithDefaultAndRequiredSlot(Component):
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

        with self.assertRaisesMessage(TemplateSyntaxError, "Slot 'main' is marked as 'required'"):
            template.render(Context())

    @parametrize_context_behavior(["django", "isolated"])
    def test_fill_tag_can_occur_within_component_nested_in_implicit_fill(self):
        registry.register("slotted", SlottedComponent)

        @register("test_comp")
        class ComponentWithDefaultSlot(Component):
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
        @register("test_comp")
        class ComponentWithDefaultSlot(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div>
                    <main>{% slot "main" default %}Easy to override{% endslot %}</main>
                </div>
            """

        with self.assertRaisesMessage(
            TemplateSyntaxError,
            "Illegal content passed to component 'test_comp'. Explicit 'fill' tags cannot occur alongside other text",
        ):
            template_str: types.django_html = """
                {% load component_tags %}
                {% component 'test_comp' %}
                  {% fill "main" %}Main content{% endfill %}
                  <p>And add this too!</p>
                {% endcomponent %}
            """
            Template(template_str).render(Context({}))

    @parametrize_context_behavior(["django", "isolated"])
    def test_comments_permitted_inside_implicit_fill_content(self):
        @register("test_comp")
        class ComponentWithDefaultSlot(Component):
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
        registry.register("test_comp", SlottedComponent)
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test_comp' %}
              <p>This shouldn't work because the included component doesn't mark
              any of its slots as 'default'</p>
            {% endcomponent %}
        """
        template = Template(template_str)

        with self.assertRaisesMessage(
            TemplateSyntaxError,
            "Component 'test_comp' passed default fill content (i.e. without explicit 'name' kwarg), "
            "even though none of its slots is marked as 'default'",
        ):
            template.render(Context())


class PassthroughSlotsTest(BaseTestCase):
    @parametrize_context_behavior(["isolated", "django"])
    def test_if_for(self):
        @register("test")
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

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "test" %}
                {% if slot_names %}
                    {% for slot in slot_names %}
                        {% fill name=slot default="default" %}
                            OVERRIDEN_SLOT "{{ slot }}" - INDEX {{ forloop.counter0 }} - ORIGINAL "{{ default }}"
                        {% endfill %}
                    {% endfor %}
                {% endif %}

                {% if 1 > 2 %}
                    {% fill "footer" %}
                        FOOTER
                    {% endfill %}
                {% endif %}
            {% endcomponent %}
        """
        template = Template(template_str)

        rendered = template.render(Context({"slot_names": ["header", "main"]}))
        self.assertHTMLEqual(
            rendered,
            """
            <custom-template>
                <header>
                    OVERRIDEN_SLOT "header" - INDEX 0 - ORIGINAL "Default header"
                </header>
                <main>
                    OVERRIDEN_SLOT "main" - INDEX 1 - ORIGINAL "Default main"
                </main>
                <footer>
                    Default footer
                </footer>
            </custom-template>
            """,
        )

    @parametrize_context_behavior(["isolated", "django"])
    def test_with(self):
        @register("test")
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

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "test" %}
                {% with slot="header" %}
                    {% fill name=slot default="default" %}
                        OVERRIDEN_SLOT "{{ slot }}" - ORIGINAL "{{ default }}"
                    {% endfill %}
                {% endwith %}
            {% endcomponent %}
        """
        template = Template(template_str)

        rendered = template.render(Context())
        self.assertHTMLEqual(
            rendered,
            """
            <custom-template>
                <header>
                    OVERRIDEN_SLOT "header" - ORIGINAL "Default header"
                </header>
                <main>Default main</main>
                <footer>Default footer</footer>
            </custom-template>
            """,
        )

    @parametrize_context_behavior(["isolated", "django"])
    def test_if_for_raises_on_content_outside_fill(self):
        @register("test")
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

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "test" %}
                {% if slot_names %}
                    {% for slot in slot_names %}
                        {{ forloop.counter0 }}
                        {% fill name=slot default="default" %}
                            OVERRIDEN_SLOT
                        {% endfill %}
                    {% endfor %}
                {% endif %}

                {% if 1 > 2 %}
                    {% fill "footer" %}
                        FOOTER
                    {% endfill %}
                {% endif %}
            {% endcomponent %}
        """
        template = Template(template_str)

        with self.assertRaisesMessage(TemplateSyntaxError, "Illegal content passed to component 'test'"):
            template.render(Context({"slot_names": ["header", "main"]}))

    @parametrize_context_behavior(["django", "isolated"])
    def test_slots_inside_loops(self):
        @register("test_comp")
        class OuterComp(Component):
            def get_context_data(self, name: Optional[str] = None) -> Dict[str, Any]:
                return {
                    "slots": ["header", "main", "footer"],
                }

            template: types.django_html = """
                {% load component_tags %}
                {% for slot_name in slots %}
                    <div>
                        {% slot name=slot_name %}
                            {{ slot_name }}
                        {% endslot %}
                    </div>
                {% endfor %}
            """

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "test_comp" %}
                {% fill "header" %}
                    CUSTOM HEADER
                {% endfill %}
                {% fill "main" %}
                    CUSTOM MAIN
                {% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context())

        expected = """
            <div>CUSTOM HEADER</div>
            <div>CUSTOM MAIN</div>
            <div>footer</div>
        """
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["django", "isolated"])
    def test_passthrough_slots(self):
        registry.register("slotted", SlottedComponent)

        @register("test_comp")
        class OuterComp(Component):
            def get_context_data(self, name: Optional[str] = None) -> Dict[str, Any]:
                return {
                    "slots": self.input.slots,
                }

            template: types.django_html = """
                {% load component_tags %}
                <div>
                    {% component "slotted" %}
                        {% for slot_name in slots %}
                            {% fill name=slot_name %}
                                {% slot name=slot_name / %}
                            {% endfill %}
                        {% endfor %}
                    {% endcomponent %}
                </div>
            """

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "test_comp" %}
                {% fill "header" %}
                    CUSTOM HEADER
                {% endfill %}
                {% fill "main" %}
                    CUSTOM MAIN
                {% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context())

        expected = """
            <div>
                <custom-template>
                <header>CUSTOM HEADER</header>
                <main>CUSTOM MAIN</main>
                <footer>Default footer</footer>
                </custom-template>
            </div>
        """
        self.assertHTMLEqual(rendered, expected)

    # NOTE: Ideally we'd (optionally) raise an error / warning here, but it's not possible
    # with current implementation. So this tests serves as a documentation of the current behavior.
    @parametrize_context_behavior(["django", "isolated"])
    def test_passthrough_slots_unknown_fills_ignored(self):
        registry.register("slotted", SlottedComponent)

        @register("test_comp")
        class OuterComp(Component):
            def get_context_data(self, name: Optional[str] = None) -> Dict[str, Any]:
                return {
                    "slots": self.input.slots,
                }

            template: types.django_html = """
                {% load component_tags %}
                <div>
                    {% component "slotted" %}
                        {% for slot_name in slots %}
                            {% fill name=slot_name %}
                                {% slot name=slot_name / %}
                            {% endfill %}
                        {% endfor %}
                    {% endcomponent %}
                </div>
            """

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "test_comp" %}
                {% fill "header1" %}
                    CUSTOM HEADER
                {% endfill %}
                {% fill "main" %}
                    CUSTOM MAIN
                {% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context())

        expected = """
            <div>
                <custom-template>
                <header>Default header</header>
                <main>CUSTOM MAIN</main>
                <footer>Default footer</footer>
                </custom-template>
            </div>
        """
        self.assertHTMLEqual(rendered, expected)


# See https://github.com/EmilStenstrom/django-components/issues/698
class NestedSlotsTests(BaseTestCase):
    class NestedSlots(Component):
        template: types.django_html = """
            {% load component_tags %}
            {% slot 'wrapper' %}
                <div>
                    Wrapper Default
                    {% slot 'parent1' %}
                        <div>
                            Parent1 Default
                            {% slot 'child1' %}
                                <div>
                                    Child 1 Default
                                </div>
                            {% endslot %}
                        </div>
                    {% endslot %}
                    {% slot 'parent2' %}
                        <div>
                            Parent2 Default
                        </div>
                    {% endslot %}
                </div>
            {% endslot %}
        """

    def setUp(self) -> None:
        super().setUp()
        registry.register("example", self.NestedSlots)

    @parametrize_context_behavior(["django", "isolated"])
    def test_empty(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'example' %}
            {% endcomponent %}
        """

        rendered = Template(template_str).render(Context())
        expected = """
            <div>
                Wrapper Default
                <div>
                    Parent1 Default
                    <div>
                        Child 1 Default
                    </div>
                </div>
                <div>
                    Parent2 Default
                </div>
            </div>
        """
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["django", "isolated"])
    def test_override_outer(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'example' %}
                {% fill 'wrapper' %}
                    <div>
                        Entire Wrapper Replaced
                    </div>
                {% endfill %}
            {% endcomponent %}
        """

        rendered = Template(template_str).render(Context())
        expected = """
            <div>
                Entire Wrapper Replaced
            </div>
        """
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["django", "isolated"])
    def test_override_middle(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'example' %}
                {% fill 'parent1' %}
                    <div>
                        Parent1 Replaced
                    </div>
                {% endfill %}
            {% endcomponent %}
        """

        rendered = Template(template_str).render(Context())
        expected = """
            <div>
                Wrapper Default
                <div>
                    Parent1 Replaced
                </div>
                <div>
                    Parent2 Default
                </div>
            </div>
        """
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["django", "isolated"])
    def test_override_inner(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'example' %}
                {% fill 'child1' %}
                    <div>
                        Child1 Replaced
                    </div>
                {% endfill %}
            {% endcomponent %}
        """

        rendered = Template(template_str).render(Context())
        expected = """
            <div>
                Wrapper Default
                <div>
                    Parent1 Default
                    <div>
                        Child1 Replaced
                    </div>
                </div>
                <div>
                    Parent2 Default
                </div>
            </div>
        """
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["django", "isolated"])
    def test_override_all(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'example' %}
                {% fill 'child1' %}
                    <div>
                        Child1 Replaced
                    </div>
                {% endfill %}
                {% fill 'parent1' %}
                    <div>
                        Parent1 Replaced
                    </div>
                {% endfill %}
                {% fill 'wrapper' %}
                    <div>
                        Entire Wrapper Replaced
                    </div>
                {% endfill %}
            {% endcomponent %}
        """

        rendered = Template(template_str).render(Context())
        expected = """
            <div>
                Entire Wrapper Replaced
            </div>
        """
        self.assertHTMLEqual(rendered, expected)


# See https://github.com/EmilStenstrom/django-components/issues/698
class NestedSlotsTests(BaseTestCase):
    class NestedSlots(Component):
        template: types.django_html = """
            {% load component_tags %}
            {% slot 'wrapper' %}
                <div>
                    Wrapper Default
                    {% slot 'parent1' %}
                        <div>
                            Parent1 Default
                            {% slot 'child1' %}
                                <div>
                                    Child 1 Default
                                </div>
                            {% endslot %}
                        </div>
                    {% endslot %}
                    {% slot 'parent2' %}
                        <div>
                            Parent2 Default
                        </div>
                    {% endslot %}
                </div>
            {% endslot %}
        """

    def setUp(self) -> None:
        super().setUp()
        registry.register("example", self.NestedSlots)

    @parametrize_context_behavior(["django", "isolated"])
    def test_empty(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'example' %}
            {% endcomponent %}
        """

        rendered = Template(template_str).render(Context())
        expected = """
            <div>
                Wrapper Default
                <div>
                    Parent1 Default
                    <div>
                        Child 1 Default
                    </div>
                </div>
                <div>
                    Parent2 Default
                </div>
            </div>
        """
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["django", "isolated"])
    def test_override_outer(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'example' %}
                {% fill 'wrapper' %}
                    <div>
                        Entire Wrapper Replaced
                    </div>
                {% endfill %}
            {% endcomponent %}
        """

        rendered = Template(template_str).render(Context())
        expected = """
            <div>
                Entire Wrapper Replaced
            </div>
        """
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["django", "isolated"])
    def test_override_middle(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'example' %}
                {% fill 'parent1' %}
                    <div>
                        Parent1 Replaced
                    </div>
                {% endfill %}
            {% endcomponent %}
        """

        rendered = Template(template_str).render(Context())
        expected = """
            <div>
                Wrapper Default
                <div>
                    Parent1 Replaced
                </div>
                <div>
                    Parent2 Default
                </div>
            </div>
        """
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["django", "isolated"])
    def test_override_inner(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'example' %}
                {% fill 'child1' %}
                    <div>
                        Child1 Replaced
                    </div>
                {% endfill %}
            {% endcomponent %}
        """

        rendered = Template(template_str).render(Context())
        expected = """
            <div>
                Wrapper Default
                <div>
                    Parent1 Default
                    <div>
                        Child1 Replaced
                    </div>
                </div>
                <div>
                    Parent2 Default
                </div>
            </div>
        """
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["django", "isolated"])
    def test_override_all(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'example' %}
                {% fill 'child1' %}
                    <div>
                        Child1 Replaced
                    </div>
                {% endfill %}
                {% fill 'parent1' %}
                    <div>
                        Parent1 Replaced
                    </div>
                {% endfill %}
                {% fill 'wrapper' %}
                    <div>
                        Entire Wrapper Replaced
                    </div>
                {% endfill %}
            {% endcomponent %}
        """

        rendered = Template(template_str).render(Context())
        expected = """
            <div>
                Entire Wrapper Replaced
            </div>
        """
        self.assertHTMLEqual(rendered, expected)


class SlottedTemplateRegressionTests(BaseTestCase):
    @parametrize_context_behavior(["django", "isolated"])
    def test_slotted_template_that_uses_missing_variable(self):
        @register("test")
        class SlottedComponentWithMissingVariable(Component):
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
    def setUp(self):
        super().setUp()
        registry.register("test", SlottedComponent)

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
        @register("test")
        class TestComponent(Component):
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
        @register("test")
        class TestComponent(Component):
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
        @register("test")
        class TestComponent(Component):
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
    def test_slot_data_with_variable(self):
        @register("test")
        class TestComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div>
                    {% slot slot_name abc=abc var123=var123 default required %}Default text{% endslot %}
                </div>
            """

            def get_context_data(self):
                return {
                    "slot_name": "my_slot",
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
    def test_slot_data_with_spread(self):
        @register("test")
        class TestComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div>
                    {% slot ...slot_props default required %}Default text{% endslot %}
                </div>
            """

            def get_context_data(self):
                return {
                    "slot_props": {
                        "name": "my_slot",
                        "abc": "def",
                        "var123": 456,
                    },
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
    def test_slot_data_and_default_on_default_slot(self):
        @register("test")
        class TestComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div>
                    <b>{% slot "slot_a" abc=abc var123=var123 %} Default text A {% endslot %}</b>
                    <b>{% slot "slot_b" abc=abc var123=var123 default %} Default text B {% endslot %}</b>
                </div>
            """

            def get_context_data(self):
                return {
                    "abc": "xyz",
                    "var123": 456,
                }

        template: types.django_html = """
            {% load component_tags %}
            {% component "test" %}
                {% fill name="default" data="slot_data_in_fill" default="slot_var" %}
                    {{ slot_data_in_fill.abc }}
                    {{ slot_var }}
                    {{ slot_data_in_fill.var123 }}
                {% endfill %}
            {% endcomponent %}
        """
        rendered = Template(template).render(Context())
        expected = """
            <div>
                <b>Default text A</b>
                <b>xyz Default text B 456</b>
            </div>
        """
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["django", "isolated"])
    def test_slot_data_raises_on_slot_data_and_slot_default_same_var(self):
        @register("test")
        class TestComponent(Component):
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
            RuntimeError,
            "Fill 'my_slot' received the same string for slot default (default=...) and slot data (data=...)",
        ):
            Template(template).render(Context())

    @parametrize_context_behavior(["django", "isolated"])
    def test_slot_data_fill_without_data(self):
        @register("test")
        class TestComponent(Component):
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
        @register("test")
        class TestComponent(Component):
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
        @register("test")
        class TestComponent(Component):
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
    def test_slot_data_fill_with_variables(self):
        @register("test")
        class TestComponent(Component):
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
                {% fill fill_name data=data_var %}
                    {{ slot_data_in_fill.abc }}
                    {{ slot_data_in_fill.var123 }}
                {% endfill %}
            {% endcomponent %}
        """
        rendered = Template(template).render(
            Context(
                {
                    "fill_name": "my_slot",
                    "data_var": "slot_data_in_fill",
                }
            )
        )

        expected = """
            <div>
                def
                456
            </div>
        """
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["django", "isolated"])
    def test_slot_data_fill_with_spread(self):
        @register("test")
        class TestComponent(Component):
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
                {% fill ...fill_props %}
                    {{ slot_data_in_fill.abc }}
                    {{ slot_data_in_fill.var123 }}
                {% endfill %}
            {% endcomponent %}
        """
        rendered = Template(template).render(
            Context(
                {
                    "fill_props": {
                        "name": "my_slot",
                        "data": "slot_data_in_fill",
                    },
                }
            )
        )

        expected = """
            <div>
                def
                456
            </div>
        """
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["django", "isolated"])
    def test_nested_fills(self):
        @register("test")
        class TestComponent(Component):
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
    class DuplicateSlotComponent(Component):
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

    class DuplicateSlotNestedComponent(Component):
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

    def setUp(self):
        super().setUp()
        registry.register(name="duplicate_slot", component=self.DuplicateSlotComponent)
        registry.register(name="duplicate_slot_nested", component=self.DuplicateSlotNestedComponent)
        registry.register(name="calendar", component=self.CalendarComponent)

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
    def setUp(self):
        super().setUp()
        registry.register("test", SlottedComponent)

    @parametrize_context_behavior(["django", "isolated"])
    def test_fill_with_no_parent_is_error(self):
        with self.assertRaisesMessage(
            TemplateSyntaxError,
            "FillNode.render() (AKA {% fill ... %} block) cannot be rendered outside of a Component context",
        ):
            template_str: types.django_html = """
                {% load component_tags %}
                {% fill "header" %}contents{% endfill %}
            """
            Template(template_str).render(Context({}))

    @parametrize_context_behavior(["django", "isolated"])
    def test_non_unique_fill_names_is_error(self):
        with self.assertRaisesMessage(
            TemplateSyntaxError,
            "Multiple fill tags cannot target the same slot name in component 'test': "
            "Detected duplicate fill tag name 'header'",
        ):
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
        with self.assertRaisesMessage(
            TemplateSyntaxError,
            "Multiple fill tags cannot target the same slot name in component 'test': "
            "Detected duplicate fill tag name 'header'",
        ):
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


class SlotInputTests(BaseTestCase):
    @parametrize_context_behavior(["django", "isolated"])
    def test_slots_accessible_when_python_render(self):
        slots: Dict = {}

        @register("test")
        class SlottedComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                <header>{% slot "header" %}Default header{% endslot %}</header>
                <main>{% slot "main" %}Default main header{% endslot %}</main>
                <footer>{% slot "footer" %}Default footer{% endslot %}</footer>
            """

            def get_context_data(self, input: Optional[int] = None) -> Dict[str, Any]:
                nonlocal slots
                slots = self.input.slots
                return {}

        self.assertEqual(slots, {})

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "test" input=1 %}
                {% fill "header" data="data1" %}
                    data1_in_slot1: {{ data1|safe }}
                {% endfill %}
                {% fill "main" / %}
            {% endcomponent %}
        """
        template = Template(template_str)
        template.render(Context())

        self.assertListEqual(
            list(slots.keys()),
            ["header", "main"],
        )
        self.assertTrue(callable(slots["header"]))
        self.assertTrue(callable(slots["main"]))
        self.assertTrue("footer" not in slots)

    @parametrize_context_behavior(["django", "isolated"])
    def test_slots_normalized_as_slot_instances(self):
        slots: Dict[str, Slot] = {}

        @register("test")
        class SlottedComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                <header>{% slot "header" %}Default header{% endslot %}</header>
                <main>{% slot "main" %}Default main header{% endslot %}</main>
                <footer>{% slot "footer" %}Default footer{% endslot %}</footer>
            """

            def get_context_data(self, input: Optional[int] = None) -> Dict[str, Any]:
                nonlocal slots
                slots = self.input.slots
                return {}

        self.assertEqual(slots, {})

        header_slot = Slot(lambda *a, **kw: "HEADER_SLOT")
        main_slot_str = "MAIN_SLOT"
        footer_slot_fn = lambda *a, **kw: "FOOTER_SLOT"  # noqa: E731

        SlottedComponent.render(
            slots={
                "header": header_slot,
                "main": main_slot_str,
                "footer": footer_slot_fn,
            }
        )

        self.assertIsInstance(slots["header"], Slot)
        self.assertEqual(slots["header"](Context(), None, None), "HEADER_SLOT")  # type: ignore[arg-type]

        self.assertIsInstance(slots["main"], Slot)
        self.assertEqual(slots["main"](Context(), None, None), "MAIN_SLOT")  # type: ignore[arg-type]

        self.assertIsInstance(slots["footer"], Slot)
        self.assertEqual(slots["footer"](Context(), None, None), "FOOTER_SLOT")  # type: ignore[arg-type]
