import difflib
import json
import re
from collections import deque
from typing import Any, Dict, List, NamedTuple, Optional, Set, Tuple, Type

from django.template import Context, Template
from django.template.base import FilterExpression, Node, NodeList, Parser, TextNode
from django.template.defaulttags import CommentNode
from django.template.exceptions import TemplateSyntaxError
from django.utils.safestring import SafeString, mark_safe

from django_components.app_settings import ContextBehavior, app_settings
from django_components.context import _FILLED_SLOTS_CONTENT_CONTEXT_KEY, _ROOT_CTX_CONTEXT_KEY
from django_components.logger import trace_msg
from django_components.node import NodeTraverse, nodelist_has_content, walk_nodelist
from django_components.utils import gen_id

DEFAULT_SLOT_KEY = "_DJANGO_COMPONENTS_DEFAULT_SLOT"

# Type aliases

SlotId = str
SlotName = str
AliasName = str


class FillContent(NamedTuple):
    """
    This represents content set with the `{% fill %}` tag, e.g.:

    ```django
    {% component "my_comp" %}
        {% fill "first_slot" %} <--- This
            hi
            {{ my_var }}
            hello
        {% endfill %}
    {% endcomponent %}
    ```
    """

    nodes: NodeList
    alias: Optional[AliasName]


class Slot(NamedTuple):
    """
    This represents content set with the `{% slot %}` tag, e.g.:

    ```django
    {% slot "my_comp" default %} <--- This
        hi
        {{ my_var }}
        hello
    {% endslot %}
    ```
    """

    id: str
    name: str
    is_default: bool
    is_required: bool
    nodelist: NodeList


class SlotFill(NamedTuple):
    """
    SlotFill describes what WILL be rendered.

    It is a Slot that has been resolved against FillContents passed to a Component.
    """

    name: str
    escaped_name: str
    is_filled: bool
    nodelist: NodeList
    context_data: Dict
    alias: Optional[AliasName]


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
        self,
        name: str,
        nodelist: NodeList,
        is_required: bool = False,
        is_default: bool = False,
        node_id: Optional[str] = None,
    ):
        self.name = name
        self.nodelist = nodelist
        self.is_required = is_required
        self.is_default = is_default
        self.node_id = node_id or gen_id()

    @property
    def active_flags(self) -> List[str]:
        flags = []
        if self.is_required:
            flags.append("required")
        if self.is_default:
            flags.append("default")
        return flags

    def __repr__(self) -> str:
        return f"<Slot Node: {self.name}. Contents: {repr(self.nodelist)}. Options: {self.active_flags}>"

    def render(self, context: Context) -> SafeString:
        trace_msg("RENDR", "SLOT", self.name, self.node_id)
        slots: dict[SlotId, "SlotFill"] = context[_FILLED_SLOTS_CONTENT_CONTEXT_KEY]
        # NOTE: Slot entry MUST be present. If it's missing, there was an issue upstream.
        slot_fill = slots[self.node_id]

        # If slot is using alias `{% slot "myslot" as "abc" %}`, then set the "abc" to
        # the context, so users can refer to the slot from within the slot.
        extra_context = {}
        if slot_fill.alias:
            if not slot_fill.alias.isidentifier():
                raise TemplateSyntaxError(f"Invalid fill alias. Must be a valid identifier. Got '{slot_fill.alias}'")
            extra_context[slot_fill.alias] = UserSlotVar(self, context)

        # For the user-provided slot fill, we want to use the context of where the slot
        # came from (or current context if configured so)
        used_ctx = self._resolve_slot_context(context, slot_fill)
        with used_ctx.update(extra_context):
            output = slot_fill.nodelist.render(used_ctx)

        trace_msg("RENDR", "SLOT", self.name, self.node_id, msg="...Done!")
        return output

    def _resolve_slot_context(self, context: Context, slot_fill: "SlotFill") -> Context:
        """Prepare the context used in a slot fill based on the settings."""
        # If slot is NOT filled, we use the slot's default AKA content between
        # the `{% slot %}` tags. These should be evaluated as if the `{% slot %}`
        # tags weren't even there, which means that we use the current context.
        if not slot_fill.is_filled:
            return context

        if app_settings.CONTEXT_BEHAVIOR == ContextBehavior.DJANGO:
            return context
        elif app_settings.CONTEXT_BEHAVIOR == ContextBehavior.ISOLATED:
            return context[_ROOT_CTX_CONTEXT_KEY]
        else:
            raise ValueError(f"Unknown value for CONTEXT_BEHAVIOR: '{app_settings.CONTEXT_BEHAVIOR}'")


