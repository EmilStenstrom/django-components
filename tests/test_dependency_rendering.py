from django.template import Template
from django.test import override_settings

from .django_test_setup import *  # NOQA
from django_components import component

from .test_templatetags import SimpleComponent
from .testutils import create_and_process_template_response, Django30CompatibleSimpleTestCase as SimpleTestCase


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


@override_settings(COMPONENTS={'RENDER_DEPENDENCIES': True})
class ComponentMediaRenderingTests(SimpleTestCase):
    def setUp(self):
        # NOTE: component.registry is global, so need to clear before each test
        component.registry.clear()

    def test_no_dependencies_when_no_components_used(self):
        component.registry.register(name="test", component=SimpleComponent)

        template = Template("{% load component_tags %}{% component_dependencies %}")
        rendered = create_and_process_template_response(template)
        self.assertInHTML('<script src="script.js>"', rendered, count=0)
        self.assertInHTML('<link href="style.css" type="text/css" media="all" rel="stylesheet"/>', rendered, count=0)
        self.assertInHTML('<link href="style.css" type="text/css" media="all" rel="stylesheet"/>', rendered, count=0)

    def test_no_js_dependencies_when_no_components_used(self):
        component.registry.register(name="test", component=SimpleComponent)

        template = Template("{% load component_tags %}{% component_js_dependencies %}")
        rendered = create_and_process_template_response(template)
        self.assertInHTML('<script src="script.js>"', rendered, count=0)

    def test_no_css_dependencies_when_no_components_used(self):
        component.registry.register(name="test", component=SimpleComponent)

        template = Template("{% load component_tags %}{% component_css_dependencies %}")
        rendered = create_and_process_template_response(template)
        self.assertInHTML('<link href="style.css" type="text/css" media="all" rel="stylesheet"/>', rendered, count=0)

    def test_single_component_dependencies_render_when_used(self):
        component.registry.register(name="test", component=SimpleComponent)

        template = Template("{% load component_tags %}{% component_dependencies %}"
                            "{% component 'test' variable='foo' %}")
        rendered = create_and_process_template_response(template)
        self.assertInHTML('<link href="style.css" type="text/css" media="all" rel="stylesheet"/>', rendered, count=1)
        self.assertInHTML('<script src="script.js">', rendered, count=1)

    def test_placeholder_removed_when_single_component_rendered(self):
        component.registry.register(name="test", component=SimpleComponent)

        template = Template("{% load component_tags %}{% component_dependencies %}"
                            "{% component 'test' variable='foo' %}")
        rendered = create_and_process_template_response(template)
        self.assertNotIn('_RENDERED', rendered)

    def test_single_component_css_dependencies(self):
        component.registry.register(name="test", component=SimpleComponent)

        template = Template("{% load component_tags %}{% component_css_dependencies %}"
                            "{% component 'test' variable='foo' %}")
        rendered = create_and_process_template_response(template)
        self.assertInHTML('<link href="style.css" type="text/css" media="all" rel="stylesheet"/>', rendered, count=1)

    def test_single_component_js_dependencies(self):
        component.registry.register(name="test", component=SimpleComponent)

        template = Template("{% load component_tags %}{% component_js_dependencies %}"
                            "{% component 'test' variable='foo' %}")
        rendered = create_and_process_template_response(template)
        self.assertInHTML('<script src="script.js">', rendered, count=1)

    def test_all_dependencies_are_rendered_for_component_with_multiple_dependencies(self):
        component.registry.register(name='test', component=MultistyleComponent)
        template = Template("{% load component_tags %}{% component_dependencies %}{% component 'test' %}")
        rendered = create_and_process_template_response(template)
        self.assertInHTML('<script src="script.js">', rendered, count=1)
        self.assertInHTML('<script src="script2.js">', rendered, count=1)
        self.assertInHTML('<link href="style.css" type="text/css" media="all" rel="stylesheet"/>', rendered, count=1)
        self.assertInHTML('<link href="style2.css" type="text/css" media="all" rel="stylesheet"/>', rendered, count=1)

    def test_all_js_dependencies_are_rendered_for_component_with_multiple_dependencies(self):
        component.registry.register(name='test', component=MultistyleComponent)
        template = Template("{% load component_tags %}{% component_js_dependencies %}{% component 'test' %}")
        rendered = create_and_process_template_response(template)
        self.assertInHTML('<script src="script.js">', rendered, count=1)
        self.assertInHTML('<script src="script2.js">', rendered, count=1)
        self.assertInHTML('<link href="style.css" type="text/css" media="all" rel="stylesheet"/>', rendered, count=0)
        self.assertInHTML('<link href="style2.css" type="text/css" media="all" rel="stylesheet"/>', rendered, count=0)

    def test_all_css_dependencies_are_rendered_for_component_with_multiple_dependencies(self):
        component.registry.register(name='test', component=MultistyleComponent)
        template = Template("{% load component_tags %}{% component_css_dependencies %}{% component 'test' %}")
        rendered = create_and_process_template_response(template)
        self.assertInHTML('<script src="script.js">', rendered, count=0)
        self.assertInHTML('<script src="script2.js">', rendered, count=0)
        self.assertInHTML('<link href="style.css" type="text/css" media="all" rel="stylesheet"/>', rendered, count=1)
        self.assertInHTML('<link href="style2.css" type="text/css" media="all" rel="stylesheet"/>', rendered, count=1)

    def test_no_dependencies_with_multiple_unused_components(self):
        component.registry.register(name="test1", component=SimpleComponent)
        component.registry.register(name="test2", component=SimpleComponentAlternate)

        template = Template("{% load component_tags %}{% component_dependencies %}")
        rendered = create_and_process_template_response(template)
        self.assertInHTML('<script src="script.js">', rendered, count=0)
        self.assertInHTML('<script src="script2.js">', rendered, count=0)
        self.assertInHTML('<link href="style.css" type="text/css" media="all" rel="stylesheet"/>', rendered, count=0)
        self.assertInHTML('<link href="style2.css" type="text/css" media="all" rel="stylesheet"/>', rendered, count=0)

    def test_correct_css_dependencies_with_multiple_components(self):
        component.registry.register(name="test1", component=SimpleComponent)
        component.registry.register(name="test2", component=SimpleComponentAlternate)

        template = Template("{% load component_tags %}{% component_css_dependencies %}"
                            "{% component 'test1' 'variable' %}")
        rendered = create_and_process_template_response(template)
        self.assertInHTML('<link href="style.css" type="text/css" media="all" rel="stylesheet"/>', rendered, count=1)
        self.assertInHTML('<link href="style2.css" type="text/css" media="all" rel="stylesheet"/>', rendered, count=0)

    def test_correct_js_dependencies_with_multiple_components(self):
        component.registry.register(name="test1", component=SimpleComponent)
        component.registry.register(name="test2", component=SimpleComponentAlternate)

        template = Template("{% load component_tags %}{% component_js_dependencies %}"
                            "{% component 'test1' 'variable' %}")
        rendered = create_and_process_template_response(template)
        self.assertInHTML('<script src="script.js">', rendered, count=1)
        self.assertInHTML('<script src="script2.js">', rendered, count=0)

    def test_correct_dependencies_with_multiple_components(self):
        component.registry.register(name="test1", component=SimpleComponent)
        component.registry.register(name="test2", component=SimpleComponentAlternate)

        template = Template("{% load component_tags %}{% component_dependencies %}"
                            "{% component 'test2' variable='variable' %}")
        rendered = create_and_process_template_response(template)
        self.assertInHTML('<script src="script.js">', rendered, count=0)
        self.assertInHTML('<script src="script2.js">', rendered, count=1)
        self.assertInHTML('<link href="style.css" type="text/css" media="all" rel="stylesheet"/>', rendered, count=0)
        self.assertInHTML('<link href="style2.css" type="text/css" media="all" rel="stylesheet"/>', rendered, count=1)

    def test_shared_dependencies_rendered_once(self):
        component.registry.register(name="test1", component=SimpleComponent)
        component.registry.register(name="test2", component=SimpleComponentAlternate)
        component.registry.register(name="test3", component=SimpleComponentWithSharedDependency)

        template = Template("{% load component_tags %}{% component_dependencies %}"
                            "{% component 'test1' variable='variable' %}{% component 'test2' variable='variable' %}"
                            "{% component 'test1' variable='variable' %}")
        rendered = create_and_process_template_response(template)
        self.assertInHTML('<script src="script.js">', rendered, count=1)
        self.assertInHTML('<script src="script2.js">', rendered, count=1)
        self.assertInHTML('<link href="style.css" type="text/css" media="all" rel="stylesheet"/>', rendered, count=1)
        self.assertInHTML('<link href="style2.css" type="text/css" media="all" rel="stylesheet"/>', rendered, count=1)

    def test_placeholder_removed_when_multiple_component_rendered(self):
        component.registry.register(name="test1", component=SimpleComponent)
        component.registry.register(name="test2", component=SimpleComponentAlternate)
        component.registry.register(name="test3", component=SimpleComponentWithSharedDependency)

        template = Template("{% load component_tags %}{% component_dependencies %}"
                            "{% component 'test1' variable='variable' %}{% component 'test2' variable='variable' %}"
                            "{% component 'test1' variable='variable' %}")
        rendered = create_and_process_template_response(template)
        self.assertNotIn('_RENDERED', rendered)
