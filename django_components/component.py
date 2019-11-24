from django.forms.widgets import MediaDefiningClass
from django.template.loader import render_to_string
from six import with_metaclass

# Allow "component.AlreadyRegistered" instead of having to import these everywhere
from django_components.component_registry import AlreadyRegistered, ComponentRegistry, NotRegistered  # NOQA


class Component(with_metaclass(MediaDefiningClass)):
    def context(self):
        return {}

    def template(self, context):
        return ""

    def render_dependencies(self):
        return self.media.render()

    def render(self, *args, **kwargs):
        context = self.context(*args, **kwargs)
        return render_to_string(self.template(context), context)

    class Media:
        css = {}
        js = []

# This variable represents the global component registry
registry = ComponentRegistry()
