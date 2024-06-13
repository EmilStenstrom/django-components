import sys
import os
from pathlib import Path

from django.forms.widgets import Media
from django.template import Context, Template
from django.test import override_settings
from django.utils.html import html_safe
from django.utils.safestring import mark_safe

# isort: off
from .django_test_setup import *  # NOQA
from .testutils import BaseTestCase, autodiscover_with_cleanup

# isort: on

from django_components import component, types


class InlineComponentTest(BaseTestCase):
    def test_html(self):
        class InlineHTMLComponent(component.Component):
            template = "<div class='inline'>Hello Inline</div>"

        comp = InlineHTMLComponent("inline_html_component")
        self.assertHTMLEqual(
            comp.render(Context({})),
            "<div class='inline'>Hello Inline</div>",
        )

    def test_html_and_css(self):
        class HTMLCSSComponent(component.Component):
            template = "<div class='html-css-only'>Content</div>"
            css = ".html-css-only { color: blue; }"

        comp = HTMLCSSComponent("html_css_component")
        self.assertHTMLEqual(
            comp.render(Context({})),
            "<div class='html-css-only'>Content</div>",
        )
        self.assertHTMLEqual(
            comp.render_css_dependencies(),
            "<style>.html-css-only { color: blue; }</style>",
        )

    def test_html_and_js(self):
        class HTMLJSComponent(component.Component):
            template = "<div class='html-js-only'>Content</div>"
            js = "console.log('HTML and JS only');"

        comp = HTMLJSComponent("html_js_component")
        self.assertHTMLEqual(
            comp.render(Context({})),
            "<div class='html-js-only'>Content</div>",
        )
        self.assertHTMLEqual(
            comp.render_js_dependencies(),
            "<script>console.log('HTML and JS only');</script>",
        )

    def test_html_inline_and_css_js_files(self):
        class HTMLStringFileCSSJSComponent(component.Component):
            template = "<div class='html-string-file'>Content</div>"

            class Media:
                css = "path/to/style.css"
                js = "path/to/script.js"

        comp = HTMLStringFileCSSJSComponent("html_string_file_css_js_component")
        self.assertHTMLEqual(
            comp.render(Context({})),
            "<div class='html-string-file'>Content</div>",
        )
        self.assertHTMLEqual(
            comp.render_dependencies(),
            """
            <link href="path/to/style.css" media="all" rel="stylesheet">
            <script src="path/to/script.js"></script>
            """,
        )

    def test_html_js_inline_and_css_file(self):
        class HTMLStringFileCSSJSComponent(component.Component):
            template = "<div class='html-string-file'>Content</div>"
            js = "console.log('HTML and JS only');"

            class Media:
                css = "path/to/style.css"

        comp = HTMLStringFileCSSJSComponent("html_string_file_css_js_component")
        self.assertHTMLEqual(
            comp.render(Context({})),
            "<div class='html-string-file'>Content</div>",
        )
        self.assertHTMLEqual(
            comp.render_dependencies(),
            """
            <link href="path/to/style.css" media="all" rel="stylesheet">
            <script>console.log('HTML and JS only');</script>
            """,
        )

    def test_html_css_inline_and_js_file(self):
        class HTMLStringFileCSSJSComponent(component.Component):
            template = "<div class='html-string-file'>Content</div>"
            css = ".html-string-file { color: blue; }"

            class Media:
                js = "path/to/script.js"

        comp = HTMLStringFileCSSJSComponent("html_string_file_css_js_component")
        self.assertHTMLEqual(
            comp.render(Context({})),
            "<div class='html-string-file'>Content</div>",
        )
        self.assertHTMLEqual(
            comp.render_dependencies(),
            """
            <style>.html-string-file { color: blue; }</style><script src="path/to/script.js"></script>
            """,
        )

    def test_html_variable(self):
        class VariableHTMLComponent(component.Component):
            def get_template(self, context):
                return Template("<div class='variable-html'>{{ variable }}</div>")

        comp = VariableHTMLComponent("variable_html_component")
        context = Context({"variable": "Dynamic Content"})
        self.assertHTMLEqual(
            comp.render(context),
            "<div class='variable-html'>Dynamic Content</div>",
        )

    def test_html_variable_filtered(self):
        class FilteredComponent(component.Component):
            template: types.django_html = """
                Var1: <strong>{{ var1 }}</strong>
                Var2 (uppercased): <strong>{{ var2|upper }}</strong>
            """

            def get_context_data(self, var1=None, var2=None):
                return {
                    "var1": var1,
                    "var2": var2,
                }

        rendered = FilteredComponent.render(kwargs={"var1": "test1", "var2": "test2"})
        self.assertHTMLEqual(
            rendered,
            """
            Var1: <strong>test1</strong>
            Var2 (uppercased): <strong>TEST2</strong>
            """,
        )


