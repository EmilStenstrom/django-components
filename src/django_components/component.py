import inspect
import os
import sys
from pathlib import Path
from typing import Any, ClassVar, Dict, Iterable, List, Mapping, MutableMapping, Optional, Tuple, Type, Union

from django.core.exceptions import ImproperlyConfigured
from django.forms.widgets import Media, MediaDefiningClass
from django.http import HttpResponse
from django.template.base import FilterExpression, Node, NodeList, Template, TextNode
from django.template.context import Context
from django.template.loader import get_template
from django.utils.html import escape
from django.utils.safestring import SafeString, mark_safe
from django.views import View

# Global registry var and register() function moved to separate module.
# Defining them here made little sense, since 1) component_tags.py and component.py
# rely on them equally, and 2) it made it difficult to avoid circularity in the
# way the two modules depend on one another.
from django_components.component_registry import registry  # NOQA
from django_components.component_registry import AlreadyRegistered, ComponentRegistry, NotRegistered, register  # NOQA
from django_components.logger import logger
from django_components.middleware import is_dependency_middleware_active
from django_components.slots import (
    DefaultFillContent,
    ImplicitFillNode,
    NamedFillContent,
    NamedFillNode,
    SlotName,
    render_component_template_with_slots,
)
from django_components.utils import search

RENDERED_COMMENT_TEMPLATE = "<!-- _RENDERED {name} -->"


class SimplifiedInterfaceMediaDefiningClass(MediaDefiningClass):
    def __new__(mcs, name: str, bases: Tuple[Type, ...], attrs: Dict[str, Any]) -> Type:
        # NOTE: Skip template/media file resolution when then Component class ITSELF
        # is being created.
        if "__module__" in attrs and attrs["__module__"] == "django_components.component":
            return super().__new__(mcs, name, bases, attrs)

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

        _resolve_component_relative_files(attrs)

        return super().__new__(mcs, name, bases, attrs)


def _resolve_component_relative_files(attrs: MutableMapping) -> None:
    """
    Check if component's HTML, JS and CSS files refer to files in the same directory
    as the component class. If so, modify the attributes so the class Django's rendering
    will pick up these files correctly.
    """
    component_name = attrs["__qualname__"]
    # Derive the full path of the file where the component was defined
    module_name = attrs["__module__"]
    module_obj = sys.modules[module_name]
    file_path = module_obj.__file__

    if not file_path:
        logger.debug(
            f"Could not resolve the path to the file for component '{component_name}'."
            " Paths for HTML, JS or CSS templates will NOT be resolved relative to the component file."
        )
        return

    # Prepare all possible directories we need to check when searching for
    # component's template and media files
    components_dirs = search()

    # Get the directory where the component class is defined
    try:
        comp_dir_abs, comp_dir_rel = _get_dir_path_from_component_path(file_path, components_dirs)
    except RuntimeError:
        # If no dir was found, we assume that the path is NOT relative to the component dir
        logger.debug(
            f"No component directory found for component '{component_name}' in {file_path}"
            " If this component defines HTML, JS or CSS templates relatively to the component file,"
            " then check that the component's directory is accessible from one of the paths"
            " specified in the Django's 'STATICFILES_DIRS' settings."
        )
        return

    # Check if filepath refers to a file that's in the same directory as the component class.
    # If yes, modify the path to refer to the relative file.
    # If not, don't modify anything.
    def resolve_file(filepath: str) -> str:
        maybe_resolved_filepath = os.path.join(comp_dir_abs, filepath)
        component_import_filepath = os.path.join(comp_dir_rel, filepath)

        if os.path.isfile(maybe_resolved_filepath):
            logger.debug(
                f"Interpreting template '{filepath}' of component '{module_name}' relatively to component file"
            )
            return component_import_filepath

        logger.debug(
            f"Interpreting template '{filepath}' of component '{module_name}' relatively to components directory"
        )
        return filepath

    # Check if template name is a local file or not
    if "template_name" in attrs and attrs["template_name"]:
        attrs["template_name"] = resolve_file(attrs["template_name"])

    if "Media" in attrs:
        media = attrs["Media"]

        # Now check the same for CSS files
        if hasattr(media, "css") and isinstance(media.css, dict):
            for media_type, path_list in media.css.items():
                media.css[media_type] = [resolve_file(filepath) for filepath in path_list]

        # And JS
        if hasattr(media, "js") and isinstance(media.js, list):
            media.js = [resolve_file(filepath) for filepath in media.js]


def _get_dir_path_from_component_path(
    abs_component_file_path: str,
    candidate_dirs: Union[List[str], List[Path]],
) -> Tuple[str, str]:
    comp_dir_path_abs = os.path.dirname(abs_component_file_path)

    # From all dirs defined in settings.STATICFILES_DIRS, find one that's the parent
    # to the component file.
    root_dir_abs = None
    for candidate_dir in candidate_dirs:
        candidate_dir_abs = os.path.abspath(candidate_dir)
        if comp_dir_path_abs.startswith(candidate_dir_abs):
            root_dir_abs = candidate_dir_abs
            break

    if root_dir_abs is None:
        raise RuntimeError(
            f"Failed to resolve template directory for component file '{abs_component_file_path}'",
        )

    # Derive the path from matched STATICFILES_DIRS to the dir where the current component file is.
    comp_dir_path_rel = os.path.relpath(comp_dir_path_abs, candidate_dir_abs)

    # Return both absolute and relative paths:
    # - Absolute path is used to check if the file exists
    # - Relative path is used for defining the import on the component class
    return comp_dir_path_abs, comp_dir_path_rel


