from django.template import Context, Template

from django_components import component

from .django_test_setup import *  # NOQA
from .testutils import Django111CompatibleSimpleTestCase as SimpleTestCase


class SimpleComponent(component.Component):
    def context(self, variable=None):
        return {"variable": variable} if variable is not None else {}

    def template(self, context):
        return "simple_template.html"

    @staticmethod
    def expected_output(variable_value):
        return 'Variable: < strong > {} < / strong >'.format(variable_value)


class ParentComponent(component.Component):
    def context(self):
        return {
            "shadowing_variable": 'NOT SHADOWED'
        }

    def template(self, context):
        return "parent_template.html"


class ParentComponentWithArgs(component.Component):
    def context(self, parent_value):
        return {
            "inner_parent_value": parent_value
        }

    def template(self, context):
        return "parent_with_args_template.html"


class VariableDisplay(component.Component):
    def context(self, shadowing_variable=None, new_variable=None):
        context = {}
        if shadowing_variable is not None:
            context['shadowing_variable'] = shadowing_variable
        if new_variable is not None:
            context['unique_variable'] = new_variable
        return context

    def template(self, context):
        return "variable_display.html"


class IncrementerComponent(component.Component):
    def context(self, value=0):
        value = int(value)
        if hasattr(self, 'call_count'):
            self.call_count += 1
        else:
            self.call_count = 1
        return {
            "value": value + 1,
            "calls": self.call_count
        }

    def template(self, context):
        return "incrementer.html"


component.registry.register(name='parent_component', component=ParentComponent)
component.registry.register(name='parent_with_args', component=ParentComponentWithArgs)
component.registry.register(name='variable_display', component=VariableDisplay)
component.registry.register(name='incrementer', component=IncrementerComponent)
component.registry.register(name='simple_component', component=SimpleComponent)


