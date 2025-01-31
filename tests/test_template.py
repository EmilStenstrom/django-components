from django.template import Context, Template

from django_components import Component, cached_template, types

from .django_test_setup import setup_test_config
from .testutils import BaseTestCase

setup_test_config({"autodiscover": False})


class TemplateCacheTest(BaseTestCase):
    def test_cached_template(self):
        template_1 = cached_template("Variable: <strong>{{ variable }}</strong>")
        template_1._test_id = "123"

        template_2 = cached_template("Variable: <strong>{{ variable }}</strong>")

        self.assertEqual(template_2._test_id, "123")

    def test_cached_template_accepts_class(self):
        class MyTemplate(Template):
            pass

        template = cached_template("Variable: <strong>{{ variable }}</strong>", MyTemplate)
        self.assertIsInstance(template, MyTemplate)

    def test_component_template_is_cached(self):
        class SimpleComponent(Component):
            def get_template(self, context):
                content: types.django_html = """
                    Variable: <strong>{{ variable }}</strong>
                """
                return content

            def get_context_data(self, variable=None):
                return {
                    "variable": variable,
                }

        comp = SimpleComponent()
        template_1 = comp._get_template(Context({}), component_id="123")
        template_1._test_id = "123"

        template_2 = comp._get_template(Context({}), component_id="123")
        self.assertEqual(template_2._test_id, "123")
