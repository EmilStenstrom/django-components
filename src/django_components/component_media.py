import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, List, MutableMapping, Optional, Tuple, Type, Union

from django.forms.widgets import Media, MediaDefiningClass
from django.utils.safestring import SafeData

from django_components.logger import logger
from django_components.utils import search

if TYPE_CHECKING:
    from django_components.component import Component


class ComponentMediaInput:
    """Defines JS and CSS media files associated with this component."""

    css: Optional[Union[str, List[str], Dict[str, str], Dict[str, List[str]]]] = None
    js: Optional[Union[str, List[str]]] = None


class MediaMeta(MediaDefiningClass):
    """
    Metaclass for handling media files for components.

    Similar to `MediaDefiningClass`, this class supports the use of `Media` attribute
    to define associated JS/CSS files, which are then available under `media`
    attribute as a instance of `Media` class.

    This subclass has following changes:

    ### 1. Support for multiple interfaces of JS/CSS

    1. As plain strings
        ```py
        class MyComponent(component.Component):
            class Media:
                js = "path/to/script.js"
                css = "path/to/style.css"
        ```

    2. As lists
        ```py
        class MyComponent(component.Component):
            class Media:
                js = ["path/to/script1.js", "path/to/script2.js"]
                css = ["path/to/style1.css", "path/to/style2.css"]
        ```

    3. [CSS ONLY] Dicts of strings
        ```py
        class MyComponent(component.Component):
            class Media:
                css = {
                    "all": "path/to/style1.css",
                    "print": "path/to/style2.css",
                }
        ```

    4. [CSS ONLY] Dicts of lists
        ```py
        class MyComponent(component.Component):
            class Media:
                css = {
                    "all": ["path/to/style1.css"],
                    "print": ["path/to/style2.css"],
                }
        ```

    ### 2. Media are first resolved relative to class definition file

    E.g. if in a directory `my_comp` you have `script.js` and `my_comp.py`,
    and `my_comp.py` looks like this:

    ```py
    class MyComponent(component.Component):
        class Media:
            js = "script.js"
    ```

    Then `script.js` will be resolved as `my_comp/script.js`.

    ### 3. Media can be defined as str, bytes, PathLike, SafeString, or function of thereof

    E.g.:

    ```py
    def lazy_eval_css():
        # do something
        return path

    class MyComponent(component.Component):
        class Media:
            js = b"script.js"
            css = lazy_eval_css
    ```

    ### 4. Subclass `Media` class with `media_class`

    Normal `MediaDefiningClass` creates an instance of `Media` class under the `media` attribute.
    This class allows to override which class will be instantiated with `media_class` attribute:

    ```py
    class MyMedia(Media):
        def render_js(self):
            ...

    class MyComponent(component.Component):
        media_class = MyMedia
        def get_context_data(self):
            assert isinstance(self.media, MyMedia)
    ```
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
def _monkeypatch_media_property(comp_cls: Type["Component"]) -> None:
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
        if isinstance(media.css, (list, tuple)):
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
            raise ValueError(f"Media.css must be a dict, got {type(media.css)}")

        for media_type, path_list in media.css.items():
            media.css[media_type] = list(map(map_fn, path_list))  # type: ignore[assignment]

    if hasattr(media, "js") and media.js:
        if not isinstance(media.js, (list, tuple)):
            raise ValueError(f"Media.css must be a list, got {type(media.css)}")

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


def _normalize_media_filepath(filepath: Any) -> Union[str, SafeData]:
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

    raise ValueError(
        "Unknown filepath. Must be str, bytes, PathLike, SafeString, or a function that returns one of the former"
    )


def _resolve_component_relative_files(attrs: MutableMapping) -> None:
    """
    Check if component's HTML, JS and CSS files refer to files in the same directory
    as the component class. If so, modify the attributes so the class Django's rendering
    will pick up these files correctly.
    """
    # First check if we even need to resolve anything. If the class doesn't define any
    # JS/CSS files, just skip.
    will_resolve_files = False
    if attrs.get("template_name", None):
        will_resolve_files = True
    if not will_resolve_files and "Media" in attrs:
        media: ComponentMediaInput = attrs["Media"]
        if getattr(media, "css", None) or getattr(media, "js", None):
            will_resolve_files = True

    if not will_resolve_files:
        return

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
    def resolve_file(filepath: Union[str, SafeData]) -> Union[str, SafeData]:
        if isinstance(filepath, str):
            maybe_resolved_filepath = os.path.join(comp_dir_abs, filepath)
            component_import_filepath = os.path.join(comp_dir_rel, filepath)

            if os.path.isfile(maybe_resolved_filepath):
                # NOTE: It's important to use `repr`, so we don't trigger __str__ on SafeStrings
                logger.debug(
                    f"Interpreting template '{repr(filepath)}' of component '{module_name}'"
                    " relatively to component file"
                )

                return component_import_filepath
            return filepath

        logger.debug(
            f"Interpreting template '{repr(filepath)}' of component '{module_name}'"
            " relatively to components directory"
        )
        return filepath

    # Check if template name is a local file or not
    if "template_name" in attrs and attrs["template_name"]:
        attrs["template_name"] = resolve_file(attrs["template_name"])

    if "Media" in attrs:
        media = attrs["Media"]
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