class ComponentMediaTests(BaseTestCase):
    def test_css_and_js(self):
        class SimpleComponent(component.Component):
            template: types.django_html = """
                Variable: <strong>{{ variable }}</strong>
            """

            class Media:
                css = "style.css"
                js = "script.js"

        comp = SimpleComponent("simple_component")
        self.assertHTMLEqual(
            comp.render_dependencies(),
            """
                <link href="style.css" media="all" rel="stylesheet">
                <script src="script.js"></script>
            """,
        )

    def test_css_only(self):
        class SimpleComponent(component.Component):
            template: types.django_html = """
                Variable: <strong>{{ variable }}</strong>
            """

            class Media:
                css = "style.css"

        comp = SimpleComponent("simple_component")

        self.assertHTMLEqual(
            comp.render_dependencies(),
            """
            <link href="style.css" media="all" rel="stylesheet">
            """,
        )

    def test_js_only(self):
        class SimpleComponent(component.Component):
            template: types.django_html = """
                Variable: <strong>{{ variable }}</strong>
            """

            class Media:
                js = "script.js"

        comp = SimpleComponent("simple_component")

        self.assertHTMLEqual(
            comp.render_dependencies(),
            """
            <script src="script.js"></script>
            """,
        )

    def test_empty_media(self):
        class SimpleComponent(component.Component):
            template: types.django_html = """
                Variable: <strong>{{ variable }}</strong>
            """

            class Media:
                pass

        comp = SimpleComponent("simple_component")

        self.assertHTMLEqual(comp.render_dependencies(), "")

    def test_missing_media(self):
        class SimpleComponent(component.Component):
            template: types.django_html = """
                Variable: <strong>{{ variable }}</strong>
            """

        comp = SimpleComponent("simple_component")

        self.assertHTMLEqual(comp.render_dependencies(), "")

    def test_css_js_as_lists(self):
        class SimpleComponent(component.Component):
            class Media:
                css = ["path/to/style.css", "path/to/style2.css"]
                js = ["path/to/script.js"]

        comp = SimpleComponent("")
        self.assertHTMLEqual(
            comp.render_dependencies(),
            """
            <link href="path/to/style.css" media="all" rel="stylesheet">
            <link href="path/to/style2.css" media="all" rel="stylesheet">
            <script src="path/to/script.js"></script>
            """,
        )

    def test_css_js_as_string(self):
        class SimpleComponent(component.Component):
            class Media:
                css = "path/to/style.css"
                js = "path/to/script.js"

        comp = SimpleComponent("")
        self.assertHTMLEqual(
            comp.render_dependencies(),
            """
            <link href="path/to/style.css" media="all" rel="stylesheet">
            <script src="path/to/script.js"></script>
            """,
        )

    def test_css_js_as_dict_and_list(self):
        class SimpleComponent(component.Component):
            class Media:
                css = {
                    "all": "path/to/style.css",
                    "print": ["path/to/style2.css"],
                    "screen": "path/to/style3.css",
                }
                js = ["path/to/script.js"]

        comp = SimpleComponent("")
        self.assertHTMLEqual(
            comp.render_dependencies(),
            """
            <link href="path/to/style.css" media="all" rel="stylesheet">
            <link href="path/to/style2.css" media="print" rel="stylesheet">
            <link href="path/to/style3.css" media="screen" rel="stylesheet">
            <script src="path/to/script.js"></script>
            """,
        )

    # TODO - ALLOW CALLABLE!
    # TODO - DOCUMENT IT ALL!
    # TODO - Document how when we pass a safe string to css/js, then
    #        Media.render_js/css DOES NOT format it (same as Django's
    #        see https://docs.djangoproject.com/en/5.0/topics/forms/media/#paths-as-objects)

    def test_path_as_object_safestring(self):
        """
        Test that media work with paths defined as instances of classes that define
        the `__html__` method.

        See https://docs.djangoproject.com/en/5.0/topics/forms/media/#paths-as-objects
        """

        # NOTE: @html_safe adds __html__ method from __str__
        @html_safe
        class JSTag:
            def __init__(self, path: str) -> None:
                self.path = path
            def __str__(self):
                return f'<script js_tag src="{self.path}" type="module"></script>'

        @html_safe
        class CSSTag:
            def __init__(self, path: str) -> None:
                self.path = path
            def __str__(self):
                return f'<link css_tag href="{self.path}" rel="stylesheet" />'

        class SimpleComponent(component.Component):
            class Media:
                css = {
                    "all": [
                        CSSTag("path/to/style.css"),                                # Formatted by CSSTag
                        mark_safe('<link hi href="path/to/style2.css" rel="stylesheet" />'), # Literal
                    ],
                    "print": [
                        CSSTag("path/to/style3.css"),                               # Formatted by CSSTag
                    ],
                    "screen": "path/to/style4.css",                                 # Formatted by Media.render_css
                }
                js = [
                    JSTag("path/to/script.js"),                                     # Formatted by JSTag
                    mark_safe('<script hi src="path/to/script2.js"></script>'),    # Literal
                    "path/to/script3.js",                                           # Formatted by Media.render_js
                ]

        comp = SimpleComponent()
        self.assertHTMLEqual(
            comp.render_dependencies(),
            """
            <link css_tag href="path/to/style.css" rel="stylesheet" />
            <link hi href="path/to/style2.css" rel="stylesheet" />
            <link css_tag href="path/to/style3.css" rel="stylesheet" />
            <link href="path/to/style4.css" media="screen" rel="stylesheet">

            <script js_tag src="path/to/script.js" type="module"></script>
            <script hi src="path/to/script2.js"></script>
            <script src="path/to/script3.js"></script>
            """,
        )

    def test_path_as_object_pathlike(self):
        """
        Test that media work with paths defined as instances of classes that define
        the `__fspath__` method.
        """
        class MyPath(os.PathLike):
            def __init__(self, path: str) -> None:
                self.path = path
            def __fspath__(self):
                return self.path

        class SimpleComponent(component.Component):
            class Media:
                css = {
                    "all": [
                        MyPath("path/to/style.css"),
                        Path('path/to/style2.css'),
                    ],
                    "print": [
                        MyPath("path/to/style3.css"),
                    ],
                    "screen": "path/to/style4.css",
                }
                js = [
                    MyPath("path/to/script.js"),
                    Path('path/to/script2.js'),
                    "path/to/script3.js",
                ]

        comp = SimpleComponent()
        self.assertHTMLEqual(
            comp.render_dependencies(),
            """
            <link href="path/to/style.css" media="all" rel="stylesheet">
            <link href="path/to/style2.css" media="all" rel="stylesheet">
            <link href="path/to/style3.css" media="print" rel="stylesheet">
            <link href="path/to/style4.css" media="screen" rel="stylesheet">

            <script src="path/to/script.js"></script>
            <script src="path/to/script2.js"></script>
            <script src="path/to/script3.js"></script>
            """,
        )

    def test_path_as_object_str(self):
        """
        Test that media work with paths defined as instances of classes that
        subclass 'str'.
        """
        class MyStr(str):
            pass

        class SimpleComponent(component.Component):
            class Media:
                css = {
                    "all": [
                        MyStr("path/to/style.css"),
                        'path/to/style2.css',
                    ],
                    "print": [
                        MyStr("path/to/style3.css"),
                    ],
                    "screen": "path/to/style4.css",
                }
                js = [
                    MyStr("path/to/script.js"),
                    "path/to/script2.js",
                ]

        comp = SimpleComponent()
        self.assertHTMLEqual(
            comp.render_dependencies(),
            """
            <link href="path/to/style.css" media="all" rel="stylesheet">
            <link href="path/to/style2.css" media="all" rel="stylesheet">
            <link href="path/to/style3.css" media="print" rel="stylesheet">
            <link href="path/to/style4.css" media="screen" rel="stylesheet">

            <script src="path/to/script.js"></script>
            <script src="path/to/script2.js"></script>
            """,
        )

    def test_path_as_object_bytes(self):
        """
        Test that media work with paths defined as instances of classes that
        subclass 'bytes'.
        """
        class MyBytes(bytes):
            pass

        class SimpleComponent(component.Component):
            class Media:
                css = {
                    "all": [
                        MyBytes(b"path/to/style.css"),
                        b'path/to/style2.css',
                    ],
                    "print": [
                        MyBytes(b"path/to/style3.css"),
                    ],
                    "screen": b"path/to/style4.css",
                }
                js = [
                    MyBytes(b"path/to/script.js"),
                    "path/to/script2.js",
                ]

        comp = SimpleComponent()
        self.assertHTMLEqual(
            comp.render_dependencies(),
            """
            <link href="path/to/style.css" media="all" rel="stylesheet">
            <link href="path/to/style2.css" media="all" rel="stylesheet">
            <link href="path/to/style3.css" media="print" rel="stylesheet">
            <link href="path/to/style4.css" media="screen" rel="stylesheet">

            <script src="path/to/script.js"></script>
            <script src="path/to/script2.js"></script>
            """,
        )

    def test_media_custom_render_js(self):
        class MyMedia(Media):
            def render_js(self):
                tags: list[str] = []
                for path in self._js:
                    tags.append(f'<my_script_tag src="{self.absolute_path(path)}"></my_script_tag>')
                return tags

        class SimpleComponent(component.Component):
            media_class = MyMedia
            class Media:
                js = ["path/to/script.js", "path/to/script2.js"]

        comp = SimpleComponent()
        self.maxDiff = None
        self.assertHTMLEqual(
            comp.render_dependencies(),
            """
            <my_script_tag src="path/to/script.js"></my_script_tag>
            <my_script_tag src="path/to/script2.js"></my_script_tag>
            """,
        )

    def test_media_custom_render_css(self):
        class MyMedia(Media):
            def render_css(self):
                tags: list[str] = []
                media = sorted(self._css)
                for medium in media:
                    for path in self._css[medium]:
                        tags.append(f'<my_link href="{path}" media="{medium}" rel="stylesheet" />')
                return tags

        class SimpleComponent(component.Component):
            media_class = MyMedia
            class Media:
                css = {
                    "all": "path/to/style.css",
                    "print": ["path/to/style2.css"],
                    "screen": "path/to/style3.css",
                }

        comp = SimpleComponent()
        self.assertHTMLEqual(
            comp.render_dependencies(),
            """
            <my_link href="path/to/style.css" media="all" rel="stylesheet" />
            <my_link href="path/to/style2.css" media="print" rel="stylesheet" />
            <my_link href="path/to/style3.css" media="screen" rel="stylesheet" />
            """,
        )


