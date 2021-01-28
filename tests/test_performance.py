from time import perf_counter

from django.template import Context, Template

from django_components import component

from .django_test_setup import *  # NOQA
from .testutils import Django111CompatibleSimpleTestCase as SimpleTestCase


class SlottedComponent(component.Component):
    def template(self, context):
        return "slotted_template.html"


class SimpleComponent(component.Component):
    def context(self, variable, variable2="default"):
        return {
            "variable": variable,
            "variable2": variable2,
        }

    def template(self, context):
        return "simple_template.html"


class RenderBenchmarks(SimpleTestCase):
    def setUp(self):
        component.registry.clear()
        component.registry.register('test_component', SlottedComponent)
        component.registry.register('inner_component', SimpleComponent)

    def test_render_time(self):
        template = Template("{% load component_tags %}{% component_block 'test_component' %}"
                            "{% slot \"header\" %}{% component 'inner_component' variable='foo' %}{% endslot %}"
                            "{% endcomponent_block %}", name='root')
        start_time = perf_counter()
        for _ in range(1000):
            template.render(Context({}))
        end_time = perf_counter()
        total_elapsed = end_time - start_time
        print(f'{total_elapsed } ms per template')