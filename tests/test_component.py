import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from django.core.exceptions import ImproperlyConfigured
from django.template import Context, Template
from django.test import override_settings

# isort: off
from .django_test_setup import *  # NOQA
from .testutils import BaseTestCase, autodiscover_with_cleanup

# isort: on

from django_components import component, types


class ComponentTest(BaseTestCase):
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

    def test_empty_component(self):
        class EmptyComponent(component.Component):
            pass

        with self.assertRaises(ImproperlyConfigured):
            EmptyComponent("empty_component").get_template(Context({}))

    def test_simple_component(self):
        class SimpleComponent(component.Component):
            template: types.django_html = """
                Variable: <strong>{{ variable }}</strong>
            """

            def get_context_data(self, variable=None):
                return {
                    "variable": variable,
                }

            class Media:
                css = "style.css"
                js = "script.js"

        comp = SimpleComponent("simple_component")
        context = Context(comp.get_context_data(variable="test"))

        self.assertHTMLEqual(
            comp.render_dependencies(),
            """
                <link href="style.css" media="all" rel="stylesheet">
                <script src="script.js"></script>
            """,
        )

        self.assertHTMLEqual(
            comp.render(context),
            """
            Variable: <strong>test</strong>
            """,
        )

    def test_css_only_component(self):
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

    def test_js_only_component(self):
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

    def test_empty_media_component(self):
        class SimpleComponent(component.Component):
            template: types.django_html = """
                Variable: <strong>{{ variable }}</strong>
            """

            class Media:
                pass

        comp = SimpleComponent("simple_component")

        self.assertHTMLEqual(comp.render_dependencies(), "")

    def test_missing_media_component(self):
        class SimpleComponent(component.Component):
            template: types.django_html = """
                Variable: <strong>{{ variable }}</strong>
            """

        comp = SimpleComponent("simple_component")

        self.assertHTMLEqual(comp.render_dependencies(), "")

    def test_component_with_list_of_styles(self):
        class MultistyleComponent(component.Component):
            class Media:
                css = ["style.css", "style2.css"]
                js = ["script.js", "script2.js"]

        comp = MultistyleComponent("multistyle_component")

        self.assertHTMLEqual(
            comp.render_dependencies(),
            """
            <link href="style.css" media="all" rel="stylesheet">
            <link href="style2.css" media="all" rel="stylesheet">
            <script src="script.js"></script>
            <script src="script2.js"></script>
            """,
        )

    def test_component_with_filtered_template(self):
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

        comp = FilteredComponent("filtered_component")
        context = Context(comp.get_context_data(var1="test1", var2="test2"))

        self.assertHTMLEqual(
            comp.render(context),
            """
            Var1: <strong>test1</strong>
            Var2 (uppercased): <strong>TEST2</strong>
            """,
        )

    def test_component_with_dynamic_template(self):
        class SvgComponent(component.Component):
            def get_context_data(self, name, css_class="", title="", **attrs):
                return {
                    "name": name,
                    "css_class": css_class,
                    "title": title,
                    **attrs,
                }

            def get_template_name(self, context):
                return f"dynamic_{context['name']}.svg"

        comp = SvgComponent("svg_component")
        self.assertHTMLEqual(
            comp.render(Context(comp.get_context_data(name="svg1"))),
            """
            <svg>Dynamic1</svg>
            """,
        )
        self.assertHTMLEqual(
            comp.render(Context(comp.get_context_data(name="svg2"))),
            """
            <svg>Dynamic2</svg>
            """,
        )

    # Settings required for autodiscover to work
    @override_settings(
        BASE_DIR=Path(__file__).resolve().parent,
        STATICFILES_DIRS=[
            Path(__file__).resolve().parent / "components",
        ],
    )
    def test_component_with_relative_paths_as_subcomponent(self):
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

    def test_component_inside_slot(self):
        class SlottedComponent(component.Component):
            template: types.django_html = """
                {% load component_tags %}
                <custom-template>
                    <header>{% slot "header" %}Default header{% endslot %}</header>
                    <main>{% slot "main" %}Default main{% endslot %}</main>
                    <footer>{% slot "footer" %}Default footer{% endslot %}</footer>
                </custom-template>
            """

            def get_context_data(self, name: Optional[str] = None) -> Dict[str, Any]:
                return {
                    "name": name,
                }

        component.registry.register("test", SlottedComponent)

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "test" name='Igor' %}
                {% fill "header" %}
                    Name: {{ name }}
                {% endfill %}
                {% fill "main" %}
                    Day: {{ day }}
                {% endfill %}
                {% fill "footer" %}
                    {% component "test" name='Joe2' %}
                        {% fill "header" %}
                            Name2: {{ name }}
                        {% endfill %}
                        {% fill "main" %}
                            Day2: {{ day }}
                        {% endfill %}
                    {% endcomponent %}
                {% endfill %}
            {% endcomponent %}
        """
        self.template = Template(template_str)

        # {{ name }} should be "Jannete" everywhere
        rendered = self.template.render(Context({"day": "Monday", "name": "Jannete"}))
        self.assertHTMLEqual(
            rendered,
            """
            <custom-template>
                <header>Name: Jannete</header>
                <main>Day: Monday</main>
                <footer>
                    <custom-template>
                        <header>Name2: Jannete</header>
                        <main>Day2: Monday</main>
                        <footer>Default footer</footer>
                    </custom-template>
                </footer>
            </custom-template>
        """,
        )

    def test_fill_inside_fill_with_same_name(self):
        class SlottedComponent(component.Component):
            template: types.django_html = """
                {% load component_tags %}
                <custom-template>
                    <header>{% slot "header" %}Default header{% endslot %}</header>
                    <main>{% slot "main" %}Default main{% endslot %}</main>
                    <footer>{% slot "footer" %}Default footer{% endslot %}</footer>
                </custom-template>
            """

            def get_context_data(self, name: Optional[str] = None) -> Dict[str, Any]:
                return {
                    "name": name,
                }

        component.registry.register("test", SlottedComponent)

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "test" name='Igor' %}
                {% fill "header" %}
                    {% component "test" name='Joe2' %}
                        {% fill "header" %}
                            Name2: {{ name }}
                        {% endfill %}
                        {% fill "main" %}
                            Day2: {{ day }}
                        {% endfill %}
                        {% fill "footer" %}
                            XYZ
                        {% endfill %}
                    {% endcomponent %}
                {% endfill %}
                {% fill "footer" %}
                    WWW
                {% endfill %}
            {% endcomponent %}
        """
        self.template = Template(template_str)

        # {{ name }} should be "Jannete" everywhere
        rendered = self.template.render(Context({"day": "Monday", "name": "Jannete"}))
        self.assertHTMLEqual(
            rendered,
            """
            <custom-template>
                <header>
                    <custom-template>
                        <header>Name2: Jannete</header>
                        <main>Day2: Monday</main>
                        <footer>XYZ</footer>
                    </custom-template>
                </header>
                <main>Default main</main>
                <footer>WWW</footer>
            </custom-template>
            """,
        )

    @override_settings(
        COMPONENTS={
            "context_behavior": "isolated",
        },
    )
    def test_slots_of_top_level_comps_can_access_full_outer_ctx(self):
        class SlottedComponent(component.Component):
            template: types.django_html = """
                {% load component_tags %}
                <div>
                    <main>{% slot "main" default %}Easy to override{% endslot %}</main>
                </div>
            """

            def get_context_data(self, name: Optional[str] = None) -> Dict[str, Any]:
                return {
                    "name": name,
                }

        component.registry.register("test", SlottedComponent)

        template_str: types.django_html = """
            {% load component_tags %}
            <body>
                {% component "test" %}
                    ABC: {{ name }} {{ some }}
                {% endcomponent %}
            </body>
        """
        self.template = Template(template_str)

        nested_ctx = Context()
        # Check that the component can access vars across different context layers
        nested_ctx.push({"some": "var"})
        nested_ctx.push({"name": "carl"})
        rendered = self.template.render(nested_ctx)

        self.assertHTMLEqual(
            rendered,
            """
            <body>
                <div>
                    <main> ABC: carl var </main>
                </div>
            </body>
            """,
        )


