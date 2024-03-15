import difflib
import inspect
from collections import ChainMap
from typing import Any, ClassVar, Dict, Iterable, List, Optional, Set, Tuple, Union

from django.core.exceptions import ImproperlyConfigured
from django.forms.widgets import Media, MediaDefiningClass
from django.http import HttpResponse
from django.template.base import NodeList, Template, TextNode
from django.template.context import Context
from django.template.exceptions import TemplateSyntaxError
from django.template.loader import get_template
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.views import View

# Global registry var and register() function moved to separate module.
# Defining them here made little sense, since 1) component_tags.py and component.py
# rely on them equally, and 2) it made it difficult to avoid circularity in the
# way the two modules depend on one another.
from django_components.component_registry import (  # NOQA
    AlreadyRegistered,
    ComponentRegistry,
    NotRegistered,
    register,
    registry,
)
from django_components.templatetags.component_tags import (
    FILLED_SLOTS_CONTENT_CONTEXT_KEY,
    DefaultFillContent,
    FillContent,
    FilledSlotsContext,
    IfSlotFilledConditionBranchNode,
    NamedFillContent,
    SlotName,
    SlotNode,
)


class SimplifiedInterfaceMediaDefiningClass(MediaDefiningClass):
    def __new__(mcs, name, bases, attrs):
        if "Media" in attrs:
            media: Component.Media = attrs["Media"]

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
                        media.css[media_type] = [path_list]  # type: ignore

            # Allow: class Media: js = "script.js"
            if hasattr(media, "js") and isinstance(media.js, str):
                media.js = [media.js]

        return super().__new__(mcs, name, bases, attrs)


class Component(View, metaclass=SimplifiedInterfaceMediaDefiningClass):
    # Either template_name or template must be set on subclass OR subclass must implement get_template() with
    # non-null return.
    template_name: ClassVar[Optional[str]] = None
    template: Optional[str] = None
    js: Optional[str] = None
    css: Optional[str] = None
    media: Media

    class Media:
        css: Optional[Union[str, List[str], Dict[str, str], Dict[str, List[str]]]] = None
        js: Optional[Union[str, List[str]]] = None

    def __init__(
        self,
        registered_name: Optional[str] = None,
        outer_context: Optional[Context] = None,
        fill_content: Union[DefaultFillContent, Iterable[NamedFillContent]] = (),  # type: ignore
    ):
        self.registered_name: Optional[str] = registered_name
        self.outer_context: Context = outer_context or Context()
        self.fill_content = fill_content

    def __init_subclass__(cls, **kwargs):
        cls.class_hash = hash(inspect.getfile(cls) + cls.__name__)

    def get_context_data(self, *args, **kwargs) -> Dict[str, Any]:
        return {}

    def get_template_name(self, context) -> Optional[str]:
        return self.template_name

    def get_template_string(self, context) -> Optional[str]:
        return self.template

    def render_dependencies(self):
        """Helper function to render all dependencies for a component."""
        dependencies = []

        css_deps = self.render_css_dependencies()
        if css_deps:
            dependencies.append(css_deps)

        js_deps = self.render_js_dependencies()
        if js_deps:
            dependencies.append(js_deps)

        return mark_safe("\n".join(dependencies))

    def render_css_dependencies(self):
        """Render only CSS dependencies available in the media class or provided as a string."""
        if self.css is not None:
            return mark_safe(f"<style>{self.css}</style>")
        return mark_safe("\n".join(self.media.render_css()))

    def render_js_dependencies(self):
        """Render only JS dependencies available in the media class or provided as a string."""
        if self.js is not None:
            return mark_safe(f"<script>{self.js}</script>")
        return mark_safe("\n".join(self.media.render_js()))

    def get_template(self, context) -> Template:
        template_string = self.get_template_string(context)
        if template_string is not None:
            return Template(template_string)

        template_name = self.get_template_name(context)
        if template_name is not None:
            return get_template(template_name).template

        raise ImproperlyConfigured(
            f"Either 'template_name' or 'template' must be set for Component {type(self).__name__}."
            f"Note: this attribute is not required if you are overriding the class's `get_template*()` methods."
        )

    def render(
        self,
        context_data: Dict[str, Any],
        slots_data: Optional[Dict[SlotName, str]] = None,
        escape_slots_content: bool = True,
    ) -> str:
        context = Context(context_data)
        template = self.get_template(context)

        if slots_data:
            self._fill_slots(slots_data, escape_slots_content)

        updated_filled_slots_context: FilledSlotsContext = self._process_template_and_update_filled_slot_context(
            context, template
        )
        with context.update({FILLED_SLOTS_CONTENT_CONTEXT_KEY: updated_filled_slots_context}):
            return template.render(context)

    def render_to_response(
        self,
        context_data: Dict[str, Any],
        slots_data: Optional[Dict[SlotName, str]] = None,
        escape_slots_content: bool = True,
        *args,
        **kwargs,
    ):
        return HttpResponse(
            self.render(context_data, slots_data, escape_slots_content),
            *args,
            **kwargs,
        )

    def _fill_slots(
        self,
        slots_data: Dict[SlotName, str],
        escape_content: bool = True,
    ):
        """Fill component slots outside of template rendering."""
        self.fill_content = [
            (
                slot_name,
                TextNode(escape(content) if escape_content else content),
                None,
            )
            for (slot_name, content) in slots_data.items()
        ]

    def _process_template_and_update_filled_slot_context(
        self,
        context: Context,
        template: Template,
    ) -> FilledSlotsContext:
        if isinstance(self.fill_content, NodeList):
            default_fill_content = (self.fill_content, None)
            named_fills_content = {}
        else:
            default_fill_content = None
            named_fills_content = {name: (nodelist, alias) for name, nodelist, alias in list(self.fill_content)}

        # If value is `None`, then slot is unfilled.
        slot_name2fill_content: Dict[SlotName, Optional[FillContent]] = {}
        default_slot_encountered: bool = False
        required_slot_names: Set[str] = set()

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
                        f"of component '{self.registered_name}'."
                    )
                content_data: Optional[FillContent] = None  # `None` -> unfilled
                if node.is_required:
                    required_slot_names.add(node.name)
                if node.is_default:
                    if default_slot_encountered:
                        raise TemplateSyntaxError(
                            "Only one component slot may be marked as 'default'. "
                            f"To fix, check template '{template.name}' "
                            f"of component '{self.registered_name}'."
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
                f"Component '{self.registered_name}' passed default fill content '{default_fill_content}'"
                f"(i.e. without explicit 'fill' tag), "
                f"even though none of its slots is marked as 'default'."
            )

        unfilled_slots: Set[str] = set(k for k, v in slot_name2fill_content.items() if v is None)
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
                f"Component '{self.registered_name}' passed fill "
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
        try:
            prev_context: FilledSlotsContext = context[FILLED_SLOTS_CONTENT_CONTEXT_KEY]
            return prev_context.new_child(filled_slots_map)
        except KeyError:
            return ChainMap(filled_slots_map)
