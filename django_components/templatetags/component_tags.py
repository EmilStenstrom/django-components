from typing import TYPE_CHECKING, Dict, Iterator, List, Optional, Tuple

from django import template
from django.conf import settings
from django.template import Context
from django.template.base import (
    Node,
    NodeList,
    TemplateSyntaxError,
    TextNode,
    TokenType,
    Variable,
    VariableDoesNotExist,
)
from django.template.defaulttags import CommentNode
from django.template.library import parse_bits
from django.utils.safestring import mark_safe

from django_components.component import FILLED_SLOTS_CONTEXT_KEY, registry
from django_components.middleware import (
    CSS_DEPENDENCY_PLACEHOLDER,
    JS_DEPENDENCY_PLACEHOLDER,
)

if TYPE_CHECKING:
    from django_components.component import Component

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
        NameVariable(component_name, tag="component"),
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

    # (lemontheme): If 'default' is accepted as option keyword for slot tags,
    #  then I propose 'original' replaces 'default' in the 'slot.super' sense.
    #  Otherwise, we would have both
    #  - {% slot ... default %} ...
    #  and
    #  - {% fill ... as <alias> %} <alias>.default {%endfill %}.
    #  I'm afraid this risks being a source of confusion, as users might wrongly assume
    #  that there is a link between the two separate usages of 'default'.
    @property
    def original(self) -> str:
        return self.default


class SlotNode(Node):
    def __init__(
        self,
        name: str,
        nodelist: NodeList,
        template_name: str = "",
        is_required: bool = False,
        is_default: bool = False,
    ):
        self.name = name
        self.nodelist = nodelist
        self.template_name = template_name
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
        return f"<Slot Node: {self.name}. Contents: {repr(self.nodelist)}. Flags: {self.active_flags}>"

    def render(self, context):
        if FILLED_SLOTS_CONTEXT_KEY not in context:
            raise TemplateSyntaxError(
                f"Attempted to render SlotNode '{self.name}' outside a parent component."
            )
        # Try to find FillNode
        filled_slots: Dict[Optional[str], List[FillNode]] = context[
            FILLED_SLOTS_CONTEXT_KEY
        ]
        fill_node_stack = filled_slots.get(self.name, None)
        fill_node: Optional[FillNode] = None
        if fill_node_stack:  # if None or []
            fill_node = fill_node_stack.pop()
        elif self.is_default:
            implicit_fill_key = None
            implicit_fill_node_stack = filled_slots.get(implicit_fill_key)
            if implicit_fill_node_stack:
                fill_node = implicit_fill_node_stack.pop()
        if self.is_required:
            if fill_node is None:
                raise TemplateSyntaxError(
                    f"Slot '{self.name}' is marked as 'required' (i.e. non-optional), "
                    f"yet no fill is provided. Check template '{self.template_name}'"
                )
        # //
        # Get nodelist and add alias variables to context.
        extra_context = {}
        if fill_node:
            nodelist = fill_node.nodelist
            if fill_node.alias_var is not None:
                aliased_slot_var = UserSlotVar(self, context)
                resolved_alias_name = fill_node.alias_var.resolve(context)
                extra_context[resolved_alias_name] = aliased_slot_var
        else:
            nodelist = self.nodelist  # slot nodelist
        # //

        with context.update(extra_context):
            return nodelist.render(context)


SLOT_REQUIRED_OPTION_KEYWORD = "required"
SLOT_DEFAULT_OPTION_KEYWORD = "default"


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
        raise_if_not_py_identifier(slot_name, bits[0])
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
            "'slot' tag does not match pattern {{% slot <name> ['default'] ['required'] %}}. "
            "Order of options is free."
        )

    nodelist = parser.parse(parse_until=["endslot"])
    parser.delete_first_token()
    template_name = parser.origin.template_name
    return SlotNode(
        slot_name,
        nodelist,
        template_name,
        is_required=is_required,
        is_default=is_default,
    )


