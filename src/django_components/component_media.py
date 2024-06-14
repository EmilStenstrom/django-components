import os
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, MutableMapping, Optional, Tuple, Type, Union, TYPE_CHECKING

from django.forms.widgets import Media, MediaDefiningClass
from django.utils.safestring import SafeData

# Global registry var and register() function moved to separate module.
# Defining them here made little sense, since 1) component_tags.py and component.py
# rely on them equally, and 2) it made it difficult to avoid circularity in the
# way the two modules depend on one another.
from django_components.component_registry import AlreadyRegistered as AlreadyRegistered  # NOQA
from django_components.component_registry import ComponentRegistry as ComponentRegistry  # NOQA
from django_components.component_registry import NotRegistered as NotRegistered  # NOQA
from django_components.component_registry import register as register  # NOQA
from django_components.logger import logger
from django_components.utils import search

if TYPE_CHECKING:
    from django_components.component import Component


class ComponentMediaInput:
    """Defines JS and CSS media files associated with this component."""

    css: Optional[Union[str, List[str], Dict[str, str], Dict[str, List[str]]]] = None
    js: Optional[Union[str, List[str]]] = None


# TODO - ALLOW CALLABLE!
# TODO - DOCUMENT IT ALL!
# TODO - Document how when we pass a safe string to css/js, then
#        Media.render_js/css DOES NOT format it (same as Django's
#        see https://docs.djangoproject.com/en/5.0/topics/forms/media/#paths-as-objects)
class MediaMeta(MediaDefiningClass):
    """
    # TODO
    Metaclass for classes that can have media definitions.
    """

    def __new__(mcs, name: str, bases: Tuple[Type, ...], attrs: Dict[str, Any]) -> Type:
        if "Media" in attrs:
            media_data: ComponentMediaInput = attrs["Media"]
            # Normalize the various forms of Media inputs we allow
            _normalize_media(media_data)
            # Given a predictable structure of Media class, get all the various JS/CSS paths
            # that user has defined, and normalize them too.
            #
            # Because we can accept:
            # str, bytes, PathLike, SafeData (AKA Django's "path as object") or a callable
            #
            # And we want to convert that to:
            # str and SafeData
            _map_media_filepaths(media_data, _normalize_media_filepath)

        # Once the inputs are normalized, attempt to resolve the JS/CSS filepaths
        # as relative to the directory where the component class is defined.
        _resolve_component_relative_files(attrs)

        # Since we're inheriting from `MediaDefiningClass`, it should take the inputs
        # from `cls.Media`, and set the `cls.media` to an instance of Django's `Media` class
        cls = super().__new__(mcs, name, bases, attrs)

        # Lastly, if the class defines `media_class` attribute, transform `cls.media`
        # to the instance of `media_class`.
        _monkeypatch_media_property(cls)

        return cls


# Allow users to provide custom subclasses of Media via `media_class`.
# `MediaDefiningClass` defines `media` as a getter (defined in django.forms.widgets.media_property).
# So we reused that and convert it to user-defined Media class
def _monkeypatch_media_property(comp_cls: type["Component"]) -> None:
    if not hasattr(comp_cls, "media_class"):
        return

    media_prop: property = comp_cls.media
    media_getter = media_prop.fget

    def media_wrapper(self: "Component") -> Any:
        if not media_getter:
            return None
        media: Media = media_getter(self)
        return self.media_class(js=media._js, css=media._css)

    comp_cls.media = property(media_wrapper)


def _normalize_media(media: ComponentMediaInput) -> None:
    if hasattr(media, "css") and media.css:
        # Allow: class Media: css = "style.css"
        if _is_media_filepath(media.css):
            media.css = [media.css]  # type: ignore[list-item]

        # Allow: class Media: css = ["style.css"]
        if isinstance(media.css, list):
            media.css = {"all": media.css}

        # Allow: class Media: css = {"all": "style.css"}
        if isinstance(media.css, dict):
            for media_type, path_list in media.css.items():
                if _is_media_filepath(path_list):
                    media.css[media_type] = [path_list]  # type: ignore

    if hasattr(media, "js") and media.js:
        # Allow: class Media: js = "script.js"
        if _is_media_filepath(media.js):
            media.js = [media.js]  # type: ignore[list-item]


def _map_media_filepaths(media: ComponentMediaInput, map_fn: Callable[[Any], Any]) -> None:
    if hasattr(media, "css") and media.css:
        if not isinstance(media.css, dict):
            raise ValueError("#TODO1")  # TODO

        for media_type, path_list in media.css.items():
            media.css[media_type] = list(map(map_fn, path_list))  # type: ignore[assignment]

    if hasattr(media, "js") and media.js:
        if not isinstance(media.js, list):
            raise ValueError("#TODO2")  # TODO

        media.js = list(map(map_fn, media.js))


def _is_media_filepath(filepath: Any) -> bool:
    if callable(filepath):
        return True

    if isinstance(filepath, SafeData) or hasattr(filepath, "__html__"):
        return True

    elif isinstance(filepath, (Path, os.PathLike)) or hasattr(filepath, "__fspath__"):
        return True

    if isinstance(filepath, bytes):
        return True

    if isinstance(filepath, str):
        return True

    return False


def _normalize_media_filepath(filepath: Any) -> str | SafeData:
    if callable(filepath):
        filepath = filepath()

    if isinstance(filepath, SafeData) or hasattr(filepath, "__html__"):
        return filepath

    if isinstance(filepath, (Path, os.PathLike)) or hasattr(filepath, "__fspath__"):
        filepath = filepath.__fspath__()

    if isinstance(filepath, bytes):
        filepath = filepath.decode("utf-8")

    if isinstance(filepath, str):
        return filepath

    raise ValueError("Unknown filepath. Must be str, bytes, PathLike or a function that returns one of the former") # TODO UPDATE


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
    components_dirs = search().searched_dirs

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
    def resolve_file(filepath: str | SafeData) -> str | SafeData:
        if isinstance(filepath, str):
            maybe_resolved_filepath = os.path.join(comp_dir_abs, filepath)
            component_import_filepath = os.path.join(comp_dir_rel, filepath)

            if os.path.isfile(maybe_resolved_filepath):
                logger.debug(
                    f"Interpreting template '{filepath}' of component '{module_name}' relatively to component file"
                )

                return component_import_filepath
            return filepath

        logger.debug(
            f"Interpreting template '{filepath}' of component '{module_name}' relatively to components directory"
        )
        return filepath

    # Check if template name is a local file or not
    if "template_name" in attrs and attrs["template_name"]:
        attrs["template_name"] = resolve_file(attrs["template_name"])

    if "Media" in attrs:
        media: ComponentMediaInput = attrs["Media"]
        _map_media_filepaths(media, resolve_file)


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
