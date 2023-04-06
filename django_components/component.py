import copy
from typing import (
    TYPE_CHECKING,
    ClassVar,
    Dict,
    Iterator,
    List,
    Optional,
    TypeVar,
)

from django.core.exceptions import ImproperlyConfigured
from django.forms.widgets import MediaDefiningClass
from django.template import Context, TemplateSyntaxError
from django.template.base import Node, NodeList, Template
from django.template.loader import get_template
from django.utils.safestring import mark_safe

# Allow "component.AlreadyRegistered" instead of having to import these everywhere
from django_components.component_registry import (  # noqa
    AlreadyRegistered,
    ComponentRegistry,
    NotRegistered,
)

if TYPE_CHECKING:
    from django_components.templatetags.component_tags import (
        FillNode,
        SlotNode,
    )


T = TypeVar("T")


FILLED_SLOTS_CONTEXT_KEY = "_DJANGO_COMPONENTS_FILLED_SLOTS"


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


class Component(metaclass=SimplifiedInterfaceMediaDefiningClass):
    # Must be set on subclass OR subclass must implement get_template_name() with
    # non-null return.
    template_name: ClassVar[str]

    def __init__(self, component_name):
        self._component_name: str = component_name
        self._instance_fills: Optional[List["FillNode"]] = None
        self._outer_context: Optional[dict] = None

    def get_context_data(self, *args, **kwargs):
        return {}

    # Can be overridden for dynamic templates
    def get_template_name(self, context):
        if not hasattr(self, "template_name") or not self.template_name:
            raise ImproperlyConfigured(
                f"Template name is not set for Component {self.__class__.__name__}"
            )

        return self.template_name

    def render_dependencies(self):
        """Helper function to access media.render()"""
        return self.media.render()

    def render_css_dependencies(self):
        """Render only CSS dependencies available in the media class."""
        return mark_safe("\n".join(self.media.render_css()))

    def render_js_dependencies(self):
        """Render only JS dependencies available in the media class."""
        return mark_safe("\n".join(self.media.render_js()))

    def get_declared_slots(
        self, context: Context, template: Optional[Template] = None
    ) -> List["SlotNode"]:
        if template is None:
            template = self.get_template(context)
        return list(
            dfs_iter_slots_in_nodelist(template.nodelist, template.name)
        )

    def get_template(self, context, template_name: Optional[str] = None):
        if template_name is None:
            template_name = self.get_template_name(context)
        template = get_template(template_name).template
        return template

    def set_instance_fills(self, fills: Dict[str, "FillNode"]) -> None:
        self._instance_fills = fills

    def set_outer_context(self, context):
        self._outer_context = context

    @property
    def instance_fills(self):
        return self._instance_fills or {}

    @property
    def outer_context(self):
        return self._outer_context or {}

    def get_updated_fill_stacks(self, context):
        current_fill_stacks = context.get(FILLED_SLOTS_CONTEXT_KEY, None)
        updated_fill_stacks = (
            copy.deepcopy(current_fill_stacks)
            if current_fill_stacks is not None
            else {}
        )
        for name, fill in self.instance_fills.items():
            if name in updated_fill_stacks:
                updated_fill_stacks[name].append(fill)
            else:
                updated_fill_stacks[name] = [fill]
        return updated_fill_stacks

    def validate_fills_and_slots_(
        self,
        context,
        template: Template,
        fills: Optional[Dict[str, "FillNode"]] = None,
    ) -> None:
        if fills is None:
            fills = self.instance_fills
        all_slots: List["SlotNode"] = self.get_declared_slots(
            context, template
        )
        slots: Dict[str, "SlotNode"] = {}
        # Each declared slot must have a unique name.
        for slot in all_slots:
            slot_name = slot.name
            if slot_name in slots:
                raise TemplateSyntaxError(
                    f"Encountered non-unique slot '{slot_name}' in template "
                    f"'{template.name}' of component '{self._component_name}'."
                )
            slots[slot_name] = slot
        # All fill nodes must correspond to a declared slot.
        unmatchable_fills = fills.keys() - slots.keys()
        if unmatchable_fills:
            msg = (
                f"Component '{self._component_name}' passed fill(s) "
                f"refering to undefined slot(s). Bad fills: {list(unmatchable_fills)}."
            )
            raise TemplateSyntaxError(msg)
        # Note: Requirement that 'required' slots be filled is enforced
        #  in SlotNode.render().

    def render(self, context):
        template_name = self.get_template_name(context)
        template = self.get_template(context, template_name)
        self.validate_fills_and_slots_(context, template)
        updated_fill_stacks = self.get_updated_fill_stacks(context)
        with context.update({FILLED_SLOTS_CONTEXT_KEY: updated_fill_stacks}):
            return template.render(context)

    class Media:
        css = {}
        js = []


def dfs_iter_slots_in_nodelist(
    nodelist: NodeList, template_name: str = None
) -> Iterator["SlotNode"]:
    from django_components.templatetags.component_tags import SlotNode

    nodes: List[Node] = list(nodelist)
    while nodes:
        node = nodes.pop()
        if isinstance(node, SlotNode):
            yield node
        for nodelist_name in node.child_nodelists:
            nodes.extend(reversed(getattr(node, nodelist_name, [])))


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
