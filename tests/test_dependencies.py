from unittest.mock import Mock

from django.http import HttpResponseNotModified
from django.template import Context, Template

from django_components import Component, registry, render_dependencies, types
from django_components.components.dynamic import DynamicComponent
from django_components.middleware import ComponentDependencyMiddleware
from django_components.util.html import SoupNode

from .django_test_setup import setup_test_config
from .testutils import BaseTestCase, create_and_process_template_response

setup_test_config({"autodiscover": False})


class SimpleComponent(Component):
    template: types.django_html = """
        Variable: <strong>{{ variable }}</strong>
    """

    css: types.css = """
        .xyz {
            color: red;
        }
    """

    js: types.js = """
        console.log("xyz");
    """

    def get_context_data(self, variable, variable2="default"):
        return {
            "variable": variable,
            "variable2": variable2,
        }

    class Media:
        css = "style.css"
        js = "script.js"


class RenderDependenciesTests(BaseTestCase):
    def test_standalone_render_dependencies(self):
        registry.register(name="test", component=SimpleComponent)

        template_str: types.django_html = """
            {% load component_tags %}
            {% component_js_dependencies %}
            {% component_css_dependencies %}
            {% component 'test' variable='foo' / %}
        """
        template = Template(template_str)
        rendered_raw = template.render(Context({}))

        # Placeholders
        self.assertEqual(rendered_raw.count('<link name="CSS_PLACEHOLDER">'), 1)
        self.assertEqual(rendered_raw.count('<script name="JS_PLACEHOLDER"></script>'), 1)

        self.assertEqual(rendered_raw.count("<script"), 1)
        self.assertEqual(rendered_raw.count("<style"), 0)
        self.assertEqual(rendered_raw.count("<link"), 1)
        self.assertEqual(rendered_raw.count("_RENDERED"), 1)

        rendered = render_dependencies(rendered_raw)

        # Dependency manager script
        self.assertInHTML('<script src="django_components/django_components.min.js"></script>', rendered, count=1)

        self.assertInHTML("<style>.xyz { color: red; }</style>", rendered, count=1)  # Inlined CSS
        self.assertInHTML(
            "<script>eval(Components.unescapeJs(`console.log(&quot;xyz&quot;);`))</script>", rendered, count=1
        )  # Inlined JS

        self.assertInHTML('<link href="style.css" media="all" rel="stylesheet">', rendered, count=1)  # Media.css

    def test_middleware_renders_dependencies(self):
        registry.register(name="test", component=SimpleComponent)

        template_str: types.django_html = """
            {% load component_tags %}
            {% component_js_dependencies %}
            {% component_css_dependencies %}
            {% component 'test' variable='foo' / %}
        """
        template = Template(template_str)
        rendered = create_and_process_template_response(template, use_middleware=True)

        # Dependency manager script
        self.assertInHTML('<script src="django_components/django_components.min.js"></script>', rendered, count=1)

        self.assertInHTML("<style>.xyz { color: red; }</style>", rendered, count=1)  # Inlined CSS
        self.assertInHTML(
            "<script>eval(Components.unescapeJs(`console.log(&quot;xyz&quot;);`))</script>", rendered, count=1
        )  # Inlined JS

        self.assertInHTML('<link href="style.css" media="all" rel="stylesheet">', rendered, count=1)  # Media.css
        self.assertEqual(rendered.count("<link"), 1)
        self.assertEqual(rendered.count("<style"), 1)

    def test_component_render_renders_dependencies(self):
        class SimpleComponentWithDeps(SimpleComponent):
            template: types.django_html = (
                """
                    {% load component_tags %}
                    {% component_js_dependencies %}
                    {% component_css_dependencies %}
                """
                + SimpleComponent.template
            )

        registry.register(name="test", component=SimpleComponentWithDeps)

        rendered = SimpleComponentWithDeps.render(
            kwargs={"variable": "foo"},
        )

        # Dependency manager script
        self.assertInHTML('<script src="django_components/django_components.min.js"></script>', rendered, count=1)

        self.assertInHTML("<style>.xyz { color: red; }</style>", rendered, count=1)  # Inlined CSS
        self.assertInHTML(
            "<script>eval(Components.unescapeJs(`console.log(&quot;xyz&quot;);`))</script>", rendered, count=1
        )  # Inlined JS

        self.assertInHTML('<link href="style.css" media="all" rel="stylesheet">', rendered, count=1)  # Media.css
        self.assertEqual(rendered.count("<link"), 1)
        self.assertEqual(rendered.count("<style"), 1)

    def test_component_render_renders_dependencies_opt_out(self):
        class SimpleComponentWithDeps(SimpleComponent):
            template: types.django_html = (
                """
                    {% load component_tags %}
                    {% component_js_dependencies %}
                    {% component_css_dependencies %}
                """
                + SimpleComponent.template
            )

        registry.register(name="test", component=SimpleComponentWithDeps)

        rendered_raw = SimpleComponentWithDeps.render(
            kwargs={"variable": "foo"},
            render_dependencies=False,
        )

        self.assertEqual(rendered_raw.count("<script"), 1)
        self.assertEqual(rendered_raw.count("<style"), 0)
        self.assertEqual(rendered_raw.count("<link"), 1)
        self.assertEqual(rendered_raw.count("_RENDERED"), 1)

        # Dependency manager script
        self.assertInHTML('<script src="django_components/django_components.min.js"></script>', rendered_raw, count=0)

        self.assertInHTML("<style>.xyz { color: red; }</style>", rendered_raw, count=0)  # Inlined CSS
        self.assertInHTML('<link href="style.css" media="all" rel="stylesheet">', rendered_raw, count=0)  # Media.css

        self.assertInHTML(
            "<script>eval(Components.unescapeJs(`console.log(&quot;xyz&quot;);`))</script>",
            rendered_raw,
            count=0,
        )  # Inlined JS

    def test_component_render_to_response_renders_dependencies(self):
        class SimpleComponentWithDeps(SimpleComponent):
            template: types.django_html = (
                """
                    {% load component_tags %}
                    {% component_js_dependencies %}
                    {% component_css_dependencies %}
                """
                + SimpleComponent.template
            )

        registry.register(name="test", component=SimpleComponentWithDeps)

        response = SimpleComponentWithDeps.render_to_response(
            kwargs={"variable": "foo"},
        )
        rendered = response.content.decode()

        # Dependency manager script
        self.assertInHTML('<script src="django_components/django_components.min.js"></script>', rendered, count=1)

        self.assertInHTML("<style>.xyz { color: red; }</style>", rendered, count=1)  # Inlined CSS
        self.assertInHTML(
            "<script>eval(Components.unescapeJs(`console.log(&quot;xyz&quot;);`))</script>", rendered, count=1
        )  # Inlined JS

        self.assertEqual(rendered.count('<link href="style.css" media="all" rel="stylesheet">'), 1)  # Media.css
        self.assertEqual(rendered.count("<link"), 1)
        self.assertEqual(rendered.count("<style"), 1)

    def test_inserts_styles_and_script_to_default_places_if_not_overriden(self):
        registry.register(name="test", component=SimpleComponent)

        template_str: types.django_html = """
            {% load component_tags %}
            <!DOCTYPE html>
            <html>
                <head></head>
                <body>
                    {% component "test" variable="foo" / %}
                </body>
            </html>
        """
        rendered_raw = Template(template_str).render(Context({}))
        rendered = render_dependencies(rendered_raw)

        self.assertEqual(rendered.count("<script"), 4)
        self.assertEqual(rendered.count("<style"), 1)
        self.assertEqual(rendered.count("<link"), 1)
        self.assertEqual(rendered.count("_RENDERED"), 0)

        self.assertInHTML(
            """
            <head>
                <style>.xyz { color: red; }</style>
                <link href="style.css" media="all" rel="stylesheet">
            </head>
            """,
            rendered,
            count=1,
        )

        # Nodes: [Doctype, whitespace, <html>]
        nodes = SoupNode.from_fragment(rendered.strip())
        rendered_body = nodes[2].find_tag("body").to_html()  # type: ignore[union-attr]

        self.assertInHTML(
            """<script src="django_components/django_components.min.js">""",
            rendered_body,
            count=1,
        )
        self.assertInHTML(
            """<script>eval(Components.unescapeJs(`console.log(&quot;xyz&quot;);`))</script>""",
            rendered_body,
            count=1,
        )

    def test_does_not_insert_styles_and_script_to_default_places_if_overriden(self):
        registry.register(name="test", component=SimpleComponent)

        template_str: types.django_html = """
            {% load component_tags %}
            <!DOCTYPE html>
            <html>
                <head>
                    {% component_js_dependencies %}
                </head>
                <body>
                    {% component "test" variable="foo" / %}
                    {% component_css_dependencies %}
                </body>
            </html>
        """
        rendered_raw = Template(template_str).render(Context({}))
        rendered = render_dependencies(rendered_raw)

        self.assertEqual(rendered.count("<script"), 4)
        self.assertEqual(rendered.count("<style"), 1)
        self.assertEqual(rendered.count("<link"), 1)
        self.assertEqual(rendered.count("_RENDERED"), 0)

        self.assertInHTML(
            """
            <body>
                Variable: <strong>foo</strong>

                <style>.xyz { color: red; }</style>
                <link href="style.css" media="all" rel="stylesheet">
            </body>
            """,
            rendered,
            count=1,
        )

        # Nodes: [Doctype, whitespace, <html>]
        nodes = SoupNode.from_fragment(rendered.strip())
        rendered_head = nodes[2].find_tag("head").to_html()  # type: ignore[union-attr]

        self.assertInHTML(
            """<script src="django_components/django_components.min.js">""",
            rendered_head,
            count=1,
        )
        self.assertInHTML(
            """<script>eval(Components.unescapeJs(`console.log(&quot;xyz&quot;);`))</script>""",
            rendered_head,
            count=1,
        )

    # NOTE: Some HTML parser libraries like selectolax or lxml try to "correct" the given HTML.
    #       We want to avoid this behavior, so user gets the exact same HTML back.
    def test_does_not_try_to_add_close_tags(self):
        registry.register(name="test", component=SimpleComponent)

        template_str: types.django_html = """
            <thead>
        """

        rendered_raw = Template(template_str).render(Context({"formset": [1]}))
        rendered = render_dependencies(rendered_raw, type="fragment")

        self.assertHTMLEqual(rendered, "<thead>")

    def test_does_not_modify_html_when_no_component_used(self):
        registry.register(name="test", component=SimpleComponent)

        template_str: types.django_html = """
            <table class="table-auto border-collapse divide-y divide-x divide-slate-300 w-full">
                <!-- Table head -->
                <thead>
                    <tr class="py-0 my-0 h-7">
                        <!-- Empty row -->
                        <th class="min-w-12">#</th>
                    </tr>
                </thead>
                <!-- Table body -->
                <tbody id="items" class="divide-y divide-slate-300">
                    {% for form in formset %}
                        {% with row_number=forloop.counter %}
                            <tr class=" hover:bg-gray-200 py-0 {% cycle 'bg-white' 'bg-gray-50' %} divide-x "
                                aria-rowindex="{{ row_number }}">
                                <!-- row num -->
                                <td class="whitespace-nowrap w-fit text-center px-4 w-px"
                                    aria-colindex="1">
                                    {{ row_number }}
                                </td>
                            </tr>
                        {% endwith %}
                    {% endfor %}
                </tbody>
            </table>
        """

        rendered_raw = Template(template_str).render(Context({"formset": [1]}))
        rendered = render_dependencies(rendered_raw, type="fragment")

        expected = """
            <table class="table-auto border-collapse divide-y divide-x divide-slate-300 w-full">
                <!-- Table head -->
                <thead>
                    <tr class="py-0 my-0 h-7">
                        <!-- Empty row -->
                        <th class="min-w-12">#</th>
                    </tr>
                </thead>
                <!-- Table body -->
                <tbody id="items" class="divide-y divide-slate-300">
                    <tr class=" hover:bg-gray-200 py-0 bg-white divide-x "
                        aria-rowindex="1">
                        <!-- row num -->
                        <td class="whitespace-nowrap w-fit text-center px-4 w-px"
                            aria-colindex="1">
                            1
                        </td>
                    </tr>
                </tbody>
            </table>
        """

        self.assertHTMLEqual(expected, rendered)

    # Explanation: The component is used in the template, but the template doesn't use
    # {% component_js_dependencies %} or {% component_css_dependencies %} tags,
    # nor defines a `<head>` or `<body>` tag. In which case, the dependencies are not rendered.
    def test_does_not_modify_html_when_component_used_but_nowhere_to_insert(self):
        registry.register(name="test", component=SimpleComponent)

        template_str: types.django_html = """
            {% load component_tags %}
            <table class="table-auto border-collapse divide-y divide-x divide-slate-300 w-full">
                <!-- Table head -->
                <thead>
                    <tr class="py-0 my-0 h-7">
                        <!-- Empty row -->
                        <th class="min-w-12">#</th>
                    </tr>
                </thead>
                <!-- Table body -->
                <tbody id="items" class="divide-y divide-slate-300">
                    {% for form in formset %}
                        {% with row_number=forloop.counter %}
                            <tr class=" hover:bg-gray-200 py-0 {% cycle 'bg-white' 'bg-gray-50' %} divide-x "
                                aria-rowindex="{{ row_number }}">
                                <!-- row num -->
                                <td class="whitespace-nowrap w-fit text-center px-4 w-px"
                                    aria-colindex="1">
                                    {{ row_number }}
                                    {% component "test" variable="hi" / %}
                                </td>
                            </tr>
                        {% endwith %}
                    {% endfor %}
                </tbody>
            </table>
        """

        rendered_raw = Template(template_str).render(Context({"formset": [1]}))
        rendered = render_dependencies(rendered_raw, type="fragment")

        expected = """
            <table class="table-auto border-collapse divide-y divide-x divide-slate-300 w-full">
                <!-- Table head -->
                <thead>
                    <tr class="py-0 my-0 h-7">
                        <!-- Empty row -->
                        <th class="min-w-12">#</th>
                    </tr>
                </thead>
                <!-- Table body -->
                <tbody id="items" class="divide-y divide-slate-300">
                    <tr class=" hover:bg-gray-200 py-0 bg-white divide-x "
                        aria-rowindex="1">
                        <!-- row num -->
                        <td class="whitespace-nowrap w-fit text-center px-4 w-px"
                            aria-colindex="1">
                            1
                            Variable: <strong>hi</strong>
                        </td>
                    </tr>
                </tbody>
            </table>
            <script type="application/json" data-djc>
                {"loadedCssUrls": [],
                "loadedJsUrls": [],
                "toLoadCssTags": ["&lt;link href=&quot;style.css&quot; media=&quot;all&quot; rel=&quot;stylesheet&quot;&gt;",
                    "&lt;link href=&quot;/components/cache/SimpleComponent_311097.css/&quot; media=&quot;all&quot; rel=&quot;stylesheet&quot;&gt;"],
                "toLoadJsTags": ["&lt;script src=&quot;script.js&quot;&gt;&lt;/script&gt;",
                "&lt;script src=&quot;/components/cache/SimpleComponent_311097.js/&quot;&gt;&lt;/script&gt;"]}
            </script>
        """  # noqa: E501

        self.assertHTMLEqual(expected, rendered)


