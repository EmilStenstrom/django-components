"""Catch-all for tests that use template tags and don't fit other files"""

from django.template import Context, Template

from django_components import Component, register, registry, types

from .django_test_setup import setup_test_config
from .testutils import BaseTestCase, parametrize_context_behavior

setup_test_config({"autodiscover": False})


class SlottedComponent(Component):
    template_file = "slotted_template.html"


class BlockedAndSlottedComponent(Component):
    template_file = "blocked_and_slotted_template.html"


#######################
# TESTS
#######################


class ExtendsCompatTests(BaseTestCase):
    @parametrize_context_behavior(["isolated", "django"])
    def test_double_extends_on_main_template_and_component_one_component(self):
        registry.register("blocked_and_slotted_component", BlockedAndSlottedComponent)

        @register("extended_component")
        class _ExtendedComponent(Component):
            template: types.django_html = """
                {% extends "blocked_and_slotted_template.html" %}
                {% block before_custom %}
                    <div>BLOCK OVERRIDEN</div>
                {% endblock %}
            """

        template: types.django_html = """
            {% extends 'block.html' %}
            {% load component_tags %}
            {% block body %}
                {% component "extended_component" %}
                    {% fill "header" %}
                        SLOT OVERRIDEN
                    {% endfill %}
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
                            <div data-djc-id-a1bc40>BLOCK OVERRIDEN</div>
                            <custom-template data-djc-id-a1bc40>
                                <header>SLOT OVERRIDEN</header>
                                <main>Default main</main>
                                <footer>Default footer</footer>
                            </custom-template>
                        </div>
                    </main>
                </body>
            </html>
        """
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["isolated", "django"])
    def test_double_extends_on_main_template_and_component_two_identical_components(self):
        registry.register("blocked_and_slotted_component", BlockedAndSlottedComponent)

        @register("extended_component")
        class _ExtendedComponent(Component):
            template: types.django_html = """
                {% extends "blocked_and_slotted_template.html" %}
                {% block before_custom %}
                    <div>BLOCK OVERRIDEN</div>
                {% endblock %}
            """

        template: types.django_html = """
            {% extends 'block.html' %}
            {% load component_tags %}
            {% block body %}
                {% component "extended_component" %}
                    {% fill "header" %}
                        SLOT OVERRIDEN
                    {% endfill %}
                {% endcomponent %}
                {% component "extended_component" %}
                    {% fill "header" %}
                        SLOT OVERRIDEN 2
                    {% endfill %}
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
                            <div data-djc-id-a1bc42>BLOCK OVERRIDEN</div>
                            <custom-template data-djc-id-a1bc42>
                                <header>SLOT OVERRIDEN</header>
                                <main>Default main</main>
                                <footer>Default footer</footer>
                            </custom-template>
                            <div data-djc-id-a1bc46>BLOCK OVERRIDEN</div>
                            <custom-template data-djc-id-a1bc46>
                                <header>SLOT OVERRIDEN 2</header>
                                <main>Default main</main>
                                <footer>Default footer</footer>
                            </custom-template>
                        </div>
                    </main>
                </body>
            </html>
        """
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["isolated", "django"])
    def test_double_extends_on_main_template_and_component_two_different_components_same_parent(self):
        registry.register("blocked_and_slotted_component", BlockedAndSlottedComponent)

        @register("extended_component")
        class _ExtendedComponent(Component):
            template: types.django_html = """
                {% extends "blocked_and_slotted_template.html" %}
                {% block before_custom %}
                    <div>BLOCK OVERRIDEN</div>
                {% endblock %}
            """

        @register("second_extended_component")
        class _SecondExtendedComponent(Component):
            template: types.django_html = """
                {% extends "blocked_and_slotted_template.html" %}
                {% block before_custom %}
                    <div>BLOCK OVERRIDEN</div>
                {% endblock %}
            """

        template_str: types.django_html = """
            {% extends 'block.html' %}
            {% load component_tags %}
            {% block body %}
                {% component "extended_component" %}
                    {% fill "header" %}
                        SLOT OVERRIDEN
                    {% endfill %}
                {% endcomponent %}
                {% component "second_extended_component" %}
                    {% fill "header" %}
                        SLOT OVERRIDEN 2
                    {% endfill %}
                {% endcomponent %}
            {% endblock %}
        """
        template = Template(template_str)
        rendered = template.render(Context())

        expected = """
            <!DOCTYPE html>
            <html lang="en">
                <body>
                    <main role="main">
                        <div class='container main-container'>
                            <div data-djc-id-a1bc42>BLOCK OVERRIDEN</div>
                            <custom-template data-djc-id-a1bc42>
                                <header>SLOT OVERRIDEN</header>
                                <main>Default main</main>
                                <footer>Default footer</footer>
                            </custom-template>
                            <div data-djc-id-a1bc46>BLOCK OVERRIDEN</div>
                            <custom-template data-djc-id-a1bc46>
                                <header>SLOT OVERRIDEN 2</header>
                                <main>Default main</main>
                                <footer>Default footer</footer>
                            </custom-template>
                        </div>
                    </main>
                </body>
            </html>
        """

        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["isolated", "django"])
    def test_double_extends_on_main_template_and_component_two_different_components_different_parent(self):
        registry.register("blocked_and_slotted_component", BlockedAndSlottedComponent)

        @register("extended_component")
        class _ExtendedComponent(Component):
            template: types.django_html = """
                {% extends "blocked_and_slotted_template.html" %}
                {% block before_custom %}
                    <div>BLOCK OVERRIDEN</div>
                {% endblock %}
            """

        @register("second_extended_component")
        class _SecondExtendedComponent(Component):
            template: types.django_html = """
                {% extends "blocked_and_slotted_template_2.html" %}
                {% block before_custom %}
                    <div>BLOCK OVERRIDEN</div>
                {% endblock %}
            """

        template: types.django_html = """
            {% extends 'block.html' %}
            {% load component_tags %}
            {% block body %}
                {% component "extended_component" %}
                    {% fill "header" %}
                        SLOT OVERRIDEN
                    {% endfill %}
                {% endcomponent %}
                {% component "second_extended_component" %}
                    {% fill "header" %}
                        SLOT OVERRIDEN 2
                    {% endfill %}
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
                            <div data-djc-id-a1bc42>BLOCK OVERRIDEN</div>
                            <custom-template data-djc-id-a1bc42>
                                <header>SLOT OVERRIDEN</header>
                                <main>Default main</main>
                                <footer>Default footer</footer>
                            </custom-template>
                            <div data-djc-id-a1bc46>BLOCK OVERRIDEN</div>
                            <custom-template data-djc-id-a1bc46>
                                <header>SLOT OVERRIDEN 2</header>
                                <main>Default main</main>
                                <footer>Default footer</footer>
                            </custom-template>
                        </div>
                    </main>
                </body>
            </html>
        """
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["isolated", "django"])
    def test_extends_on_component_one_component(self):
        registry.register("blocked_and_slotted_component", BlockedAndSlottedComponent)

        @register("extended_component")
        class _ExtendedComponent(Component):
            template: types.django_html = """
                {% extends "blocked_and_slotted_template.html" %}
                {% block before_custom %}
                    <div>BLOCK OVERRIDEN</div>
                {% endblock %}
            """

        template: types.django_html = """
            {% load component_tags %}
            <!DOCTYPE html>
            <html lang="en">
            <body>
                {% component "extended_component" %}
                    {% fill "header" %}
                        SLOT OVERRIDEN
                    {% endfill %}
                {% endcomponent %}
            </body>
            </html>
        """
        rendered = Template(template).render(Context())

        expected = """
            <!DOCTYPE html>
            <html lang="en">
                <body>
                    <div data-djc-id-a1bc40>BLOCK OVERRIDEN</div>
                    <custom-template data-djc-id-a1bc40>
                        <header>SLOT OVERRIDEN</header>
                        <main>Default main</main>
                        <footer>Default footer</footer>
                    </custom-template>
                </body>
            </html>
        """
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["isolated", "django"])
    def test_extends_on_component_two_component(self):
        registry.register("blocked_and_slotted_component", BlockedAndSlottedComponent)

        @register("extended_component")
        class _ExtendedComponent(Component):
            template: types.django_html = """
                {% extends "blocked_and_slotted_template.html" %}
                {% block before_custom %}
                    <div>BLOCK OVERRIDEN</div>
                {% endblock %}
            """

        template: types.django_html = """
            {% load component_tags %}
            <!DOCTYPE html>
            <html lang="en">
            <body>
                {% component "extended_component" %}
                    {% fill "header" %}
                        SLOT OVERRIDEN
                    {% endfill %}
                {% endcomponent %}
                {% component "extended_component" %}
                    {% fill "header" %}
                        SLOT OVERRIDEN 2
                    {% endfill %}
                {% endcomponent %}
            </body>
            </html>
        """
        rendered = Template(template).render(Context())

        expected = """
            <!DOCTYPE html>
            <html lang="en">
                <body>
                    <div data-djc-id-a1bc42>BLOCK OVERRIDEN</div>
                    <custom-template data-djc-id-a1bc42>
                        <header>SLOT OVERRIDEN</header>
                        <main>Default main</main>
                        <footer>Default footer</footer>
                    </custom-template>
                    <div data-djc-id-a1bc46>BLOCK OVERRIDEN</div>
                    <custom-template data-djc-id-a1bc46>
                        <header>SLOT OVERRIDEN 2</header>
                        <main>Default main</main>
                        <footer>Default footer</footer>
                    </custom-template>
                </body>
            </html>
        """
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["isolated", "django"])
    def test_double_extends_on_main_template_and_nested_component(self):
        registry.register("slotted_component", SlottedComponent)
        registry.register("blocked_and_slotted_component", BlockedAndSlottedComponent)

        @register("extended_component")
        class _ExtendedComponent(Component):
            template: types.django_html = """
                {% extends "blocked_and_slotted_template.html" %}
                {% block before_custom %}
                    <div>BLOCK OVERRIDEN</div>
                {% endblock %}
            """

        template: types.django_html = """
            {% extends 'block.html' %}
            {% load component_tags %}
            {% block body %}
                {% component "slotted_component" %}
                    {% fill "main" %}
                        {% component "extended_component" %}
                            {% fill "header" %}
                                SLOT OVERRIDEN
                            {% endfill %}
                        {% endcomponent %}
                    {% endfill %}
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
                            <custom-template data-djc-id-a1bc42>
                                <header>Default header</header>
                                <main>
                                    <div data-djc-id-a1bc46>BLOCK OVERRIDEN</div>
                                    <custom-template data-djc-id-a1bc46>
                                        <header>SLOT OVERRIDEN</header>
                                        <main>Default main</main>
                                        <footer>Default footer</footer>
                                    </custom-template>
                                </main>
                                <footer>Default footer</footer>
                            </custom-template>
                        </div>
                    </main>
                </body>
            </html>
        """

        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["isolated", "django"])
    def test_double_extends_on_main_template_and_nested_component_and_include(self):
        registry.register("slotted_component", SlottedComponent)
        registry.register("blocked_and_slotted_component", BlockedAndSlottedComponent)

        @register("extended_component")
        class _ExtendedComponent(Component):
            template_file = "included.html"

        template: types.django_html = """
            {% extends 'block.html' %}
            {% load component_tags %}
            {% block body %}
                {% include 'included.html' %}
                {% component "extended_component" / %}
            {% endblock %}
        """
        rendered = Template(template).render(Context())

        expected = """
            <!DOCTYPE html>
            <html lang="en">
                <body>
                    <main role="main">
                        <div class='container main-container'>
                            Variable: <strong></strong>
                            Variable: <strong data-djc-id-a1bc3f></strong>
                        </div>
                    </main>
                </body>
            </html>
        """
        self.assertHTMLEqual(rendered, expected)

        # second rendering after cache built
        rendered_2 = Template(template).render(Context())
        expected_2 = expected.replace("data-djc-id-a1bc3f", "data-djc-id-a1bc41")
        self.assertHTMLEqual(rendered_2, expected_2)

    @parametrize_context_behavior(["django", "isolated"])
    def test_slots_inside_extends(self):
        registry.register("slotted_component", SlottedComponent)

        @register("slot_inside_extends")
        class SlotInsideExtendsComponent(Component):
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
            <html data-djc-id-a1bc40 lang="en">
            <body>
                <custom-template data-djc-id-a1bc45>
                    <header></header>
                    <main>BODY_FROM_FILL</main>
                    <footer>Default footer</footer>
                </custom-template>
            </body>
            </html>
        """
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["django", "isolated"])
    def test_slots_inside_include(self):
        registry.register("slotted_component", SlottedComponent)

        @register("slot_inside_include")
        class SlotInsideIncludeComponent(Component):
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
            <html data-djc-id-a1bc40 lang="en">
            <body>
                <custom-template data-djc-id-a1bc45>
                    <header></header>
                    <main>BODY_FROM_FILL</main>
                    <footer>Default footer</footer>
                </custom-template>
            </body>
            </html>
        """
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["django", "isolated"])
    def test_component_inside_block(self):
        registry.register("slotted_component", SlottedComponent)
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
                        <custom-template data-djc-id-a1bc42>
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

    @parametrize_context_behavior(["django", "isolated"])
    def test_block_inside_component(self):
        registry.register("slotted_component", SlottedComponent)

        template: types.django_html = """
            {% extends "block_in_component.html" %}
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
                <custom-template data-djc-id-a1bc41>
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

    @parametrize_context_behavior(["django", "isolated"])
    def test_block_inside_component_parent(self):
        registry.register("slotted_component", SlottedComponent)

        @register("block_in_component_parent")
        class BlockInCompParent(Component):
            template_file = "block_in_component_parent.html"

        template: types.django_html = """
            {% load component_tags %}
            {% component "block_in_component_parent" %}{% endcomponent %}
        """
        rendered = Template(template).render(Context())
        expected = """
            <!DOCTYPE html>
            <html data-djc-id-a1bc3f lang="en">
            <body>
                <custom-template data-djc-id-a1bc43>
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

    @parametrize_context_behavior(["django", "isolated"])
    def test_block_does_not_affect_inside_component(self):
        """
        Assert that when we call a component with `{% component %}`, that
        the `{% block %}` will NOT affect the inner component.
        """
        registry.register("slotted_component", SlottedComponent)

        @register("block_inside_slot_v1")
        class BlockInSlotInComponent(Component):
            template_file = "block_in_slot_in_component.html"

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
            <html data-djc-id-a1bc40 lang="en">
            <body>
                <custom-template data-djc-id-a1bc49>
                    <header></header>
                    <main>BODY_FROM_FILL</main>
                    <footer>Default footer</footer>
                </custom-template>
            </body>
            </html>
            wow
        """
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["django", "isolated"])
    def test_slot_inside_block__slot_default_block_default(self):
        registry.register("slotted_component", SlottedComponent)

        @register("slot_inside_block")
        class _SlotInsideBlockComponent(Component):
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
            <html data-djc-id-a1bc3f lang="en">
            <body>
                <custom-template data-djc-id-a1bc44>
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

    @parametrize_context_behavior(["django", "isolated"])
    def test_slot_inside_block__slot_default_block_override(self):
        registry.clear()
        registry.register("slotted_component", SlottedComponent)

        @register("slot_inside_block")
        class _SlotInsideBlockComponent(Component):
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
            <html data-djc-id-a1bc3f lang="en">
            <body>
                <custom-template data-djc-id-a1bc44>
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

    @parametrize_context_behavior(["isolated", "django"])
    def test_slot_inside_block__slot_overriden_block_default(self):
        registry.register("slotted_component", SlottedComponent)

        @register("slot_inside_block")
        class _SlotInsideBlockComponent(Component):
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
            <html data-djc-id-a1bc40 lang="en">
            <body>
                <custom-template data-djc-id-a1bc45>
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

    @parametrize_context_behavior(["django", "isolated"])
    def test_slot_inside_block__slot_overriden_block_overriden(self):
        registry.register("slotted_component", SlottedComponent)

        @register("slot_inside_block")
        class _SlotInsideBlockComponent(Component):
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
            <html data-djc-id-a1bc41 lang="en">
            <body>
                <custom-template data-djc-id-a1bc47>
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

    @parametrize_context_behavior(["django", "isolated"])
    def test_inject_inside_block(self):
        registry.register("slotted_component", SlottedComponent)

        @register("injectee")
        class InjectComponent(Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_context_data(self):
                var = self.inject("block_provide")
                return {"var": var}

        template: types.django_html = """
            {% extends "block_in_component_provide.html" %}
            {% load component_tags %}
            {% block body %}
                {% component "injectee" %}
                {% endcomponent %}
            {% endblock %}
        """
        rendered = Template(template).render(Context())
        expected = """
            <!DOCTYPE html>
            <html lang="en">
            <body>
                <custom-template data-djc-id-a1bc44>
                    <header></header>
                    <main>
                        <div data-djc-id-a1bc48> injected: DepInject(hello='from_block') </div>
                    </main>
                    <footer>Default footer</footer>
                </custom-template>
            </body>
            </html>
        """
        self.assertHTMLEqual(rendered, expected)
