from collections import ChainMap
from typing import (
    Any,
    ClassVar,
    Dict,
    Optional,
    TypeVar,
    Iterable,
    Tuple,
    Union,
)

from django.core.exceptions import ImproperlyConfigured
from django.forms.widgets import MediaDefiningClass, Media
from django.template import Context
from django.template.exceptions import TemplateSyntaxError
from django.template.base import Template
from django.template.loader import get_template
from django.utils.safestring import mark_safe

from django_components.component_registry import (
    register,
    registry,
    ComponentRegistry,
    AlreadyRegistered,
    NotRegistered
)  # NOQA

from django_components.templatetags.component_tags import (
    FILLED_SLOTS_CONTEXT_KEY,
    NamedFillNode,
    IfSlotFilledConditionBranchNode,
    SlotNode,
    DefaultFillNode,
    SlotName,
    BaseFillNode,
    FilledSlotsContext,
)


T = TypeVar("T")


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
    media: Media
    default_fill: Optional[DefaultFillNode] = None
    named_fills: Dict[str, NamedFillNode]

    class Media:
        css = {}
        js = []

    def __init__(
        self,
        registered_name: Optional[str] = None,
        outer_context: Optional[Context] = None,
        fill_nodes: Optional[Union[Tuple[DefaultFillNode], Tuple[NamedFillNode, ...]]] = None,
    ):
        self.registered_name: Optional[str] = registered_name
        self.outer_context: Context = outer_context or Context()
        self._init_fills(fill_nodes or (), self.outer_context)

    def _init_fills(
        self,
        fill_nodes: Iterable[Union[DefaultFillNode, NamedFillNode]],
        context: Context,
    ) -> None:
        named_fills = {}
        for fill_node in fill_nodes:
            if isinstance(fill_node, DefaultFillNode):
                if self.default_fill:
                    raise ValueError(
                        "Component cannot be initialized with multiple DefaultFillNodes"
                    )
                self.default_fill = fill_node
            else:
                if self.default_fill:
                    raise ValueError(
                        (
                            "Component cannot be initialized with both DefaultFillNodes "
                            "and NamedFillNodes."
                        )
                    )
                named_fills[fill_node.get_resolved_name(context)] = fill_node
        self.named_fills = named_fills

    def get_context_data(self, *args, **kwargs) -> Dict[str, Any]:
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
        ...

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
        template = self.get_template(context)
        updated_filled_slots_context: FilledSlotsContext = (
            self._process_template_and_update_filled_slot_context(context, template)
        )
        with context.update({FILLED_SLOTS_CONTEXT_KEY: updated_filled_slots_context}):
            return template.render(context)

    def _process_template_and_update_filled_slot_context(
        self, context: Context, template: Template
    ) -> FilledSlotsContext:
        slot_name2fill: Dict[SlotName:BaseFillNode] = {}
        default_slot_encountered: bool = False
        for node in template.nodelist.get_nodes_by_type(
            (SlotNode, IfSlotFilledConditionBranchNode)  # type: ignore
        ):
            if isinstance(node, SlotNode):
                node.template = template
                slot_name = node.name
                if slot_name in slot_name2fill:
                    raise TemplateSyntaxError(
                        f"Slot name '{slot_name}' re-used within the same template. "
                        f"Slot names must be unique."
                        f"To fix, check template '{template.name}' "
                        f"of component '{self.registered_name}'."
                    )
                fill: Optional[BaseFillNode] = None
                if node.is_default:
                    if default_slot_encountered:
                        raise TemplateSyntaxError(
                            "Only one component slot may be marked as 'default'. "
                            f"To fix, check template '{template.name}' "
                            f"of component '{self.registered_name}'."
                        )
                    default_slot_encountered = True
                    fill = self.default_fill
                if not fill:
                    fill = self.named_fills.get(node.name)
                if not fill and node.is_required:
                    raise TemplateSyntaxError(
                        f"Slot '{slot_name}' is marked as 'required' (i.e. non-optional), "
                        f"yet no fill is provided. Check template.'"
                    )
                slot_name2fill[slot_name] = fill
            elif isinstance(node, IfSlotFilledConditionBranchNode):
                node.template = template
            else:
                raise RuntimeError(
                    f"Node of {type(node).__name__} does not require linking."
                )
        # Check fills
        if self.default_fill and not default_slot_encountered:
            raise TemplateSyntaxError(
                f"Component '{self.registered_name}' passed default fill content "
                f"(i.e. without explicit 'fill' tag), "
                f"even though none of its slots is marked as 'default'."
            )
        for fill_name in self.named_fills.keys():
            if fill_name not in slot_name2fill:
                raise TemplateSyntaxError(
                    f"Component '{self.registered_name}' passed fill "
                    f"that refers to undefined slot: {fill_name}"
                )
        # Return updated FILLED_SLOTS_CONTEXT map
        filled_slots_map: Dict[Tuple[SlotName, Template], BaseFillNode] = {
            (slot_name, template): fill_node
            for slot_name, fill_node in slot_name2fill.items()
        }
        try:
            prev_context: FilledSlotsContext = context[FILLED_SLOTS_CONTEXT_KEY]
            return prev_context.new_child(filled_slots_map)
        except KeyError:
            return ChainMap(filled_slots_map)
