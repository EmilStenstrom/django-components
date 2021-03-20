from django.template import Template
from django.test import override_settings

from .django_test_setup import *  # NOQA
from django_components import component

from .test_templatetags import SimpleComponent
from .testutils import create_and_process_template_response, Django30CompatibleSimpleTestCase as SimpleTestCase


class SimpleComponentAlternate(component.Component):
    def context(self, variable):
        return {}

    def template(self, context):
        return "simple_template.html"

    class Media:
        css = {"all": ["style2.css"]}
        js = ["script2.js"]


class SimpleComponentWithSharedDependency(component.Component):
    def context(self, variable, variable2="default"):
        return {
            "variable": variable,
            "variable2": variable2,
        }

    def template(self, context):
        return "simple_template.html"

    class Media:
        css = {"all": ["style.css", "style2.css"]}
        js = ["script.js", "script2.js"]


class MultistyleComponent(component.Component):
    def template(self, context):
        return "simple_template.html"

    class Media:
        css = {"all": ["style.css", "style2.css"]}
        js = ["script.js", "script2.js"]


@override_settings(COMPONENTS={'RENDER_DEPENDENCIES': True})
class ComponentMediaRenderingTests(SimpleTestCase):
    def setUp(self):
        # NOTE: component.registry is global, so need to clear before each test
        component.registry.clear()

    def assert_script_count(self, rendered, script_name, count):
        """Assert that named script is included in rendered HTML in either old or new Django format.

            New format: '<script src="{}"></script>'
            Old format: '<script type="text/javascript" src="{}"></script>'"""
        try:
            self.assertInHTML('<script src="{}"></script>'.format(script_name), rendered, count=count)
        except AssertionError:
            self.assertInHTML('<script type="text/javascript" src="{}"></script>'.format(script_name),
                              rendered, count=count)

    def assert_stylesheet_count(self, rendered, stylesheet_name, count):
        """Assert that named stylesheet is included in rendered HTML in either old or new Django format.

            New format: '<link href="{}" type="text/css" media="{}" rel="stylesheet">'
            Old format: '<link href="{}" type="text/css" media="{}" rel="stylesheet">'"""
        try:
            self.assertInHTML('<link href="{}" type="text/css" media="all" rel="stylesheet">'.format(stylesheet_name),
                              rendered, count=count)
        except AssertionError:
            self.assertInHTML(
                '<link href="{}" type="text/css" media="all" rel="stylesheet" />'.format(stylesheet_name),
                rendered, count=count)

    def test_no_dependencies_when_no_components_used(self):
        component.registry.register(name="test", component=SimpleComponent)

        template = Template("{% load component_tags %}{% component_dependencies %}")
        response = create_and_process_template_response(template)
        rendered = response.content.decode('utf-8')
        self.assert_script_count(rendered, 'script.js', 0)
        self.assert_stylesheet_count(rendered, 'style.css', 0)

    def test_no_js_dependencies_when_no_components_used(self):
        component.registry.register(name="test", component=SimpleComponent)

        template = Template("{% load component_tags %}{% component_js_dependencies %}")
        response = create_and_process_template_response(template)
        rendered = response.content.decode('utf-8')
        self.assert_script_count(rendered, 'script.js', 0)

    def test_no_css_dependencies_when_no_components_used(self):
        component.registry.register(name="test", component=SimpleComponent)

        template = Template("{% load component_tags %}{% component_css_dependencies %}")
        response = create_and_process_template_response(template)
        rendered = response.content.decode('utf-8')
        self.assert_stylesheet_count(rendered, 'style.css', 0)

    def test_single_component_dependencies_render_when_used(self):
        component.registry.register(name="test", component=SimpleComponent)

        template = Template("{% load component_tags %}{% component_dependencies %}"
                            "{% component 'test' variable='foo' %}")
        response = create_and_process_template_response(template)
        rendered = response.content.decode('utf-8')
        print(rendered)
        self.assert_stylesheet_count(rendered, 'style.css', 1)
        self.assert_script_count(rendered, 'script.js', 1)

    def test_single_component_css_dependencies(self):
        component.registry.register(name="test", component=SimpleComponent)

        template = Template("{% load component_tags %}{% component_css_dependencies %}"
                            "{% component 'test' variable='foo' %}")
        response = create_and_process_template_response(template)
        rendered = response.content.decode('utf-8')
        self.assert_stylesheet_count(rendered, 'style.css', 1)

    def test_single_component_js_dependencies(self):
        component.registry.register(name="test", component=SimpleComponent)

        template = Template("{% load component_tags %}{% component_js_dependencies %}"
                            "{% component 'test' variable='foo' %}")
        response = create_and_process_template_response(template)
        rendered = response.content.decode('utf-8')
        self.assert_script_count(rendered, 'script.js', 1)

    def test_all_dependencies_are_rendered_for_component_with_multiple_dependencies(self):
        component.registry.register(name='test', component=MultistyleComponent)
        template = Template("{% load component_tags %}{% component_dependencies %}{% component 'test' %}")
        response = create_and_process_template_response(template)
        rendered = response.content.decode('utf-8')
        self.assert_script_count(rendered, 'script2.js', 1)
        self.assert_script_count(rendered, 'script.js', 1)
        self.assert_stylesheet_count(rendered, 'style2.css', 1)
        self.assert_stylesheet_count(rendered, 'style.css', 1)

    def test_all_js_dependencies_are_rendered_for_component_with_multiple_dependencies(self):
        component.registry.register(name='test', component=MultistyleComponent)
        template = Template("{% load component_tags %}{% component_js_dependencies %}{% component 'test' %}")
        response = create_and_process_template_response(template)
        rendered = response.content.decode('utf-8')
        self.assert_script_count(rendered, 'script2.js', 1)
        self.assert_script_count(rendered, 'script.js', 1)
        self.assert_stylesheet_count(rendered, 'style2.css', 0)
        self.assert_stylesheet_count(rendered, 'style.css', 0)

    def test_all_css_dependencies_are_rendered_for_component_with_multiple_dependencies(self):
        component.registry.register(name='test', component=MultistyleComponent)
        template = Template("{% load component_tags %}{% component_css_dependencies %}{% component 'test' %}")
        response = create_and_process_template_response(template)
        rendered = response.content.decode('utf-8')
        self.assert_script_count(rendered, 'script2.js', 0)
        self.assert_script_count(rendered, 'script.js', 0)
        self.assert_stylesheet_count(rendered, 'style2.css', 1)
        self.assert_stylesheet_count(rendered, 'style.css', 1)

    def test_no_dependencies_with_multiple_unused_components(self):
        component.registry.register(name="test1", component=SimpleComponent)
        component.registry.register(name="test2", component=SimpleComponentAlternate)

        template = Template("{% load component_tags %}{% component_dependencies %}")
        response = create_and_process_template_response(template)
        rendered = response.content.decode('utf-8')
        self.assert_script_count(rendered, 'script.js', 0)
        self.assert_script_count(rendered, 'script2.js', 0)
        self.assert_stylesheet_count(rendered, 'style.css', 0)
        self.assert_stylesheet_count(rendered, 'style2.css', 0)

    def test_correct_css_dependencies_with_multiple_components(self):
        component.registry.register(name="test1", component=SimpleComponent)
        component.registry.register(name="test2", component=SimpleComponentAlternate)

        template = Template("{% load component_tags %}{% component_css_dependencies %}"
                            "{% component 'test1' 'variable' %}")
        response = create_and_process_template_response(template)
        rendered = response.content.decode('utf-8')
        self.assert_stylesheet_count(rendered, 'style.css', 1)
        self.assert_stylesheet_count(rendered, 'style2.css', 0)

    def test_correct_js_dependencies_with_multiple_components(self):
        component.registry.register(name="test1", component=SimpleComponent)
        component.registry.register(name="test2", component=SimpleComponentAlternate)

        template = Template("{% load component_tags %}{% component_js_dependencies %}"
                            "{% component 'test1' 'variable' %}")
        response = create_and_process_template_response(template)
        rendered = response.content.decode('utf-8')
        self.assert_script_count(rendered, "script.js", 1)
        self.assert_script_count(rendered, "script2.js", 0)

    def test_correct_dependencies_with_multiple_components(self):
        component.registry.register(name="test1", component=SimpleComponent)
        component.registry.register(name="test2", component=SimpleComponentAlternate)

        template = Template("{% load component_tags %}{% component_dependencies %}"
                            "{% component 'test2' variable='variable' %}")
        response = create_and_process_template_response(template)
        rendered = response.content.decode('utf-8')
        self.assert_script_count(rendered, 'script2.js', 1)
        self.assert_script_count(rendered, 'script.js', 0)
        self.assert_stylesheet_count(rendered, 'style2.css', 1)
        self.assert_stylesheet_count(rendered, 'style.css', 0)

    def test_shared_dependencies_rendered_once(self):
        component.registry.register(name="test1", component=SimpleComponent)
        component.registry.register(name="test2", component=SimpleComponentAlternate)
        component.registry.register(name="test3", component=SimpleComponentWithSharedDependency)

        template = Template("{% load component_tags %}{% component_dependencies %}"
                            "{% component 'test1' variable='variable' %}{% component 'test2' variable='variable' %}"
                            "{% component 'test1' variable='variable' %}")
        response = create_and_process_template_response(template)
        rendered = response.content.decode('utf-8')
        self.assert_script_count(rendered, 'script2.js', 1)
        self.assert_script_count(rendered, 'script.js', 1)
        self.assert_stylesheet_count(rendered, 'style2.css', 1)
        self.assert_stylesheet_count(rendered, 'style.css', 1)
