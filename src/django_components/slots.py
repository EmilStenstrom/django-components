import difflib
import json
from copy import copy
from typing import Dict, List, NamedTuple, Optional, Set, Type, Union

from django.template import Context, Template
from django.template.base import FilterExpression, Node, NodeList, Parser, TextNode
from django.template.defaulttags import CommentNode
from django.template.exceptions import TemplateSyntaxError
from django.utils.safestring import SafeString, mark_safe

from django_components.app_settings import SlotContextBehavior, app_settings
from django_components.context import (
    copy_forloop_context,
    get_outer_root_context,
    get_slot_component_association,
    get_slot_fill,
    set_slot_fill,
)
from django_components.logger import trace_msg
from django_components.node import nodelist_has_content
from django_components.utils import gen_id

DEFAULT_SLOT_KEY = "_DJANGO_COMPONENTS_DEFAULT_SLOT"

# Type aliases

SlotName = str
AliasName = str


class FillContent(NamedTuple):
    """Data passed from component to slot to render that slot"""

    nodes: NodeList
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


class ComponentIdMixin:
    """
    Mixin for classes use or pass through component ID.

    We use component IDs to identify which slots should be
    rendered with which fills for which components.
    """

    _component_id: str

    @property
    def component_id(self) -> str:
        try:
            return self._component_id
        except AttributeError:
            raise RuntimeError(
                f"Internal error: Instance of {type(self).__name__} was not "
                "linked to Component before use in render() context. "
                "Make sure that the 'component_id' field is set."
            )

    @component_id.setter
    def component_id(self, value: Template) -> None:
        self._component_id = value


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
        m = []
        if self.is_required:
            m.append("required")
        if self.is_default:
            m.append("default")
        return m

    def __repr__(self) -> str:
        return f"<Slot Node: {self.name}. Contents: {repr(self.nodelist)}. Options: {self.active_flags}>"

    def render(self, context: Context) -> SafeString:
        component_id = get_slot_component_association(context, self.node_id)
        trace_msg("RENDR", "SLOT", self.name, self.node_id, component_id=component_id)

        slot_fill_content = get_slot_fill(context, component_id, self.name)
        extra_context = {}

        # Slot fill was NOT found. Will render the default fill
        if slot_fill_content is None:
            if self.is_required:
                raise TemplateSyntaxError(
                    f"Slot '{self.name}' is marked as 'required' (i.e. non-optional), " f"yet no fill is provided. "
                )
            nodelist = self.nodelist

        # Slot fill WAS found
        else:
            nodelist, alias = slot_fill_content
            if alias:
                if not alias.isidentifier():
                    raise TemplateSyntaxError()
                extra_context[alias] = UserSlotVar(self, context)

        used_ctx = self.resolve_slot_context(context)
        with used_ctx.update(extra_context):
            output = nodelist.render(used_ctx)

        trace_msg("RENDR", "SLOT", self.name, self.node_id, component_id=component_id, msg="...Done!")
        return output

    def resolve_slot_context(self, context: Context) -> Context:
        """
        Prepare the context used in a slot fill based on the settings.

        See SlotContextBehavior for the description of each option.
        """
        root_ctx = get_outer_root_context(context) or Context()

        if app_settings.SLOT_CONTEXT_BEHAVIOR == SlotContextBehavior.ALLOW_OVERRIDE:
            return context
        elif app_settings.SLOT_CONTEXT_BEHAVIOR == SlotContextBehavior.ISOLATED:
            new_context: Context = copy(root_ctx)
            copy_forloop_context(context, new_context)
            return new_context
        elif app_settings.SLOT_CONTEXT_BEHAVIOR == SlotContextBehavior.PREFER_ROOT:
            new_context = copy(context)
            new_context.update(root_ctx.flatten())
            return new_context
        else:
            raise ValueError(f"Unknown value for SLOT_CONTEXT_BEHAVIOR: '{app_settings.SLOT_CONTEXT_BEHAVIOR}'")


class FillNode(Node, ComponentIdMixin):
    is_implicit: bool
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


class _IfSlotFilledBranchNode(Node):
    def __init__(self, nodelist: NodeList) -> None:
        self.nodelist = nodelist

    def render(self, context: Context) -> str:
        return self.nodelist.render(context)

    def evaluate(self, context: Context) -> bool:
        raise NotImplementedError


class IfSlotFilledConditionBranchNode(_IfSlotFilledBranchNode, ComponentIdMixin):
    def __init__(
        self,
        slot_name: str,
        nodelist: NodeList,
        is_positive: Union[bool, None] = True,
        node_id: Optional[str] = None,
    ) -> None:
        self.slot_name = slot_name
        self.is_positive: Optional[bool] = is_positive
        self.node_id = node_id or gen_id()
        super().__init__(nodelist)

    def evaluate(self, context: Context) -> bool:
        slot_fill = get_slot_fill(context, self.component_id, self.slot_name)
        is_filled = slot_fill is not None
        # Make polarity switchable.
        # i.e. if slot name is NOT filled and is_positive=False,
        # then False == False -> True
        return is_filled == self.is_positive


