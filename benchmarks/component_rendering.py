from time import perf_counter

from django.template import Context, Template
from django.test import override_settings

from django_components import component
from django_components.middleware import CSS_DEPENDENCY_PLACEHOLDER, JS_DEPENDENCY_PLACEHOLDER
from tests.django_test_setup import *  # NOQA
from tests.testutils import BaseTestCase
from tests.testutils import create_and_process_template_response


class SlottedComponent(component.Component):
    template_name = "slotted_template.html"


class SimpleComponent(component.Component):
    template_name = "simple_template.html"

    def get_context_data(self, variable, variable2="default"):
        return {
            "variable": variable,
            "variable2": variable2,
        }

    class Media:
        css = {"all": ["style.css"]}
        js = ["script.js"]


class BreadcrumbComponent(component.Component):
    template_name = "mdn_component_template.html"

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


@override_settings(COMPONENTS={"RENDER_DEPENDENCIES": True})
class RenderBenchmarks(BaseTestCase):
    def setUp(self):
        component.registry.clear()
        component.registry.register("test_component", SlottedComponent)
        component.registry.register("inner_component", SimpleComponent)
        component.registry.register("breadcrumb_component", BreadcrumbComponent)

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
        template = Template(
            """
            {% load component_tags %}
            {% component 'test_component' %}
                {% slot "header" %}
                    {% component 'inner_component' variable='foo' %}{% endcomponent %}
                {% endslot %}
            {% endcomponent %}
        """
        )

        print(f"{self.timed_loop(lambda: template.render(Context({})))} ms per iteration")

    def test_middleware_time_with_dependency_for_small_page(self):
        template = Template(
            """
            {% load component_tags %}{% component_dependencies %}
            {% component 'test_component' %}
                {% slot "header" %}
                    {% component 'inner_component' variable='foo' %}{% endcomponent %}
                {% endslot %}
            {% endcomponent %}
        """
        )
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
