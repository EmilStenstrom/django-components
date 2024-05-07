from django.template import Template, Context
from django.utils.safestring import mark_safe, SafeString

from django_components.attributes import (
    attributes_to_string,
    merge_attributes,
    normalize_html_class,
    append_attributes,
)
from django_components import component, types

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


class MergeAttributesTest(BaseTestCase):
    def test_merges_attributes(self):
        self.assertEqual(
            merge_attributes({"foo": "bar"}, {"bar": "baz"}),
            {"foo": "bar", "bar": "baz"},
        )

    def test_overwrites_attributes(self):
        self.assertEqual(
            merge_attributes({"foo": "bar"}, {"foo": "baz", "data": "foo"}),
            {"foo": "baz", "data": "foo"},
        )

    def test_normalizes_classes(self):
        self.assertEqual(
            merge_attributes({"foo": "bar", "class": "baz"}, {"class": "qux"}),
            {"foo": "bar", "class": "baz qux"},
        )

    def test_merge_multiple_dicts(self):
        self.assertEqual(
            merge_attributes(
                {"foo": "bar"},
                {"class": "baz"},
                {"id": "qux"},
            ),
            {"foo": "bar", "class": "baz", "id": "qux"},
        )


class AppendAttributesTest(BaseTestCase):
    def test_single_dict(self):
        self.assertEqual(
            append_attributes({"foo": "bar"}),
            {"foo": "bar"},
        )

    def test_appends_dicts(self):
        self.assertEqual(
            append_attributes({"class": "foo"}, {"id": "bar"}, {"class": "baz"}),
            {"class": "foo baz", "id": "bar"},
        )


class NormalizeClassTest(BaseTestCase):
    def test_str(self):
        self.assertEqual(
            normalize_html_class("foo"),
            "foo",
        )

    def test_list(self):
        self.assertEqual(
            normalize_html_class(["foo", "bar"]),
            "foo bar",
        )

    def test_nested_list(self):
        self.assertEqual(
            normalize_html_class(["foo", ["bar", "baz"]]),
            "foo bar baz",
        )

    def test_tuple(self):
        self.assertEqual(
            normalize_html_class(("foo", "bar")),
            "foo bar",
        )

    def test_dict(self):
        self.assertEqual(
            normalize_html_class({"foo": True, "bar": False, "baz": None}),
            "foo",
        )

    def test_combined(self):
        self.assertEqual(
            normalize_html_class(
                [
                    "class1",
                    ["class2", "class3"],
                    {
                        "class4": True,
                        "class5": False,
                        "class6": "foo",
                    },
                ]
            ),
            "class1 class2 class3 class4 class6",
        )


class AttrsInTemplateTests(BaseTestCase):
    def test_attrs_accessible_in_template(self):
        @component.register("test")
        class AttrsComponent(component.Component):
            template: types.django_html = """
                {% load component_tags %}
                <div {{ component_vars.attrs }} >
                </div>
            """

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "test" attrs:@click.stop="dispatch('click_event')" attrs:x-data="{hello: 'world'}" attrs:class=class_var %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"class_var": "padding-top-8"}))
        self.assertHTMLEqual(
            rendered,
            """
            <div @click.stop="dispatch('click_event')" x-data="{hello: 'world'}" class="padding-top-8" >
            </div>
            """,
        )

    def test_attrs_accessible_in_get_context_data(self):
        @component.register("test")
        class AttrsComponent(component.Component):
            template: types.django_html = """
                {% load component_tags %}
                <div {{ attrs }} >
                </div>
            """

            def get_context_data(self, *args, attrs):
                return {"attrs": attrs}

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "test" attrs:@click.stop="dispatch('click_event')" attrs:x-data="{hello: 'world'}" attrs:class=class_var %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"class_var": "padding-top-8"}))
        self.assertHTMLEqual(
            rendered,
            """
            <div @click.stop="dispatch('click_event')" x-data="{hello: 'world'}" class="padding-top-8" >
            </div>
            """,
        )

    def test_attrs_immutable(self):
        @component.register("test")
        class AttrsComponent(component.Component):
            template: types.django_html = """
                {% load component_tags %}
                <div {{ attrs }} >
                </div>
            """

            def get_context_data(self, *args, attrs):
                attrs["my_super_key"] = "abc"
                return {"attrs": attrs}

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "test" attrs:@click.stop="dispatch('click_event')" attrs:x-data="{hello: 'world'}" attrs:class=class_var %}
            {% endcomponent %}
        """
        template = Template(template_str)
        with self.assertRaisesMessage(TypeError, "cannot change object - object is immutable"):
            template.render(Context({"class_var": "padding-top-8"}))

    def test_attrs_tag(self):
        @component.register("test")
        class AttrsComponent(component.Component):
            template: types.django_html = """
                {% load component_tags %}
                <div {% merge_attrs component_vars.attrs class+="added_class" data-id=123 %}>
                    content
                </div>
            """

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "test" attrs:@click.stop="dispatch('click_event')" attrs:x-data="{hello: 'world'}" attrs:class=class_var %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"class_var": "padding-top-8"}))
        self.assertHTMLEqual(
            rendered,
            """
            <div @click.stop="dispatch('click_event')" x-data="{hello: 'world'}" class="padding-top-8 added_class" data-id=123>
                content
            </div>
            """,
        )
