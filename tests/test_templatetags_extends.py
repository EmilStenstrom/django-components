"""Catch-all for tests that use template tags and don't fit other files"""

from django.template import Context, Template

from django_components import Component, register, registry, types

from .django_test_setup import setup_test_config
from .testutils import BaseTestCase, parametrize_context_behavior

setup_test_config({"autodiscover": False})


class SlottedComponent(Component):
    template_name = "slotted_template.html"


class BlockedAndSlottedComponent(Component):
    template_name = "blocked_and_slotted_template.html"


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
                <div>BLOCK OVERRIDEN</div>
                <custom-template>
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
                <div>BLOCK OVERRIDEN</div>
                <custom-template>
                    <header>SLOT OVERRIDEN</header>
                    <main>Default main</main>
                    <footer>Default footer</footer>
                </custom-template>
                <div>BLOCK OVERRIDEN</div>
                <custom-template>
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
                <div>BLOCK OVERRIDEN</div>
                <custom-template>
                    <header>SLOT OVERRIDEN</header>
                    <main>Default main</main>
                    <footer>Default footer</footer>
                </custom-template>
                <div>BLOCK OVERRIDEN</div>
                <custom-template>
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
                <div>BLOCK OVERRIDEN</div>
                <custom-template>
                    <header>SLOT OVERRIDEN</header>
                    <main>Default main</main>
                    <footer>Default footer</footer>
                </custom-template>
                <div>BLOCK OVERRIDEN</div>
                <custom-template>
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
                <div>BLOCK OVERRIDEN</div>
                <custom-template>
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
                <div>BLOCK OVERRIDEN</div>
                <custom-template>
                    <header>SLOT OVERRIDEN</header>
                    <main>Default main</main>
                    <footer>Default footer</footer>
                </custom-template>
                <div>BLOCK OVERRIDEN</div>
                <custom-template>
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
            <custom-template>
            <header>Default header</header>
            <main>
                <div>BLOCK OVERRIDEN</div>
                <custom-template>
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
