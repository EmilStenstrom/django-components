from django.template.loader import render_to_string
from .component_registry import ComponentRegistry, AlreadyRegistered, NotRegistered  # NOQA

class Component(object):
    CSS_TEMPLATE = '<link href="{}" type="text/css" media="{}" rel="stylesheet" />'
    JS_TEMPLATE = '<script type="text/javascript" src="{}"></script>'

    def __init__(self):
        self._media = self.Media()

    def context(self):
        return {}

    def render_dependencies(self):
        out = []

        for css_media, css_path in self._media.css.items():
            out.append(Component.CSS_TEMPLATE.format(css_path, css_media))

        for js_path in self._media.js:
            out.append(Component.JS_TEMPLATE.format(js_path))

        return "\n".join(out)

    def render(self, *args, **kwargs):
        return render_to_string(self._media.template, self.context(*args, **kwargs))

    class Media:
        template = None
        css = {}
        js = ()

# This variable represents the global component registry
registry = ComponentRegistry()
