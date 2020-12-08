import django
from django import template
from django.template.base import Node, NodeList, TemplateSyntaxError, token_kwargs
from django.template.library import parse_bits
from django.utils.safestring import mark_safe

from django_components.component import registry

# Django < 2.1 compatibility
try:
    from django.template.base import TokenType
except ImportError:
    from django.template.base import TOKEN_BLOCK, TOKEN_TEXT, TOKEN_VAR

    class TokenType:
        TEXT = TOKEN_TEXT
        VAR = TOKEN_VAR
        BLOCK = TOKEN_BLOCK


# Django < 2.0 compatibility
if django.VERSION > (2, 0):
    PARSE_BITS_DEFAULTS = {
        "varargs": None,
        "varkw": [],
        "defaults": None,
        "kwonly": [],
        "kwonly_defaults": None,
    }
else:
    PARSE_BITS_DEFAULTS = {
        "varargs": None,
        "varkw": [],
        "defaults": None,
    }

register = template.Library()

COMPONENT_CONTEXT_KEY = "component_context"


def get_components_from_registry(registry):
    """Returns a list unique components from the registry."""

    unique_component_classes = set(registry.all().values())

    components = []
    for component_class in unique_component_classes:
        components.append(component_class())

    return components


@register.simple_tag(name="component_dependencies")
def component_dependencies_tag():
    """Render both the CSS and JS dependency tags."""

    rendered_dependencies = []
    for component in get_components_from_registry(registry):
        rendered_dependencies.append(component.render_dependencies())

    return mark_safe("\n".join(rendered_dependencies))


@register.simple_tag(name="component_css_dependencies")
def component_css_dependencies_tag():
    """Render the CSS tags."""

    rendered_dependencies = []
    for component in get_components_from_registry(registry):
        rendered_dependencies.append(component.render_css_dependencies())

    return mark_safe("\n".join(rendered_dependencies))


@register.simple_tag(name="component_js_dependencies")
def component_js_dependencies_tag():
    """Render the JS tags."""

    rendered_dependencies = []
    for component in get_components_from_registry(registry):
        rendered_dependencies.append(component.render_js_dependencies())

    return mark_safe("\n".join(rendered_dependencies))


@register.simple_tag(name="component")
def component_tag(name, *args, **kwargs):
    component_class = registry.get(name)
    component = component_class()
    return component.render(*args, **kwargs)


class SlotNode(Node):
    def __init__(self, name, nodelist, component=None):
        self.name, self.nodelist, self.component = name, nodelist, component

    def __repr__(self):
        return "<Slot Node: %s. Contents: %r>" % (self.name, self.nodelist)

    def render(self, context):
        if COMPONENT_CONTEXT_KEY not in context.render_context:
            context.render_context[COMPONENT_CONTEXT_KEY] = {}

        if self.component not in context.render_context[COMPONENT_CONTEXT_KEY]:
            context.render_context[COMPONENT_CONTEXT_KEY][self.component] = {}

        rendered_slot = self.nodelist.render(context)

        if self.component:
            context.render_context[COMPONENT_CONTEXT_KEY][self.component][
                self.name
            ] = rendered_slot

        return ""


@register.tag("slot")
def do_slot(parser, token, component=None):
    bits = token.split_contents()
    if len(bits) != 2:
        raise TemplateSyntaxError("'%s' tag takes only one argument" % bits[0])

    slot_name = bits[1].strip('"')
    nodelist = parser.parse(parse_until=["endslot"])
    parser.delete_first_token()

    return SlotNode(slot_name, nodelist, component=component)


class ComponentNode(Node):
    def __init__(self, component, extra_context, slots):
        extra_context = extra_context or {}
        self.component, self.extra_context, self.slots = component, extra_context, slots

    def __repr__(self):
        return "<Component Node: %s. Contents: %r>" % (self.component, self.slots)

    def render(self, context):
        extra_context = {
            key: filter_expression.resolve(context)
            for key, filter_expression in self.extra_context.items()
        }
        context.update(extra_context)

        self.slots.render(context)

        if COMPONENT_CONTEXT_KEY in context.render_context:
            slots_filled = context.render_context[COMPONENT_CONTEXT_KEY][self.component]
            return self.component.render(slots_filled=slots_filled, **context.flatten())

        return self.component.render()


@register.tag("component_block")
def do_component(parser, token):
    """
        {% component_block "name" variable="value" variable2="value2" ... %}
    """

    bits = token.split_contents()

    tag_args, tag_kwargs = parse_bits(
        parser=parser,
        bits=bits,
        params=["tag_name", "component_name"],
        takes_context=False,
        name="component_block",
        **PARSE_BITS_DEFAULTS
    )
    tag_name = tag_args.pop(0)

    if len(bits) < 2:
        raise TemplateSyntaxError(
            "Call the '%s' tag with a component name as the first parameter" % tag_name
        )

    component_name = bits[1]
    if not component_name.startswith(('"', "'")) or not component_name.endswith(
        ('"', "'")
    ):
        raise TemplateSyntaxError(
            "Component name '%s' should be in quotes" % component_name
        )

    component_name = component_name.strip('"\'')
    component_class = registry.get(component_name)
    component = component_class()

    extra_context = {}
    if len(bits) > 2:
        extra_context = component.context(**token_kwargs(bits[2:], parser))

    slots_filled = NodeList()
    tag_name = bits[0]
    while tag_name != "endcomponent_block":
        token = parser.next_token()
        if token.token_type != TokenType.BLOCK:
            continue

        tag_name = token.split_contents()[0]

        if tag_name == "slot":
            slots_filled += do_slot(parser, token, component=component)
        elif tag_name == "endcomponent_block":
            break

    return ComponentNode(component, extra_context, slots_filled)