class FillNode(Node):
    """
    Instantiated explicitly by 'fill' tag (is_implicit=False) inside component_block or
    implicitly by component_block containing zero top-level 'fill' tags.

    Notes:
        - When `is_implicit` = True, `name_var` must be None.
        - Behavior: `is_implicit` = True -> node targets SlotNode with `is_default` = True.
    """

    def __init__(
        self,
        name_var: Optional["NameVariable"],
        nodelist: NodeList,
        alias_var: Optional["NameVariable"] = None,
        is_implicit: bool = False,
    ):
        assert name_var is None if is_implicit else True
        self.name_var = name_var
        self.nodelist = nodelist
        self.alias_var: Optional[NameVariable] = alias_var
        self.is_implicit = is_implicit

    @property
    def active_flags(self):
        m = []
        if self.is_implicit:
            m.append("implicit")
        return m

    def get_resolved_name(self, context: Context) -> Optional[str]:
        if self.name_var:
            return self.name_var.resolve(context)
        else:
            return None

    def __repr__(self):
        return f"<{type(self)}: {self.name_var}. Contents: {repr(self.nodelist)}. Flags: {self.active_flags}>"

    def render(self, context):
        raise TemplateSyntaxError(
            f"{{% fill {self.name_var} %}} blocks cannot be rendered directly. "
            f"You are probably seeing this because you have used one outside "
            f"a {{% component_block %}} context."
        )


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
    alias_var = None
    if len(args) == 1:
        tgt_slot_name: str = args[0]
    # e.g. {% fill <name> as <alias> %}
    elif len(args) == 3:
        tgt_slot_name, as_keyword, alias = args
        if as_keyword.lower() != "as":
            raise TemplateSyntaxError(
                f"{tag} tag args do not conform to pattern '<target slot> as <alias>'"
            )
        raise_if_not_py_identifier(strip_quotes(alias), tag="alias")
        alias_var = NameVariable(alias, tag="alias")
    else:
        raise TemplateSyntaxError(
            f"'{tag}' tag takes either 1 or 3 arguments: Received {len(args)}."
        )

    raise_if_not_py_identifier(strip_quotes(tgt_slot_name), tag=tag)

    nodelist = parser.parse(parse_until=["endfill"])
    parser.delete_first_token()

    return FillNode(NameVariable(tgt_slot_name, tag), nodelist, alias_var)


class ComponentNode(Node):
    child_nodelists = ("fill_nodes",)

    def __init__(
        self,
        name_var: "NameVariable",
        context_args,
        context_kwargs,
        isolated_context=False,
    ):
        self.name_var = name_var
        self.context_args = context_args or []
        self.context_kwargs = context_kwargs or {}
        self.fill_nodes: NodeList[FillNode] = NodeList()
        self.isolated_context = isolated_context

    def __repr__(self):
        return "<Component Node: %s. Contents: %r>" % (
            self.name_var,
            getattr(
                self, "nodelist", None
            ),  # 'nodelist' attribute only assigned later.
        )

    def render(self, context):
        resolved_component_name = self.name_var.resolve(context)
        component_cls = registry.get(resolved_component_name)
        component: Component = component_cls(resolved_component_name)

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

        resolved_fills: Dict[Optional[str], FillNode] = {
            fill_node.get_resolved_name(context): fill_node
            for fill_node in self.fill_nodes
        }

        component.set_instance_fills(resolved_fills)
        component.set_outer_context(context)

        component_context = component.get_context_data(
            *resolved_context_args, **resolved_context_kwargs
        )
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
    component_node = ComponentNode(
        NameVariable(component_name, "component"),
        context_args,
        context_kwargs,
        isolated_context=isolated_context,
    )

    component_node.fill_nodes.extend(fill_nodes(parser))

    return component_node


def can_be_parsed_as_fill_tag_set(nodelist: NodeList) -> bool:
    for node in nodelist:
        if isinstance(node, (FillNode, CommentNode)):
            pass
        elif isinstance(node, TextNode) and node.s.isspace():
            pass
        else:
            return False
    return True


def can_be_parsed_as_implicit_fill_node(nodelist: NodeList) -> bool:
    # nodelist.get_nodes_by_type()
    nodes: List[Node] = list(nodelist)
    while nodes:
        node = nodes.pop()
        if isinstance(node, FillNode):
            return False
        elif isinstance(node, ComponentNode):
            # Stop searching here, as fill tags are permitted inside component blocks
            # embedded within an implicit fill node.
            continue
        for nodelist_attr_name in node.child_nodelists:
            nodes.extend(getattr(node, nodelist_attr_name, []))
    return True


