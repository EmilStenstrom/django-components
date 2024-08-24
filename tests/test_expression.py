"""Catch-all for tests that use template tags and don't fit other files"""

from typing import Any, Dict

from django.template import Context, Template, TemplateSyntaxError
from django.template.base import Parser

from django_components import Component, register, types
from django_components.expression import safe_resolve_dict, safe_resolve_list

from .django_test_setup import setup_test_config
from .testutils import BaseTestCase, parametrize_context_behavior

setup_test_config({"autodiscover": False})


engine = Template("").engine
default_parser = Parser("", engine.template_libraries, engine.template_builtins)


def make_context(d: Dict):
    ctx = Context(d)
    ctx.template = Template("")
    return ctx


#######################
# TESTS
#######################


class ResolveTests(BaseTestCase):
    def test_safe_resolve(self):
        expr = default_parser.compile_filter("var_abc")

        ctx = make_context({"var_abc": 123})
        self.assertEqual(
            expr.resolve(ctx),
            123,
        )

        ctx2 = make_context({"var_xyz": 123})
        self.assertEqual(expr.resolve(ctx2), "")

    def test_safe_resolve_list(self):
        exprs = [default_parser.compile_filter(f"var_{char}") for char in "abc"]

        ctx = make_context({"var_a": 123, "var_b": [{}, {}]})
        self.assertEqual(
            safe_resolve_list(ctx, exprs),
            [123, [{}, {}], ""],
        )

    def test_safe_resolve_dict(self):
        exprs = {char: default_parser.compile_filter(f"var_{char}") for char in "abc"}

        ctx = make_context({"var_a": 123, "var_b": [{}, {}]})
        self.assertEqual(
            safe_resolve_dict(ctx, exprs),
            {"a": 123, "b": [{}, {}], "c": ""},
        )


