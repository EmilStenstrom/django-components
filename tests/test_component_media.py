import os
import sys
from pathlib import Path

from django.forms.widgets import Media
from django.template import Context, Template
from django.templatetags.static import static
from django.test import override_settings
from django.utils.html import format_html, html_safe
from django.utils.safestring import mark_safe

from django_components import Component, registry, render_dependencies, types

from .django_test_setup import setup_test_config
from .testutils import BaseTestCase, autodiscover_with_cleanup

setup_test_config({"autodiscover": False})


class InlineComponentTest(BaseTestCase):
    def test_html(self):
        class InlineHTMLComponent(Component):
            template = "<div class='inline'>Hello Inline</div>"

        self.assertHTMLEqual(
            InlineHTMLComponent.render(),
            "<div class='inline'>Hello Inline</div>",
        )

    def test_inlined_js_and_css(self):
        class TestComponent(Component):
            template = """
                {% load component_tags %}
                {% component_js_dependencies %}
                {% component_css_dependencies %}
                <div class='html-css-only'>Content</div>
            """
            css = ".html-css-only { color: blue; }"
            js = "console.log('HTML and JS only');"

        rendered = TestComponent.render()

        self.assertInHTML(
            "<div class='html-css-only'>Content</div>",
            rendered,
        )
        self.assertInHTML(
            "<style>.html-css-only { color: blue; }</style>",
            rendered,
        )
        self.assertInHTML(
            "<script>eval(Components.unescapeJs(`console.log(&#x27;HTML and JS only&#x27;);`))</script>",
            rendered,
        )

    def test_html_variable(self):
        class VariableHTMLComponent(Component):
            def get_template(self, context):
                return Template("<div class='variable-html'>{{ variable }}</div>")

        comp = VariableHTMLComponent("variable_html_component")
        context = Context({"variable": "Dynamic Content"})
        self.assertHTMLEqual(
            comp.render(context),
            "<div class='variable-html'>Dynamic Content</div>",
        )

    def test_html_variable_filtered(self):
        class FilteredComponent(Component):
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
    def test_empty_media(self):
        class SimpleComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                {% component_js_dependencies %}
                {% component_css_dependencies %}
                Variable: <strong>{{ variable }}</strong>
            """

            class Media:
                pass

        rendered = SimpleComponent.render()

        self.assertEqual(rendered.count("<style"), 0)
        self.assertEqual(rendered.count("<link"), 0)

        self.assertEqual(rendered.count("<script"), 1)  # 1 Boilerplate script

    def test_css_js_as_lists(self):
        class SimpleComponent(Component):
            template = """
                {% load component_tags %}
                {% component_js_dependencies %}
                {% component_css_dependencies %}
            """

            class Media:
                css = ["path/to/style.css", "path/to/style2.css"]
                js = ["path/to/script.js"]

        rendered = SimpleComponent.render()

        self.assertInHTML('<link href="path/to/style.css" media="all" rel="stylesheet">', rendered)
        self.assertInHTML('<link href="path/to/style2.css" media="all" rel="stylesheet">', rendered)

        self.assertInHTML('<script src="path/to/script.js"></script>', rendered)

    def test_css_js_as_string(self):
        class SimpleComponent(Component):
            template = """
                {% load component_tags %}
                {% component_js_dependencies %}
                {% component_css_dependencies %}
            """

            class Media:
                css = "path/to/style.css"
                js = "path/to/script.js"

        rendered = SimpleComponent.render()

        self.assertInHTML('<link href="path/to/style.css" media="all" rel="stylesheet">', rendered)
        self.assertInHTML('<script src="path/to/script.js"></script>', rendered)

    def test_css_as_dict(self):
        class SimpleComponent(Component):
            template = """
                {% load component_tags %}
                {% component_js_dependencies %}
                {% component_css_dependencies %}
            """

            class Media:
                css = {
                    "all": "path/to/style.css",
                    "print": ["path/to/style2.css"],
                    "screen": "path/to/style3.css",
                }
                js = ["path/to/script.js"]

        rendered = SimpleComponent.render()

        self.assertInHTML('<link href="path/to/style.css" media="all" rel="stylesheet">', rendered)
        self.assertInHTML('<link href="path/to/style2.css" media="print" rel="stylesheet">', rendered)
        self.assertInHTML('<link href="path/to/style3.css" media="screen" rel="stylesheet">', rendered)

        self.assertInHTML('<script src="path/to/script.js"></script>', rendered)

    def test_media_custom_render_js(self):
        class MyMedia(Media):
            def render_js(self):
                tags: list[str] = []
                for path in self._js:  # type: ignore[attr-defined]
                    abs_path = self.absolute_path(path)  # type: ignore[attr-defined]
                    tags.append(f'<script defer src="{abs_path}"></script>')
                return tags

        class SimpleComponent(Component):
            template = """
                {% load component_tags %}
                {% component_js_dependencies %}
                {% component_css_dependencies %}
            """

            media_class = MyMedia

            class Media:
                js = ["path/to/script.js", "path/to/script2.js"]

        rendered = SimpleComponent.render()

        self.assertIn('<script defer src="path/to/script.js"></script>', rendered)
        self.assertIn('<script defer src="path/to/script2.js"></script>', rendered)

    def test_media_custom_render_css(self):
        class MyMedia(Media):
            def render_css(self):
                tags: list[str] = []
                media = sorted(self._css)  # type: ignore[attr-defined]
                for medium in media:
                    for path in self._css[medium]:  # type: ignore[attr-defined]
                        tags.append(f'<link abc href="{path}" media="{medium}" rel="stylesheet" />')
                return tags

        class SimpleComponent(Component):
            template = """
                {% load component_tags %}
                {% component_js_dependencies %}
                {% component_css_dependencies %}
            """

            media_class = MyMedia

            class Media:
                css = {
                    "all": "path/to/style.css",
                    "print": ["path/to/style2.css"],
                    "screen": "path/to/style3.css",
                }

        rendered = SimpleComponent.render()

        self.assertInHTML('<link abc href="path/to/style.css" media="all" rel="stylesheet">', rendered)
        self.assertInHTML('<link abc href="path/to/style2.css" media="print" rel="stylesheet">', rendered)
        self.assertInHTML('<link abc href="path/to/style3.css" media="screen" rel="stylesheet">', rendered)


class MediaPathAsObjectTests(BaseTestCase):
    def test_safestring(self):
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

        # Format as mentioned in https://github.com/EmilStenstrom/django-components/issues/522#issuecomment-2173577094
        @html_safe
        class PathObj:
            def __init__(self, static_path: str) -> None:
                self.static_path = static_path

            def __str__(self):
                return format_html('<script type="module" src="{}"></script>', static(self.static_path))

        class SimpleComponent(Component):
            template = """
                {% load component_tags %}
                {% component_js_dependencies %}
                {% component_css_dependencies %}
            """

            class Media:
                css = {
                    "all": [
                        CSSTag("path/to/style.css"),  # Formatted by CSSTag
                        mark_safe('<link hi href="path/to/style2.css" rel="stylesheet" />'),  # Literal
                    ],
                    "print": [
                        CSSTag("path/to/style3.css"),  # Formatted by CSSTag
                    ],
                    "screen": "path/to/style4.css",  # Formatted by Media.render_css
                }
                js = [
                    JSTag("path/to/script.js"),  # Formatted by JSTag
                    mark_safe('<script hi src="path/to/script2.js"></script>'),  # Literal
                    PathObj("path/to/script3.js"),  # Literal
                    "path/to/script4.js",  # Formatted by Media.render_js
                ]

        rendered = SimpleComponent.render()

        self.assertInHTML('<link css_tag href="path/to/style.css" rel="stylesheet" />', rendered)
        self.assertInHTML('<link hi href="path/to/style2.css" rel="stylesheet" />', rendered)
        self.assertInHTML('<link css_tag href="path/to/style3.css" rel="stylesheet" />', rendered)
        self.assertInHTML('<link href="path/to/style4.css" media="screen" rel="stylesheet">', rendered)

        self.assertInHTML('<script js_tag src="path/to/script.js" type="module"></script>', rendered)
        self.assertInHTML('<script hi src="path/to/script2.js"></script>', rendered)
        self.assertInHTML('<script type="module" src="path/to/script3.js"></script>', rendered)
        self.assertInHTML('<script src="path/to/script4.js"></script>', rendered)

    def test_pathlike(self):
        """
        Test that media work with paths defined as instances of classes that define
        the `__fspath__` method.
        """

        class MyPath(os.PathLike):
            def __init__(self, path: str) -> None:
                self.path = path

            def __fspath__(self):
                return self.path

        class SimpleComponent(Component):
            template = """
                {% load component_tags %}
                {% component_js_dependencies %}
                {% component_css_dependencies %}
            """

            class Media:
                css = {
                    "all": [
                        MyPath("path/to/style.css"),
                        Path("path/to/style2.css"),
                    ],
                    "print": [
                        MyPath("path/to/style3.css"),
                    ],
                    "screen": "path/to/style4.css",
                }
                js = [
                    MyPath("path/to/script.js"),
                    Path("path/to/script2.js"),
                    "path/to/script3.js",
                ]

        rendered = SimpleComponent.render()

        self.assertInHTML('<link href="path/to/style.css" media="all" rel="stylesheet">', rendered)
        self.assertInHTML('<link href="path/to/style2.css" media="all" rel="stylesheet">', rendered)
        self.assertInHTML('<link href="path/to/style3.css" media="print" rel="stylesheet">', rendered)
        self.assertInHTML('<link href="path/to/style4.css" media="screen" rel="stylesheet">', rendered)

        self.assertInHTML('<script src="path/to/script.js"></script>', rendered)
        self.assertInHTML('<script src="path/to/script2.js"></script>', rendered)
        self.assertInHTML('<script src="path/to/script3.js"></script>', rendered)

    def test_str(self):
        """
        Test that media work with paths defined as instances of classes that
        subclass 'str'.
        """

        class MyStr(str):
            pass

        class SimpleComponent(Component):
            template = """
                {% load component_tags %}
                {% component_js_dependencies %}
                {% component_css_dependencies %}
            """

            class Media:
                css = {
                    "all": [
                        MyStr("path/to/style.css"),
                        "path/to/style2.css",
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

        rendered = SimpleComponent.render()

        self.assertInHTML('<link href="path/to/style.css" media="all" rel="stylesheet">', rendered)
        self.assertInHTML('<link href="path/to/style2.css" media="all" rel="stylesheet">', rendered)
        self.assertInHTML('<link href="path/to/style3.css" media="print" rel="stylesheet">', rendered)
        self.assertInHTML('<link href="path/to/style4.css" media="screen" rel="stylesheet">', rendered)

        self.assertInHTML('<script src="path/to/script.js"></script>', rendered)
        self.assertInHTML('<script src="path/to/script2.js"></script>', rendered)

    def test_bytes(self):
        """
        Test that media work with paths defined as instances of classes that
        subclass 'bytes'.
        """

        class MyBytes(bytes):
            pass

        class SimpleComponent(Component):
            template = """
                {% load component_tags %}
                {% component_js_dependencies %}
                {% component_css_dependencies %}
            """

            class Media:
                css = {
                    "all": [
                        MyBytes(b"path/to/style.css"),
                        b"path/to/style2.css",
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

        rendered = SimpleComponent.render()

        self.assertInHTML('<link href="path/to/style.css" media="all" rel="stylesheet">', rendered)
        self.assertInHTML('<link href="path/to/style2.css" media="all" rel="stylesheet">', rendered)
        self.assertInHTML('<link href="path/to/style3.css" media="print" rel="stylesheet">', rendered)
        self.assertInHTML('<link href="path/to/style4.css" media="screen" rel="stylesheet">', rendered)

        self.assertInHTML('<script src="path/to/script.js"></script>', rendered)
        self.assertInHTML('<script src="path/to/script2.js"></script>', rendered)

    def test_function(self):
        class SimpleComponent(Component):
            template = """
                {% load component_tags %}
                {% component_js_dependencies %}
                {% component_css_dependencies %}
            """

            class Media:
                css = [
                    lambda: mark_safe('<link hi href="calendar/style.css" rel="stylesheet" />'),  # Literal
                    lambda: Path("calendar/style1.css"),
                    lambda: "calendar/style2.css",
                    lambda: b"calendar/style3.css",
                ]
                js = [
                    lambda: mark_safe('<script hi src="calendar/script.js"></script>'),  # Literal
                    lambda: Path("calendar/script1.js"),
                    lambda: "calendar/script2.js",
                    lambda: b"calendar/script3.js",
                ]

        rendered = SimpleComponent.render()

        self.assertInHTML('<link hi href="calendar/style.css" rel="stylesheet" />', rendered)
        self.assertInHTML('<link href="calendar/style1.css" media="all" rel="stylesheet">', rendered)
        self.assertInHTML('<link href="calendar/style2.css" media="all" rel="stylesheet">', rendered)
        self.assertInHTML('<link href="calendar/style3.css" media="all" rel="stylesheet">', rendered)

        self.assertInHTML('<script hi src="calendar/script.js"></script>', rendered)
        self.assertInHTML('<script src="calendar/script1.js"></script>', rendered)
        self.assertInHTML('<script src="calendar/script2.js"></script>', rendered)
        self.assertInHTML('<script src="calendar/script3.js"></script>', rendered)

    @override_settings(STATIC_URL="static/")
    def test_works_with_static(self):
        """Test that all the different ways of defining media files works with Django's staticfiles"""

        class SimpleComponent(Component):
            template = """
                {% load component_tags %}
                {% component_js_dependencies %}
                {% component_css_dependencies %}
            """

            class Media:
                css = [
                    mark_safe(f'<link hi href="{static("calendar/style.css")}" rel="stylesheet" />'),  # Literal
                    Path("calendar/style1.css"),
                    "calendar/style2.css",
                    b"calendar/style3.css",
                    lambda: "calendar/style4.css",
                ]
                js = [
                    mark_safe(f'<script hi src="{static("calendar/script.js")}"></script>'),  # Literal
                    Path("calendar/script1.js"),
                    "calendar/script2.js",
                    b"calendar/script3.js",
                    lambda: "calendar/script4.js",
                ]

        rendered = SimpleComponent.render()

        self.assertInHTML('<link hi href="/static/calendar/style.css" rel="stylesheet" />', rendered)
        self.assertInHTML('<link href="/static/calendar/style1.css" media="all" rel="stylesheet" />', rendered)
        self.assertInHTML('<link href="/static/calendar/style1.css" media="all" rel="stylesheet">', rendered)
        self.assertInHTML('<link href="/static/calendar/style2.css" media="all" rel="stylesheet">', rendered)
        self.assertInHTML('<link href="/static/calendar/style3.css" media="all" rel="stylesheet">', rendered)

        self.assertInHTML('<script hi src="/static/calendar/script.js"></script>', rendered)
        self.assertInHTML('<script src="/static/calendar/script1.js"></script>', rendered)
        self.assertInHTML('<script src="/static/calendar/script2.js"></script>', rendered)
        self.assertInHTML('<script src="/static/calendar/script3.js"></script>', rendered)


