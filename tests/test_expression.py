"""Catch-all for tests that use template tags and don't fit other files"""

from typing import Any, Dict

from django.template import Context, Template, TemplateSyntaxError
from django.template.base import FilterExpression, Node, Parser, Token

from django_components import Component, register, registry, types
from django_components.expression import DynamicFilterExpression, safe_resolve_dict, safe_resolve_list

from .django_test_setup import setup_test_config
from .testutils import BaseTestCase, parametrize_context_behavior

setup_test_config({"autodiscover": False})


engine = Template("").engine
default_parser = Parser("", engine.template_libraries, engine.template_builtins)


# A tag that just returns the value, so we can
# check if the value is stringified
class NoopNode(Node):
    def __init__(self, expr: FilterExpression):
        self.expr = expr

    def render(self, context: Context):
        return self.expr.resolve(context)


def noop(parser: Parser, token: Token):
    tag, raw_expr = token.split_contents()
    expr = parser.compile_filter(raw_expr)

    return NoopNode(expr)


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


# NOTE: Django calls the `{{ }}` syntax "variables" and `{% %}` "blocks"
class DynamicExprTests(BaseTestCase):
    def test_variable_resolve_dynamic_expr(self):
        expr = DynamicFilterExpression(default_parser, '"{{ var_a|lower }}"')

        ctx = make_context({"var_a": "LoREM"})
        self.assertEqual(expr.resolve(ctx), "lorem")

    def test_variable_raises_on_dynamic_expr_with_quotes_mismatch(self):
        with self.assertRaises(TemplateSyntaxError):
            DynamicFilterExpression(default_parser, "'{{ var_a|lower }}\"")

    @parametrize_context_behavior(["django", "isolated"])
    def test_variable_in_template(self):
        captured = {}

        @register("test")
        class SimpleComponent(Component):
            def get_context_data(
                self,
                pos_var1: Any,
                *args: Any,
                bool_var: bool,
                list_var: Dict,
            ):
                captured["pos_var1"] = pos_var1
                captured["bool_var"] = bool_var
                captured["list_var"] = list_var

                return {
                    "pos_var1": pos_var1,
                    "bool_var": bool_var,
                    "list_var": list_var,
                }

            template: types.django_html = """
                <div>{{ pos_var1 }}</div>
                <div>{{ bool_var }}</div>
                <div>{{ list_var|safe }}</div>
            """

        template_str: types.django_html = (
            """
            {% load component_tags %}
            {% component 'test'
                "{{ var_a|lower }}"
                bool_var="{{ is_active }}"
                list_var="{{ list|slice:':-1' }}"
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
                    "is_active": True,
                    "list": [{"a": 1}, {"a": 2}, {"a": 3}],
                }
            ),
        )

        # Check that variables passed to the component are of correct type
        self.assertEqual(captured["pos_var1"], "lorem")
        self.assertEqual(captured["bool_var"], True)
        self.assertEqual(captured["list_var"], [{"a": 1}, {"a": 2}])

        self.assertEqual(
            rendered.strip(),
            "<div>lorem</div>\n                <div>True</div>\n                <div>[{'a': 1}, {'a': 2}]</div>",
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_block_in_template(self):
        registry.library.tag(noop)
        captured = {}

        @register("test")
        class SimpleComponent(Component):
            def get_context_data(
                self,
                pos_var1: Any,
                *args: Any,
                bool_var: bool,
                list_var: Dict,
                dict_var: Dict,
            ):
                captured["pos_var1"] = pos_var1
                captured["bool_var"] = bool_var
                captured["list_var"] = list_var
                captured["dict_var"] = dict_var

                return {
                    "pos_var1": pos_var1,
                    "bool_var": bool_var,
                    "list_var": list_var,
                    "dict_var": dict_var,
                }

            template: types.django_html = """
                <div>{{ pos_var1 }}</div>
                <div>{{ bool_var }}</div>
                <div>{{ list_var|safe }}</div>
                <div>{{ dict_var|safe }}</div>
            """

        template_str: types.django_html = (
            """
            {% load component_tags %}
            {% component 'test'
                "{% lorem var_a w %}"
                bool_var="{% noop is_active %}"
                list_var="{% noop list %}"
                dict_var="{% noop dict %}"
            / %}
        """.replace(
                "\n", " "
            )
        )

        template = Template(template_str)
        rendered = template.render(
            Context(
                {
                    "var_a": 3,
                    "is_active": True,
                    "list": [{"a": 1}, {"a": 2}],
                    "dict": {"a": 3},
                }
            ),
        )

        # Check that variables passed to the component are of correct type
        self.assertEqual(captured["bool_var"], True)
        self.assertEqual(captured["dict_var"], {"a": 3})
        self.assertEqual(captured["list_var"], [{"a": 1}, {"a": 2}])

        self.assertEqual(
            rendered.strip(),
            "<div>lorem ipsum dolor</div>\n                <div>True</div>\n                <div>[{'a': 1}, {'a': 2}]</div>\n                <div>{'a': 3}</div>",  # noqa E501
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_comment_in_template(self):
        registry.library.tag(noop)
        captured = {}

        @register("test")
        class SimpleComponent(Component):
            def get_context_data(
                self,
                pos_var1: Any,
                pos_var2: Any,
                *args: Any,
                bool_var: bool,
                list_var: Dict,
            ):
                captured["pos_var1"] = pos_var1
                captured["pos_var2"] = pos_var2
                captured["bool_var"] = bool_var
                captured["list_var"] = list_var

                return {
                    "pos_var1": pos_var1,
                    "pos_var2": pos_var2,
                    "bool_var": bool_var,
                    "list_var": list_var,
                }

            template: types.django_html = """
                <div>{{ pos_var1 }}</div>
                <div>{{ pos_var2 }}</div>
                <div>{{ bool_var }}</div>
                <div>{{ list_var|safe }}</div>
            """

        template_str: types.django_html = (
            """
            {% load component_tags %}
            {% component 'test'
                "{# lorem var_a w #}"
                " {# lorem var_a w #} abc"
                bool_var="{# noop is_active #}"
                list_var=" {# noop list #} "
            / %}
        """.replace(
                "\n", " "
            )
        )

        template = Template(template_str)
        rendered = template.render(
            Context(
                {
                    "var_a": 3,
                    "is_active": True,
                    "list": [{"a": 1}, {"a": 2}],
                }
            ),
        )

        # Check that variables passed to the component are of correct type
        self.assertEqual(captured["pos_var1"], "")
        self.assertEqual(captured["pos_var2"], "  abc")
        self.assertEqual(captured["bool_var"], "")
        self.assertEqual(captured["list_var"], "  ")

        self.assertEqual(
            rendered.strip(),
            "<div></div>\n                <div>  abc</div>\n                <div></div>\n                <div>  </div>",  # noqa E501
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_mixed_in_template(self):
        registry.library.tag(noop)
        captured = {}

        @register("test")
        class SimpleComponent(Component):
            def get_context_data(
                self,
                pos_var1: Any,
                pos_var2: Any,
                *args: Any,
                bool_var: bool,
                list_var: Dict,
                dict_var: Dict,
            ):
                captured["pos_var1"] = pos_var1
                captured["bool_var"] = bool_var
                captured["list_var"] = list_var
                captured["dict_var"] = dict_var

                return {
                    "pos_var1": pos_var1,
                    "pos_var2": pos_var2,
                    "bool_var": bool_var,
                    "list_var": list_var,
                    "dict_var": dict_var,
                }

            template: types.django_html = """
                <div>{{ pos_var1 }}</div>
                <div>{{ pos_var2 }}</div>
                <div>{{ bool_var }}</div>
                <div>{{ list_var|safe }}</div>
                <div>{{ dict_var|safe }}</div>
            """

        template_str: types.django_html = (
            """
            {% load component_tags %}
            {% component 'test'
                " {% lorem var_a w %} "
                " {% lorem var_a w %} {{ list|slice:':-1' }} "
                bool_var=" {% noop is_active %} "
                list_var=" {% noop list %} "
                dict_var=" {% noop dict %} "
            / %}
        """.replace(
                "\n", " "
            )
        )

        template = Template(template_str)
        rendered = template.render(
            Context(
                {
                    "var_a": 3,
                    "is_active": True,
                    "list": [{"a": 1}, {"a": 2}],
                    "dict": {"a": 3},
                }
            ),
        )

        # Check that variables passed to the component are of correct type
        self.assertEqual(captured["bool_var"], " True ")
        self.assertEqual(captured["dict_var"], " {'a': 3} ")
        self.assertEqual(captured["list_var"], " [{'a': 1}, {'a': 2}] ")

        self.assertEqual(
            rendered.strip(),
            "<div> lorem ipsum dolor </div>\n                <div> lorem ipsum dolor [{&#x27;a&#x27;: 1}] </div>\n                <div> True </div>\n                <div> [{'a': 1}, {'a': 2}] </div>\n                <div> {'a': 3} </div>",  # noqa E501
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_ignores_invalid_tag(self):
        registry.library.tag(noop)

        @register("test")
        class SimpleComponent(Component):
            def get_context_data(
                self,
                pos_var1: Any,
                pos_var2: Any,
                *args: Any,
                bool_var: bool,
            ):
                return {
                    "pos_var1": pos_var1,
                    "pos_var2": pos_var2,
                    "bool_var": bool_var,
                }

            template: types.django_html = """
                <div>{{ pos_var1 }}</div>
                <div>{{ pos_var2 }}</div>
                <div>{{ bool_var }}</div>
            """

        template_str: types.django_html = (
            """
            {% load component_tags %}
            {% component 'test' '"' "{%}" bool_var="{% noop is_active %}" / %}
            """.replace(
                "\n", " "
            )
        )

        template = Template(template_str)
        rendered = template.render(
            Context({"is_active": True}),
        )

        self.assertEqual(
            rendered.strip(),
            '<div>"</div>\n                <div>{%}</div>\n                <div>True</div>',
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_nested_in_template(self):
        registry.library.tag(noop)

        @register("test")
        class SimpleComponent(Component):
            def get_context_data(
                self,
                pos_var1: Any,
                *args: Any,
                bool_var: bool,
            ):
                return {
                    "pos_var1": pos_var1,
                    "bool_var": bool_var,
                }

            template: types.django_html = """
                <div>{{ pos_var1 }}</div>
                <div>{{ bool_var }}</div>
            """

        template_str: types.django_html = (
            """
            {% load component_tags %}
            {% component 'test'
                "{% component 'test' '{{ var_a }}' bool_var=is_active / %}"
                bool_var="{% noop is_active %}"
            / %}
            """.replace(
                "\n", " "
            )
        )

        template = Template(template_str)
        rendered = template.render(
            Context(
                {
                    "var_a": 3,
                    "is_active": True,
                }
            ),
        )

        self.assertEqual(
            rendered.strip(),
            "<div>\n                <div>3</div>\n                <div>True</div>\n            </div>\n                <div>True</div>",  # noqa E501
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
                ..."{{ list|first }}"
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
                    "list": [{"a": 1}, {"a": 2}, {"a": 3}],
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
                    "list": [{"a": 1}, {"a": 2}, {"a": 3}],
                }

            template: types.django_html = """
                {% load component_tags %}
                {% slot "my_slot" ...my_dict ..."{{ list|first }}" x=123 default / %}
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
                    "list": [{"a": 1}, {"a": 2}, {"a": 3}],
                }

            template: types.django_html = """
                {% load component_tags %}
                {% slot "my_slot" ...my_dict ..."{{ list|first }}" x=123 default %}
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
            {% provide 'test' ...my_dict ..."{{ list|first }}" %}
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
                    "list": [{"a": 1}, {"a": 2}, {"a": 3}],
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
                ..."{{ list|first }}"
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
                    "list": [{"a": 1, "x": "OVERWRITTEN_X"}, {"a": 2}, {"a": 3}],
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
    def test_raises_if_positional_arg_after_spread(self):
        @register("test")
        class SimpleComponent(Component):
            pass

        template_str: types.django_html = (
            """
            {% load component_tags %}
            {% component 'test'
                ...my_dict
                var_a
                ..."{{ list|first }}"
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
        with self.assertRaisesMessage(
            RuntimeError, "Spread operator expression must resolve to a Dict, got [1, 2, 3]"
        ):
            template.render(
                Context(
                    {
                        "var_a": "abc",
                        "var_b": [1, 2, 3],
                    }
                )
            )

        # String
        with self.assertRaisesMessage(RuntimeError, "Spread operator expression must resolve to a Dict, got def"):
            template.render(
                Context(
                    {
                        "var_a": "abc",
                        "var_b": "def",
                    }
                )
            )
