from django import template
from django_components.component import registry
from django.utils.safestring import mark_safe

import re

register = template.Library()

@register.simple_tag(name="component_dependencies")
def component_dependencies_tag(*args, **kwargs):
    current_component_class = registry._registry[kwargs['component']]

    dependencies = (current_component_class.render_dependencies(),)

    return mark_safe("\n".join(dependencies))

@register.simple_tag(name="component")
def component_tag(name, *args, **kwargs):
    component_class = registry._registry[name]
    component = component_class()
    return component.render(*args, **kwargs)


# Custom parser and compiler for children components

@register.tag(name="child_component")
def child_component(parser,token):
    # nodelist now contains exactly what we need to store
    nodelist = parser.parse(('end_child_component',))

    parser.delete_first_token() # Skips 'end_child_component' tag

    try:
        # Splitting by None == splitting by spaces.
        tag_name, arg = token.contents.split(None, 1)

    except ValueError:
        raise template.TemplateSyntaxError(
            "%r tag requires arguments" % token.contents.split()[0]
        )

    m = re.search(r'as (\w+)', arg)

    if not m:
        raise template.TemplateSyntaxError("%r tag had invalid arguments" % tag_name)

    component_name = m.groups() # Gets the matched var name.

    return ChildComponentNode(nodelist,component_name)

class ChildComponentNode(template.Node):
    def __init__(self, nodelist, component_name):
        self.nodelist = nodelist
        self.component_name = component_name[0]

    def render(self, context):
        # context.add(self.component_name, self.nodelist)
        print("Comp name is: " + self.component_name)
        context[self.component_name] = self.nodelist.render(context)
        return ''