class MediaRelativePathTests(BaseTestCase):
    class ParentComponent(component.Component):
        template: types.django_html = """
            {% load component_tags %}
            <div>
                <h1>Parent content</h1>
                {% component name="variable_display" shadowing_variable='override' new_variable='unique_val' %}
                {% endcomponent %}
            </div>
            <div>
                {% slot 'content' %}
                    <h2>Slot content</h2>
                    {% component name="variable_display" shadowing_variable='slot_default_override' new_variable='slot_default_unique' %}
                    {% endcomponent %}
                {% endslot %}
            </div>
        """  # noqa

        def get_context_data(self):
            return {"shadowing_variable": "NOT SHADOWED"}

    class VariableDisplay(component.Component):
        template: types.django_html = """
            {% load component_tags %}
            <h1>Shadowing variable = {{ shadowing_variable }}</h1>
            <h1>Uniquely named variable = {{ unique_variable }}</h1>
        """

        def get_context_data(self, shadowing_variable=None, new_variable=None):
            context = {}
            if shadowing_variable is not None:
                context["shadowing_variable"] = shadowing_variable
            if new_variable is not None:
                context["unique_variable"] = new_variable
            return context

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        component.registry.register(name="parent_component", component=cls.ParentComponent)
        component.registry.register(name="variable_display", component=cls.VariableDisplay)

    # Settings required for autodiscover to work
    @override_settings(
        BASE_DIR=Path(__file__).resolve().parent,
        STATICFILES_DIRS=[
            Path(__file__).resolve().parent / "components",
        ],
    )
    def test_component_with_relative_media_paths(self):
        # Ensure that the module is executed again after import in autodiscovery
        if "tests.components.relative_file.relative_file" in sys.modules:
            del sys.modules["tests.components.relative_file.relative_file"]

        # Fix the paths, since the "components" dir is nested
        with autodiscover_with_cleanup(map_import_paths=lambda p: f"tests.{p}"):
            template_str: types.django_html = """
                {% load component_tags %}{% component_dependencies %}
                {% component name='relative_file_component' variable=variable %}
                {% endcomponent %}
            """
            template = Template(template_str)
            rendered = template.render(Context({"variable": "test"}))
            self.assertHTMLEqual(
                rendered,
                """
                <link href="relative_file/relative_file.css" media="all" rel="stylesheet">
                <script src="relative_file/relative_file.js"></script>
                <form method="post">
                    <input type="text" name="variable" value="test">
                    <input type="submit">
                </form>
                """,
            )

    # Settings required for autodiscover to work
    @override_settings(
        BASE_DIR=Path(__file__).resolve().parent,
        STATICFILES_DIRS=[
            Path(__file__).resolve().parent / "components",
        ],
    )
    def test_component_with_relative_media_paths_as_subcomponent(self):
        # Ensure that the module is executed again after import in autodiscovery
        if "tests.components.relative_file.relative_file" in sys.modules:
            del sys.modules["tests.components.relative_file.relative_file"]

        # Fix the paths, since the "components" dir is nested
        with autodiscover_with_cleanup(map_import_paths=lambda p: f"tests.{p}"):
            template_str: types.django_html = """
                {% load component_tags %}{% component_dependencies %}
                {% component 'parent_component' %}
                    {% fill 'content' %}
                        {% component name='relative_file_component' variable='hello' %}
                        {% endcomponent %}
                    {% endfill %}
                {% endcomponent %}
            """
            template = Template(template_str)
            rendered = template.render(Context({}))
            self.assertIn('<input type="text" name="variable" value="hello">', rendered, rendered)
