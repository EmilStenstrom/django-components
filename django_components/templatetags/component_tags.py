import sys
from typing import TYPE_CHECKING, Iterable, List, Optional, Tuple, Type, Union

if sys.version_info[:2] < (3, 9):
    from typing import ChainMap
else:
    from collections import ChainMap

import django.template
from django.conf import settings
from django.template import Context, Template
from django.template.base import (
    FilterExpression,
    Node,
    NodeList,
    TextNode,
    TokenType,
)
from django.template.defaulttags import CommentNode
from django.template.exceptions import TemplateSyntaxError
from django.template.library import parse_bits
from django.utils.safestring import mark_safe

from django_components.component_registry import ComponentRegistry
from django_components.component_registry import registry as component_registry
from django_components.middleware import (
    CSS_DEPENDENCY_PLACEHOLDER,
    JS_DEPENDENCY_PLACEHOLDER,
)

if TYPE_CHECKING:
    from django_components.component import Component


register = django.template.Library()


RENDERED_COMMENT_TEMPLATE = "<!-- _RENDERED {name} -->"

SLOT_REQUIRED_OPTION_KEYWORD = "required"
SLOT_DEFAULT_OPTION_KEYWORD = "default"

FILLED_SLOTS_CONTENT_CONTEXT_KEY = "_DJANGO_COMPONENTS_FILLED_SLOTS"

# Type aliases

SlotName = str
AliasName = str

DefaultFillContent = NodeList
NamedFillContent = Tuple[SlotName, NodeList, Optional[AliasName]]

FillContent = Tuple[NodeList, Optional[AliasName]]
FilledSlotsContext = ChainMap[Tuple[SlotName, Template], FillContent]


def get_components_from_registry(registry: ComponentRegistry):
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
        component_class = component_registry.get(component_name)
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
                    name=component.registered_name
                )
            )
        return mark_safe(
            "\n".join(preloaded_dependencies)
            + CSS_DEPENDENCY_PLACEHOLDER
            + JS_DEPENDENCY_PLACEHOLDER
        )
    else:
        rendered_dependencies = []
        for component in get_components_from_registry(component_registry):
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
                    name=component.registered_name
                )
            )
        return mark_safe(
            "\n".join(preloaded_dependencies) + CSS_DEPENDENCY_PLACEHOLDER
        )
    else:
        rendered_dependencies = []
        for component in get_components_from_registry(component_registry):
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
                    name=component.registered_name
                )
            )
        return mark_safe(
            "\n".join(preloaded_dependencies) + JS_DEPENDENCY_PLACEHOLDER
        )
    else:
        rendered_dependencies = []
        for component in get_components_from_registry(component_registry):
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
        FilterExpression(component_name, parser),
        context_args,
        context_kwargs,
        isolated_context=isolated_context,
    )


class UserSlotVar:
    """
    Extensible mechanism for offering 'fill' blocks in template access to properties
    of parent slot.

    How it works: At render time, SlotNode(s) that have been aliased in the fill tag
    of the component instance create an instance of UserSlotVar. This instance is made
    available to the rendering context on a key matching the slot alias (see
    SlotNode.render() for implementation).
    """

    def __init__(self, slot: "SlotNode", context: Context):
        self._slot = slot
        self._context = context

    @property
    def default(self) -> str:
        return mark_safe(self._slot.nodelist.render(self._context))


class TemplateAwareNodeMixin:
    _template: Template

    @property
    def template(self) -> Template:
        try:
            return self._template
        except AttributeError:
            raise RuntimeError(
                f"Internal error: Instance of {type(self).__name__} was not "
                "linked to Template before use in render() context."
            )

    @template.setter
    def template(self, value) -> None:
        self._template = value


