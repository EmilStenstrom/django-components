from django.template.loader import render_to_string
from .component_registry import ComponentRegistry, AlreadyRegistered, NotRegistered  # NOQA
from django.forms.widgets import MediaDefiningClass

class Component(metaclass=MediaDefiningClass):
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
