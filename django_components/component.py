from copy import deepcopy
import warnings
from itertools import chain

from django.conf import settings
from django.forms.widgets import MediaDefiningClass
from django.template.base import NodeList
from django.template.loader import get_template
from django.utils.safestring import mark_safe
from six import with_metaclass

# Allow "component.AlreadyRegistered" instead of having to import these everywhere
from django_components.component_registry import AlreadyRegistered, ComponentRegistry, NotRegistered  # noqa

# Django < 2.1 compatibility
try:
    from django.template.base import TokenType
except ImportError:
    from django.template.base import TOKEN_BLOCK, TOKEN_TEXT, TOKEN_VAR

    class TokenType:
        TEXT = TOKEN_TEXT
        VAR = TOKEN_VAR
        BLOCK = TOKEN_BLOCK


class Component(with_metaclass(MediaDefiningClass)):

    def __init__(self, component_name):
        self.__component_name = component_name

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
        return {node.name: node.nodelist for node in template.template.nodelist if is_slot_node(node)}

    def render(self, context, slots_filled=None):
        slots_filled = slots_filled or {}

        template = get_template(self.template(context))
        slots_in_template = self.slots_in_template(template)

        defined_slot_names = set(slots_in_template.keys())
        filled_slot_names = set(slots_filled.keys())
        unexpected_slots = filled_slot_names - defined_slot_names
        if unexpected_slots:
            if settings.DEBUG:
                warnings.warn(
                    "Component {} was provided with unexpected slots: {}".format(
                        self.__component_name, unexpected_slots
                    )
                )
            for unexpected_slot in unexpected_slots:
                del slots_filled[unexpected_slot]

        combined_slots = dict(slots_in_template, **slots_filled)
        # Replace slot nodes with their nodelists, then combine into a single, flat nodelist
        node_iterator = ([node] if not is_slot_node(node) else combined_slots[node.name]
                         for node in template.template.nodelist)

        cloned_template = deepcopy(template)
        cloned_template.template.nodelist = NodeList(chain.from_iterable(node_iterator))

        return cloned_template.template.render(context)

    class Media:
        css = {}
        js = []


def is_slot_node(node):
    return node.token.token_type == TokenType.BLOCK and node.token.split_contents()[0] == "slot"


# This variable represents the global component registry
registry = ComponentRegistry()