class DuplicateSlotTest(BaseTestCase):
    class DuplicateSlotComponent(component.Component):
        template: types.django_html = """
            {% load component_tags %}
            <header>{% slot "header" %}Default header{% endslot %}</header>
             {# Slot name 'header' used twice. #}
            <main>{% slot "header" %}Default main header{% endslot %}</main>
            <footer>{% slot "footer" %}Default footer{% endslot %}</footer>
        """

        def get_context_data(self, name: Optional[str] = None) -> Dict[str, Any]:
            return {
                "name": name,
            }

    class DuplicateSlotNestedComponent(component.Component):
        template: types.django_html = """
            {% load component_tags %}
            {% slot "header" %}START{% endslot %}
            <div class="dashboard-component">
            {% component "calendar" date="2020-06-06" %}
                {% fill "header" %}  {# fills and slots with same name relate to diff. things. #}
                    {% slot "header" %}NESTED{% endslot %}
                {% endfill %}
                {% fill "body" %}Here are your to-do items for today:{% endfill %}
            {% endcomponent %}
            <ol>
                {% for item in items %}
                    <li>{{ item }}</li>
                    {% slot "header" %}LOOP {{ item }} {% endslot %}
                {% endfor %}
            </ol>
            </div>
        """

        def get_context_data(self, items: List) -> Dict[str, Any]:
            return {
                "items": items,
            }

    class CalendarComponent(component.Component):
        """Nested in ComponentWithNestedComponent"""

        template: types.django_html = """
            {% load component_tags %}
            <div class="calendar-component">
            <h1>
                {% slot "header" %}Today's date is <span>{{ date }}</span>{% endslot %}
            </h1>
            <main>
                {% slot "body" %}
                    You have no events today.
                {% endslot %}
            </main>
            </div>
        """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        component.registry.register(name="duplicate_slot", component=cls.DuplicateSlotComponent)
        component.registry.register(name="duplicate_slot_nested", component=cls.DuplicateSlotNestedComponent)
        component.registry.register(name="calendar", component=cls.CalendarComponent)

    def test_duplicate_slots(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component "duplicate_slot" %}
                {% fill "header" %}
                    Name: {{ name }}
                {% endfill %}
                {% fill "footer" %}
                    Hello
                {% endfill %}
            {% endcomponent %}
        """
        self.template = Template(template_str)

        rendered = self.template.render(Context({"name": "Jannete"}))
        self.assertHTMLEqual(
            rendered,
            """
            <header>Name: Jannete</header>
            <main>Name: Jannete</main>
            <footer>Hello</footer>
            """,
        )

    def test_duplicate_slots_fallback(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component "duplicate_slot" %}
            {% endcomponent %}
        """
        self.template = Template(template_str)
        rendered = self.template.render(Context({}))

        # NOTE: Slots should have different fallbacks even though they use the same name
        self.assertHTMLEqual(
            rendered,
            """
            <header>Default header</header>
            <main>Default main header</main>
            <footer>Default footer</footer>
            """,
        )

    def test_duplicate_slots_nested(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component "duplicate_slot_nested" items=items %}
                {% fill "header" %}
                    OVERRIDDEN!
                {% endfill %}
            {% endcomponent %}
        """
        self.template = Template(template_str)
        rendered = self.template.render(Context({"items": [1, 2, 3]}))

        # NOTE: Slots should have different fallbacks even though they use the same name
        self.assertHTMLEqual(
            rendered,
            """
            OVERRIDDEN!
            <div class="dashboard-component">
                <div class="calendar-component">
                    <h1>
                        OVERRIDDEN!
                    </h1>
                    <main>
                        Here are your to-do items for today:
                    </main>
                </div>

                <ol>
                    <li>1</li>
                    OVERRIDDEN!
                    <li>2</li>
                    OVERRIDDEN!
                    <li>3</li>
                    OVERRIDDEN!
                </ol>
            </div>
            """,
        )

    def test_duplicate_slots_nested_fallback(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component "duplicate_slot_nested" items=items %}
            {% endcomponent %}
        """
        self.template = Template(template_str)
        rendered = self.template.render(Context({"items": [1, 2, 3]}))

        # NOTE: Slots should have different fallbacks even though they use the same name
        self.assertHTMLEqual(
            rendered,
            """
            START
            <div class="dashboard-component">
                <div class="calendar-component">
                    <h1>
                        NESTED
                    </h1>
                    <main>
                        Here are your to-do items for today:
                    </main>
                </div>

                <ol>
                    <li>1</li>
                    LOOP 1
                    <li>2</li>
                    LOOP 2
                    <li>3</li>
                    LOOP 3
                </ol>
            </div>
            """,
        )


