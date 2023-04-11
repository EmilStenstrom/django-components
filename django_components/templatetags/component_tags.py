from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from django import template
from django.conf import settings
from django.template import Context
from django.template.base import (
    Node,
    NodeList,
    TemplateSyntaxError,
    TokenType,
    Variable,
    VariableDoesNotExist,
)
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


class SlotNode(Node):
    def __init__(
        self, name, nodelist, template_name: str = "", required=False
    ):
        self.name = name
        self.nodelist = nodelist
        self.template_name = template_name
        self.is_required = required

    def __repr__(self):
        return f"<Slot Node: {self.name}. Contents: {repr(self.nodelist)}>"

    def render(self, context):
        if FILLED_SLOTS_CONTEXT_KEY not in context:
            raise TemplateSyntaxError(
                f"Attempted to render SlotNode '{self.name}' outside a parent component."
            )
        filled_slots: Dict[str, List[FillNode]] = context[
            FILLED_SLOTS_CONTEXT_KEY
        ]
        fill_node_stack = filled_slots.get(self.name, None)
        extra_context = {}
        if not fill_node_stack:  # if None or []
            nodelist = self.nodelist
            # Raise if slot is 'required'
            if self.is_required:
                raise TemplateSyntaxError(
                    f"Slot '{self.name}' is marked as 'required' (i.e. non-optional), "
                    f"yet no fill is provided. Check template '{self.template_name}'"
                )
        else:
            fill_node = fill_node_stack.pop()
            nodelist = fill_node.nodelist

            if fill_node.alias_var is not None:
                aliased_slot_var = UserSlotVar(self, context)
                resolved_alias_name = fill_node.alias_var.resolve(context)
                extra_context[resolved_alias_name] = aliased_slot_var
        with context.update(extra_context):
            return nodelist.render(context)


@register.tag("slot")
def do_slot(parser, token):
    bits = token.split_contents()
    args = bits[1:]
    # e.g. {% slot <name> %}
    if len(args) == 1:
        slot_name: str = args[0]
        required = False
    elif len(args) == 2:
        slot_name: str = args[0]
        required_keyword = args[1]
        if required_keyword != "required":
            raise TemplateSyntaxError(
                f"'{bits[0]}' only accepts 'required' keyword as optional second argument"
            )
        else:
            required = True
    else:
        raise TemplateSyntaxError(
            f"{bits[0]}' tag takes only one argument (the slot name)"
        )

    if not is_wrapped_in_quotes(slot_name):
        raise TemplateSyntaxError(
            f"'{bits[0]}' name must be a string 'literal'."
        )

    slot_name = strip_quotes(slot_name)
    raise_if_not_py_identifier(slot_name, bits[0])

    nodelist = parser.parse(parse_until=["endslot"])
    parser.delete_first_token()

    template_name = parser.origin.template_name
    return SlotNode(slot_name, nodelist, template_name, required)


class FillNode(Node):
    def __init__(
        self,
        name_var: "NameVariable",
        nodelist: NodeList,
        alias_var: Optional["NameVariable"] = None,
    ):
        self.name_var = name_var
        self.nodelist = nodelist
        self.alias_var: Optional[NameVariable] = alias_var

    def __repr__(self):
        return f"<Fill Node: {self.name_var}. Contents: {repr(self.nodelist)}>"

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

        resolved_fills = {
            fill_node.name_var.resolve(context): fill_node
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

    seen_fill_name_vars = set()
    fill_nodes = component_node.fill_nodes
    for token in fill_tokens(parser):
        fill_node = do_fill(parser, token)
        fill_node.parent_component = component_node
        if fill_node.name_var.var in seen_fill_name_vars:
            raise TemplateSyntaxError(
                f"Multiple fill tags cannot target the same slot name: "
                f"Detected duplicate fill tag name '{fill_node.name_var}'."
            )
        seen_fill_name_vars.add(fill_node.name_var.var)
        fill_nodes.append(fill_node)

    return component_node


def fill_tokens(parser):
    """Yield each 'fill' token appearing before the next 'endcomponent_block' token.

    Raises TemplateSyntaxError if:
    - there are other content tokens
    - there is no endcomponent_block token.
    - a (deprecated) 'slot' token is encountered.
    """

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
        elif is_block_tag(token, name="fill"):
            yield token
        elif is_block_tag(token, name="slot"):
            raise TemplateSyntaxError(
                "Use of {% slot %} to pass slot content is deprecated. "
                "Use {% fill % } instead."
            )
        elif (
            not is_whitespace(token) and token.token_type != TokenType.COMMENT
        ):
            raise TemplateSyntaxError(
                "Component block EITHER contains illegal tokens tag that are not "
                "{{% fill ... %}} tags OR the proper closing tag -- "
                "{{% endcomponent_block %}} -- is missing."
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


def norm_and_validate_name(name: str, tag: str, context: str = None):
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


def raise_if_not_py_identifier(name: str, tag: str, content: str = None):
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
