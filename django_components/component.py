from django.forms.widgets import MediaDefiningClass
from django.template import Context
from django.template.base import NodeList, TextNode
from django.template.loader import get_template
from django.utils.safestring import mark_safe
from six import with_metaclass

# Allow "component.AlreadyRegistered" instead of having to import these everywhere
from django_components.component_registry import AlreadyRegistered, ComponentRegistry, NotRegistered  # noqa

# Python 2 compatibility
try:
    from inspect import getfullargspec
except ImportError:
    from inspect import getargspec as getfullargspec

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
        nodelist = NodeList()
        for node in template.template.nodelist:
            if (
                node.token.token_type == TokenType.BLOCK
                and node.token.split_contents()[0] == "slot"
            ):
                nodelist.append(node)

        return nodelist

    def render(self, slots_filled=None, *args, **kwargs):
        slots_filled = slots_filled or []
        context_args_variables = getfullargspec(self.context).args[1:]
        context_args = {
            key: kwargs[key] for key in context_args_variables if key in kwargs
        }
        context = self.context(**context_args)
        template = get_template(self.template(context))
        slots_in_template = self.slots_in_template(template)

        if slots_in_template:
            valid_slot_names = set([slot.name for slot in slots_in_template])
            nodelist = NodeList()
            for node in template.template.nodelist:
                if (
                    node.token.token_type == TokenType.BLOCK
                    and node.token.split_contents()[0] == "slot"
                ):
                    if node.name in valid_slot_names and node.name in slots_filled:
                        nodelist.append(TextNode(slots_filled[node.name]))
                    else:
                        for node in node.nodelist:
                            nodelist.append(node)
                else:
                    nodelist.append(node)

            render_context = Context(context)
            with render_context.bind_template(template.template):
                return nodelist.render(render_context)

        return template.render(context)

    class Media:
        css = {}
        js = []


# This variable represents the global component registry
registry = ComponentRegistry()
