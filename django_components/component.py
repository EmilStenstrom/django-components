from __future__ import annotations

import warnings
from collections import defaultdict
from contextlib import contextmanager
from functools import lru_cache
from typing import (
    TYPE_CHECKING,
    ClassVar,
    Dict,
    List,
    Optional,
    Tuple,
    TypeVar,
)

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.forms.widgets import MediaDefiningClass
from django.template import TemplateSyntaxError
from django.template.base import Node, NodeList, Template
from django.template.loader import get_template
from django.utils.safestring import mark_safe

from django_components.app_settings import app_settings

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
        self._instance_fills: Optional[List[FillNode]] = None
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

    @classmethod
    @lru_cache(maxsize=app_settings.TEMPLATE_CACHE_SIZE)
    def fetch_and_analyze_template(
        cls, template_name: str
    ) -> Tuple[Template, Dict[str, SlotNode]]:
        template: Template = get_template(template_name).template
        slots = {}
        for slot in iter_slots_in_nodelist(template.nodelist, template.name):
            slot.component_cls = cls
            slots[slot.name] = slot
        return template, slots

    def get_processed_template(self, context):
        template_name = self.get_template_name(context)
        # Note: return of method below is cached.
        template, slots = self.fetch_and_analyze_template(template_name)
        self._raise_if_fills_do_not_match_slots(
            slots, self.instance_fills, self._component_name
        )
        self._raise_if_declared_slots_are_unfilled(
            slots, self.instance_fills, self._component_name
        )
        return template

    @staticmethod
    def _raise_if_declared_slots_are_unfilled(
        slots: Dict[str, SlotNode], fills: Dict[str, FillNode], comp_name: str
    ):
        # 'unconditional_slots' are slots that were encountered within an 'if_filled'
        # context. They are exempt from filling checks.
        unconditional_slots = {
            slot.name for slot in slots.values() if not slot.is_conditional
        }
        unused_slots = unconditional_slots - fills.keys()
        if unused_slots:
            msg = (
                f"Component '{comp_name}' declares slots that "
                f"are not filled: '{unused_slots}'"
            )
            if app_settings.STRICT_SLOTS:
                raise TemplateSyntaxError(msg)
            elif settings.DEBUG:
                warnings.warn(msg)

    @staticmethod
    def _raise_if_fills_do_not_match_slots(
        slots: Dict[str, SlotNode], fills: Dict[str, FillNode], comp_name: str
    ):
        unmatchable_fills = fills.keys() - slots.keys()
        if unmatchable_fills:
            msg = (
                f"Component '{comp_name}' passed fill(s) "
                f"refering to undefined slot(s). Bad fills: {list(unmatchable_fills)}."
            )
            raise TemplateSyntaxError(msg)

    @property
    def instance_fills(self):
        return self._instance_fills or {}

    @property
    def outer_context(self):
        return self._outer_context or {}

    @contextmanager
    def assign(
        self: T,
        fills: Optional[Dict[str, FillNode]] = None,
        outer_context: Optional[dict] = None,
    ) -> T:
        if fills is not None:
            self._instance_fills = fills
        if outer_context is not None:
            self._outer_context = outer_context
        yield self
        self._instance_fills = None
        self._outer_context = None

    def render(self, context):
        template = self.get_processed_template(context)
        current_fills_stack = context.get(
            FILLED_SLOTS_CONTEXT_KEY, defaultdict(list)
        )
        for name, fill in self.instance_fills.items():
            current_fills_stack[name].append(fill)
        with context.update({FILLED_SLOTS_CONTEXT_KEY: current_fills_stack}):
            return template.render(context)

    class Media:
        css = {}
        js = []


def iter_slots_in_nodelist(nodelist: NodeList, template_name: str = None):
    from django_components.templatetags.component_tags import SlotNode

    nodes: List[Node] = list(nodelist)
    slot_names = set()
    while nodes:
        node = nodes.pop()
        if isinstance(node, SlotNode):
            slot_name = node.name
            if slot_name in slot_names:
                context = (
                    f" in template '{template_name}'" if template_name else ""
                )
                raise TemplateSyntaxError(
                    f"Encountered non-unique slot '{slot_name}'{context}"
                )
            slot_names.add(slot_name)
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