class InlineComponentTest(BaseTestCase):
    def test_inline_html_component(self):
        class InlineHTMLComponent(component.Component):
            template = "<div class='inline'>Hello Inline</div>"

        comp = InlineHTMLComponent("inline_html_component")
        self.assertHTMLEqual(
            comp.render(Context({})),
            "<div class='inline'>Hello Inline</div>",
        )

    def test_html_and_css_only(self):
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

    def test_html_and_js_only(self):
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

    def test_html_string_with_css_js_files(self):
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

    def test_html_js_string_with_css_file(self):
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

    def test_html_css_string_with_js_file(self):
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

    def test_component_with_variable_in_html(self):
        class VariableHTMLComponent(component.Component):
            def get_template(self, context):
                return Template("<div class='variable-html'>{{ variable }}</div>")

        comp = VariableHTMLComponent("variable_html_component")
        context = Context({"variable": "Dynamic Content"})
        self.assertHTMLEqual(
            comp.render(context),
            "<div class='variable-html'>Dynamic Content</div>",
        )


class ComponentMediaTests(BaseTestCase):
    def test_component_media_with_strings(self):
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

    def test_component_media_with_lists(self):
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

    def test_component_media_with_dict_and_list(self):
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

    def test_component_media_with_dict_with_list_and_list(self):
        class SimpleComponent(component.Component):
            class Media:
                css = {"all": ["path/to/style.css"]}
                js = ["path/to/script.js"]

        comp = SimpleComponent("")
        self.assertHTMLEqual(
            comp.render_dependencies(),
            """
            <link href="path/to/style.css" media="all" rel="stylesheet">
            <script src="path/to/script.js"></script>
            """,
        )

    # Settings required for autodiscover to work
    @override_settings(
        BASE_DIR=Path(__file__).resolve().parent,
        STATICFILES_DIRS=[
            Path(__file__).resolve().parent / "components",
        ],
    )
    def test_component_media_with_dict_with_relative_paths(self):
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


