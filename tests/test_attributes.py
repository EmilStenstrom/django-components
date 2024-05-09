from django.template import Context, Template
from django.utils.safestring import SafeString, mark_safe

from django_components import component, types
from django_components.attributes import append_attributes, attributes_to_string

# isort: off
from .django_test_setup import *  # NOQA
from .testutils import BaseTestCase

# isort: on


class AttributesToStringTest(BaseTestCase):
    def test_simple_attribute(self):
        self.assertEqual(
            attributes_to_string({"foo": "bar"}),
            'foo="bar"',
        )

    def test_multiple_attributes(self):
        self.assertEqual(
            attributes_to_string({"class": "foo", "style": "color: red;"}),
            'class="foo" style="color: red;"',
        )

    def test_escapes_special_characters(self):
        self.assertEqual(
            attributes_to_string({"x-on:click": "bar", "@click": "'baz'"}),
            'x-on:click="bar" @click="&#x27;baz&#x27;"',
        )

    def test_does_not_escape_special_characters_if_safe_string(self):
        self.assertEqual(
            attributes_to_string({"foo": mark_safe("'bar'")}),
            "foo=\"'bar'\"",
        )

    def test_result_is_safe_string(self):
        result = attributes_to_string({"foo": mark_safe("'bar'")})
        self.assertTrue(type(result) == SafeString)

    def test_attribute_with_no_value(self):
        self.assertEqual(
            attributes_to_string({"required": None}),
            "",
        )

    def test_attribute_with_false_value(self):
        self.assertEqual(
            attributes_to_string({"required": False}),
            "",
        )

    def test_attribute_with_true_value(self):
        self.assertEqual(
            attributes_to_string({"required": True}),
            "required",
        )


class AppendAttributesTest(BaseTestCase):
    def test_single_dict(self):
        self.assertEqual(
            append_attributes(("foo", "bar")),
            {"foo": "bar"},
        )

    def test_appends_dicts(self):
        self.assertEqual(
            append_attributes(("class", "foo"), ("id", "bar"), ("class", "baz")),
            {"class": "foo baz", "id": "bar"},
        )


class HtmlAttrsTests(BaseTestCase):
    def test_attrs_tag(self):
        @component.register("test")
        class AttrsComponent(component.Component):
            template: types.django_html = """
                {% load component_tags %}
                <div {% html_attrs attrs class="override-me" add::class="added_class" add::class="another-class" data-id=123 %}>
                    content
                </div>
            """

            def get_context_data(self, *args, attrs):
                return {"attrs": attrs}

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "test" attrs::@click.stop="dispatch('click_event')" attrs::x-data="{hello: 'world'}" attrs::class=class_var %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"class_var": "padding-top-8"}))
        self.assertHTMLEqual(
            rendered,
            """
            <div @click.stop="dispatch('click_event')" x-data="{hello: 'world'}" class="padding-top-8 added_class another-class" data-id=123>
                content
            </div>
            """,
        )
        self.assertNotIn("override-me", rendered)
