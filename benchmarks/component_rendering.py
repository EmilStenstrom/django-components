from time import perf_counter

from django.template import Context, Template

from django_components import Component, registry, types
from django_components.dependencies import CSS_DEPENDENCY_PLACEHOLDER, JS_DEPENDENCY_PLACEHOLDER
from tests.django_test_setup import *  # NOQA
from tests.testutils import BaseTestCase, create_and_process_template_response


class SlottedComponent(Component):
    template: types.django_html = """
        {% load component_tags %}
        <custom-template>
            <header>{% slot "header" %}Default header{% endslot %}</header>
            <main>{% slot "main" %}Default main{% endslot %}</main>
            <footer>{% slot "footer" %}Default footer{% endslot %}</footer>
        </custom-template>
    """


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
        css = {"all": ["style.css"]}
        js = ["script.js"]


class BreadcrumbComponent(Component):
    template: types.django_html = """
        <div class="breadcrumb-container">
            <nav class="breadcrumbs">
                <ol typeof="BreadcrumbList" vocab="https://schema.org/" aria-label="breadcrumbs">
                    {% for label, url in links %}
                        <li property="itemListElement" typeof="ListItem">
                            <a class="breadcrumb-current-page" property="item" typeof="WebPage" href="{{ url }}">
                                <span property="name">{{ label }}</span>
                            </a>
                            <meta property="position" content="4">
                        </li>
                    {% endfor %}
                </ol>
            </nav>
        </div>
    """

    LINKS = [
        (
            "https://developer.mozilla.org/en-US/docs/Learn",
            "Learn web development",
        ),
        (
            "https://developer.mozilla.org/en-US/docs/Learn/HTML",
            "Structuring the web with HTML",
        ),
        (
            "https://developer.mozilla.org/en-US/docs/Learn/HTML/Introduction_to_HTML",
            "Introduction to HTML",
        ),
        (
            "https://developer.mozilla.org/en-US/docs/Learn/HTML/Introduction_to_HTML/Document_and_website_structure",
            "Document and website structure",
        ),
    ]

    def get_context_data(self, items):
        if items > 4:
            items = 4
        elif items < 0:
            items = 0
        return {"links": self.LINKS[: items - 1]}

    class Media:
        css = {"all": ["test.css"]}
        js = ["test.js"]


EXPECTED_CSS = """<link href="test.css" media="all" rel="stylesheet">"""
EXPECTED_JS = """<script src="test.js"></script>"""


class RenderBenchmarks(BaseTestCase):
    def setUp(self):
        registry.clear()
        registry.register("test_component", SlottedComponent)
        registry.register("inner_component", SimpleComponent)
        registry.register("breadcrumb_component", BreadcrumbComponent)

    @staticmethod
    def timed_loop(func, iterations=1000):
        """Run func iterations times, and return the time in ms per iteration."""
        start_time = perf_counter()
        for _ in range(iterations):
            func()
        end_time = perf_counter()
        total_elapsed = end_time - start_time  # NOQA
        return total_elapsed * 1000 / iterations

    def test_render_time_for_small_component(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test_component' %}
                {% slot "header" %}
                    {% component 'inner_component' variable='foo' %}{% endcomponent %}
                {% endslot %}
            {% endcomponent %}
        """
        template = Template(template_str)

        print(f"{self.timed_loop(lambda: template.render(Context({})))} ms per iteration")

    def test_middleware_time_with_dependency_for_small_page(self):
        template_str: types.django_html = """
            {% load component_tags %}{% component_dependencies %}
            {% component 'test_component' %}
                {% slot "header" %}
                    {% component 'inner_component' variable='foo' %}{% endcomponent %}
                {% endslot %}
            {% endcomponent %}
        """
        template = Template(template_str)
        # Sanity tests
        response_content = create_and_process_template_response(template)
        self.assertNotIn(CSS_DEPENDENCY_PLACEHOLDER, response_content)
        self.assertNotIn(JS_DEPENDENCY_PLACEHOLDER, response_content)
        self.assertIn("style.css", response_content)
        self.assertIn("script.js", response_content)

        without_middleware = self.timed_loop(
            lambda: create_and_process_template_response(template, use_middleware=False)
        )
        with_middleware = self.timed_loop(lambda: create_and_process_template_response(template, use_middleware=True))

        print("Small page middleware test")
        self.report_results(with_middleware, without_middleware)

    def test_render_time_with_dependency_for_large_page(self):
        from django.template.loader import get_template

        template = get_template("mdn_complete_page.html")
        response_content = create_and_process_template_response(template, {})
        self.assertNotIn(CSS_DEPENDENCY_PLACEHOLDER, response_content)
        self.assertNotIn(JS_DEPENDENCY_PLACEHOLDER, response_content)
        self.assertIn("test.css", response_content)
        self.assertIn("test.js", response_content)

        without_middleware = self.timed_loop(
            lambda: create_and_process_template_response(template, {}, use_middleware=False)
        )
        with_middleware = self.timed_loop(
            lambda: create_and_process_template_response(template, {}, use_middleware=True)
        )

        print("Large page middleware test")
        self.report_results(with_middleware, without_middleware)

    @staticmethod
    def report_results(with_middleware, without_middleware):
        print(f"Middleware active\t\t{with_middleware:.3f} ms per iteration")
        print(f"Middleware inactive\t{without_middleware:.3f} ms per iteration")
        time_difference = with_middleware - without_middleware
        if without_middleware > with_middleware:
            print(f"Decrease of {-100 * time_difference / with_middleware:.2f}%")
        else:
            print(f"Increase of {100 * time_difference / without_middleware:.2f}%")