def fill_nodes(parser) -> Iterator[FillNode]:
    nodelist = parser.parse(parse_until=["endcomponent_block"])
    parser.delete_first_token()
    # Standard filling context. Multiple fills with explicit 'fill' tags.
    if not nodelist:
        return
    # Implements pre-v0.28 behavior: a component_block is treated as containing
    # one or more fill tags plus optional comment tags and whitespaces.
    if can_be_parsed_as_fill_tag_set(nodelist):
        seen_name_vars = set()
        for node in nodelist:
            if not isinstance(node, FillNode):
                continue
            if node.name_var in seen_name_vars:
                raise TemplateSyntaxError(
                    f"Multiple fill tags cannot target the same slot name: "
                    f"Detected duplicate fill tag name '{node.name_var}'."
                )
            else:
                seen_name_vars.add(node.name_var)
                yield node
    # Implicit filling context. component_block tag pair contains arbitrary
    # content corresponding to a single slot marked as default in the component template.
    # Only fill tags are prohibited.
    elif can_be_parsed_as_implicit_fill_node(nodelist):
        fill_node = FillNode(
            name_var=None, nodelist=nodelist, alias_var=None, is_implicit=True
        )
        fill_node.nodelist = nodelist
        yield fill_node
    else:
        raise TemplateSyntaxError(
            "Illegal content passed to 'component_block' tag pair. "
            "Possible causes: 1) Explicit 'fill' tags cannot occur alongside other "
            "tags except comment tags; 2) Implicit (default slot-targeting) content "
            "is mixed with explict 'fill' tags."
        )


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
    slot_name_var: Optional[NameVariable]
    slot_name_var, is_positive = parse_if_filled_bits(bits)
    nodelist = parser.parse(("elif_filled", "else_filled", "endif_filled"))
    branches: List[Tuple[Optional[NameVariable], NodeList, Optional[bool]]] = [
        (slot_name_var, nodelist, is_positive)
    ]

    token = parser.next_token()

    # {% elif_filled <slot> (<is_positive>) %} (repeatable)
    while token.contents.startswith("elif_filled"):
        bits = token.split_contents()
        slot_name_var, is_positive = parse_if_filled_bits(bits)
        nodelist: NodeList = parser.parse(
            ("elif_filled", "else_filled", "endif_filled")
        )
        branches.append((slot_name_var, nodelist, is_positive))
        token = parser.next_token()

    # {% else_filled %} (optional)
    if token.contents.startswith("else_filled"):
        bits = token.split_contents()
        _, _ = parse_if_filled_bits(bits)
        nodelist = parser.parse(("endif_filled",))
        branches.append((None, nodelist, None))
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
) -> Tuple[Optional["NameVariable"], Optional[bool]]:
    tag, args = bits[0], bits[1:]
    if tag in ("else_filled", "endif_filled"):
        if len(args) != 0:
            raise TemplateSyntaxError(
                f"Tag '{tag}' takes no arguments. "
                f"Received '{' '.join(args)}'"
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
    raise_if_not_py_identifier(strip_quotes(slot_name), tag=tag)
    slot_name_var = NameVariable(slot_name, tag)
    return slot_name_var, is_positive


class IfSlotFilledNode(Node):
    def __init__(
        self,
        branches: List[
            Tuple[Optional["NameVariable"], NodeList, Optional[bool]]
        ],
    ):
        # [(<slot name var | None (= condition)>, nodelist, <is_positive>)]
        self.branches = branches

    def __iter__(self):
        for _, nodelist, _ in self.branches:
            for node in nodelist:
                yield node

    def __repr__(self):
        return f"<{self.__class__.__name__}>"

    @property
    def nodelist(self):
        return NodeList(self)

    def render(self, context):
        current_fills = context.get(FILLED_SLOTS_CONTEXT_KEY)
        for slot_name_var, nodelist, is_positive in self.branches:
            # None indicates {% else_filled %} has been reached.
            # This means all other branches have been exhausted.
            if slot_name_var is None:
                return nodelist.render(context)
            # Make polarity switchable.
            # i.e. if slot name is NOT filled and is_positive=False,
            # then False == False -> True
            slot_name = slot_name_var.resolve(context)
            if (slot_name in current_fills) == is_positive:
                return nodelist.render(context)
            else:
                continue
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


def raise_if_not_py_identifier(
    name: str, tag: str, content: Optional[str] = None
):
    """
    Notes:
        - Value of `tag` in {"slot", "fill", "alias", "component"}
    """
    if not name.isidentifier():
        content = f" in '{{% {content} ...'" if content else ""
        raise TemplateSyntaxError(
            f"'{tag}' name '{name}'{content} with/without quotes "
            "is not a valid Python identifier."
        )


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


class NameVariable(Variable):
    def __init__(self, var: str, tag: str):
        super().__init__(var)
        self._tag = tag

    def resolve(self, context):
        try:
            return super().resolve(context)
        except VariableDoesNotExist:
            raise TemplateSyntaxError(
                f"<name> = '{self.var}' in '{{% {self._tag} <name> ...' can't be resolved "
                f"against context."
            )