class ContextTests(SimpleTestCase):
    def test_nested_component_context_shadows_parent_with_unfilled_slots_and_component_tag(self):
        template = Template("{% load component_tags %}{% component_dependencies %}"
                            "{% component 'parent_component' %}")
        rendered = template.render(Context())

        self.assertIn('<h1>Shadowing variable = override</h1>', rendered, rendered)
        self.assertIn('<h1>Shadowing variable = slot_default_override</h1>', rendered, rendered)
        self.assertNotIn('<h1>Shadowing variable = NOT SHADOWED</h1>', rendered, rendered)

    def test_nested_component_instances_have_unique_context_with_unfilled_slots_and_component_tag(self):
        template = Template("{% load component_tags %}{% component_dependencies %}"
                            "{% component name='parent_component' %}")
        rendered = template.render(Context())

        self.assertIn('<h1>Uniquely named variable = unique_val</h1>', rendered, rendered)
        self.assertIn('<h1>Uniquely named variable = slot_default_unique</h1>', rendered, rendered)

    def test_nested_component_context_shadows_parent_with_unfilled_slots_and_component_block_tag(self):
        template = Template("{% load component_tags %}{% component_dependencies %}"
                            "{% component_block 'parent_component' %}{% endcomponent_block %}")
        rendered = template.render(Context())

        self.assertIn('<h1>Shadowing variable = override</h1>', rendered, rendered)
        self.assertIn('<h1>Shadowing variable = slot_default_override</h1>', rendered, rendered)
        self.assertNotIn('<h1>Shadowing variable = NOT SHADOWED</h1>', rendered, rendered)

    def test_nested_component_instances_have_unique_context_with_unfilled_slots_and_component_block_tag(self):
        template = Template("{% load component_tags %}{% component_dependencies %}"
                            "{% component_block 'parent_component' %}{% endcomponent_block %}")
        rendered = template.render(Context())

        self.assertIn('<h1>Uniquely named variable = unique_val</h1>', rendered, rendered)
        self.assertIn('<h1>Uniquely named variable = slot_default_unique</h1>', rendered, rendered)

    def test_nested_component_context_shadows_parent_with_filled_slots(self):
        template = Template("{% load component_tags %}{% component_dependencies %}"
                            "{% component_block 'parent_component' %}"
                            "{% slot 'content' %}{% component name='variable_display' "
                            "shadowing_variable='shadow_from_slot' new_variable='unique_from_slot' %}{% endslot %}"
                            "{% endcomponent_block %}")
        rendered = template.render(Context())

        self.assertIn('<h1>Shadowing variable = override</h1>', rendered, rendered)
        self.assertIn('<h1>Shadowing variable = shadow_from_slot</h1>', rendered, rendered)
        self.assertNotIn('<h1>Shadowing variable = NOT SHADOWED</h1>', rendered, rendered)

    def test_nested_component_instances_have_unique_context_with_filled_slots(self):
        template = Template("{% load component_tags %}{% component_dependencies %}"
                            "{% component_block 'parent_component' %}"
                            "{% slot 'content' %}{% component name='variable_display' "
                            "shadowing_variable='shadow_from_slot' new_variable='unique_from_slot' %}{% endslot %}"
                            "{% endcomponent_block %}")
        rendered = template.render(Context())

        self.assertIn('<h1>Uniquely named variable = unique_val</h1>', rendered, rendered)
        self.assertIn('<h1>Uniquely named variable = unique_from_slot</h1>', rendered, rendered)

    def test_nested_component_context_shadows_outer_context_with_unfilled_slots_and_component_tag(self):
        template = Template("{% load component_tags %}{% component_dependencies %}"
                            "{% component name='parent_component' %}")
        rendered = template.render(Context({'shadowing_variable': 'NOT SHADOWED'}))

        self.assertIn('<h1>Shadowing variable = override</h1>', rendered, rendered)
        self.assertIn('<h1>Shadowing variable = slot_default_override</h1>', rendered, rendered)
        self.assertNotIn('<h1>Shadowing variable = NOT SHADOWED</h1>', rendered, rendered)

    def test_nested_component_context_shadows_outer_context_with_unfilled_slots_and_component_block_tag(self):
        template = Template("{% load component_tags %}{% component_dependencies %}"
                            "{% component_block 'parent_component' %}{% endcomponent_block %}")
        rendered = template.render(Context({'shadowing_variable': 'NOT SHADOWED'}))

        self.assertIn('<h1>Shadowing variable = override</h1>', rendered, rendered)
        self.assertIn('<h1>Shadowing variable = slot_default_override</h1>', rendered, rendered)
        self.assertNotIn('<h1>Shadowing variable = NOT SHADOWED</h1>', rendered, rendered)

    def test_nested_component_context_shadows_outer_context_with_filled_slots(self):
        template = Template("{% load component_tags %}{% component_dependencies %}"
                            "{% component_block 'parent_component' %}"
                            "{% slot 'content' %}{% component name='variable_display' "
                            "shadowing_variable='shadow_from_slot' new_variable='unique_from_slot' %}{% endslot %}"
                            "{% endcomponent_block %}")
        rendered = template.render(Context({'shadowing_variable': 'NOT SHADOWED'}))

        self.assertIn('<h1>Shadowing variable = override</h1>', rendered, rendered)
        self.assertIn('<h1>Shadowing variable = shadow_from_slot</h1>', rendered, rendered)
        self.assertNotIn('<h1>Shadowing variable = NOT SHADOWED</h1>', rendered, rendered)


class ParentArgsTests(SimpleTestCase):
    def test_parent_args_can_be_drawn_from_context(self):
        template = Template("{% load component_tags %}{% component_dependencies %}"
                            "{% component_block 'parent_with_args' parent_value=parent_value %}"
                            "{% endcomponent_block %}")
        rendered = template.render(Context({'parent_value': 'passed_in'}))

        self.assertIn('<h1>Shadowing variable = passed_in</h1>', rendered, rendered)
        self.assertIn('<h1>Uniquely named variable = passed_in</h1>', rendered, rendered)
        self.assertNotIn('<h1>Shadowing variable = NOT SHADOWED</h1>', rendered, rendered)

    def test_parent_args_available_outside_slots(self):
        template = Template("{% load component_tags %}{% component_dependencies %}"
                            "{% component_block 'parent_with_args' parent_value='passed_in' %}{%endcomponent_block %}")
        rendered = template.render(Context())

        self.assertIn('<h1>Shadowing variable = passed_in</h1>', rendered, rendered)
        self.assertIn('<h1>Uniquely named variable = passed_in</h1>', rendered, rendered)
        self.assertNotIn('<h1>Shadowing variable = NOT SHADOWED</h1>', rendered, rendered)

    def test_parent_args_available_in_slots(self):
        template = Template("{% load component_tags %}{% component_dependencies %}"
                            "{% component_block 'parent_with_args' parent_value='passed_in' %}"
                            "{% slot 'content' %}{% component name='variable_display' "
                            "shadowing_variable='value_from_slot' new_variable=inner_parent_value %}{% endslot %}"
                            "{%endcomponent_block %}")
        rendered = template.render(Context())

        self.assertIn('<h1>Shadowing variable = value_from_slot</h1>', rendered, rendered)
        self.assertIn('<h1>Uniquely named variable = passed_in</h1>', rendered, rendered)
        self.assertNotIn('<h1>Shadowing variable = NOT SHADOWED</h1>', rendered, rendered)