class MiddlewareTests(BaseTestCase):
    def test_middleware_response_without_content_type(self):
        response = HttpResponseNotModified()
        middleware = ComponentDependencyMiddleware(get_response=lambda _: response)
        request = Mock()
        self.assertEqual(response, middleware(request=request))

    def test_middleware_response_with_components_with_slash_dash_and_underscore(
        self,
    ):
        registry.register("dynamic", DynamicComponent)

        component_names = [
            "test-component",
            "test/component",
            "test_component",
        ]
        for component_name in component_names:
            registry.register(name=component_name, component=SimpleComponent)
            template_str: types.django_html = """
                {% load component_tags %}
                {% component_css_dependencies %}
                {% component_js_dependencies %}
                {% component "dynamic" is=component_name variable='value' / %}
            """
            template = Template(template_str)
            rendered = create_and_process_template_response(
                template, context=Context({"component_name": component_name})
            )

            # Dependency manager script (empty)
            self.assertInHTML('<script src="django_components/django_components.min.js"></script>', rendered, count=1)

            # Inlined JS
            self.assertInHTML(
                "<script>eval(Components.unescapeJs(`console.log(&quot;xyz&quot;);`))</script>", rendered, count=1
            )
            # Inlined CSS
            self.assertInHTML("<style>.xyz { color: red; }</style>", rendered, count=1)
            # Media.css
            self.assertInHTML('<link href="style.css" media="all" rel="stylesheet">', rendered, count=1)

            self.assertEqual(rendered.count("Variable: <strong>value</strong>"), 1)
