from django.template import Context, Template
from django.template.base import Lexer, Parser

from django_components import Component, registry, types
from django_components.expression import (
    is_aggregate_key,
    process_aggregate_kwargs,
    safe_resolve_dict,
    safe_resolve_list,
)
from django_components.templatetags.component_tags import _parse_tag

from .django_test_setup import setup_test_config
from .testutils import BaseTestCase, parametrize_context_behavior

setup_test_config({"autodiscover": False})


class ParserTest(BaseTestCase):
    def test_parses_args_kwargs(self):
        template_str = "{% component 42 myvar key='val' key2=val2 %}"
        tokens = Lexer(template_str).tokenize()
        parser = Parser(tokens=tokens)
        tag = _parse_tag("component", parser, parser.tokens[0], params=["num", "var"], keywordonly_kwargs=True)

        ctx = {"myvar": {"a": "b"}, "val2": 1}
        args = safe_resolve_list(ctx, tag.args)
        named_args = safe_resolve_dict(ctx, tag.named_args)
        kwargs = tag.kwargs.resolve(ctx)

        self.assertListEqual(args, [42, {"a": "b"}])
        self.assertDictEqual(named_args, {"num": 42, "var": {"a": "b"}})
        self.assertDictEqual(kwargs, {"key": "val", "key2": 1})

    def test_parses_special_kwargs(self):
        template_str = "{% component date=date @lol=2 na-me=bzz @event:na-me.mod=bzz #my-id=True %}"
        tokens = Lexer(template_str).tokenize()
        parser = Parser(tokens=tokens)
        tag = _parse_tag("component", parser, parser.tokens[0], keywordonly_kwargs=True)

        ctx = Context({"date": 2024, "bzz": "fzz"})
        args = safe_resolve_list(ctx, tag.args)
        kwargs = tag.kwargs.resolve(ctx)

        self.assertListEqual(args, [])
        self.assertDictEqual(
            kwargs,
            {
                "@event": {"na-me.mod": "fzz"},
                "@lol": 2,
                "date": 2024,
                "na-me": "fzz",
                "#my-id": True,
            },
        )


class ParserComponentTest(BaseTestCase):
    class SimpleComponent(Component):
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
        registry.register("test", self.SimpleComponent)

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


class AggregateKwargsTest(BaseTestCase):
    def test_aggregate_kwargs(self):
        processed = process_aggregate_kwargs(
            {
                "attrs:@click.stop": "dispatch('click_event')",
                "attrs:x-data": "{hello: 'world'}",
                "attrs:class": "class_var",
                "my_dict:one": 2,
                "three": "four",
                ":placeholder": "No text",
            }
        )

        self.assertDictEqual(
            processed,
            {
                "attrs": {
                    "@click.stop": "dispatch('click_event')",
                    "x-data": "{hello: 'world'}",
                    "class": "class_var",
                },
                "my_dict": {"one": 2},
                "three": "four",
                ":placeholder": "No text",
            },
        )

    def is_aggregate_key(self):
        self.assertEqual(is_aggregate_key(""), False)
        self.assertEqual(is_aggregate_key(" "), False)
        self.assertEqual(is_aggregate_key(" : "), False)
        self.assertEqual(is_aggregate_key("attrs"), False)
        self.assertEqual(is_aggregate_key(":attrs"), False)
        self.assertEqual(is_aggregate_key(" :attrs "), False)
        self.assertEqual(is_aggregate_key("attrs:"), False)
        self.assertEqual(is_aggregate_key(":attrs:"), False)
        self.assertEqual(is_aggregate_key("at:trs"), True)
        self.assertEqual(is_aggregate_key(":at:trs"), False)