class ContextCalledOnceTests(SimpleTestCase):
    def test_one_context_call_with_simple_component(self):
        template = Template("{% load component_tags %}{% component_dependencies %}"
                            "{% component name='incrementer' %}")
        rendered = template.render(Context()).strip()

        self.assertEqual(rendered, '<p class="incrementer">value=1;calls=1</p>', rendered)

    def test_one_context_call_with_simple_component_and_arg(self):
        template = Template("{% load component_tags %}{% component_dependencies %}"
                            "{% component name='incrementer' value='2' %}")
        rendered = template.render(Context()).strip()

        self.assertEqual(rendered, '<p class="incrementer">value=3;calls=1</p>', rendered)

    def test_one_context_call_with_component_block(self):
        template = Template("{% load component_tags %}{% component_dependencies %}"
                            "{% component_block 'incrementer' %}{% endcomponent_block %}")
        rendered = template.render(Context()).strip()

        self.assertEqual(rendered, '<p class="incrementer">value=1;calls=1</p>', rendered)

    def test_one_context_call_with_component_block_and_arg(self):
        template = Template("{% load component_tags %}{% component_dependencies %}"
                            "{% component_block 'incrementer' value='3' %}{% endcomponent_block %}")
        rendered = template.render(Context()).strip()

        self.assertEqual(rendered, '<p class="incrementer">value=4;calls=1</p>', rendered)

    def test_one_context_call_with_slot(self):
        template = Template("{% load component_tags %}{% component_dependencies %}"
                            "{% component_block 'incrementer' %}{% slot 'content' %}"
                            "<p>slot</p>{% endslot %}{% endcomponent_block %}")
        rendered = template.render(Context()).strip()

        self.assertEqual(rendered, '<p class="incrementer">value=1;calls=1</p>\n<p>slot</p>', rendered)

    def test_one_context_call_with_slot_and_arg(self):
        template = Template("{% load component_tags %}{% component_dependencies %}"
                            "{% component_block 'incrementer' value='3' %}{% slot 'content' %}"
                            "<p>slot</p>{% endslot %}{% endcomponent_block %}")
        rendered = template.render(Context()).strip()

        self.assertEqual(rendered, '<p class="incrementer">value=4;calls=1</p>\n<p>slot</p>', rendered)


class ComponentsCanAccessOuterContext(SimpleTestCase):
    def test_simple_component_can_use_outer_context(self):
        template = Template("{% load component_tags %}{% component_dependencies %}"
                            "{% component 'simple_component' %}")
        rendered = template.render(Context({'variable': 'outer_value'})).strip()
        self.assertIn('outer_value', rendered, rendered)


class IsolatedContextTests(SimpleTestCase):
    def test_simple_component_can_pass_outer_context_in_args(self):
        template = Template("{% load component_tags %}{% component_dependencies %}"
                            "{% component 'simple_component' variable only %}")
        rendered = template.render(Context({'variable': 'outer_value'})).strip()
        self.assertIn('outer_value', rendered, rendered)

    def test_simple_component_cannot_use_outer_context(self):
        template = Template("{% load component_tags %}{% component_dependencies %}"
                            "{% component 'simple_component' only %}")
        rendered = template.render(Context({'variable': 'outer_value'})).strip()
        self.assertNotIn('outer_value', rendered, rendered)
