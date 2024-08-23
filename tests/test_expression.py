"""Catch-all for tests that use template tags and don't fit other files"""

from typing import Dict

from django.template import Context, Template
from django.template.base import Parser

from django_components.expression import safe_resolve_dict, safe_resolve_list

from .django_test_setup import setup_test_config
from .testutils import BaseTestCase

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