class MediaStaticfilesTests(BaseTestCase):
    # For context see https://github.com/EmilStenstrom/django-components/issues/522
    @override_settings(
        # Configure static files. The dummy files are set up in the `./static_root` dir.
        # The URL should have path prefix /static/.
        # NOTE: We don't need STATICFILES_DIRS, because we don't run collectstatic
        #       See https://docs.djangoproject.com/en/5.0/ref/settings/#std-setting-STATICFILES_DIRS
        STATIC_URL="static/",
        STATIC_ROOT=os.path.join(Path(__file__).resolve().parent, "static_root"),
        # `django.contrib.staticfiles` MUST be installed for staticfiles resolution to work.
        INSTALLED_APPS=[
            "django.contrib.staticfiles",
            "django_components",
        ],
    )
    def test_default_static_files_storage(self):
        """Test integration with Django's staticfiles app"""

        class MyMedia(Media):
            def render_js(self):
                tags: list[str] = []
                for path in self._js:  # type: ignore[attr-defined]
                    abs_path = self.absolute_path(path)  # type: ignore[attr-defined]
                    tags.append(f'<script defer src="{abs_path}"></script>')
                return tags

        class SimpleComponent(Component):
            template = """
                {% load component_tags %}
                {% component_js_dependencies %}
                {% component_css_dependencies %}
            """

            media_class = MyMedia

            class Media:
                css = "calendar/style.css"
                js = "calendar/script.js"

        rendered = SimpleComponent.render()

        # NOTE: Since we're using the default storage class for staticfiles, the files should
        # be searched as specified above (e.g. `calendar/script.js`) inside `static_root` dir.
        self.assertInHTML('<link href="/static/calendar/style.css" media="all" rel="stylesheet">', rendered)

        self.assertInHTML('<script defer src="/static/calendar/script.js"></script>', rendered)

    # For context see https://github.com/EmilStenstrom/django-components/issues/522
    @override_settings(
        # Configure static files. The dummy files are set up in the `./static_root` dir.
        # The URL should have path prefix /static/.
        # NOTE: We don't need STATICFILES_DIRS, because we don't run collectstatic
        #       See https://docs.djangoproject.com/en/5.0/ref/settings/#std-setting-STATICFILES_DIRS
        STATIC_URL="static/",
        STATIC_ROOT=os.path.join(Path(__file__).resolve().parent, "static_root"),
        # NOTE: STATICFILES_STORAGE is deprecated since 5.1, use STORAGES instead
        #       See https://docs.djangoproject.com/en/5.0/ref/settings/#staticfiles-storage
        STORAGES={
            # This was NOT changed
            "default": {
                "BACKEND": "django.core.files.storage.FileSystemStorage",
            },
            # This WAS changed so that static files are looked up by the `staticfiles.json`
            "staticfiles": {
                "BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage",
            },
        },
        # `django.contrib.staticfiles` MUST be installed for staticfiles resolution to work.
        INSTALLED_APPS=[
            "django.contrib.staticfiles",
            "django_components",
        ],
    )
    def test_manifest_static_files_storage(self):
        """Test integration with Django's staticfiles app and ManifestStaticFilesStorage"""

        class MyMedia(Media):
            def render_js(self):
                tags: list[str] = []
                for path in self._js:  # type: ignore[attr-defined]
                    abs_path = self.absolute_path(path)  # type: ignore[attr-defined]
                    tags.append(f'<script defer src="{abs_path}"></script>')
                return tags

        class SimpleComponent(Component):
            template = """
                {% load component_tags %}
                {% component_js_dependencies %}
                {% component_css_dependencies %}
            """

            media_class = MyMedia

            class Media:
                css = "calendar/style.css"
                js = "calendar/script.js"

        rendered = SimpleComponent.render()

        # NOTE: Since we're using ManifestStaticFilesStorage, we expect the rendered media to link
        # to the files as defined in staticfiles.json
        self.assertInHTML(
            '<link href="/static/calendar/style.0eeb72042b59.css" media="all" rel="stylesheet">', rendered
        )

        self.assertInHTML('<script defer src="/static/calendar/script.e1815e23e0ec.js"></script>', rendered)


