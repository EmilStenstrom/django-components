from itertools import chain

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
        return NodeList(node for node in template.template.nodelist if is_slot_node(node))

    def render(self, context, slots_filled=None):
        slots_filled = slots_filled or {}
        template = get_template(self.template(context))
        slots_in_template = self.slots_in_template(template)
        for default_slot in slots_in_template:
            if default_slot.name not in slots_filled:
                slots_filled[default_slot.name] = default_slot.nodelist

        # Replace slot nodes with their nodelists, then combine into a single, flat nodelist
        node_iterator = ([node] if not is_slot_node(node) else slots_filled[node.name]
                         for node in template.template.nodelist)
        flattened_nodelist = NodeList(chain.from_iterable(node_iterator))

        return flattened_nodelist.render(context)

    class Media:
        css = {}
        js = []


def is_slot_node(node):
    return node.token.token_type == TokenType.BLOCK and node.token.split_contents()[0] == "slot"


# This variable represents the global component registry
registry = ComponentRegistry()