class ComponentIsolationTests(BaseTestCase):
    def setUp(self):
        class SlottedComponent(component.Component):
            template: types.django_html = """
                {% load component_tags %}
                <custom-template>
                    <header>{% slot "header" %}Default header{% endslot %}</header>
                    <main>{% slot "main" %}Default main{% endslot %}</main>
                    <footer>{% slot "footer" %}Default footer{% endslot %}</footer>
                </custom-template>
            """

        component.registry.register("test", SlottedComponent)

    def test_instances_of_component_do_not_share_slots(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component "test" %}
                {% fill "header" %}Override header{% endfill %}
            {% endcomponent %}
            {% component "test" %}
                {% fill "main" %}Override main{% endfill %}
            {% endcomponent %}
            {% component "test" %}
                {% fill "footer" %}Override footer{% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)

        template.render(Context({}))
        rendered = template.render(Context({}))

        self.assertHTMLEqual(
            rendered,
            """
            <custom-template>
                <header>Override header</header>
                <main>Default main</main>
                <footer>Default footer</footer>
            </custom-template>
            <custom-template>
                <header>Default header</header>
                <main>Override main</main>
                <footer>Default footer</footer>
            </custom-template>
            <custom-template>
                <header>Default header</header>
                <main>Default main</main>
                <footer>Override footer</footer>
            </custom-template>
        """,
        )


