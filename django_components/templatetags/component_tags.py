from collections import defaultdict

from django import template
from django.conf import settings
from django.template.base import Node, NodeList, TemplateSyntaxError, TokenType
from django.template.library import parse_bits
from django.utils.safestring import mark_safe

from django_components.component import ACTIVE_SLOT_CONTEXT_KEY, registry
from django_components.middleware import (
    CSS_DEPENDENCY_PLACEHOLDER,
    JS_DEPENDENCY_PLACEHOLDER,
)

register = template.Library()


RENDERED_COMMENT_TEMPLATE = "<!-- _RENDERED {name} -->"


def get_components_from_registry(registry):
    """Returns a list unique components from the registry."""

    unique_component_classes = set(registry.all().values())

    components = []
    for component_class in unique_component_classes:
        components.append(component_class(component_class.__name__))

    return components


def get_components_from_preload_str(preload_str):
    """Returns a list of unique components from a comma-separated str"""

    components = []
    for component_name in preload_str.split(","):
        component_name = component_name.strip()
        if not component_name:
            continue
        component_class = registry.get(component_name)
        components.append(component_class(component_name))

    return components


@register.simple_tag(name="component_dependencies")
def component_dependencies_tag(preload=""):
    """Marks location where CSS link and JS script tags should be rendered."""

    if is_dependency_middleware_active():
        preloaded_dependencies = []
        for component in get_components_from_preload_str(preload):
            preloaded_dependencies.append(
                RENDERED_COMMENT_TEMPLATE.format(
                    name=component._component_name
                )
            )
        return mark_safe(
            "\n".join(preloaded_dependencies)
            + CSS_DEPENDENCY_PLACEHOLDER
            + JS_DEPENDENCY_PLACEHOLDER
        )
    else:
        rendered_dependencies = []
        for component in get_components_from_registry(registry):
            rendered_dependencies.append(component.render_dependencies())

        return mark_safe("\n".join(rendered_dependencies))


@register.simple_tag(name="component_css_dependencies")
def component_css_dependencies_tag(preload=""):
    """Marks location where CSS link tags should be rendered."""

    if is_dependency_middleware_active():
        preloaded_dependencies = []
        for component in get_components_from_preload_str(preload):
            preloaded_dependencies.append(
                RENDERED_COMMENT_TEMPLATE.format(
                    name=component._component_name
                )
            )
        return mark_safe(
            "\n".join(preloaded_dependencies) + CSS_DEPENDENCY_PLACEHOLDER
        )
    else:
        rendered_dependencies = []
        for component in get_components_from_registry(registry):
            rendered_dependencies.append(component.render_css_dependencies())

        return mark_safe("\n".join(rendered_dependencies))


@register.simple_tag(name="component_js_dependencies")
def component_js_dependencies_tag(preload=""):
    """Marks location where JS script tags should be rendered."""

    if is_dependency_middleware_active():
        preloaded_dependencies = []
        for component in get_components_from_preload_str(preload):
            preloaded_dependencies.append(
                RENDERED_COMMENT_TEMPLATE.format(
                    name=component._component_name
                )
            )
        return mark_safe(
            "\n".join(preloaded_dependencies) + JS_DEPENDENCY_PLACEHOLDER
        )
    else:
        rendered_dependencies = []
        for component in get_components_from_registry(registry):
            rendered_dependencies.append(component.render_js_dependencies())

        return mark_safe("\n".join(rendered_dependencies))


@register.tag(name="component")
def do_component(parser, token):
    bits = token.split_contents()
    bits, isolated_context = check_for_isolated_context_keyword(bits)
    component_name, context_args, context_kwargs = parse_component_with_args(
        parser, bits, "component"
    )
    return ComponentNode(
        component_name,
        context_args,
        context_kwargs,
        isolated_context=isolated_context,
    )


class SlotNode(Node):
    def __init__(self, name, nodelist):
        self.name, self.nodelist = name, nodelist
        self.parent_component = None
        self.context = None

    def __repr__(self):
        return "<Slot Node: %s. Contents: %r>" % (self.name, self.nodelist)

    def render(self, context):
        # Thread safety: storing the context as a property of the cloned SlotNode without using
        # the render_context facility should be thread-safe, since each cloned_node
        # is only used for a single render.
        cloned_node = SlotNode(self.name, self.nodelist)
        cloned_node.parent_component = self.parent_component
        cloned_node.context = context

        with context.update({"slot": cloned_node}):
            return self.get_nodelist(context).render(context)

    def get_nodelist(self, context):
        if ACTIVE_SLOT_CONTEXT_KEY not in context:
            raise TemplateSyntaxError(
                f"Attempted to render SlotNode {self.name} outside of a parent Component or "
                "without access to context provided by its parent Component. This will not"
                "work properly."
            )

        overriding_nodelist = context[ACTIVE_SLOT_CONTEXT_KEY].get(
            self.name, None
        )
        return (
            overriding_nodelist
            if overriding_nodelist is not None
            else self.nodelist
        )

    def super(self):
        """Render default slot content."""
        return mark_safe(self.nodelist.render(self.context))