class SlotNode(Node, TemplateAwareNodeMixin):
    def __init__(
        self,
        name: str,
        nodelist: NodeList,
        is_required: bool = False,
        is_default: bool = False,
    ):
        self.name = name
        self.nodelist = nodelist
        self.is_required = is_required
        self.is_default = is_default

    @property
    def active_flags(self):
        m = []
        if self.is_required:
            m.append("required")
        if self.is_default:
            m.append("default")
        return m

    def __repr__(self):
        return f"<Slot Node: {self.name}. Contents: {repr(self.nodelist)}. Options: {self.active_flags}>"

    def render(self, context):
        try:
            filled_slots_map: FilledSlotsContext = context[
                FILLED_SLOTS_CONTENT_CONTEXT_KEY
            ]
        except KeyError:
            raise TemplateSyntaxError(
                f"Attempted to render SlotNode '{self.name}' outside a parent component."
            )

        extra_context = {}
        try:
            slot_fill_content: Optional[FillContent] = filled_slots_map[
                (self.name, self.template)
            ]
        except KeyError:
            if self.is_required:
                raise TemplateSyntaxError(
                    f"Slot '{self.name}' is marked as 'required' (i.e. non-optional), "
                    f"yet no fill is provided. "
                )
            nodelist = self.nodelist
        else:
            nodelist, alias = slot_fill_content
            if alias:
                if not alias.isidentifier():
                    raise TemplateSyntaxError()
                extra_context[alias] = UserSlotVar(self, context)

        with context.update(extra_context):
            return nodelist.render(context)


@register.tag("slot")
def do_slot(parser, token):
    bits = token.split_contents()
    args = bits[1:]
    # e.g. {% slot <name> %}
    is_required = False
    is_default = False
    if 1 <= len(args) <= 3:
        slot_name, *options = args
        if not is_wrapped_in_quotes(slot_name):
            raise TemplateSyntaxError(
                f"'{bits[0]}' name must be a string 'literal'."
            )
        slot_name = strip_quotes(slot_name)
        modifiers_count = len(options)
        if SLOT_REQUIRED_OPTION_KEYWORD in options:
            is_required = True
            modifiers_count -= 1
        if SLOT_DEFAULT_OPTION_KEYWORD in options:
            is_default = True
            modifiers_count -= 1
        if modifiers_count != 0:
            keywords = [
                SLOT_REQUIRED_OPTION_KEYWORD,
                SLOT_DEFAULT_OPTION_KEYWORD,
            ]
            raise TemplateSyntaxError(
                f"Invalid options passed to 'slot' tag. Valid choices: {keywords}."
            )
    else:
        raise TemplateSyntaxError(
            "'slot' tag does not match pattern "
            "{% slot <name> ['default'] ['required'] %}. "
            "Order of options is free."
        )

    nodelist = parser.parse(parse_until=["endslot"])
    parser.delete_first_token()
    return SlotNode(
        slot_name,
        nodelist,
        is_required=is_required,
        is_default=is_default,
    )


class BaseFillNode(Node):
    def __init__(self, nodelist: NodeList):
        self.nodelist: NodeList = nodelist

    def __repr__(self):
        raise NotImplementedError

    def render(self, context):
        raise TemplateSyntaxError(
            "{% fill ... %} block cannot be rendered directly. "
            "You are probably seeing this because you have used one outside "
            "a {% component_block %} context."
        )


class NamedFillNode(BaseFillNode):
    def __init__(
        self,
        nodelist: NodeList,
        name_fexp: FilterExpression,
        alias_fexp: Optional[FilterExpression] = None,
    ):
        super().__init__(nodelist)
        self.name_fexp = name_fexp
        self.alias_fexp = alias_fexp

    def __repr__(self):
        return f"<{type(self)} Name: {self.name_fexp}. Contents: {repr(self.nodelist)}.>"


class ImplicitFillNode(BaseFillNode):
    """
    Instantiated when a `component_block` tag pair is passed template content that
    excludes `fill` tags. Nodes of this type contribute their nodelists to slots marked
    as 'default'.
    """

    def __repr__(self):
        return f"<{type(self)} Contents: {repr(self.nodelist)}.>"