class SpreadOperatorTests(BaseTestCase):
    @parametrize_context_behavior(["django", "isolated"])
    def test_component(self):
        captured = {}

        @register("test")
        class SimpleComponent(Component):
            def get_context_data(
                self,
                pos_var1: Any,
                *args: Any,
                **kwargs: Any,
            ):
                nonlocal captured
                captured = kwargs

                return {
                    "pos_var1": pos_var1,
                    **kwargs,
                }

            template: types.django_html = """
                <div>{{ pos_var1 }}</div>
                <div>{{ attrs }}</div>
                <div>{{ items }}</div>
                <div>{{ a }}</div>
                <div>{{ x }}</div>
            """

        template_str: types.django_html = (
            """
            {% load component_tags %}
            {% component 'test'
                var_a
                ...my_dict
                ...item
                x=123
            / %}
        """.replace(
                "\n", " "
            )
        )

        template = Template(template_str)
        rendered = template.render(
            Context(
                {
                    "var_a": "LoREM",
                    "my_dict": {
                        "attrs:@click": "() => {}",
                        "attrs:style": "height: 20px",
                        "items": [1, 2, 3],
                    },
                    "item": {"a": 1},
                }
            ),
        )

        # Check that variables passed to the component are of correct type
        self.assertEqual(captured["attrs"], {"@click": "() => {}", "style": "height: 20px"})
        self.assertEqual(captured["items"], [1, 2, 3])
        self.assertEqual(captured["a"], 1)
        self.assertEqual(captured["x"], 123)

        self.assertHTMLEqual(
            rendered,
            """
            <div>LoREM</div>
            <div>{'@click': '() =&gt; {}', 'style': 'height: 20px'}</div>
            <div>[1, 2, 3]</div>
            <div>1</div>
            <div>123</div>
            """,
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_slot(self):
        @register("test")
        class SimpleComponent(Component):
            def get_context_data(self):
                return {
                    "my_dict": {
                        "attrs:@click": "() => {}",
                        "attrs:style": "height: 20px",
                        "items": [1, 2, 3],
                    },
                    "item": {"a": 1},
                }

            template: types.django_html = """
                {% load component_tags %}
                {% slot "my_slot" ...my_dict ...item x=123 default / %}
            """

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test' %}
                {% fill "my_slot" data="slot_data" %}
                    {{ slot_data }}
                {% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        self.assertHTMLEqual(
            rendered,
            """
            {'items': [1, 2, 3], 'a': 1, 'x': 123, 'attrs': {'@click': '() =&gt; {}', 'style': 'height: 20px'}}
            """,
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_fill(self):
        @register("test")
        class SimpleComponent(Component):
            def get_context_data(self):
                return {
                    "my_dict": {
                        "attrs:@click": "() => {}",
                        "attrs:style": "height: 20px",
                        "items": [1, 2, 3],
                    },
                    "item": {"a": 1},
                }

            template: types.django_html = """
                {% load component_tags %}
                {% slot "my_slot" ...my_dict ...item x=123 default %}
                    __SLOT_DEFAULT__
                {% endslot %}
            """

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test' %}
                {% fill "my_slot" ...fill_data %}
                    {{ slot_data }}
                    {{ slot_default }}
                {% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(
            Context(
                {
                    "fill_data": {
                        "data": "slot_data",
                        "default": "slot_default",
                    },
                }
            ),
        )

        self.assertHTMLEqual(
            rendered,
            """
            {'items': [1, 2, 3], 'a': 1, 'x': 123, 'attrs': {'@click': '() =&gt; {}', 'style': 'height: 20px'}}
            __SLOT_DEFAULT__
            """,
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_provide(self):
        @register("test")
        class SimpleComponent(Component):
            def get_context_data(self):
                data = self.inject("test")
                return {
                    "attrs": data.attrs,
                    "items": data.items,
                    "a": data.a,
                }

            template: types.django_html = """
                {% load component_tags %}
                <div>{{ attrs }}</div>
                <div>{{ items }}</div>
                <div>{{ a }}</div>
            """

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide 'test' ...my_dict ...item %}
                {% component 'test' / %}
            {% endprovide %}
        """
        template = Template(template_str)
        rendered = template.render(
            Context(
                {
                    "my_dict": {
                        "attrs:@click": "() => {}",
                        "attrs:style": "height: 20px",
                        "items": [1, 2, 3],
                    },
                    "item": {"a": 1},
                }
            ),
        )

        self.assertHTMLEqual(
            rendered,
            """
            <div>{'@click': '() =&gt; {}', 'style': 'height: 20px'}</div>
            <div>[1, 2, 3]</div>
            <div>1</div>
            """,
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_html_attrs(self):
        template_str: types.django_html = """
            {% load component_tags %}
            <div {% html_attrs defaults:test="hi" ...my_dict attrs:lol="123" %}>
        """
        template = Template(template_str)
        rendered = template.render(
            Context(
                {
                    "my_dict": {
                        "attrs:style": "height: 20px",
                        "class": "button",
                        "defaults:class": "my-class",
                        "defaults:style": "NONO",
                    },
                }
            ),
        )
        self.assertHTMLEqual(
            rendered,
            """
            <div test="hi" class="my-class button" style="height: 20px" lol="123">
            """,
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_later_spreads_overwrite_earlier(self):
        @register("test")
        class SimpleComponent(Component):
            def get_context_data(
                self,
                *args: Any,
                **kwargs: Any,
            ):
                return {
                    **kwargs,
                }

            template: types.django_html = """
                <div>{{ attrs }}</div>
                <div>{{ items }}</div>
                <div>{{ a }}</div>
                <div>{{ x }}</div>
            """

        template_str: types.django_html = (
            """
            {% load component_tags %}
            {% component 'test'
                ...my_dict
                attrs:style="OVERWRITTEN"
                x=123
                ...item
            / %}
        """.replace(
                "\n", " "
            )
        )

        template = Template(template_str)
        rendered = template.render(
            Context(
                {
                    "my_dict": {
                        "attrs:@click": "() => {}",
                        "attrs:style": "height: 20px",
                        "items": [1, 2, 3],
                    },
                    "item": {"a": 1, "x": "OVERWRITTEN_X"},
                }
            ),
        )

        self.assertHTMLEqual(
            rendered,
            """
            <div>{'@click': '() =&gt; {}', 'style': 'OVERWRITTEN'}</div>
            <div>[1, 2, 3]</div>
            <div>1</div>
            <div>OVERWRITTEN_X</div>
            """,
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_raises_if_position_arg_after_spread(self):
        @register("test")
        class SimpleComponent(Component):
            pass

        template_str: types.django_html = (
            """
            {% load component_tags %}
            {% component 'test'
                ...my_dict
                var_a
                ...item
                x=123
            / %}
        """.replace(
                "\n", " "
            )
        )

        with self.assertRaisesMessage(
            TemplateSyntaxError, "'component' received some positional argument(s) after some keyword argument(s)"
        ):
            Template(template_str)

    @parametrize_context_behavior(["django", "isolated"])
    def test_raises_on_missing_value(self):
        @register("test")
        class SimpleComponent(Component):
            pass

        template_str: types.django_html = (
            """
            {% load component_tags %}
            {% component 'test'
                var_a
                ...
            / %}
        """.replace(
                "\n", " "
            )
        )

        with self.assertRaisesMessage(TemplateSyntaxError, "Syntax operator is missing a value"):
            Template(template_str)

    @parametrize_context_behavior(["django", "isolated"])
    def test_raises_on_non_dict(self):
        @register("test")
        class SimpleComponent(Component):
            pass

        template_str: types.django_html = (
            """
            {% load component_tags %}
            {% component 'test'
                var_a
                ...var_b
            / %}
        """.replace(
                "\n", " "
            )
        )

        template = Template(template_str)

        # List
        with self.assertRaisesMessage(AttributeError, "'list' object has no attribute 'items'"):
            template.render(
                Context(
                    {
                        "var_a": "abc",
                        "var_b": [1, 2, 3],
                    }
                )
            )

        # String
        with self.assertRaisesMessage(AttributeError, "'str' object has no attribute 'items'"):
            template.render(
                Context(
                    {
                        "var_a": "abc",
                        "var_b": "def",
                    }
                )
            )
