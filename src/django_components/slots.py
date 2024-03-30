import difflib
import sys
from typing import Dict, Iterable, List, Optional, Set, Tuple, Type, Union

if sys.version_info[:2] < (3, 9):
    from typing import ChainMap
else:
    from collections import ChainMap

if sys.version_info[:2] < (3, 10):
    from typing_extensions import TypeAlias
else:
    from typing import TypeAlias

from django.template import Context, Template
from django.template.base import FilterExpression, Node, NodeList, TextNode
from django.template.defaulttags import CommentNode
from django.template.exceptions import TemplateSyntaxError
from django.utils.safestring import SafeString, mark_safe

FILLED_SLOTS_CONTENT_CONTEXT_KEY = "_DJANGO_COMPONENTS_FILLED_SLOTS"

# Type aliases

SlotName = str
AliasName = str

DefaultFillContent: TypeAlias = NodeList
NamedFillContent = Tuple[SlotName, NodeList, Optional[AliasName]]

FillContent = Tuple[NodeList, Optional[AliasName]]
FilledSlotsContext = ChainMap[Tuple[SlotName, Template], FillContent]


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
    def template(self, value: Template) -> None:
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
        try:
            filled_slots_map: FilledSlotsContext = context[FILLED_SLOTS_CONTENT_CONTEXT_KEY]
        except KeyError:
            raise TemplateSyntaxError(f"Attempted to render SlotNode '{self.name}' outside a parent component.")

        extra_context = {}
        try:
            slot_fill_content: FillContent = filled_slots_map[(self.name, self.template)]
        except KeyError:
            if self.is_required:
                raise TemplateSyntaxError(
                    f"Slot '{self.name}' is marked as 'required' (i.e. non-optional), " f"yet no fill is provided. "
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


class BaseFillNode(Node):
    def __init__(self, nodelist: NodeList):
        self.nodelist: NodeList = nodelist

    def __repr__(self) -> str:
        raise NotImplementedError

    def render(self, context: Context) -> str:
        raise TemplateSyntaxError(
            "{% fill ... %} block cannot be rendered directly. "
            "You are probably seeing this because you have used one outside "
            "a {% component %} context."
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


class ImplicitFillNode(BaseFillNode):
    """
    Instantiated when a `component` tag pair is passed template content that
    excludes `fill` tags. Nodes of this type contribute their nodelists to slots marked
    as 'default'.
    """

    def __repr__(self) -> str:
        return f"<{type(self)} Contents: {repr(self.nodelist)}.>"


class _IfSlotFilledBranchNode(Node):
    def __init__(self, nodelist: NodeList) -> None:
        self.nodelist = nodelist

    def render(self, context: Context) -> str:
        return self.nodelist.render(context)

    def evaluate(self, context: Context) -> bool:
        raise NotImplementedError


class IfSlotFilledConditionBranchNode(_IfSlotFilledBranchNode, TemplateAwareNodeMixin):
    def __init__(
        self,
        slot_name: str,
        nodelist: NodeList,
        is_positive: Union[bool, None] = True,
    ) -> None:
        self.slot_name = slot_name
        self.is_positive: Optional[bool] = is_positive
        super().__init__(nodelist)

    def evaluate(self, context: Context) -> bool:
        try:
            filled_slots: FilledSlotsContext = context[FILLED_SLOTS_CONTENT_CONTEXT_KEY]
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
) -> Union[Iterable[NamedFillNode], ImplicitFillNode]:
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
    fill_nodes: Union[Iterable[NamedFillNode], ImplicitFillNode] = []
    if _block_has_content(component_nodelist):
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
) -> Optional[Iterable[NamedFillNode]]:
    result = []
    seen_name_fexps: Set[FilterExpression] = set()
    for node in nodelist:
        if isinstance(node, NamedFillNode):
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
            return None
    return result


def _try_parse_as_default_fill(
    nodelist: NodeList,
    ComponentNodeCls: Type[Node],
) -> Optional[ImplicitFillNode]:
    nodes_stack: List[Node] = list(nodelist)
    while nodes_stack:
        node = nodes_stack.pop()
        if isinstance(node, NamedFillNode):
            return None
        elif isinstance(node, ComponentNodeCls):
            # Stop searching here, as fill tags are permitted inside component blocks
            # embedded within a default fill node.
            continue
        for nodelist_attr_name in node.child_nodelists:
            nodes_stack.extend(getattr(node, nodelist_attr_name, []))
    else:
        return ImplicitFillNode(nodelist=nodelist)


