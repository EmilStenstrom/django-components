from django.template.loader import render_to_string
from .component_registry import ComponentRegistry, AlreadyRegistered, NotRegistered  # NOQA

class Component(object):
    CSS_TEMPLATE = '<link href="{}" type="text/css" rel="stylesheet" />'
    JS_TEMPLATE = '<script type="text/javascript" src="{}"></script>'

    def context(self):
        return {}

    @classmethod
    def render_dependencies(cls):
        out = []

        for css_path in cls.Media.css:
            out.append(cls.CSS_TEMPLATE.format(css_path))

        for js_path in cls.Media.js:
            out.append(cls.JS_TEMPLATE.format(js_path))

        return "\n".join(out)

    def render(self, *args, **kwargs):
        return render_to_string(self.Media.template, self.context(*args, **kwargs))

    class Media:
        template = None
        css = {}
        js = ()

# This variable represents the global component registry
registry = ComponentRegistry()