class FillNode(Node):
    """
    Set when a `component` tag pair is passed template content that
    excludes `fill` tags. Nodes of this type contribute their nodelists to slots marked
    as 'default'.
    """

    def __init__(
        self,
        nodelist: NodeList,
        name_fexp: FilterExpression,
        alias_fexp: Optional[FilterExpression] = None,
        is_implicit: bool = False,
        node_id: Optional[str] = None,
    ):
        self.node_id = node_id or gen_id()
        self.nodelist = nodelist
        self.name_fexp = name_fexp
        self.alias_fexp = alias_fexp
        self.is_implicit = is_implicit
        self.component_id: Optional[str] = None

    def render(self, context: Context) -> str:
        raise TemplateSyntaxError(
            "{% fill ... %} block cannot be rendered directly. "
            "You are probably seeing this because you have used one outside "
            "a {% component %} context."
        )

    def __repr__(self) -> str:
        return f"<{type(self)} Name: {self.name_fexp}. Contents: {repr(self.nodelist)}.>"

    def resolve_alias(self, context: Context, component_name: Optional[str] = None) -> Optional[str]:
        if not self.alias_fexp:
            return None

        resolved_alias: Optional[str] = self.alias_fexp.resolve(context)
        if resolved_alias and not resolved_alias.isidentifier():
            raise TemplateSyntaxError(
                f"Fill tag alias '{self.alias_fexp.var}' in component "
                f"{component_name} does not resolve to "
                f"a valid Python identifier. Got: '{resolved_alias}'."
            )
        return resolved_alias


def parse_slot_fill_nodes_from_component_nodelist(
    component_nodelist: NodeList,
    ComponentNodeCls: Type[Node],
) -> List[FillNode]:
    """
    Given a component body (`django.template.NodeList`), find all slot fills,
    whether defined explicitly with `{% fill %}` or implicitly.

    So if we have a component body:
    ```django
    {% component "mycomponent" %}
        {% fill "first_fill" %}
            Hello!
        {% endfill %}
        {% fill "second_fill" %}
            Hello too!
        {% endfill %}
    {% endcomponent %}
    ```
    Then this function returns the nodes (`django.template.Node`) for `fill "first_fill"`
    and `fill "second_fill"`.
    """
    fill_nodes: List[FillNode] = []
    if nodelist_has_content(component_nodelist):
        for parse_fn in (
            _try_parse_as_default_fill,
            _try_parse_as_named_fill_tag_set,
        ):
            curr_fill_nodes = parse_fn(component_nodelist, ComponentNodeCls)
            if curr_fill_nodes:
                fill_nodes = curr_fill_nodes
                break
        else:
            raise TemplateSyntaxError(
                "Illegal content passed to 'component' tag pair. "
                "Possible causes: 1) Explicit 'fill' tags cannot occur alongside other "
                "tags except comment tags; 2) Default (default slot-targeting) content "
                "is mixed with explict 'fill' tags."
            )
    return fill_nodes


def _try_parse_as_named_fill_tag_set(
    nodelist: NodeList,
    ComponentNodeCls: Type[Node],
) -> List[FillNode]:
    result = []
    seen_name_fexps: Set[str] = set()
    for node in nodelist:
        if isinstance(node, FillNode):
            # Check that, after we've resolved the names, that there's still no duplicates.
            # This makes sure that if two different variables refer to same string, we detect
            # them.
            if node.name_fexp.token in seen_name_fexps:
                raise TemplateSyntaxError(
                    f"Multiple fill tags cannot target the same slot name: "
                    f"Detected duplicate fill tag name '{node.name_fexp}'."
                )
            seen_name_fexps.add(node.name_fexp.token)
            result.append(node)
        elif isinstance(node, CommentNode):
            pass
        elif isinstance(node, TextNode) and node.s.isspace():
            pass
        else:
            return []
    return result


def _try_parse_as_default_fill(
    nodelist: NodeList,
    ComponentNodeCls: Type[Node],
) -> List[FillNode]:
    nodes_stack: List[Node] = list(nodelist)
    while nodes_stack:
        node = nodes_stack.pop()
        if isinstance(node, FillNode):
            return []
        elif isinstance(node, ComponentNodeCls):
            # Stop searching here, as fill tags are permitted inside component blocks
            # embedded within a default fill node.
            continue
        for nodelist_attr_name in node.child_nodelists:
            nodes_stack.extend(getattr(node, nodelist_attr_name, []))
    else:
        return [
            FillNode(
                nodelist=nodelist,
                name_fexp=FilterExpression(json.dumps(DEFAULT_SLOT_KEY), Parser("")),
                is_implicit=True,
            )
        ]


