from django import template
from django_components.component import registry
from django.utils.safestring import mark_safe

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
