from django.template import Context, Template
from django.template.base import Parser

# isort: off
from .django_test_setup import *  # NOQA
from .testutils import BaseTestCase, parametrize_context_behavior

# isort: on

from django_components import component, types
from django_components.component import safe_resolve_dict, safe_resolve_list
from django_components.templatetags.component_tags import _parse_component_with_args


class ParserTest(BaseTestCase):
    def test_parses_args_kwargs(self):
        bits = ["component", "my_component", "42", "myvar", "key='val'", "key2=val2"]
        name, raw_args, raw_kwargs = _parse_component_with_args(Parser(""), bits, "component")

        ctx = {"myvar": {"a": "b"}, "val2": 1}
        args = safe_resolve_list(raw_args, ctx)
        kwargs = safe_resolve_dict(raw_kwargs, ctx)

        self.assertEqual(name, "my_component")
        self.assertListEqual(args, [42, {"a": "b"}])
        self.assertDictEqual(kwargs, {"key": "val", "key2": 1})

    def test_parses_special_kwargs(self):
        bits = [
            "component",
            "my_component",
            "date=date",
            "@lol=2",
            "na-me=bzz",
            "@event:na-me.mod=bzz",
            "#my-id=True",
        ]
        name, raw_args, raw_kwargs = _parse_component_with_args(Parser(""), bits, "component")

        ctx = Context({"date": 2024, "bzz": "fzz"})
        args = safe_resolve_list(raw_args, ctx)
        kwargs = safe_resolve_dict(raw_kwargs, ctx)

        self.assertEqual(name, "my_component")
        self.assertListEqual(args, [])
        self.assertDictEqual(
            kwargs,
            {
                "@event:na-me.mod": "fzz",
                "@lol": 2,
                "date": 2024,
                "na-me": "fzz",
                "#my-id": True,
            },
        )


class ParserComponentTest(BaseTestCase):
    class SimpleComponent(component.Component):
        template: types.django_html = """
            {{ date }}
            {{ id }}
            {{ on_click }}
        """

        def get_context_data(self, **kwargs):
            return {
                "date": kwargs["my-date"],
                "id": kwargs["#some_id"],
                "on_click": kwargs["@click.native"],
            }

    @parametrize_context_behavior(["django", "isolated"])
    def test_special_chars_accessible_via_kwargs(self):
        component.registry.register("test", self.SimpleComponent)

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "test" my-date="2015-06-19" @click.native=do_something #some_id=True %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"do_something": "abc"}))
        self.assertHTMLEqual(
            rendered,
            """
            2015-06-19
            True
            abc
            """,
        )
