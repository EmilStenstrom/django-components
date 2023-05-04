from collections import ChainMap
from typing import (
    TYPE_CHECKING,
    ClassVar,
    Dict,
    Iterator,
    List,
    Optional,
    TypeVar,
    Type,
    Iterable,
    Tuple,
    Union,
)

from django.core.exceptions import ImproperlyConfigured
from django.forms.widgets import MediaDefiningClass
from django.template import Context, TemplateSyntaxError
from django.template.base import Node, NodeList, Template
from django.template.loader import get_template
from django.utils.safestring import mark_safe

from django_components.component_registry import (  # noqa
    AlreadyRegistered,
    ComponentRegistry,
    NotRegistered,
)

if TYPE_CHECKING:
    from django_components.templatetags.component_tags import SlotNode, IfSlotFilledNode


T = TypeVar("T")


FILLED_SLOTS_CONTEXT_KEY = "_DJANGO_COMPONENTS_FILLED_SLOTS"
NODE_COMPONENT_MAP_CONTEXT_KEY = "_DJANGO_COMPONENTS_NODE_2_COMPONENT"


class SimplifiedInterfaceMediaDefiningClass(MediaDefiningClass):
    def __new__(mcs, name, bases, attrs):
        if "Media" in attrs:
            media = attrs["Media"]

            # Allow: class Media: css = "style.css"
            if hasattr(media, "css") and isinstance(media.css, str):
                media.css = [media.css]

            # Allow: class Media: css = ["style.css"]
            if hasattr(media, "css") and isinstance(media.css, list):
                media.css = {"all": media.css}

            # Allow: class Media: css = {"all": "style.css"}
            if hasattr(media, "css") and isinstance(media.css, dict):
                for media_type, path_list in media.css.items():
                    if isinstance(path_list, str):
                        media.css[media_type] = [path_list]

            # Allow: class Media: js = "script.js"
            if hasattr(media, "js") and isinstance(media.js, str):
                media.js = [media.js]

        return super().__new__(mcs, name, bases, attrs)


# {name: (content, alias?))
FillName = FillAlias = str
NamedFillDict = Dict[FillName, Tuple[NodeList, Optional[FillAlias]]]


class Component(metaclass=SimplifiedInterfaceMediaDefiningClass):
    # Must be set on subclass OR subclass must implement get_template_name() with
    # non-null return.
    template_name: ClassVar[str]

    default_fill_content: Optional[NodeList] = None
    named_fill_content: Optional[NamedFillDict] = None

    class Media:
        css = {}
        js = []

    def __init__(
        self,
        registered_name: Optional[str] = None,
        outer_context: Optional[Context] = None,
        fill_content: Optional[Union[NodeList, NamedFillDict]] = None,
    ):
        self.registered_name: Optional[str] = registered_name
        self.outer_context: Context = outer_context or Context()

        if isinstance(fill_content, NodeList):
            self.default_fill_content = fill_content
        elif isinstance(fill_content, dict):
            self.named_fill_content = fill_content

    def get_context_data(self, *args, **kwargs):
        return {}

    # Can be overridden for dynamic templates
    def get_template_name(self, context) -> str:
        try:
            name = self.template_name
        except AttributeError:
            raise ImproperlyConfigured(
                f"Template name is not set for Component {type(self).__name__}. "
                f"Note: this attribute is not required if you are overriding any of "
                f"the class's `get_template*()` methods."
            )
        return name

    def get_template_string(self, context) -> str:
        """Override to use template string directly."""
        pass

    def render_dependencies(self):
        """Helper function to access media.render()"""
        return self.media.render()

    def render_css_dependencies(self):
        """Render only CSS dependencies available in the media class."""
        return mark_safe("\n".join(self.media.render_css()))

    def render_js_dependencies(self):
        """Render only JS dependencies available in the media class."""
        return mark_safe("\n".join(self.media.render_js()))

    def get_template(self, context) -> Template:
        template_string = self.get_template_string(context)
        if template_string is not None:
            return Template(template_string)
        else:
            template_name = self.get_template_name(context)
            template: Template = get_template(template_name).template
            return template

    def render(self, context):
        from django_components.templatetags.component_tags import (
            SlotNode,
            IfSlotFilledNode,
        )

        template = self.get_template(context)

        nodes_to_link = list(
            template.nodelist.get_nodes_by_type((SlotNode, IfSlotFilledNode))
        )

        _raise_if_bad_slots_or_fills(
            self,
            (node for node in nodes_to_link if isinstance(node, SlotNode)),
            template,
        )

        updated_node_component_map = _update_node_component_map(
            self, nodes_to_link, context
        )

        with context.update(
            {NODE_COMPONENT_MAP_CONTEXT_KEY: updated_node_component_map}
        ):
            return template.render(context)


def _update_node_component_map(
    component: Component, nodes: Iterable[Node], context: Context
) -> ChainMap:
    current_node_component_map: Optional[ChainMap] = context.get(
        NODE_COMPONENT_MAP_CONTEXT_KEY
    )
    node2comp = {node: component for node in nodes}
    if current_node_component_map is None:
        updated = ChainMap(node2comp)
    else:
        updated = current_node_component_map.new_child(node2comp)
    return updated


def _raise_if_bad_slots_or_fills(
    component: Component, slots: Iterable["SlotNode"], template: Template
) -> None:
    # Implementation note: One of the constraints that isn't checked in this function
    # is the requirement that slots marked as 'requires' are always filled.
    # This is skipped because checking is complicated by the possibility of
    # conditional slots. The constraint is enforced by SlotNode.render() instead.

    # Slot constraints:
    # - Slot names are unique.
    # - At most 1 slot is marked as 'default'.
    checked_slots: Dict[str, "SlotNode"] = {}
    default_slot_encountered = False
    for slot in slots:
        slot_name = slot.name
        if slot_name in checked_slots:
            raise TemplateSyntaxError(
                f"Slot name '{slot_name}' re-used within the same template. "
                f"Slot names must be unique."
                f"To fix, check template '{template.name}' "
                f"of component '{component.registered_name}'."
            )
        if slot.is_default:
            if default_slot_encountered:
                raise TemplateSyntaxError(
                    "Only one component slot may be marked as 'default'. "
                    f"To fix, check template '{template.name}' "
                    f"of component '{component.registered_name}'."
                )
            else:
                default_slot_encountered = True
        checked_slots[slot_name] = slot

    # Fill constraints:
    # - Fill names correspond to a slot declared in `template`
    # - Implicit fill node (with name = `None`) allowed iff defaul slot in `template`.
    # NOT checked:
    # - Fill names are unique. This happens in `component_tags.fill_nodes()`.
    if component.default_fill_content and not default_slot_encountered:
        raise TemplateSyntaxError(
            f"Component '{component.registered_name}' passed implicit fill content "
            f"(i.e. without explicit 'fill' tag), "
            f"even though none of its slots is marked as 'default'."
        )
    if component.named_fill_content:
        unmatchable_fills = component.named_fill_content.keys() - checked_slots.keys()
        if unmatchable_fills:
            raise TemplateSyntaxError(
                f"Component '{component.registered_name}' passed fill(s) "
                f"refering to undefined slot(s). Bad fills: {list(filter(None, unmatchable_fills))}."
            )


# This variable represents the global component registry
registry = ComponentRegistry()


def register(name):
    """Class decorator to register a component.

    Usage:

    @register("my_component")
    class MyComponent(component.Component):
        ...
    """

    def decorator(component):
        registry.register(name=name, component=component)
        return component

    return decorator
