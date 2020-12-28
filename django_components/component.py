from django.forms.widgets import MediaDefiningClass
from django.template.base import NodeList, TextNode
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

    def slots_in_template(self, template):
        return NodeList(node for node in template.template.nodelist if is_slot_node(node))

    def render(self, context, slots_filled=None):
        slots_filled = slots_filled or []
        template = get_template(self.template(context))
        slots_in_template = self.slots_in_template(template)

        # If there are no slots, then we can simply render the template
        if not slots_in_template:
            return template.template.render(context)

        # Otherwise, we need to assemble and render a nodelist containing the nodes from the template, slots that were
        # provided when the component was called (previously rendered by the component's render method) and the
        # unrendered default slots
        nodelist = NodeList()
        for node in template.template.nodelist:
            if is_slot_node(node):
                if node.name in slots_filled:
                    nodelist.append(TextNode(slots_filled[node.name]))
                else:
                    nodelist.extend(node.nodelist)
            else:
                nodelist.append(node)

        return nodelist.render(context)

    class Media:
        css = {}
        js = []


def is_slot_node(node):
    return node.token.token_type == TokenType.BLOCK and node.token.split_contents()[0] == "slot"


# This variable represents the global component registry
registry = ComponentRegistry()