@register.tag("fill")
def do_fill(parser, token):
    """Block tag whose contents 'fill' (are inserted into) an identically named
    'slot'-block in the component template referred to by a parent component_block.
    It exists to make component nesting easier.

    This tag is available only within a {% component_block %}..{% endcomponent_block %} block.
    Runtime checks should prohibit other usages.
    """
    bits = token.split_contents()
    tag = bits[0]
    args = bits[1:]
    # e.g. {% fill <name> %}
    alias_fexp: Optional[FilterExpression] = None
    if len(args) == 1:
        tgt_slot_name: str = args[0]
    # e.g. {% fill <name> as <alias> %}
    elif len(args) == 3:
        tgt_slot_name, as_keyword, alias = args
        if as_keyword.lower() != "as":
            raise TemplateSyntaxError(
                f"{tag} tag args do not conform to pattern '<target slot> as <alias>'"
            )
        alias_fexp = FilterExpression(alias, parser)
    else:
        raise TemplateSyntaxError(
            f"'{tag}' tag takes either 1 or 3 arguments: Received {len(args)}."
        )
    nodelist = parser.parse(parse_until=["endfill"])
    parser.delete_first_token()

    return NamedFillNode(
        nodelist,
        name_fexp=FilterExpression(tgt_slot_name, tag),
        alias_fexp=alias_fexp,
    )


