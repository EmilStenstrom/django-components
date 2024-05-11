from django.template import Context, Template, TemplateSyntaxError
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
        self.assertTrue(isinstance(result, SafeString))

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
    def setUp(self):
        super().setUp()

        self.template_str: types.django_html = """
            {% load component_tags %}
            {% component "test" attrs:@click.stop="dispatch('click_event')" attrs:x-data="{hello: 'world'}" attrs:class=class_var %}
            {% endcomponent %}
        """  # noqa: E501

    def test_tag_positional_args(self):
        @component.register("test")
        class AttrsComponent(component.Component):
            template: types.django_html = """
                {% load component_tags %}
                <div {% html_attrs attrs defaults class="added_class" class="another-class" data-id=123 %}>
                    content
                </div>
            """  # noqa: E501

            def get_context_data(self, *args, attrs):
                return {
                    "attrs": attrs,
                    "defaults": {"class": "override-me"},
                }

        template = Template(self.template_str)
        rendered = template.render(Context({"class_var": "padding-top-8"}))
        self.assertHTMLEqual(
            rendered,
            """
            <div @click.stop="dispatch('click_event')" x-data="{hello: 'world'}" class="padding-top-8 added_class another-class" data-id=123>
                content
            </div>
            """,  # noqa: E501
        )
        self.assertNotIn("override-me", rendered)

    def test_tag_raises_on_extra_positional_args(self):
        @component.register("test")
        class AttrsComponent(component.Component):
            template: types.django_html = """
                {% load component_tags %}
                <div {% html_attrs attrs defaults class %}>
                    content
                </div>
            """  # noqa: E501

            def get_context_data(self, *args, attrs):
                return {
                    "attrs": attrs,
                    "defaults": {"class": "override-me"},
                    "class": "123 457",
                }

        template = Template(self.template_str)

        with self.assertRaisesMessage(
            TemplateSyntaxError, "Tag 'html_attrs' received unexpected positional arguments"
        ):
            template.render(Context({"class_var": "padding-top-8"}))

    def test_tag_kwargs(self):
        @component.register("test")
        class AttrsComponent(component.Component):
            template: types.django_html = """
                {% load component_tags %}
                <div {% html_attrs attrs=attrs defaults=defaults class="added_class" class="another-class" data-id=123 %}>
                    content
                </div>
            """  # noqa: E501

            def get_context_data(self, *args, attrs):
                return {
                    "attrs": attrs,
                    "defaults": {"class": "override-me"},
                }

        template = Template(self.template_str)
        rendered = template.render(Context({"class_var": "padding-top-8"}))
        self.assertHTMLEqual(
            rendered,
            """
            <div @click.stop="dispatch('click_event')" class="added_class another-class padding-top-8" data-id="123" x-data="{hello: 'world'}">
                content
            </div>
            """,  # noqa: E501
        )
        self.assertNotIn("override-me", rendered)

    def test_tag_kwargs_2(self):
        @component.register("test")
        class AttrsComponent(component.Component):
            template: types.django_html = """
                {% load component_tags %}
                <div {% html_attrs class="added_class" class="another-class" data-id=123 defaults=defaults attrs=attrs %}>
                    content
                </div>
            """  # noqa: E501

            def get_context_data(self, *args, attrs):
                return {
                    "attrs": attrs,
                    "defaults": {"class": "override-me"},
                }

        template = Template(self.template_str)
        rendered = template.render(Context({"class_var": "padding-top-8"}))
        self.assertHTMLEqual(
            rendered,
            """
            <div @click.stop="dispatch('click_event')" x-data="{hello: 'world'}" class="padding-top-8 added_class another-class" data-id=123>
                content
            </div>
            """,  # noqa: E501
        )
        self.assertNotIn("override-me", rendered)

    def test_tag_aggregate_args(self):
        @component.register("test")
        class AttrsComponent(component.Component):
            template: types.django_html = """
                {% load component_tags %}
                <div {% html_attrs attrs:class="from_agg_key" attrs:type="submit" defaults:class="override-me" class="added_class" class="another-class" data-id=123 %}>
                    content
                </div>
            """  # noqa: E501

            def get_context_data(self, *args, attrs):
                return {"attrs": attrs}

        template = Template(self.template_str)
        rendered = template.render(Context({"class_var": "padding-top-8"}))

        # NOTE: The attrs from self.template_str should be ignored because they are not used.
        self.assertHTMLEqual(
            rendered,
            """
            <div class="added_class another-class from_agg_key" data-id="123" type="submit">
                content
            </div>
            """,  # noqa: E501
        )
        self.assertNotIn("override-me", rendered)

    def test_tag_raises_on_aggregate_and_positional_args_for_attrs(self):
        @component.register("test")
        class AttrsComponent(component.Component):
            template: types.django_html = """
                {% load component_tags %}
                <div {% html_attrs attrs attrs:class="from_agg_key" defaults:class="override-me" class="added_class" class="another-class" data-id=123 %}>
                    content
                </div>
            """  # noqa: E501

            def get_context_data(self, *args, attrs):
                return {"attrs": attrs}

        template = Template(self.template_str)
        with self.assertRaisesMessage(TemplateSyntaxError, "Received argument 'attrs' both as a regular input"):
            template.render(Context({"class_var": "padding-top-8"}))

    def test_tag_raises_on_aggregate_and_positional_args_for_defaults(self):
        @component.register("test")
        class AttrsComponent(component.Component):
            template: types.django_html = """
                {% load component_tags %}
                <div {% html_attrs defaults=defaults attrs:class="from_agg_key" defaults:class="override-me" class="added_class" class="another-class" data-id=123 %}>
                    content
                </div>
            """  # noqa: E501

            def get_context_data(self, *args, attrs):
                return {"attrs": attrs}

        template = Template(self.template_str)
        with self.assertRaisesMessage(
            TemplateSyntaxError,
            "Received argument 'defaults' both as a regular input",
        ):
            template.render(Context({"class_var": "padding-top-8"}))

    def test_tag_no_attrs(self):
        @component.register("test")
        class AttrsComponent(component.Component):
            template: types.django_html = """
                {% load component_tags %}
                <div {% html_attrs defaults:class="override-me" class="added_class" class="another-class" data-id=123 %}>
                    content
                </div>
            """  # noqa: E501

            def get_context_data(self, *args, attrs):
                return {"attrs": attrs}

        template = Template(self.template_str)
        rendered = template.render(Context({"class_var": "padding-top-8"}))
        self.assertHTMLEqual(
            rendered,
            """
            <div class="added_class another-class" data-id=123>
                content
            </div>
            """,
        )
        self.assertNotIn("override-me", rendered)

    def test_tag_no_defaults(self):
        @component.register("test")
        class AttrsComponent(component.Component):
            template: types.django_html = """
                {% load component_tags %}
                <div {% html_attrs attrs class="added_class" class="another-class" data-id=123 %}>
                    content
                </div>
            """  # noqa: E501

            def get_context_data(self, *args, attrs):
                return {"attrs": attrs}

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "test" attrs:@click.stop="dispatch('click_event')" attrs:x-data="{hello: 'world'}" attrs:class=class_var %}
            {% endcomponent %}
        """  # noqa: E501
        template = Template(template_str)
        rendered = template.render(Context({"class_var": "padding-top-8"}))
        self.assertHTMLEqual(
            rendered,
            """
            <div @click.stop="dispatch('click_event')" x-data="{hello: 'world'}" class="padding-top-8 added_class another-class" data-id=123>
                content
            </div>
            """,  # noqa: E501
        )
        self.assertNotIn("override-me", rendered)

    def test_tag_no_attrs_no_defaults(self):
        @component.register("test")
        class AttrsComponent(component.Component):
            template: types.django_html = """
                {% load component_tags %}
                <div {% html_attrs class="added_class" class="another-class" data-id=123 %}>
                    content
                </div>
            """  # noqa: E501

            def get_context_data(self, *args, attrs):
                return {"attrs": attrs}

        template = Template(self.template_str)
        rendered = template.render(Context({"class_var": "padding-top-8"}))
        self.assertHTMLEqual(
            rendered,
            """
            <div class="added_class another-class" data-id="123">
                content
            </div>
            """,
        )
        self.assertNotIn("override-me", rendered)

    def test_tag_empty(self):
        @component.register("test")
        class AttrsComponent(component.Component):
            template: types.django_html = """
                {% load component_tags %}
                <div {% html_attrs %}>
                    content
                </div>
            """

            def get_context_data(self, *args, attrs):
                return {
                    "attrs": attrs,
                    "defaults": {"class": "override-me"},
                }

        template = Template(self.template_str)
        rendered = template.render(Context({"class_var": "padding-top-8"}))
        self.assertHTMLEqual(
            rendered,
            """
            <div >
                content
            </div>
            """,
        )
        self.assertNotIn("override-me", rendered)