class IfSlotFilledElseBranchNode(_IfSlotFilledBranchNode):
    def evaluate(self, context: Context) -> bool:
        return True


class IfSlotFilledNode(Node):
    def __init__(
        self,
        branches: List[_IfSlotFilledBranchNode],
    ):
        self.branches = branches
        self.nodelist = self._create_nodelist(branches)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"

    def _create_nodelist(self, branches: List[_IfSlotFilledBranchNode]) -> NodeList:
        return NodeList(branches)

    def render(self, context: Context) -> str:
        for node in self.branches:
            if isinstance(node, IfSlotFilledElseBranchNode):
                return node.render(context)
            elif isinstance(node, IfSlotFilledConditionBranchNode):
                if node.evaluate(context):
                    return node.render(context)
        return ""


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
    seen_name_fexps: Set[FilterExpression] = set()
    for node in nodelist:
        if isinstance(node, FillNode):
            if node.name_fexp in seen_name_fexps:
                raise TemplateSyntaxError(
                    f"Multiple fill tags cannot target the same slot name: "
                    f"Detected duplicate fill tag name '{node.name_fexp}'."
                )
            seen_name_fexps.add(node.name_fexp)
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


def render_component_template_with_slots(
    component_id: str,
    template: Template,
    context: Context,
    fill_content: Dict[str, FillContent],
    registered_name: Optional[str],
) -> str:
    """
    This function first prepares the template to be able to render the fills
    in the place of slots, and then renders the template with given context.

    NOTE: The nodes in the template are mutated in the process!
    """
    # ---- Prepare slot fills ----
    slot_name2fill_content = _collect_slot_fills_from_component_template(template, fill_content, registered_name)

    # Give slot nodes knowledge of their parent component.
    for node in template.nodelist.get_nodes_by_type(IfSlotFilledConditionBranchNode):
        if isinstance(node, IfSlotFilledConditionBranchNode):
            trace_msg("ASSOC", "IFSB", node.slot_name, node.node_id, component_id=component_id)
            node.component_id = component_id

    with context.update({}):
        for slot_name, content_data in slot_name2fill_content.items():
            # Slots whose content is None (i.e. unfilled) are dropped.
            if not content_data:
                continue
            set_slot_fill(context, component_id, slot_name, content_data)

        # ---- Render ----
        return template.render(context)


def _collect_slot_fills_from_component_template(
    template: Template,
    fill_content: Dict[str, FillContent],
    registered_name: Optional[str],
) -> Dict[SlotName, Optional[FillContent]]:
    if DEFAULT_SLOT_KEY in fill_content:
        named_fills_content = fill_content.copy()
        default_fill_content = named_fills_content.pop(DEFAULT_SLOT_KEY)
    else:
        named_fills_content = fill_content
        default_fill_content = None

    # If value is `None`, then slot is unfilled.
    slot_name2fill_content: Dict[SlotName, Optional[FillContent]] = {}
    default_slot_encountered: bool = False
    required_slot_names: Set[str] = set()

    # Collect fills and check for errors
    for node in template.nodelist.get_nodes_by_type(SlotNode):
        # Type check so the rest of the logic has type of `node` is inferred
        if not isinstance(node, SlotNode):
            continue

        slot_name = node.name
        if slot_name in slot_name2fill_content:
            raise TemplateSyntaxError(
                f"Slot name '{slot_name}' re-used within the same template. "
                f"Slot names must be unique."
                f"To fix, check template '{template.name}' "
                f"of component '{registered_name}'."
            )
        if node.is_required:
            required_slot_names.add(node.name)

        content_data: Optional[FillContent] = None  # `None` -> unfilled
        if node.is_default:
            if default_slot_encountered:
                raise TemplateSyntaxError(
                    "Only one component slot may be marked as 'default'. "
                    f"To fix, check template '{template.name}' "
                    f"of component '{registered_name}'."
                )
            content_data = default_fill_content
            default_slot_encountered = True

        # If default fill was not found, try to fill it with named slot
        # Effectively, this allows to fill in default slot as named ones.
        if not content_data:
            content_data = named_fills_content.get(node.name)

        slot_name2fill_content[slot_name] = content_data

    # Check: Only component templates that include a 'default' slot
    # can be invoked with implicit filling.
    if default_fill_content and not default_slot_encountered:
        raise TemplateSyntaxError(
            f"Component '{registered_name}' passed default fill content '{default_fill_content}'"
            f"(i.e. without explicit 'fill' tag), "
            f"even though none of its slots is marked as 'default'."
        )

    unfilled_slots: Set[str] = {k for k, v in slot_name2fill_content.items() if v is None}
    unmatched_fills: Set[str] = named_fills_content.keys() - slot_name2fill_content.keys()

    _report_slot_errors(unfilled_slots, unmatched_fills, registered_name, required_slot_names)

    return slot_name2fill_content


def _report_slot_errors(
    unfilled_slots: Set[str],
    unmatched_fills: Set[str],
    registered_name: Optional[str],
    required_slot_names: Set[str],
) -> None:
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