class ComponentNode(Node):
    def __init__(
        self,
        name_fexp: FilterExpression,
        context_args,
        context_kwargs,
        isolated_context=False,
        fill_nodes: Union[ImplicitFillNode, Iterable[NamedFillNode]] = (),
    ):
        self.name_fexp = name_fexp
        self.context_args = context_args or []
        self.context_kwargs = context_kwargs or {}
        self.isolated_context = isolated_context
        self.fill_nodes = fill_nodes

    @property
    def nodelist(self) -> Union[NodeList, Node]:
        if isinstance(self.fill_nodes, ImplicitFillNode):
            return NodeList([self.fill_nodes])
        else:
            return NodeList(self.fill_nodes)

    def __repr__(self):
        return "<ComponentNode: %s. Contents: %r>" % (
            self.name_fexp,
            getattr(
                self, "nodelist", None
            ),  # 'nodelist' attribute only assigned later.
        )

    def render(self, context: Context):
        resolved_component_name = self.name_fexp.resolve(context)
        component_cls: Type[Component] = component_registry.get(
            resolved_component_name
        )

        # Resolve FilterExpressions and Variables that were passed as args to the
        # component, then call component's context method
        # to get values to insert into the context
        resolved_context_args = [
            safe_resolve(arg, context) for arg in self.context_args
        ]
        resolved_context_kwargs = {
            key: safe_resolve(kwarg, context)
            for key, kwarg in self.context_kwargs.items()
        }

        if isinstance(self.fill_nodes, ImplicitFillNode):
            fill_content = self.fill_nodes.nodelist
        else:
            fill_content = []
            for fill_node in self.fill_nodes:
                # Note that outer component context is used to resolve variables in
                # fill tag.
                resolved_name = fill_node.name_fexp.resolve(context)
                if fill_node.alias_fexp:
                    resolved_alias: str = fill_node.alias_fexp.resolve(context)
                    if not resolved_alias.isidentifier():
                        raise TemplateSyntaxError(
                            f"Fill tag alias '{fill_node.alias_fexp.var}' in component "
                            f"{resolved_component_name} does not resolve to "
                            f"a valid Python identifier. Got: '{resolved_alias}'."
                        )
                else:
                    resolved_alias: None = None
                fill_content.append(
                    (resolved_name, fill_node.nodelist, resolved_alias)
                )

        component: Component = component_cls(
            registered_name=resolved_component_name,
            outer_context=context,
            fill_content=fill_content,
        )

        component_context: dict = component.get_context_data(
            *resolved_context_args, **resolved_context_kwargs
        )

        if self.isolated_context:
            context = context.new()
        with context.update(component_context):
            rendered_component = component.render(context)

        if is_dependency_middleware_active():
            return (
                RENDERED_COMMENT_TEMPLATE.format(name=resolved_component_name)
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
    body: NodeList = parser.parse(parse_until=["endcomponent_block"])
    parser.delete_first_token()
    fill_nodes = ()
    if block_has_content(body):
        for parse_fn in (
            try_parse_as_default_fill,
            try_parse_as_named_fill_tag_set,
        ):
            fill_nodes = parse_fn(body)
            if fill_nodes:
                break
        else:
            raise TemplateSyntaxError(
                "Illegal content passed to 'component_block' tag pair. "
                "Possible causes: 1) Explicit 'fill' tags cannot occur alongside other "
                "tags except comment tags; 2) Default (default slot-targeting) content "
                "is mixed with explict 'fill' tags."
            )
    component_node = ComponentNode(
        FilterExpression(component_name, parser),
        context_args,
        context_kwargs,
        isolated_context=isolated_context,
        fill_nodes=fill_nodes,
    )

    return component_node


def try_parse_as_named_fill_tag_set(
    nodelist: NodeList,
) -> Optional[Iterable[NamedFillNode]]:
    result = []
    seen_name_fexps = set()
    for node in nodelist:
        if isinstance(node, NamedFillNode):
            if node.name_fexp in seen_name_fexps:
                raise TemplateSyntaxError(
                    f"Multiple fill tags cannot target the same slot name: "
                    f"Detected duplicate fill tag name '{node.name_fexp}'."
                )
            result.append(node)
        elif isinstance(node, CommentNode):
            pass
        elif isinstance(node, TextNode) and node.s.isspace():
            pass
        else:
            return None
    return result


def try_parse_as_default_fill(
    nodelist: NodeList,
) -> Optional[ImplicitFillNode]:
    # nodelist.get_nodes_by_type()
    nodes_stack: List[Node] = list(nodelist)
    while nodes_stack:
        node = nodes_stack.pop()
        if isinstance(node, NamedFillNode):
            return None
        elif isinstance(node, ComponentNode):
            # Stop searching here, as fill tags are permitted inside component blocks
            # embedded within a default fill node.
            continue
        for nodelist_attr_name in node.child_nodelists:
            nodes_stack.extend(getattr(node, nodelist_attr_name, []))
    else:
        return ImplicitFillNode(nodelist=nodelist)


def block_has_content(nodelist) -> bool:
    for node in nodelist:
        if isinstance(node, TextNode) and node.s.isspace():
            pass
        elif isinstance(node, CommentNode):
            pass
        else:
            return True
    return False


def is_whitespace_node(node: Node) -> bool:
    return isinstance(node, TextNode) and node.s.isspace()


def is_whitespace_token(token):
    return token.token_type == TokenType.TEXT and not token.contents.strip()


def is_block_tag_token(token, name):
    return (
        token.token_type == TokenType.BLOCK
        and token.split_contents()[0] == name
    )


@register.tag(name="if_filled")
def do_if_filled_block(parser, token):
    """
    ### Usage

    Example:

    ```
    {% if_filled <slot> (<bool>) %}
        ...
    {% elif_filled <slot> (<bool>) %}
        ...
    {% else_filled %}
        ...
    {% endif_filled %}
    ```

    Notes:

    Optional arg `<bool>` is True by default.
    If a False is provided instead, the effect is a negation of the `if_filled` check:
    The behavior is analogous to `if not is_filled <slot>`.
    This design prevents us having to define a separate `if_unfilled` tag.
    """
    bits = token.split_contents()
    starting_tag = bits[0]
    slot_name, is_positive = parse_if_filled_bits(bits)
    nodelist = parser.parse(("elif_filled", "else_filled", "endif_filled"))
    branches: List[_IfSlotFilledBranchNode] = [
        IfSlotFilledConditionBranchNode(
            slot_name=slot_name, nodelist=nodelist, is_positive=is_positive
        )
    ]

    token = parser.next_token()

    # {% elif_filled <slot> (<is_positive>) %} (repeatable)
    while token.contents.startswith("elif_filled"):
        bits = token.split_contents()
        slot_name, is_positive = parse_if_filled_bits(bits)
        nodelist: NodeList = parser.parse(
            ("elif_filled", "else_filled", "endif_filled")
        )
        branches.append(
            IfSlotFilledConditionBranchNode(
                slot_name=slot_name, nodelist=nodelist, is_positive=is_positive
            )
        )

        token = parser.next_token()

    # {% else_filled %} (optional)
    if token.contents.startswith("else_filled"):
        bits = token.split_contents()
        _, _ = parse_if_filled_bits(bits)
        nodelist = parser.parse(("endif_filled",))
        branches.append(IfSlotFilledElseBranchNode(nodelist))
        token = parser.next_token()

    # {% endif_filled %}
    if token.contents != "endif_filled":
        raise TemplateSyntaxError(
            f"{{% {starting_tag} %}} missing closing {{% endif_filled %}} tag"
            f" at line {token.lineno}: '{token.contents}'"
        )

    return IfSlotFilledNode(branches)


def parse_if_filled_bits(
    bits: List[str],
) -> Tuple[Optional[str], Optional[bool]]:
    tag, args = bits[0], bits[1:]
    if tag in ("else_filled", "endif_filled"):
        if len(args) != 0:
            raise TemplateSyntaxError(
                f"Tag '{tag}' takes no arguments. Received '{' '.join(args)}'"
            )
        else:
            return None, None
    if len(args) == 1:
        slot_name = args[0]
        is_positive = True
    elif len(args) == 2:
        slot_name = args[0]
        is_positive = bool_from_string(args[1])
    else:
        raise TemplateSyntaxError(
            f"{bits[0]} tag arguments '{' '.join(args)}' do not match pattern "
            f"'<slotname> (<is_positive>)'"
        )
    if not is_wrapped_in_quotes(slot_name):
        raise TemplateSyntaxError(
            f"First argument of '{bits[0]}' must be a quoted string 'literal'."
        )
    slot_name = strip_quotes(slot_name)
    return slot_name, is_positive


class _IfSlotFilledBranchNode(Node):
    def __init__(self, nodelist: NodeList) -> None:
        self.nodelist = nodelist

    def render(self, context: Context) -> str:
        return self.nodelist.render(context)

    def evaluate(self, context) -> bool:
        raise NotImplementedError


class IfSlotFilledConditionBranchNode(
    _IfSlotFilledBranchNode, TemplateAwareNodeMixin
):
    def __init__(
        self,
        slot_name: str,
        nodelist: NodeList,
        is_positive=True,
    ) -> None:
        self.slot_name = slot_name
        self.is_positive: bool = is_positive
        super().__init__(nodelist)

    def evaluate(self, context) -> bool:
        try:
            filled_slots: FilledSlotsContext = context[
                FILLED_SLOTS_CONTENT_CONTEXT_KEY
            ]
        except KeyError:
            raise TemplateSyntaxError(
                f"Attempted to render {type(self).__name__} outside a Component rendering context."
            )
        slot_key = (self.slot_name, self.template)
        is_filled = filled_slots.get(slot_key, None) is not None
        # Make polarity switchable.
        # i.e. if slot name is NOT filled and is_positive=False,
        # then False == False -> True
        return is_filled == self.is_positive


class IfSlotFilledElseBranchNode(_IfSlotFilledBranchNode):
    def evaluate(self, context) -> bool:
        return True


class IfSlotFilledNode(Node):
    def __init__(
        self,
        branches: List[_IfSlotFilledBranchNode],
    ):
        self.branches = branches

    def __repr__(self):
        return f"<{self.__class__.__name__}>"

    @property
    def nodelist(self):
        return NodeList(self.branches)

    def render(self, context):
        for node in self.branches:
            if isinstance(node, IfSlotFilledElseBranchNode):
                return node.render(context)
            elif isinstance(node, IfSlotFilledConditionBranchNode):
                if node.evaluate(context):
                    return node.render(context)
        return ""


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

    if tag_name != tag_args[0].token:
        raise RuntimeError(
            f"Internal error: Expected tag_name to be {tag_name}, but it was {tag_args[0].token}"
        )
    if len(tag_args) > 1:
        # At least one position arg, so take the first as the component name
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
                f"Call the '{tag_name}' tag with a component name as the first parameter"
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


def norm_and_validate_name(name: str, tag: str, context: Optional[str] = None):
    """
    Notes:
        - Value of `tag` in {"slot", "fill", "alias"}
    """
    name = strip_quotes(name)
    if not name.isidentifier():
        context = f" in '{context}'" if context else ""
        raise TemplateSyntaxError(
            f"{tag} name '{name}'{context} "
            "is not a valid Python identifier."
        )
    return name


def strip_quotes(s: str) -> str:
    return s.strip("\"'")


def bool_from_string(s: str):
    s = strip_quotes(s.lower())
    if s == "true":
        return True
    elif s == "false":
        return False
    else:
        raise TemplateSyntaxError(f"Expected a bool value. Received: '{s}'")
