"""
Here we check that the logic around dependency rendering outputs correct HTML.
During actual rendering, the HTML is then picked up by the JS-side dependency manager.
"""

import re

from django.template import Template

from django_components import Component, registry, types

from .django_test_setup import setup_test_config
from .testutils import BaseTestCase, create_and_process_template_response

setup_test_config({"autodiscover": False})


def to_spaces(s: str):
    return re.compile(r"\s+").sub(" ", s)


class SimpleComponent(Component):
    template: types.django_html = """
        Variable: <strong>{{ variable }}</strong>
    """

    def get_context_data(self, variable, variable2="default"):
        return {
            "variable": variable,
            "variable2": variable2,
        }

    class Media:
        css = "style.css"
        js = "script.js"


class SimpleComponentNested(Component):
    template: types.django_html = """
        {% load component_tags %}
        <div>
            {% component "inner" variable=variable / %}
            {% slot "default" default / %}
        </div>
    """

    css: types.css = """
        .my-class {
            color: red;
        }
    """

    js: types.js = """
        console.log("Hello");
    """

    def get_context_data(self, variable):
        return {}

    class Media:
        css = ["style.css", "style2.css"]
        js = "script2.js"


class OtherComponent(Component):
    template: types.django_html = """
        XYZ: <strong>{{ variable }}</strong>
    """

    css: types.css = """
        .xyz {
            color: red;
        }
    """

    js: types.js = """
        console.log("xyz");
    """

    def get_context_data(self, variable):
        return {}

    class Media:
        css = "xyz1.css"
        js = "xyz1.js"


class SimpleComponentWithSharedDependency(Component):
    template: types.django_html = """
        Variable: <strong>{{ variable }}</strong>
    """

    def get_context_data(self, variable, variable2="default"):
        return {}

    class Media:
        css = ["style.css", "style2.css"]
        js = ["script.js", "script2.js"]


class MultistyleComponent(Component):
    template: types.django_html = """
        Variable: <strong>{{ variable }}</strong>
    """

    class Media:
        css = ["style.css", "style2.css"]
        js = ["script.js", "script2.js"]


