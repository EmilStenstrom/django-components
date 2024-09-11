import unittest

from django.template import Context, Engine, Library, Template
from django.test import override_settings

from django_components import (
    AlreadyRegistered,
    Component,
    ComponentRegistry,
    ContextBehavior,
    NotRegistered,
    RegistrySettings,
    TagProtectedError,
    component_formatter,
    component_shorthand_formatter,
    register,
    registry,
    types,
)

from .django_test_setup import setup_test_config
from .testutils import BaseTestCase, parametrize_context_behavior

setup_test_config({"autodiscover": False})


class MockComponent(Component):
    pass


class MockComponent2(Component):
    pass


class MockComponentView(Component):
    def get(self, request, *args, **kwargs):
        pass


class ComponentRegistryTest(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.registry = ComponentRegistry()

    def test_register_class_decorator(self):
        @register("decorated_component")
        class TestComponent(Component):
            pass

        self.assertEqual(registry.get("decorated_component"), TestComponent)

        # Cleanup
        registry.unregister("decorated_component")

    def test_register_class_decorator_custom_registry(self):
        my_lib = Library()
        my_reg = ComponentRegistry(library=my_lib)

        default_registry_comps_before = len(registry.all())

        self.assertDictEqual(my_reg.all(), {})

        @register("decorated_component", registry=my_reg)
        class TestComponent(Component):
            pass

        self.assertDictEqual(my_reg.all(), {"decorated_component": TestComponent})

        # Check that the component was NOT added to the default registry
        default_registry_comps_after = len(registry.all())
        self.assertEqual(default_registry_comps_before, default_registry_comps_after)

    def test_simple_register(self):
        self.registry.register(name="testcomponent", component=MockComponent)
        self.assertEqual(self.registry.all(), {"testcomponent": MockComponent})

    def test_register_two_components(self):
        self.registry.register(name="testcomponent", component=MockComponent)
        self.registry.register(name="testcomponent2", component=MockComponent)
        self.assertEqual(
            self.registry.all(),
            {
                "testcomponent": MockComponent,
                "testcomponent2": MockComponent,
            },
        )

    def test_unregisters_only_unused_tags(self):
        self.assertDictEqual(self.registry._tags, {})
        # NOTE: We preserve the default component tags
        self.assertNotIn("component", self.registry.library.tags)

        # Register two components that use the same tag
        self.registry.register(name="testcomponent", component=MockComponent)
        self.registry.register(name="testcomponent2", component=MockComponent)

        self.assertDictEqual(
            self.registry._tags,
            {
                "component": {"testcomponent", "testcomponent2"},
            },
        )

        self.assertIn("component", self.registry.library.tags)

        # Unregister only one of the components. The tags should remain
        self.registry.unregister(name="testcomponent")

        self.assertDictEqual(
            self.registry._tags,
            {
                "component": {"testcomponent2"},
            },
        )

        self.assertIn("component", self.registry.library.tags)

        # Unregister the second components. The tags should be removed
        self.registry.unregister(name="testcomponent2")

        self.assertDictEqual(self.registry._tags, {})
        self.assertNotIn("component", self.registry.library.tags)

    def test_prevent_registering_different_components_with_the_same_name(self):
        self.registry.register(name="testcomponent", component=MockComponent)
        with self.assertRaises(AlreadyRegistered):
            self.registry.register(name="testcomponent", component=MockComponent2)

    def test_allow_duplicated_registration_of_the_same_component(self):
        try:
            self.registry.register(name="testcomponent", component=MockComponentView)
            self.registry.register(name="testcomponent", component=MockComponentView)
        except AlreadyRegistered:
            self.fail("Should not raise AlreadyRegistered")

    def test_simple_unregister(self):
        self.registry.register(name="testcomponent", component=MockComponent)
        self.registry.unregister(name="testcomponent")
        self.assertEqual(self.registry.all(), {})

    def test_raises_on_failed_unregister(self):
        with self.assertRaises(NotRegistered):
            self.registry.unregister(name="testcomponent")


class MultipleComponentRegistriesTest(BaseTestCase):
    @parametrize_context_behavior(["django", "isolated"])
    def test_different_registries_have_different_settings(self):
        library_a = Library()
        registry_a = ComponentRegistry(
            library=library_a,
            settings=RegistrySettings(
                CONTEXT_BEHAVIOR=ContextBehavior.ISOLATED,
                TAG_FORMATTER=component_shorthand_formatter,
            ),
        )

        library_b = Library()
        registry_b = ComponentRegistry(
            library=library_b,
            settings=RegistrySettings(
                CONTEXT_BEHAVIOR=ContextBehavior.DJANGO,
                TAG_FORMATTER=component_formatter,
            ),
        )

        # NOTE: We cannot load the Libraries above using `{% load xxx %}` tag, because
        # for that we'd need to register a Django app and whatnot.
        # Instead, we insert the Libraries directly into the engine's builtins.
        engine = Engine.get_default()

        # Add the custom template tags to Django's built-in tags
        engine.template_builtins.append(library_a)
        engine.template_builtins.append(library_b)

        class SimpleComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                Variable: <strong>{{ variable }}</strong>
                Slot: {% slot "default" default / %}
            """

            def get_context_data(self, variable=None):
                return {
                    "variable": variable,
                }

        registry_a.register("simple_a", SimpleComponent)
        registry_b.register("simple_b", SimpleComponent)

        template_str: types.django_html = """
            {% simple_a variable=123 %}
                SLOT 123
            {% endsimple_a %}
            {% component "simple_b" variable=123 %}
                SLOT ABC
            {% endcomponent %}
        """
        template = Template(template_str)

        rendered = template.render(Context({}))

        self.assertHTMLEqual(
            rendered,
            """
            Variable: <strong>123</strong>
            Slot:
            SLOT 123

            Variable: <strong>123</strong>
            Slot:
            SLOT ABC
            """,
        )

        # Remove the custom template tags to clean up after tests
        engine.template_builtins.remove(library_a)
        engine.template_builtins.remove(library_b)


class ProtectedTagsTest(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.registry = ComponentRegistry()

    # NOTE: Use the `component_shorthand_formatter` formatter, so the components
    # are registered under that tag
    @override_settings(COMPONENTS={"tag_formatter": "django_components.component_shorthand_formatter"})
    def test_raises_on_overriding_our_tags(self):
        for tag in [
            "component_dependencies",
            "component_css_dependencies",
            "component_js_dependencies",
            "fill",
            "html_attrs",
            "provide",
            "slot",
        ]:
            with self.assertRaises(TagProtectedError):

                @register(tag)
                class TestComponent(Component):
                    pass

        @register("sth_else")
        class TestComponent2(Component):
            pass

        # Cleanup
        registry.unregister("sth_else")
