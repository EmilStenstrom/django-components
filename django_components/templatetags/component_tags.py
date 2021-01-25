from collections import defaultdict

import django
from django import template
from django.template.base import Node, NodeList, TemplateSyntaxError
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
        "varkw": [],
        "defaults": None,
        "kwonly": [],
        "kwonly_defaults": None,
    }
else:
    PARSE_BITS_DEFAULTS = {
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
        components.append(component_class(component_class.__name__))

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


@register.tag(name='component')
def do_component(parser, token):
    bits = token.split_contents()
    bits, isolated_context = check_for_isolated_context_keyword(bits)
    component, context_args, context_kwargs = parse_component_with_args(parser, bits, 'component')
    return ComponentNode(component, context_args, context_kwargs, isolated_context=isolated_context)


class SlotNode(Node):
    def __init__(self, name, nodelist, component=None):
        self.name, self.nodelist, self.component = name, nodelist, component

    def __repr__(self):
        return "<Slot Node: %s. Contents: %r>" % (self.name, self.nodelist)

    def render(self, context):
        # This method should only be called if a slot tag is used outside of a component.
        assert self.component is None
        return self.nodelist.render(context)


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
    def __init__(self, component, context_args, context_kwargs, slots=None, isolated_context=False):
        self.slots = defaultdict(NodeList)
        for slot in slots or []:
            self.slots[slot.name].extend(slot.nodelist)
        self.context_args = context_args or []
        self.context_kwargs = context_kwargs or {}
        self.component, self.isolated_context = component, isolated_context

    def __repr__(self):
        return "<Component Node: %s. Contents: %r>" % (self.component, self.slots)

    def render(self, context):
        self.component.outer_context = context.flatten()

        # Resolve FilterExpressions and Variables that were passed as args to the component, then call component's
        # context method to get values to insert into the context
        resolved_context_args = [safe_resolve(arg, context) for arg in self.context_args]
        resolved_context_kwargs = {
            key: safe_resolve(kwarg, context) for key, kwarg in self.context_kwargs.items()
        }
        component_context = self.component.context(*resolved_context_args, **resolved_context_kwargs)

        # Create a fresh context if requested
        if self.isolated_context:
            context = context.new()

        with context.update(component_context):
            return self.component.render(context, slots_filled=self.slots)


@register.tag("component_block")
def do_component_block(parser, token):
    """
    To give the component access to the template context:
        {% component_block "name" positional_arg keyword_arg=value ... %}

    To render the component in an isolated context:
        {% component_block "name" positional_arg keyword_arg=value ... only %}

    Positional and keyword arguments can be literals or template variables.
    The component name must be a single- or double-quotes string and must
    be either the first positional argument or, if there are no positional
    arguments, passed as 'name'.
    """

    bits = token.split_contents()
    bits, isolated_context = check_for_isolated_context_keyword(bits)

    tag_name, token = next_block_token(parser)
    component, context_args, context_kwargs = parse_component_with_args(parser, bits, 'component_block')

    slots_filled = NodeList()
    while tag_name != "endcomponent_block":
        if tag_name == "slot":
            slots_filled += do_slot(parser, token, component=component)
        tag_name, token = next_block_token(parser)

    return ComponentNode(component, context_args, context_kwargs, slots=slots_filled,
                         isolated_context=isolated_context)


def next_block_token(parser):
    """Return tag and token for next block token.

    Raises IndexError if there are not more block tokens in the remainder of the template."""

    while True:
        token = parser.next_token()
        if token.token_type != TokenType.BLOCK:
            continue

        tag_name = token.split_contents()[0]
        return tag_name, token


def check_for_isolated_context_keyword(bits):
    """Return True and strip the last word if token ends with 'only' keyword."""

    if bits[-1] == 'only':
        return bits[:-1], True
    return bits, False


def parse_component_with_args(parser, bits, tag_name):
    tag_args, tag_kwargs = parse_bits(
        parser=parser,
        bits=bits,
        params=["tag_name", "name"],
        takes_context=False,
        name=tag_name,
        varargs=True,
        **PARSE_BITS_DEFAULTS
    )

    assert tag_name == tag_args[0].token, "Internal error: Expected tag_name to be {}, but it was {}".format(
        tag_name, tag_args[0].token)
    if len(tag_args) > 1:  # At least one position arg, so take the first as the component name
        component_name = tag_args[1].token
        context_args = tag_args[2:]
        context_kwargs = tag_kwargs
    else:  # No positional args, so look for component name as keyword arg
        try:
            component_name = tag_kwargs.pop('name').token
            context_args = []
            context_kwargs = tag_kwargs
        except IndexError:
            raise TemplateSyntaxError(
                "Call the '%s' tag with a component name as the first parameter" % tag_name
            )

    if not is_wrapped_in_quotes(component_name):
        raise TemplateSyntaxError(
            "Component name '%s' should be in quotes" % component_name
        )

    trimmed_component_name = component_name[1: -1]
    component_class = registry.get(trimmed_component_name)
    component = component_class(trimmed_component_name)

    return component, context_args, context_kwargs


def safe_resolve(context_item, context):
    """Resolve FilterExpressions and Variables in context if possible.  Return other items unchanged."""

    return context_item.resolve(context) if hasattr(context_item, 'resolve') else context_item


def is_wrapped_in_quotes(s):
    return s.startswith(('"', "'")) and s[0] == s[-1]
