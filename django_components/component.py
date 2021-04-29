import time
import warnings
from copy import copy, deepcopy
from functools import lru_cache

from django.conf import settings
from django.forms.widgets import MediaDefiningClass
from django.template.base import TokenType, Node, NodeList
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
        return (isinstance(node, Node)
                and node.token.token_type == TokenType.BLOCK
                and node.token.split_contents()[0] == "slot")

    @lru_cache(maxsize=TEMPLATE_CACHE_SIZE)
    def get_processed_template(self, template_name):
        """Retrieve the requested template and add a link to this component to each SlotNode in the template."""

        source_template = get_template(template_name)
        component_template = copy(source_template)
        # The template may be shared with another component if (e.g., due to caching). To ensure that each
        # SlotNode is unique between components, we have to copy the nodes in the template nodelist and
        # any contained nodelists.
        nodelist_class = type(source_template.template.nodelist)
        cloned_nodelist = [duplicate_node(node) for node in source_template.template.nodelist]
        component_template.template.nodelist = nodelist_class(cloned_nodelist)

        # Traverse template nodes and descendants, and give each slot node a reference to this component.
        visited_nodes = set()
        nodes_to_visit = list(component_template.template.nodelist)
        slots_seen = set()
        while nodes_to_visit:
            current_node = nodes_to_visit.pop()
            if current_node in visited_nodes:
                continue
            visited_nodes.add(current_node)
            for nodelist_name in current_node.child_nodelists:
                nodes_to_visit.extend(getattr(current_node, nodelist_name, []))
            if self.is_slot_node(current_node):
                slots_seen.add(current_node.name)
                current_node.parent_component = self

        # Check and warn for unknown slots
        if settings.DEBUG:
            filled_slot_names = set(self.slots.keys())
            unused_slots = filled_slot_names - slots_seen
            if unused_slots:
                warnings.warn(
                    "Component {} was provided with slots that were not used in a template: {}".format(
                        self._component_name, unused_slots
                    )
                )

        return component_template.template

    def render(self, context):
        template_name = self.template(context)
        instance_template = self.get_processed_template(template_name)
        return instance_template.render(context)

    class Media:
        css = {}
        js = []


# This variable represents the global component registry
registry = ComponentRegistry()


def duplicate_node(source_node):
    """Perform a shallow copy of source_node and then recursively copy over each of source_node's nodelists.

    If a nodelist is a dynamic property that cannot be set, fall back to a deepcopy of source_node."""

    try:
        clone = copy(source_node)
        for nodelist_name in source_node.child_nodelists:
            nodelist = getattr(source_node, nodelist_name, NodeList())
            nodelist_contents = [duplicate_node(n) for n in nodelist]
            setattr(clone, nodelist_name, type(nodelist)(nodelist_contents))
        return clone
    except AttributeError:
        # AttributeError is raised if an attribute cannot be set (e.g., IfNode's nodelist,
        # which is a read-only property).
        return deepcopy(source_node)


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
