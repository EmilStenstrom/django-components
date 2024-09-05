from django.template import Context, Template
from django.test import override_settings

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

    @override_settings(COMPONENTS={"template_cache_size": 2})
    def test_cache_discards_old_entries(self):
        template_1 = cached_template("Variable: <strong>{{ variable }}</strong>")
        template_1._test_id = "123"

        template_2 = cached_template("Variable2")
        template_2._test_id = "456"

        # Templates 1 and 2 should still be available
        template_1_copy = cached_template("Variable: <strong>{{ variable }}</strong>")
        self.assertEqual(template_1_copy._test_id, "123")

        template_2_copy = cached_template("Variable2")
        self.assertEqual(template_2_copy._test_id, "456")

        # But once we add the third template, template 1 should go
        cached_template("Variable3")

        template_1_copy2 = cached_template("Variable: <strong>{{ variable }}</strong>")
        self.assertEqual(hasattr(template_1_copy2, "_test_id"), False)

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
        template_1 = comp._get_template(Context({}))
        template_1._test_id = "123"

        template_2 = comp._get_template(Context({}))
        self.assertEqual(template_2._test_id, "123")
