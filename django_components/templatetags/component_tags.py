from django import template
from django.utils.safestring import mark_safe

from django_components.component import registry

register = template.Library()

@register.simple_tag(name="component_dependencies")
def component_dependencies_tag():
    unique_component_classes = set(registry.all().values())

    out = []
    for component_class in unique_component_classes:
        component = component_class()
        out.append(component.render_dependencies())

    return mark_safe("\n".join(out))

@register.simple_tag(name="component")
def component_tag(name, *args, **kwargs):
    component_class = registry.get(name)
    component = component_class()
    return component.render(*args, **kwargs)