####################
# SLOT RESOLUTION
####################


def resolve_slots(
    context: Context,
    template: Template,
    component_name: Optional[str],
    context_data: Dict[str, Any],
    fill_content: Dict[SlotName, FillContent],
) -> Tuple[Dict[SlotId, Slot], Dict[SlotId, SlotFill]]:
    """
    Search the template for all SlotNodes, and associate the slots
    with the given fills.

    Returns tuple of:
    - Slots defined in the component's Template with `{% slot %}` tag
    - SlotFills (AKA slots matched with fills) describing what will be rendered for each slot.
    """
    slot_fills = {
        name: SlotFill(
            name=name,
            escaped_name=_escape_slot_name(name),
            is_filled=True,
            nodelist=fill.nodes,
            context_data=context_data,
            alias=fill.alias,
        )
        for name, fill in fill_content.items()
    }

    slots: Dict[SlotId, Slot] = {}
    # This holds info on which slot (key) has which slots nested in it (value list)
    slot_children: Dict[SlotId, List[SlotId]] = {}

    def on_node(entry: NodeTraverse) -> None:
        node = entry.node
        if not isinstance(node, SlotNode):
            return

        # 1. Collect slots
        # Basically we take all the important info form the SlotNode, so the logic is
        # less coupled to Django's Template/Node. Plain tuples should also help with
        # troubleshooting.
        slot = Slot(
            id=node.node_id,
            name=node.name,
            nodelist=node.nodelist,
            is_default=node.is_default,
            is_required=node.is_required,
        )
        slots[node.node_id] = slot

        # 2. Figure out which Slots are nested in other Slots, so we can render
        # them from outside-inwards, so we can skip inner Slots if fills are provided.
        # We should end up with a graph-like data like:
        # - 0001: [0002]
        # - 0002: []
        # - 0003: [0004]
        # In other words, the data tells us that slot ID 0001 is PARENT of slot 0002.
        curr_entry = entry.parent
        while curr_entry and curr_entry.parent is not None:
            if not isinstance(curr_entry.node, SlotNode):
                curr_entry = curr_entry.parent
                continue

            parent_slot_id = curr_entry.node.node_id
            if parent_slot_id not in slot_children:
                slot_children[parent_slot_id] = []
            slot_children[parent_slot_id].append(node.node_id)
            break

    walk_nodelist(template.nodelist, on_node, context)

    # 3. Figure out which slot the default/implicit fill belongs to
    slot_fills = _resolve_default_slot(
        template_name=template.name,
        component_name=component_name,
        slots=slots,
        slot_fills=slot_fills,
    )

    # 4. Detect any errors with slots/fills
    _report_slot_errors(slots, slot_fills, component_name)

    # 5. Find roots of the slot relationships
    top_level_slot_ids: List[SlotId] = []
    for node_id, slot in slots.items():
        if node_id not in slot_children or not slot_children[node_id]:
            top_level_slot_ids.append(node_id)

    # 6. Walk from out-most slots inwards, and decide whether and how
    # we will render each slot.
    resolved_slots: Dict[SlotId, SlotFill] = {}
    slot_ids_queue = deque([*top_level_slot_ids])
    while len(slot_ids_queue):
        slot_id = slot_ids_queue.pop()
        slot = slots[slot_id]

        # Check if there is a slot fill for given slot name
        if slot.name in slot_fills:
            # If yes, we remember which slot we want to replace with already-rendered fills
            resolved_slots[slot_id] = slot_fills[slot.name]
            # Since the fill cannot include other slots, we can leave this path
            continue
        else:
            # If no, then the slot is NOT filled, and we will render the slot's default (what's
            # between the slot tags)
            resolved_slots[slot_id] = SlotFill(
                name=slot.name,
                escaped_name=_escape_slot_name(slot.name),
                is_filled=False,
                nodelist=slot.nodelist,
                context_data=context_data,
                alias=None,
            )
            # Since the slot's default CAN include other slots (because it's defined in
            # the same template), we need to enqueue the slot's children
            if slot_id in slot_children and slot_children[slot_id]:
                slot_ids_queue.extend(slot_children[slot_id])

    # By the time we get here, we should know, for each slot, how it will be rendered
    # -> Whether it will be replaced with a fill, or whether we render slot's defaults.
    return slots, resolved_slots