class SlotBehaviorTests(BaseTestCase):
    # NOTE: This is standalone function instead of setUp, so we can configure
    # Django settings per test with `@override_settings`
    def make_template(self) -> Template:
        class SlottedComponent(component.Component):
            template: types.django_html = """
                {% load component_tags %}
                <custom-template>
                    <header>{% slot "header" %}Default header{% endslot %}</header>
                    <main>{% slot "main" %}Default main{% endslot %}</main>
                    <footer>{% slot "footer" %}Default footer{% endslot %}</footer>
                </custom-template>
            """

            def get_context_data(self, name: Optional[str] = None) -> Dict[str, Any]:
                return {
                    "name": name,
                }

        component.registry.register("test", SlottedComponent)

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "test" name='Igor' %}
                {% fill "header" %}
                    Name: {{ name }}
                {% endfill %}
                {% fill "main" %}
                    Day: {{ day }}
                {% endfill %}
                {% fill "footer" %}
                    {% component "test" name='Joe2' %}
                        {% fill "header" %}
                            Name2: {{ name }}
                        {% endfill %}
                        {% fill "main" %}
                            Day2: {{ day }}
                        {% endfill %}
                    {% endcomponent %}
                {% endfill %}
            {% endcomponent %}
        """
        return Template(template_str)

    @override_settings(
        COMPONENTS={"context_behavior": "django"},
    )
    def test_slot_context__django(self):
        template = self.make_template()
        # {{ name }} should be neither Jannete not empty, because overriden everywhere
        rendered = template.render(Context({"day": "Monday", "name": "Jannete"}))
        self.assertHTMLEqual(
            rendered,
            """
            <custom-template>
                <header>Name: Igor</header>
                <main>Day: Monday</main>
                <footer>
                    <custom-template>
                        <header>Name2: Joe2</header>
                        <main>Day2: Monday</main>
                        <footer>Default footer</footer>
                    </custom-template>
                </footer>
            </custom-template>
        """,
        )

        # {{ name }} should be effectively the same as before, because overriden everywhere
        rendered2 = template.render(Context({"day": "Monday"}))
        self.assertHTMLEqual(rendered2, rendered)

    @override_settings(
        COMPONENTS={"context_behavior": "isolated"},
    )
    def test_slot_context__isolated(self):
        template = self.make_template()
        # {{ name }} should be "Jannete" everywhere
        rendered = template.render(Context({"day": "Monday", "name": "Jannete"}))
        self.assertHTMLEqual(
            rendered,
            """
            <custom-template>
                <header>Name: Jannete</header>
                <main>Day: Monday</main>
                <footer>
                    <custom-template>
                        <header>Name2: Jannete</header>
                        <main>Day2: Monday</main>
                        <footer>Default footer</footer>
                    </custom-template>
                </footer>
            </custom-template>
        """,
        )

        # {{ name }} should be empty everywhere
        rendered2 = template.render(Context({"day": "Monday"}))
        self.assertHTMLEqual(
            rendered2,
            """
            <custom-template>
                <header>Name: </header>
                <main>Day: Monday</main>
                <footer>
                    <custom-template>
                        <header>Name2: </header>
                        <main>Day2: Monday</main>
                        <footer>Default footer</footer>
                    </custom-template>
                </footer>
            </custom-template>
        """,
        )


class AggregateInputTests(BaseTestCase):
    def test_agg_input_accessible_in_get_context_data(self):
        @component.register("test")
        class AttrsComponent(component.Component):
            template: types.django_html = """
                {% load component_tags %}
                <div>
                    attrs: {{ attrs|safe }}
                    my_dict: {{ my_dict|safe }}
                </div>
            """

            def get_context_data(self, *args, attrs, my_dict):
                return {"attrs": attrs, "my_dict": my_dict}

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "test" attrs:@click.stop="dispatch('click_event')" attrs:x-data="{hello: 'world'}" attrs:class=class_var my_dict:one=2 %}
            {% endcomponent %}
        """  # noqa: E501
        template = Template(template_str)
        rendered = template.render(Context({"class_var": "padding-top-8"}))
        self.assertHTMLEqual(
            rendered,
            """
            <div>
                attrs: {'@click.stop': "dispatch('click_event')", 'x-data': "{hello: 'world'}", 'class': 'padding-top-8'}
                my_dict: {'one': 2}
            </div>
            """,  # noqa: E501
        )
