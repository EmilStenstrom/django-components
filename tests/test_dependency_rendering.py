from unittest.mock import Mock

from django.http import HttpResponseNotModified
from django.template import Template
from django.test import override_settings

from django_components import component
from django_components.middleware import ComponentDependencyMiddleware

from .django_test_setup import *  # NOQA
from .test_templatetags import SimpleComponent
from .testutils import Django30CompatibleSimpleTestCase as SimpleTestCase
from .testutils import create_and_process_template_response


class SimpleComponentAlternate(component.Component):
    template_name = "simple_template.html"

    def get_context_data(self, variable):
        return {}

    class Media:
        css = "style2.css"
        js = "script2.js"


class SimpleComponentWithSharedDependency(component.Component):
    template_name = "simple_template.html"

    def get_context_data(self, variable, variable2="default"):
        return {}

    class Media:
        css = ["style.css", "style2.css"]
        js = ["script.js", "script2.js"]


class MultistyleComponent(component.Component):
    template_name = "simple_template.html"

    class Media:
        css = ["style.css", "style2.css"]
        js = ["script.js", "script2.js"]


@override_settings(COMPONENTS={"RENDER_DEPENDENCIES": True})
class ComponentMediaRenderingTests(SimpleTestCase):
    def setUp(self):
        # NOTE: component.registry is global, so need to clear before each test
        component.registry.clear()

    def test_no_dependencies_when_no_components_used(self):
        component.registry.register(name="test", component=SimpleComponent)

        template = Template(
            "{% load component_tags %}{% component_dependencies %}"
        )
        rendered = create_and_process_template_response(template)
        self.assertInHTML('<script src="script.js">', rendered, count=0)
        self.assertInHTML(
            '<link href="style.css" media="all" rel="stylesheet"/>',
            rendered,
            count=0,
        )

    def test_no_js_dependencies_when_no_components_used(self):
        component.registry.register(name="test", component=SimpleComponent)

        template = Template(
            "{% load component_tags %}{% component_js_dependencies %}"
        )
        rendered = create_and_process_template_response(template)
        self.assertInHTML('<script src="script.js">', rendered, count=0)

    def test_no_css_dependencies_when_no_components_used(self):
        component.registry.register(name="test", component=SimpleComponent)

        template = Template(
            "{% load component_tags %}{% component_css_dependencies %}"
        )
        rendered = create_and_process_template_response(template)
        self.assertInHTML(
            '<link href="style.css" media="all" rel="stylesheet"/>',
            rendered,
            count=0,
        )

    def test_preload_dependencies_render_when_no_components_used(self):
        component.registry.register(name="test", component=SimpleComponent)

        template = Template(
            "{% load component_tags %}{% component_dependencies preload='test' %}"
        )
        rendered = create_and_process_template_response(template)
        self.assertInHTML('<script src="script.js">', rendered, count=1)
        self.assertInHTML(
            '<link href="style.css" media="all" rel="stylesheet"/>',
            rendered,
            count=1,
        )

    def test_preload_css_dependencies_render_when_no_components_used(self):
        component.registry.register(name="test", component=SimpleComponent)

        template = Template(
            "{% load component_tags %}{% component_css_dependencies preload='test' %}"
        )
        rendered = create_and_process_template_response(template)
        self.assertInHTML(
            '<link href="style.css" media="all" rel="stylesheet"/>',
            rendered,
            count=1,
        )

    def test_single_component_dependencies_render_when_used(self):
        component.registry.register(name="test", component=SimpleComponent)

        template = Template(
            "{% load component_tags %}{% component_dependencies %}"
            "{% component 'test' variable='foo' %}"
        )
        rendered = create_and_process_template_response(template)
        self.assertInHTML(
            '<link href="style.css" media="all" rel="stylesheet"/>',
            rendered,
            count=1,
        )
        self.assertInHTML('<script src="script.js">', rendered, count=1)

    def test_single_component_with_dash_or_slash_in_name(self):
        component.registry.register(name="test", component=SimpleComponent)

        template = Template(
            "{% load component_tags %}{% component_dependencies %}"
            "{% component 'test' variable='foo' %}"
        )
        rendered = create_and_process_template_response(template)
        self.assertInHTML(
            '<link href="style.css" media="all" rel="stylesheet"/>',
            rendered,
            count=1,
        )
        self.assertInHTML('<script src="script.js">', rendered, count=1)

    def test_preload_dependencies_render_once_when_used(self):
        component.registry.register(name="test", component=SimpleComponent)

        template = Template(
            "{% load component_tags %}{% component_dependencies preload='test' %}"
            "{% component 'test' variable='foo' %}"
        )
        rendered = create_and_process_template_response(template)
        self.assertInHTML(
            '<link href="style.css" media="all" rel="stylesheet"/>',
            rendered,
            count=1,
        )
        self.assertInHTML('<script src="script.js">', rendered, count=1)

    def test_placeholder_removed_when_single_component_rendered(self):
        component.registry.register(name="test", component=SimpleComponent)

        template = Template(
            "{% load component_tags %}{% component_dependencies %}"
            "{% component 'test' variable='foo' %}"
        )
        rendered = create_and_process_template_response(template)
        self.assertNotIn("_RENDERED", rendered)

    def test_placeholder_removed_when_preload_rendered(self):
        component.registry.register(name="test", component=SimpleComponent)

        template = Template(
            "{% load component_tags %}{% component_dependencies preload='test' %}"
        )
        rendered = create_and_process_template_response(template)
        self.assertNotIn("_RENDERED", rendered)

    def test_single_component_css_dependencies(self):
        component.registry.register(name="test", component=SimpleComponent)

        template = Template(
            "{% load component_tags %}{% component_css_dependencies %}"
            "{% component 'test' variable='foo' %}"
        )
        rendered = create_and_process_template_response(template)
        self.assertInHTML(
            '<link href="style.css" media="all" rel="stylesheet"/>',
            rendered,
            count=1,
        )

    def test_single_component_js_dependencies(self):
        component.registry.register(name="test", component=SimpleComponent)

        template = Template(
            "{% load component_tags %}{% component_js_dependencies %}"
            "{% component 'test' variable='foo' %}"
        )
        rendered = create_and_process_template_response(template)
        self.assertInHTML('<script src="script.js">', rendered, count=1)

    def test_all_dependencies_are_rendered_for_component_with_multiple_dependencies(
        self,
    ):
        component.registry.register(name="test", component=MultistyleComponent)
        template = Template(
            "{% load component_tags %}{% component_dependencies %}{% component 'test' %}"
        )
        rendered = create_and_process_template_response(template)
        self.assertInHTML('<script src="script.js">', rendered, count=1)
        self.assertInHTML('<script src="script2.js">', rendered, count=1)
        self.assertInHTML(
            '<link href="style.css" media="all" rel="stylesheet"/>',
            rendered,
            count=1,
        )
        self.assertInHTML(
            '<link href="style2.css" media="all" rel="stylesheet"/>',
            rendered,
            count=1,
        )

    def test_all_js_dependencies_are_rendered_for_component_with_multiple_dependencies(
        self,
    ):
        component.registry.register(name="test", component=MultistyleComponent)
        template = Template(
            "{% load component_tags %}{% component_js_dependencies %}{% component 'test' %}"
        )
        rendered = create_and_process_template_response(template)
        self.assertInHTML('<script src="script.js">', rendered, count=1)
        self.assertInHTML('<script src="script2.js">', rendered, count=1)
        self.assertInHTML(
            '<link href="style.css" media="all" rel="stylesheet"/>',
            rendered,
            count=0,
        )
        self.assertInHTML(
            '<link href="style2.css" media="all" rel="stylesheet"/>',
            rendered,
            count=0,
        )

    def test_all_css_dependencies_are_rendered_for_component_with_multiple_dependencies(
        self,
    ):
        component.registry.register(name="test", component=MultistyleComponent)
        template = Template(
            "{% load component_tags %}{% component_css_dependencies %}{% component 'test' %}"
        )
        rendered = create_and_process_template_response(template)
        self.assertInHTML('<script src="script.js">', rendered, count=0)
        self.assertInHTML('<script src="script2.js">', rendered, count=0)
        self.assertInHTML(
            '<link href="style.css" media="all" rel="stylesheet"/>',
            rendered,
            count=1,
        )
        self.assertInHTML(
            '<link href="style2.css" media="all" rel="stylesheet"/>',
            rendered,
            count=1,
        )

    def test_no_dependencies_with_multiple_unused_components(self):
        component.registry.register(name="test1", component=SimpleComponent)
        component.registry.register(
            name="test2", component=SimpleComponentAlternate
        )

        template = Template(
            "{% load component_tags %}{% component_dependencies %}"
        )
        rendered = create_and_process_template_response(template)
        self.assertInHTML('<script src="script.js">', rendered, count=0)
        self.assertInHTML('<script src="script2.js">', rendered, count=0)
        self.assertInHTML(
            '<link href="style.css" media="all" rel="stylesheet"/>',
            rendered,
            count=0,
        )
        self.assertInHTML(
            '<link href="style2.css" media="all" rel="stylesheet"/>',
            rendered,
            count=0,
        )

    def test_correct_css_dependencies_with_multiple_components(self):
        component.registry.register(name="test1", component=SimpleComponent)
        component.registry.register(
            name="test2", component=SimpleComponentAlternate
        )

        template = Template(
            "{% load component_tags %}{% component_css_dependencies %}"
            "{% component 'test1' 'variable' %}"
        )
        rendered = create_and_process_template_response(template)
        self.assertInHTML(
            '<link href="style.css" media="all" rel="stylesheet"/>',
            rendered,
            count=1,
        )
        self.assertInHTML(
            '<link href="style2.css" media="all" rel="stylesheet"/>',
            rendered,
            count=0,
        )

    def test_correct_js_dependencies_with_multiple_components(self):
        component.registry.register(name="test1", component=SimpleComponent)
        component.registry.register(
            name="test2", component=SimpleComponentAlternate
        )

        template = Template(
            "{% load component_tags %}{% component_js_dependencies %}"
            "{% component 'test1' 'variable' %}"
        )
        rendered = create_and_process_template_response(template)
        self.assertInHTML('<script src="script.js">', rendered, count=1)
        self.assertInHTML('<script src="script2.js">', rendered, count=0)

    def test_correct_dependencies_with_multiple_components(self):
        component.registry.register(name="test1", component=SimpleComponent)
        component.registry.register(
            name="test2", component=SimpleComponentAlternate
        )

        template = Template(
            "{% load component_tags %}{% component_dependencies %}"
            "{% component 'test2' variable='variable' %}"
        )
        rendered = create_and_process_template_response(template)
        self.assertInHTML('<script src="script.js">', rendered, count=0)
        self.assertInHTML('<script src="script2.js">', rendered, count=1)
        self.assertInHTML(
            '<link href="style.css" media="all" rel="stylesheet"/>',
            rendered,
            count=0,
        )
        self.assertInHTML(
            '<link href="style2.css" media="all" rel="stylesheet"/>',
            rendered,
            count=1,
        )

    def test_shared_dependencies_rendered_once(self):
        component.registry.register(name="test1", component=SimpleComponent)
        component.registry.register(
            name="test2", component=SimpleComponentAlternate
        )
        component.registry.register(
            name="test3", component=SimpleComponentWithSharedDependency
        )

        template = Template(
            "{% load component_tags %}{% component_dependencies %}"
            "{% component 'test1' variable='variable' %}{% component 'test2' variable='variable' %}"
            "{% component 'test1' variable='variable' %}"
        )
        rendered = create_and_process_template_response(template)
        self.assertInHTML('<script src="script.js">', rendered, count=1)
        self.assertInHTML('<script src="script2.js">', rendered, count=1)
        self.assertInHTML(
            '<link href="style.css" media="all" rel="stylesheet"/>',
            rendered,
            count=1,
        )
        self.assertInHTML(
            '<link href="style2.css" media="all" rel="stylesheet"/>',
            rendered,
            count=1,
        )

    def test_placeholder_removed_when_multiple_component_rendered(self):
        component.registry.register(name="test1", component=SimpleComponent)
        component.registry.register(
            name="test2", component=SimpleComponentAlternate
        )
        component.registry.register(
            name="test3", component=SimpleComponentWithSharedDependency
        )

        template = Template(
            "{% load component_tags %}{% component_dependencies %}"
            "{% component 'test1' variable='variable' %}{% component 'test2' variable='variable' %}"
            "{% component 'test1' variable='variable' %}"
        )
        rendered = create_and_process_template_response(template)
        self.assertNotIn("_RENDERED", rendered)

    def test_middleware_response_without_content_type(self):
        response = HttpResponseNotModified()
        middleware = ComponentDependencyMiddleware(
            get_response=lambda _: response
        )
        request = Mock()
        self.assertEqual(response, middleware(request=request))

    def test_middleware_response_with_components_with_slash_dash_and_underscore(
        self,
    ):
        component_names = [
            "test-component",
            "test/component",
            "test_component",
        ]
        for component_name in component_names:
            component.registry.register(
                name=component_name, component=SimpleComponent
            )
            template = Template(
                "{% load component_tags %}"
                "{% component_js_dependencies %}"
                "{% component_css_dependencies %}"
                f"{{% component '{component_name}' variable='value' %}}"
            )
            rendered = create_and_process_template_response(template)
            self.assertHTMLEqual(
                rendered,
                (
                    '<script src="script.js"></script>'
                    '<link href="style.css" media="all" rel="stylesheet">'
                    "Variable: <strong>value</strong>\n"
                ),
            )