def _block_has_content(nodelist: NodeList) -> bool:
    for node in nodelist:
        if isinstance(node, TextNode) and node.s.isspace():
            pass
        elif isinstance(node, CommentNode):
            pass
        else:
            return True
    return False


def render_component_template_with_slots(
    template: Template,
    context: Context,
    fill_content: Union[DefaultFillContent, Iterable[NamedFillContent]],
    registered_name: Optional[str],
) -> str:
    """
    Given a template, context, and slot fills, this function first prepares
    the template to be able to render the fills in the place of slots, and then
    renders the template with given context.

    NOTE: The template is mutated in the process!
    """
    prev_filled_slots_context: Optional[FilledSlotsContext] = context.get(FILLED_SLOTS_CONTENT_CONTEXT_KEY)
    updated_filled_slots_context = _prepare_component_template_filled_slot_context(
        template,
        fill_content,
        prev_filled_slots_context,
        registered_name,
    )
    with context.update({FILLED_SLOTS_CONTENT_CONTEXT_KEY: updated_filled_slots_context}):
        return template.render(context)


def _prepare_component_template_filled_slot_context(
    template: Template,
    fill_content: Union[DefaultFillContent, Iterable[NamedFillContent]],
    slots_context: Optional[FilledSlotsContext],
    registered_name: Optional[str],
) -> FilledSlotsContext:
    if isinstance(fill_content, NodeList):
        default_fill_content = (fill_content, None)
        named_fills_content = {}
    else:
        default_fill_content = None
        named_fills_content = {name: (nodelist, alias) for name, nodelist, alias in list(fill_content)}

    # If value is `None`, then slot is unfilled.
    slot_name2fill_content: Dict[SlotName, Optional[FillContent]] = {}
    default_slot_encountered: bool = False
    required_slot_names: Set[str] = set()

    # Collect fills and check for errors
    for node in template.nodelist.get_nodes_by_type((SlotNode, IfSlotFilledConditionBranchNode)):  # type: ignore
        if isinstance(node, SlotNode):
            # Give slot node knowledge of its parent template.
            node.template = template
            slot_name = node.name
            if slot_name in slot_name2fill_content:
                raise TemplateSyntaxError(
                    f"Slot name '{slot_name}' re-used within the same template. "
                    f"Slot names must be unique."
                    f"To fix, check template '{template.name}' "
                    f"of component '{registered_name}'."
                )
            content_data: Optional[FillContent] = None  # `None` -> unfilled
            if node.is_required:
                required_slot_names.add(node.name)
            if node.is_default:
                if default_slot_encountered:
                    raise TemplateSyntaxError(
                        "Only one component slot may be marked as 'default'. "
                        f"To fix, check template '{template.name}' "
                        f"of component '{registered_name}'."
                    )
                content_data = default_fill_content
                default_slot_encountered = True
            if not content_data:
                content_data = named_fills_content.get(node.name)
            slot_name2fill_content[slot_name] = content_data
        elif isinstance(node, IfSlotFilledConditionBranchNode):
            node.template = template
        else:
            raise RuntimeError(f"Node of {type(node).__name__} does not require linking.")

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
            f"Component '{registered_name}' passed fill "
            f"that refers to undefined slot: '{fill_name}'."
            f"\nUnfilled slot names are: {sorted(unfilled_slots)}."
        )
        if fuzzy_slot_name_matches:
            msg += f"\nDid you mean '{fuzzy_slot_name_matches[0]}'?"
        raise TemplateSyntaxError(msg)

    # Return updated FILLED_SLOTS_CONTEXT map
    filled_slots_map: Dict[Tuple[SlotName, Template], FillContent] = {
        (slot_name, template): content_data
        for slot_name, content_data in slot_name2fill_content.items()
        if content_data  # Slots whose content is None (i.e. unfilled) are dropped.
    }
    if slots_context is not None:
        return slots_context.new_child(filled_slots_map)
    else:
        return ChainMap(filled_slots_map)