class DependencyRenderingTests(BaseTestCase):
    def test_no_dependencies_when_no_components_used(self):
        registry.register(name="test", component=SimpleComponent)

        template_str: types.django_html = """
            {% load component_tags %}
            {% component_js_dependencies %}
            {% component_css_dependencies %}
        """
        template = Template(template_str)
        rendered = create_and_process_template_response(template)

        # Dependency manager script
        self.assertInHTML('<script src="django_components/django_components.min.js"></script>', rendered, count=1)

        self.assertEqual(rendered.count("<script"), 1)  # 1 boilerplate script
        self.assertEqual(rendered.count("<link"), 0)  # No CSS
        self.assertEqual(rendered.count("<style"), 0)

        self.assertNotIn("loadedJsUrls", rendered)
        self.assertNotIn("loadedCssUrls", rendered)
        self.assertNotIn("toLoadJsTags", rendered)
        self.assertNotIn("toLoadCssTags", rendered)

    def test_no_js_dependencies_when_no_components_used(self):
        registry.register(name="test", component=SimpleComponent)

        template_str: types.django_html = """
            {% load component_tags %}{% component_js_dependencies %}
        """
        template = Template(template_str)
        rendered = create_and_process_template_response(template)

        # Dependency manager script
        self.assertInHTML('<script src="django_components/django_components.min.js"></script>', rendered, count=1)

        self.assertEqual(rendered.count("<script"), 1)  # 1 boilerplate script
        self.assertEqual(rendered.count("<link"), 0)  # No CSS
        self.assertEqual(rendered.count("<style"), 0)

        self.assertNotIn("loadedJsUrls", rendered)
        self.assertNotIn("loadedCssUrls", rendered)
        self.assertNotIn("toLoadJsTags", rendered)
        self.assertNotIn("toLoadCssTags", rendered)

    def test_no_css_dependencies_when_no_components_used(self):
        registry.register(name="test", component=SimpleComponent)

        template_str: types.django_html = """
            {% load component_tags %}{% component_css_dependencies %}
        """
        template = Template(template_str)
        rendered = create_and_process_template_response(template)

        self.assertEqual(rendered.count("<script"), 0)  # No JS
        self.assertEqual(rendered.count("<link"), 0)  # No CSS
        self.assertEqual(rendered.count("<style"), 0)

    def test_single_component_dependencies(self):
        registry.register(name="test", component=SimpleComponent)

        template_str: types.django_html = """
            {% load component_tags %}
            {% component_js_dependencies %}
            {% component_css_dependencies %}
            {% component 'test' variable='foo' / %}
        """
        template = Template(template_str)
        rendered = create_and_process_template_response(template)

        # Dependency manager script
        self.assertInHTML('<script src="django_components/django_components.min.js"></script>', rendered, count=1)

        self.assertEqual(rendered.count('<link href="style.css" media="all" rel="stylesheet">'), 1)  # Media.css
        self.assertEqual(rendered.count("<link"), 1)
        self.assertEqual(rendered.count("<style"), 0)
        self.assertEqual(rendered.count("<script"), 3)

        self.assertInHTML(
            """
            <script type="application/json" data-djc>
                {"loadedCssUrls": ["style.css"],
                "loadedJsUrls": ["script.js"],
                "toLoadCssTags": [],
                "toLoadJsTags": []}
            </script>
            """,
            rendered,
            count=1,
        )

    def test_single_component_with_dash_or_slash_in_name(self):
        registry.register(name="te-s/t", component=SimpleComponent)

        template_str: types.django_html = """
            {% load component_tags %}
            {% component_js_dependencies %}
            {% component_css_dependencies %}
            {% component 'te-s/t' variable='foo' / %}
        """
        template = Template(template_str)
        rendered = create_and_process_template_response(template)

        # Dependency manager script
        self.assertInHTML('<script src="django_components/django_components.min.js"></script>', rendered, count=1)

        self.assertEqual(rendered.count('<link href="style.css" media="all" rel="stylesheet">'), 1)  # Media.css
        self.assertEqual(rendered.count("<link"), 1)
        self.assertEqual(rendered.count("<style"), 0)
        self.assertEqual(rendered.count("<script"), 3)

        self.assertInHTML(
            """
            <script type="application/json" data-djc>
                {"loadedCssUrls": ["style.css"],
                "loadedJsUrls": ["script.js"],
                "toLoadCssTags": [],
                "toLoadJsTags": []}
            </script>
            """,
            rendered,
            count=1,
        )

    def test_single_component_placeholder_removed(self):
        registry.register(name="test", component=SimpleComponent)

        template_str: types.django_html = """
            {% load component_tags %}
            {% component_js_dependencies %}
            {% component_css_dependencies %}
            {% component 'test' variable='foo' / %}
        """
        template = Template(template_str)
        rendered = create_and_process_template_response(template)

        self.assertNotIn("_RENDERED", rendered)

    def test_single_component_css_dependencies(self):
        registry.register(name="test", component=SimpleComponent)

        template_str: types.django_html = """
            {% load component_tags %}{% component_css_dependencies %}
            {% component 'test' variable='foo' / %}
        """
        template = Template(template_str)
        rendered = create_and_process_template_response(template)

        # Dependency manager script - NOT present
        self.assertInHTML('<script src="django_components/django_components.min.js"></script>', rendered, count=0)

        self.assertEqual(rendered.count("<link"), 1)
        self.assertEqual(rendered.count("<style"), 0)
        self.assertEqual(rendered.count("<script"), 0)  # No JS scripts

        self.assertEqual(rendered.count('<link href="style.css" media="all" rel="stylesheet">'), 1)  # Media.css

    def test_single_component_js_dependencies(self):
        registry.register(name="test", component=SimpleComponent)

        template_str: types.django_html = """
            {% load component_tags %}{% component_js_dependencies %}
            {% component 'test' variable='foo' %}{% endcomponent %}
        """
        template = Template(template_str)
        rendered = create_and_process_template_response(template)

        # Dependency manager script
        self.assertInHTML('<script src="django_components/django_components.min.js"></script>', rendered, count=1)

        # CSS NOT included
        self.assertEqual(rendered.count("<link"), 0)
        self.assertEqual(rendered.count("<style"), 0)
        self.assertEqual(rendered.count("<script"), 3)

        self.assertInHTML(
            """
            <script type="application/json" data-djc>
                {"loadedCssUrls": ["style.css"],
                "loadedJsUrls": ["script.js"],
                "toLoadCssTags": [],
                "toLoadJsTags": []}
            </script>
            """,
            rendered,
            count=1,
        )

    def test_all_dependencies_are_rendered_for_component_with_multiple_dependencies(
        self,
    ):
        registry.register(name="test", component=MultistyleComponent)
        template_str: types.django_html = """
            {% load component_tags %}
            {% component_js_dependencies %}
            {% component_css_dependencies %}
            {% component 'test' / %}
        """
        template = Template(template_str)
        rendered = create_and_process_template_response(template)

        # Dependency manager script
        self.assertInHTML('<script src="django_components/django_components.min.js"></script>', rendered, count=1)

        self.assertEqual(rendered.count("<link"), 2)
        self.assertEqual(rendered.count("<style"), 0)
        self.assertEqual(rendered.count("<script"), 4)  # 2 scripts belong to the boilerplate

        # Media.css
        self.assertInHTML(
            """
            <link href="style.css" media="all" rel="stylesheet">
            <link href="style2.css" media="all" rel="stylesheet">
            """,
            rendered,
            count=1,
        )

        # Media.js
        self.assertInHTML(
            """
            <script src="script.js"></script>
            <script src="script2.js"></script>
            """,
            rendered,
            count=1,
        )

        self.assertInHTML(
            """
            <script type="application/json" data-djc>
                {"loadedCssUrls": ["style.css", "style2.css"],
                "loadedJsUrls": ["script.js", "script2.js"],
                "toLoadCssTags": [],
                "toLoadJsTags": []}
            </script>
            """,
            rendered,
            count=1,
        )

    def test_no_dependencies_with_multiple_unused_components(self):
        registry.register(name="inner", component=SimpleComponent)
        registry.register(name="outer", component=SimpleComponentNested)

        template_str: types.django_html = """
            {% load component_tags %}
            {% component_js_dependencies %}
            {% component_css_dependencies %}
        """
        template = Template(template_str)
        rendered = create_and_process_template_response(template)

        # Dependency manager script
        self.assertInHTML('<script src="django_components/django_components.min.js"></script>', rendered, count=1)

        self.assertEqual(rendered.count("<script"), 1)  # 1 boilerplate script
        self.assertEqual(rendered.count("<link"), 0)  # No CSS
        self.assertEqual(rendered.count("<style"), 0)

        self.assertNotIn("loadedJsUrls", rendered)
        self.assertNotIn("loadedCssUrls", rendered)
        self.assertNotIn("toLoadJsTags", rendered)
        self.assertNotIn("toLoadCssTags", rendered)

    def test_multiple_components_dependencies(self):
        registry.register(name="inner", component=SimpleComponent)
        registry.register(name="outer", component=SimpleComponentNested)
        registry.register(name="other", component=OtherComponent)

        template_str: types.django_html = """
            {% load component_tags %}
            {% component_js_dependencies %}
            {% component_css_dependencies %}
            {% component 'outer' variable='variable' %}
                {% component 'other' variable='variable_inner' / %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = create_and_process_template_response(template)

        # Dependency manager script
        # NOTE: Should be present only ONCE!
        self.assertInHTML('<script src="django_components/django_components.min.js"></script>', rendered, count=1)

        self.assertEqual(rendered.count("<script"), 7)  # 2 scripts belong to the boilerplate
        self.assertEqual(rendered.count("<link"), 3)
        self.assertEqual(rendered.count("<style"), 2)

        # Components' inlined CSS
        # NOTE: Each of these should be present only ONCE!
        self.assertInHTML(
            """
            <style>.my-class { color: red; }</style>
            <style>.xyz { color: red; }</style>
            """,
            rendered,
            count=1,
        )

        # Components' Media.css
        # Order:
        # - "style.css", "style2.css" (from SimpleComponentNested)
        # - "style.css" (from SimpleComponent inside SimpleComponentNested)
        # - "xyz1.css" (from OtherComponent inserted into SimpleComponentNested)
        self.assertInHTML(
            """
            <link href="style.css" media="all" rel="stylesheet">
            <link href="style2.css" media="all" rel="stylesheet">
            <link href="xyz1.css" media="all" rel="stylesheet">
            """,
            rendered,
            count=1,
        )

        # Components' Media.js followed by inlined JS
        # Order:
        # - "script2.js" (from SimpleComponentNested)
        # - "script.js" (from SimpleComponent inside SimpleComponentNested)
        # - "xyz1.js" (from OtherComponent inserted into SimpleComponentNested)
        self.assertInHTML(
            """
            <script src="script2.js"></script>
            <script src="script.js"></script>
            <script src="xyz1.js"></script>
            <script>eval(Components.unescapeJs(`console.log(&quot;Hello&quot;);`))</script>
            <script>eval(Components.unescapeJs(`console.log(&quot;xyz&quot;);`))</script>
            """,
            rendered,
            count=1,
        )

        self.assertInHTML(
            """
            <script type="application/json" data-djc>
                {"loadedCssUrls": ["/components/cache/OtherComponent_6329ae.css/", "/components/cache/SimpleComponentNested_f02d32.css/", "style.css", "style2.css", "xyz1.css"],
                "loadedJsUrls": ["/components/cache/OtherComponent_6329ae.js/", "/components/cache/SimpleComponentNested_f02d32.js/", "script.js", "script2.js", "xyz1.js"],
                "toLoadCssTags": [],
                "toLoadJsTags": []}
            </script>
            """,
            rendered,
            count=1,
        )

    def test_multiple_components_all_placeholders_removed(self):
        registry.register(name="inner", component=SimpleComponent)
        registry.register(name="outer", component=SimpleComponentNested)
        registry.register(name="test", component=SimpleComponentWithSharedDependency)

        template_str: types.django_html = """
            {% load component_tags %}
            {% component_js_dependencies %}
            {% component_css_dependencies %}
            {% component 'inner' variable='variable' / %}
            {% component 'outer' variable='variable' / %}
            {% component 'test' variable='variable' / %}
        """
        template = Template(template_str)
        rendered = create_and_process_template_response(template)
        self.assertNotIn("_RENDERED", rendered)