@register.tag("slot")
def do_slot(parser, token):
    bits = token.split_contents()
    if len(bits) != 2:
        raise TemplateSyntaxError("'%s' tag takes only one argument" % bits[0])

    slot_name = bits[1].strip('"')
    nodelist = parser.parse(parse_until=["endslot"])
    parser.delete_first_token()

    return SlotNode(slot_name, nodelist)


class ComponentNode(Node):
    class InvalidSlot:
        def super(self):
            raise TemplateSyntaxError(
                "slot.super may only be called within a {% slot %}/{% endslot %} block."
            )

    def __init__(
        self,
        component_name,
        context_args,
        context_kwargs,
        slots=None,
        isolated_context=False,
    ):
        self.context_args = context_args or []
        self.context_kwargs = context_kwargs or {}
        self.component_name, self.isolated_context = (
            component_name,
            isolated_context,
        )
        self.slots = slots

    def __repr__(self):
        return "<Component Node: %s. Contents: %r>" % (
            self.component_name,
            self.nodelist,
        )

    def render(self, context):
        component_name = template.Variable(self.component_name).resolve(
            context
        )
        component_class = registry.get(component_name)
        component = component_class(component_name)

        # Group slot notes by name and concatenate their nodelists
        component.slots = defaultdict(NodeList)
        for slot in self.slots or []:
            component.slots[slot.name].extend(slot.nodelist)

        component.outer_context = context.flatten()

        # Resolve FilterExpressions and Variables that were passed as args to the component, then call component's
        # context method to get values to insert into the context
        resolved_context_args = [
            safe_resolve(arg, context) for arg in self.context_args
        ]
        resolved_context_kwargs = {
            key: safe_resolve(kwarg, context)
            for key, kwarg in self.context_kwargs.items()
        }
        component_context = component.get_context_data(
            *resolved_context_args, **resolved_context_kwargs
        )

        # Create a fresh context if requested
        if self.isolated_context:
            context = context.new()

        with context.update(component_context):
            rendered_component = component.render(context)
            if is_dependency_middleware_active():
                return (
                    RENDERED_COMMENT_TEMPLATE.format(
                        name=component._component_name
                    )
                    + rendered_component
                )
            else:
                return rendered_component


@register.tag(name="component_block")
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
    component_name, context_args, context_kwargs = parse_component_with_args(
        parser, bits, "component_block"
    )
    return ComponentNode(
        component_name,
        context_args,
        context_kwargs,
        slots=[
            do_slot(parser, slot_token) for slot_token in slot_tokens(parser)
        ],
        isolated_context=isolated_context,
    )


def slot_tokens(parser):
    """Yield each 'slot' token appearing before the next 'endcomponent_block' token.

    Raises TemplateSyntaxError if there are other content tokens or if there is no endcomponent_block token."""

    def is_whitespace(token):
        return (
            token.token_type == TokenType.TEXT and not token.contents.strip()
        )

    def is_block_tag(token, name):
        return (
            token.token_type == TokenType.BLOCK
            and token.split_contents()[0] == name
        )

    while True:
        try:
            token = parser.next_token()
        except IndexError:
            raise TemplateSyntaxError("Unclosed component_block tag")
        if is_block_tag(token, name="endcomponent_block"):
            return
        elif is_block_tag(token, name="slot"):
            yield token
        elif (
            not is_whitespace(token) and token.token_type != TokenType.COMMENT
        ):
            raise TemplateSyntaxError(
                f"Content tokens in component blocks must be inside of slot tags: {token}"
            )


def check_for_isolated_context_keyword(bits):
    """Return True and strip the last word if token ends with 'only' keyword."""

    if bits[-1] == "only":
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
        varkw=[],
        defaults=None,
        kwonly=[],
        kwonly_defaults=None,
    )
    assert (
        tag_name == tag_args[0].token
    ), "Internal error: Expected tag_name to be {}, but it was {}".format(
        tag_name, tag_args[0].token
    )
    if (
        len(tag_args) > 1
    ):  # At least one position arg, so take the first as the component name
        component_name = tag_args[1].token
        context_args = tag_args[2:]
        context_kwargs = tag_kwargs
    else:  # No positional args, so look for component name as keyword arg
        try:
            component_name = tag_kwargs.pop("name").token
            context_args = []
            context_kwargs = tag_kwargs
        except IndexError:
            raise TemplateSyntaxError(
                "Call the '%s' tag with a component name as the first parameter"
                % tag_name
            )

    return component_name, context_args, context_kwargs


def safe_resolve(context_item, context):
    """Resolve FilterExpressions and Variables in context if possible.  Return other items unchanged."""

    return (
        context_item.resolve(context)
        if hasattr(context_item, "resolve")
        else context_item
    )


def is_wrapped_in_quotes(s):
    return s.startswith(('"', "'")) and s[0] == s[-1]


def is_dependency_middleware_active():
    return getattr(settings, "COMPONENTS", {}).get(
        "RENDER_DEPENDENCIES", False
    )