class MediaRelativePathTests(BaseTestCase):
    class ParentComponent(Component):
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

    class VariableDisplay(Component):
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

    def setUp(self):
        super().setUp()
        registry.register(name="parent_component", component=self.ParentComponent)
        registry.register(name="variable_display", component=self.VariableDisplay)

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
        with autodiscover_with_cleanup(map_module=lambda p: f"tests.{p}" if p.startswith("components") else p):
            # Make sure that only relevant components are registered:
            comps_to_remove = [
                comp_name
                for comp_name in registry.all()
                if comp_name not in ["relative_file_component", "parent_component", "variable_display"]
            ]
            for comp_name in comps_to_remove:
                registry.unregister(comp_name)

            template_str: types.django_html = """
                {% load component_tags %}
                {% component_js_dependencies %}
                {% component_css_dependencies %}
                {% component name='relative_file_component' variable=variable / %}
            """
            template = Template(template_str)
            rendered = render_dependencies(template.render(Context({"variable": "test"})))

            self.assertInHTML('<link href="relative_file/relative_file.css" media="all" rel="stylesheet">', rendered)

            self.assertInHTML(
                """
                <form method="post">
                    <input type="text" name="variable" value="test">
                    <input type="submit">
                </form>
                """,
                rendered,
            )

            self.assertInHTML('<link href="relative_file/relative_file.css" media="all" rel="stylesheet">', rendered)

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
        with autodiscover_with_cleanup(map_module=lambda p: f"tests.{p}" if p.startswith("components") else p):
            registry.unregister("relative_file_pathobj_component")

            template_str: types.django_html = """
                {% load component_tags %}
                {% component_js_dependencies %}
                {% component_css_dependencies %}
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

    # Settings required for autodiscover to work
    @override_settings(
        BASE_DIR=Path(__file__).resolve().parent,
        STATICFILES_DIRS=[
            Path(__file__).resolve().parent / "components",
        ],
    )
    def test_component_with_relative_media_does_not_trigger_safestring_path_at__new__(self):
        """
        Test that, for the __html__ objects are not coerced into string throughout
        the class creation. This is important to allow to call `collectstatic` command.
        Because some users use `static` inside the `__html__` or `__str__` methods.
        So if we "render" the safestring using str() during component class creation (__new__),
        then we force to call `static`. And if this happens during `collectstatic` run,
        then this triggers an error, because `static` is called before the static files exist.

        https://github.com/EmilStenstrom/django-components/issues/522#issuecomment-2173577094
        """

        # Ensure that the module is executed again after import in autodiscovery
        if "tests.components.relative_file_pathobj.relative_file_pathobj" in sys.modules:
            del sys.modules["tests.components.relative_file_pathobj.relative_file_pathobj"]

        # Fix the paths, since the "components" dir is nested
        with autodiscover_with_cleanup(map_module=lambda p: f"tests.{p}" if p.startswith("components") else p):
            # Mark the PathObj instances of 'relative_file_pathobj_component' so they won't raise
            # error if PathObj.__str__ is triggered.
            CompCls = registry.get("relative_file_pathobj_component")
            CompCls.Media.js[0].throw_on_calling_str = False  # type: ignore
            CompCls.Media.css["all"][0].throw_on_calling_str = False  # type: ignore

            rendered = CompCls.render(kwargs={"variable": "abc"})

            self.assertInHTML('<input type="text" name="variable" value="abc">', rendered)
            self.assertInHTML('<link href="relative_file_pathobj.css" rel="stylesheet">', rendered)

            self.assertInHTML('<script type="module" src="relative_file_pathobj.js"></script>', rendered)
