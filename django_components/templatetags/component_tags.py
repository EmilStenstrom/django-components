from django import template
from django_components.component import registry

register = template.Library()

@register.simple_tag(name="component_dependencies")
def component_dependencies_tag():
    out = []
    for comp in registry._registry.values():
        out.append(comp.render_dependencies())

    return "\n".join(out)