def _resolve_default_slot(
    template_name: str,
    component_name: Optional[str],
    slots: Dict[SlotId, Slot],
    slot_fills: Dict[SlotName, SlotFill],
) -> Dict[SlotName, SlotFill]:
    """Figure out which slot the default fill refers to, and perform checks."""
    named_fills = slot_fills.copy()

    if DEFAULT_SLOT_KEY in named_fills:
        default_fill = named_fills.pop(DEFAULT_SLOT_KEY)
    else:
        default_fill = None

    default_slot_encountered: bool = False

    # Check for errors
    for slot in slots.values():
        if slot.is_default:
            if default_slot_encountered:
                raise TemplateSyntaxError(
                    "Only one component slot may be marked as 'default'. "
                    f"To fix, check template '{template_name}' "
                    f"of component '{component_name}'."
                )
            default_slot_encountered = True

            # Here we've identified which slot the default/implicit fill belongs to
            if default_fill:
                # NOTE: We recreate new instance, passing all fields, instead of using
                # `NamedTuple._replace`, because `_replace` is not typed.
                named_fills[slot.name] = SlotFill(
                    is_filled=default_fill.is_filled,
                    nodelist=default_fill.nodelist,
                    context_data=default_fill.context_data,
                    alias=default_fill.alias,
                    # Updated fields
                    name=slot.name,
                    escaped_name=_escape_slot_name(slot.name),
                )

    # Check: Only component templates that include a 'default' slot
    # can be invoked with implicit filling.
    if default_fill and not default_slot_encountered:
        raise TemplateSyntaxError(
            f"Component '{component_name}' passed default fill content '{default_fill.name}'"
            f"(i.e. without explicit 'fill' tag), "
            f"even though none of its slots is marked as 'default'."
        )

    return named_fills


def _report_slot_errors(
    slots: Dict[SlotId, Slot],
    slot_fills: Dict[SlotName, SlotFill],
    registered_name: Optional[str],
) -> None:
    slots_by_name = {slot.name: slot for slot in slots.values()}
    unfilled_slots: Set[str] = {slot.name for slot in slots.values() if slot.name not in slot_fills}
    unmatched_fills: Set[str] = {
        slot_fill.name for slot_fill in slot_fills.values() if slot_fill.name not in slots_by_name
    }
    required_slot_names: Set[str] = set([slot.name for slot in slots.values() if slot.is_required])

    # Check that 'required' slots are filled.
    for slot_name in unfilled_slots:
        if slot_name in required_slot_names:
            msg = (
                f"Slot '{slot_name}' is marked as 'required' (i.e. non-optional), "
                f"yet no fill is provided. Check template.'"
            )
            if unmatched_fills:
                msg = f"{msg}\nPossible typo in unresolvable fills: {unmatched_fills}."
            raise TemplateSyntaxError(msg)

    # Check that all fills can be matched to a slot on the component template.
    # To help with easy-to-overlook typos, we fuzzy match unresolvable fills to
    # those slots for which no matching fill was encountered. In the event of
    # a close match, we include the name of the matched unfilled slot as a
    # hint in the error message.
    #
    # Note: Finding a good `cutoff` value may require further trial-and-error.
    # Higher values make matching stricter. This is probably preferable, as it
    # reduces false positives.
    for fill_name in unmatched_fills:
        fuzzy_slot_name_matches = difflib.get_close_matches(fill_name, unfilled_slots, n=1, cutoff=0.7)
        msg = (
            f"Component '{registered_name}' passed fill that refers to undefined slot:"
            f" '{fill_name}'."
            f"\nUnfilled slot names are: {sorted(unfilled_slots)}."
        )
        if fuzzy_slot_name_matches:
            msg += f"\nDid you mean '{fuzzy_slot_name_matches[0]}'?"
        raise TemplateSyntaxError(msg)


name_escape_re = re.compile(r"[^\w]")


def _escape_slot_name(name: str) -> str:
    """
    Users may define slots with names which are invalid identifiers like 'my slot'.
    But these cannot be used as keys in the template context, e.g. `{{ component_vars.is_filled.'my slot' }}`.
    So as workaround, we instead use these escaped names which are valid identifiers.

    So e.g. `my slot` should be escaped as `my_slot`.
    """
    # NOTE: Do a simple substitution where we replace all non-identifier characters with `_`.
    # Identifiers consist of alphanum (a-zA-Z0-9) and underscores.
    # We don't check if these escaped names conflict with other existing slots in the template,
    # we leave this obligation to the user.
    escaped_name = name_escape_re.sub("_", name)
    return escaped_name