class Component(View, metaclass=SimplifiedInterfaceMediaDefiningClass):
    # Either template_name or template must be set on subclass OR subclass must implement get_template() with
    # non-null return.
    class_hash: ClassVar[int]
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

    def __init_subclass__(cls, **kwargs: Any) -> None:
        cls.class_hash = hash(inspect.getfile(cls) + cls.__name__)

    def get_context_data(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        return {}

    def get_template_name(self, context: Mapping) -> Optional[str]:
        return self.template_name

    def get_template_string(self, context: Mapping) -> Optional[str]:
        return self.template

    def render_dependencies(self) -> SafeString:
        """Helper function to render all dependencies for a component."""
        dependencies = []

        css_deps = self.render_css_dependencies()
        if css_deps:
            dependencies.append(css_deps)

        js_deps = self.render_js_dependencies()
        if js_deps:
            dependencies.append(js_deps)

        return mark_safe("\n".join(dependencies))

    def render_css_dependencies(self) -> SafeString:
        """Render only CSS dependencies available in the media class or provided as a string."""
        if self.css is not None:
            return mark_safe(f"<style>{self.css}</style>")
        return mark_safe("\n".join(self.media.render_css()))

    def render_js_dependencies(self) -> SafeString:
        """Render only JS dependencies available in the media class or provided as a string."""
        if self.js is not None:
            return mark_safe(f"<script>{self.js}</script>")
        return mark_safe("\n".join(self.media.render_js()))

    def get_template(self, context: Mapping) -> Template:
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
        # NOTE: This if/else is important to avoid nested Contexts,
        # See https://github.com/EmilStenstrom/django-components/issues/414
        context = context_data if isinstance(context_data, Context) else Context(context_data)
        template = self.get_template(context)

        if slots_data:
            self._fill_slots(slots_data, escape_slots_content)

        return render_component_template_with_slots(template, context, self.fill_content, self.registered_name)

    def render_to_response(
        self,
        context_data: Dict[str, Any],
        slots_data: Optional[Dict[SlotName, str]] = None,
        escape_slots_content: bool = True,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponse:
        return HttpResponse(
            self.render(context_data, slots_data, escape_slots_content),
            *args,
            **kwargs,
        )

    def _fill_slots(
        self,
        slots_data: Dict[SlotName, str],
        escape_content: bool = True,
    ) -> None:
        """Fill component slots outside of template rendering."""
        self.fill_content = [
            (
                slot_name,
                TextNode(escape(content) if escape_content else content),
                None,
            )
            for (slot_name, content) in slots_data.items()
        ]


class ComponentNode(Node):
    """Django.template.Node subclass that renders a django-components component"""

    def __init__(
        self,
        name_fexp: FilterExpression,
        context_args: List[FilterExpression],
        context_kwargs: Mapping[str, FilterExpression],
        isolated_context: bool = False,
        fill_nodes: Union[ImplicitFillNode, Iterable[NamedFillNode]] = (),
    ) -> None:
        self.name_fexp = name_fexp
        self.context_args = context_args or []
        self.context_kwargs = context_kwargs or {}
        self.isolated_context = isolated_context
        self.fill_nodes = fill_nodes
        self.nodelist = self._create_nodelist(fill_nodes)

    def _create_nodelist(self, fill_nodes: Union[Iterable[Node], ImplicitFillNode]) -> NodeList:
        if isinstance(fill_nodes, ImplicitFillNode):
            return NodeList([fill_nodes])
        else:
            return NodeList(fill_nodes)

    def __repr__(self) -> str:
        return "<ComponentNode: {}. Contents: {!r}>".format(
            self.name_fexp,
            getattr(self, "nodelist", None),  # 'nodelist' attribute only assigned later.
        )

    def render(self, context: Context) -> str:
        resolved_component_name = self.name_fexp.resolve(context)
        component_cls: Type[Component] = registry.get(resolved_component_name)

        # Resolve FilterExpressions and Variables that were passed as args to the
        # component, then call component's context method
        # to get values to insert into the context
        resolved_context_args = [safe_resolve(arg, context) for arg in self.context_args]
        resolved_context_kwargs = {key: safe_resolve(kwarg, context) for key, kwarg in self.context_kwargs.items()}

        if isinstance(self.fill_nodes, ImplicitFillNode):
            fill_content = self.fill_nodes.nodelist
        else:
            fill_content = []
            for fill_node in self.fill_nodes:
                # Note that outer component context is used to resolve variables in
                # fill tag.
                resolved_name = fill_node.name_fexp.resolve(context)
                resolved_fill_alias = fill_node.resolve_alias(context, resolved_component_name)
                fill_content.append((resolved_name, fill_node.nodelist, resolved_fill_alias))

        component: Component = component_cls(
            registered_name=resolved_component_name,
            outer_context=context,
            fill_content=fill_content,
        )

        component_context: dict = component.get_context_data(*resolved_context_args, **resolved_context_kwargs)

        if self.isolated_context:
            context = context.new()
        with context.update(component_context):
            rendered_component = component.render(context)

        if is_dependency_middleware_active():
            return RENDERED_COMMENT_TEMPLATE.format(name=resolved_component_name) + rendered_component
        else:
            return rendered_component


def safe_resolve(context_item: FilterExpression, context: Context) -> Any:
    """Resolve FilterExpressions and Variables in context if possible.  Return other items unchanged."""

    return context_item.resolve(context) if hasattr(context_item, "resolve") else context_item
