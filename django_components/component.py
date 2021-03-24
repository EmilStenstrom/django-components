import warnings
from copy import copy
from functools import lru_cache
from itertools import chain

from django.conf import settings
from django.forms.widgets import MediaDefiningClass
from django.template.base import NodeList, TokenType
from django.template.loader import get_template
from django.utils.safestring import mark_safe

# Allow "component.AlreadyRegistered" instead of having to import these everywhere
from django_components.component_registry import AlreadyRegistered, ComponentRegistry, NotRegistered  # noqa

TEMPLATE_CACHE_SIZE = getattr(settings, "COMPONENTS", {}).get('TEMPLATE_CACHE_SIZE', 128)

class SimplifiedInterfaceMediaDefiningClass(MediaDefiningClass):
    def __new__(mcs, name, bases, attrs):
        if "Media" in attrs:
            media = attrs["Media"]

            # Allow: class Media: css = "style.css"
            if isinstance(media.css, str):
                media.css = [media.css]

            # Allow: class Media: css = ["style.css"]
            if isinstance(media.css, list):
                media.css = {"all": media.css}

            # Allow: class Media: css = {"all": "style.css"}
            if isinstance(media.css, dict):
                for media_type, path_list in media.css.items():
                    if isinstance(path_list, str):
                        media.css[media_type] = [path_list]

            # Allow: class Media: js = "script.js"
            if isinstance(media.js, str):
                media.js = [media.js]

        return super().__new__(mcs, name, bases, attrs)

class Component(metaclass=SimplifiedInterfaceMediaDefiningClass):

    def __init__(self, component_name):
        self._component_name = component_name
        self.instance_template = None
        self.slots = {}

    def context(self):
        return {}

    def template(self, context):
        raise NotImplementedError("Missing template() method on component")

    def render_dependencies(self):
        """Helper function to access media.render()"""

        return self.media.render()

    def render_css_dependencies(self):
        """Render only CSS dependencies available in the media class."""

        return mark_safe("\n".join(self.media.render_css()))

    def render_js_dependencies(self):
        """Render only JS dependencies available in the media class."""

        return mark_safe("\n".join(self.media.render_js()))

    @staticmethod
    def slots_in_template(template):
        return {node.name: node.nodelist for node in template.template.nodelist if Component.is_slot_node(node)}

    @staticmethod
    def is_slot_node(node):
        return node.token.token_type == TokenType.BLOCK and node.token.split_contents()[0] == "slot"

    @lru_cache(maxsize=TEMPLATE_CACHE_SIZE)
    def compile_instance_template(self, template_name):
        """Use component's base template and the slots used for this instance to compile
        a unified template for this instance."""

        component_template = get_template(template_name)
        slots_in_template = Component.slots_in_template(component_template)

        defined_slot_names = set(slots_in_template.keys())
        filled_slot_names = set(self.slots.keys())
        unexpected_slots = filled_slot_names - defined_slot_names
        if unexpected_slots:
            if settings.DEBUG:
                warnings.warn(
                    "Component {} was provided with unexpected slots: {}".format(
                        self._component_name, unexpected_slots
                    )
                )
            for unexpected_slot in unexpected_slots:
                del self.slots[unexpected_slot]

        combined_slots = dict(slots_in_template, **self.slots)
        if combined_slots:
            # Replace slot nodes with their nodelists, then combine into a single, flat nodelist
            node_iterator = ([node] if not Component.is_slot_node(node) else combined_slots[node.name]
                             for node in component_template.template.nodelist)

            instance_template = copy(component_template.template)
            instance_template.nodelist = NodeList(chain.from_iterable(node_iterator))
        else:
            instance_template = component_template.template

        return instance_template

    def render(self, context):
        template_name = self.template(context)
        instance_template = self.compile_instance_template(template_name)
        return instance_template.render(context)

    class Media:
        css = {}
        js = []


# This variable represents the global component registry
registry = ComponentRegistry()

def register(name):
    """Class decorator to register a component.


    Usage:

    @register("my_component")
    class MyComponent(component.Component):
        ...

    """
    def decorator(component):
        registry.register(name=name, component=component)
        return component

    return decorator
