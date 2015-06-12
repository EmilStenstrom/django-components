from textwrap import dedent
import unittest
import django
from django.conf import settings
from django_components import component

class SimpleComponent(component.Component):
    def context(self, variable=None):
        return {
            "variable": variable,
        }

    class Media:
        template = "simple_template.html"
        css = {"all": "style.css"}
        js = ("script.js",)

class ComponentRegistryTest(unittest.TestCase):
    def setUp(self):
        settings.configure(
            TEMPLATES=[{
                'BACKEND': 'django.template.backends.django.DjangoTemplates',
                'DIRS': ["tests/templates/"],
            }]
        )
        django.setup()

    def test_simple_component(self):
        comp = SimpleComponent()

        self.assertEqual(comp.render_dependencies(), dedent("""
            <link href="style.css" type="text/css" media="all" rel="stylesheet" />
            <script type="text/javascript" src="script.js"></script>
        """).strip())

        self.assertEqual(comp.render(variable="test"), dedent("""
            Variable: <strong>test</strong>
        """).lstrip())
