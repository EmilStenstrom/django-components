import re
from dataclasses import dataclass
from enum import Enum
from os import PathLike
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Callable,
    Generic,
    List,
    Literal,
    NamedTuple,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
    Union,
    cast,
)

from django.conf import settings

from django_components.util.misc import default

if TYPE_CHECKING:
    from django_components.tag_formatter import TagFormatterABC


T = TypeVar("T")


ContextBehaviorType = Literal["django", "isolated"]


class ContextBehavior(str, Enum):
    DJANGO = "django"
    """
    With this setting, component fills behave as usual Django tags.
    That is, they enrich the context, and pass it along.

    1. Component fills use the context of the component they are within.
    2. Variables from `get_context_data` are available to the component fill.

    Example:

    Given this template
    ```django
    {% with cheese="feta" %}
      {% component 'my_comp' %}
        {{ my_var }}  # my_var
        {{ cheese }}  # cheese
      {% endcomponent %}
    {% endwith %}
    ```

    and this context returned from the `get_context_data()` method
    ```py
    { "my_var": 123 }
    ```

    Then if component "my_comp" defines context
    ```py
    { "my_var": 456 }
    ```

    Then this will render:
    ```django
    456   # my_var
    feta  # cheese
    ```

    Because "my_comp" overrides the variable "my_var",
    so `{{ my_var }}` equals `456`.

    And variable "cheese" will equal `feta`, because the fill CAN access
    the current context.
    """

    ISOLATED = "isolated"
    """
    This setting makes the component fills behave similar to Vue or React, where
    the fills use EXCLUSIVELY the context variables defined in `get_context_data`.

    Example:

    Given this template
    ```django
    {% with cheese="feta" %}
      {% component 'my_comp' %}
        {{ my_var }}  # my_var
        {{ cheese }}  # cheese
      {% endcomponent %}
    {% endwith %}
    ```

    and this context returned from the `get_context_data()` method
    ```py
    { "my_var": 123 }
    ```

    Then if component "my_comp" defines context
    ```py
    { "my_var": 456 }
    ```

    Then this will render:
    ```django
    123   # my_var
          # cheese
    ```

    Because both variables "my_var" and "cheese" are taken from the root context.
    Since "cheese" is not defined in root context, it's empty.
    """


# This is the source of truth for the settings that are available. If the documentation
# or the defaults do NOT match this, they should be updated.
class ComponentsSettings(NamedTuple):
    autodiscover: Optional[bool] = None
    dirs: Optional[Sequence[Union[str, PathLike, Tuple[str, str], Tuple[str, PathLike]]]] = None
    app_dirs: Optional[Sequence[str]] = None
    context_behavior: Optional[ContextBehaviorType] = None
    dynamic_component_name: Optional[str] = None
    libraries: Optional[List[str]] = None
    multiline_tags: Optional[bool] = None
    # TODO_REMOVE_IN_V1
    reload_on_template_change: Optional[bool] = None
    """Deprecated. Use `reload_on_file_change` instead."""

    reload_on_file_change: Optional[bool] = None
    static_files_allowed: Optional[List[Union[str, re.Pattern]]] = None
    # TODO_REMOVE_IN_V1
    forbidden_static_files: Optional[List[Union[str, re.Pattern]]] = None
    """Deprecated. Use `static_files_forbidden` instead."""

    static_files_forbidden: Optional[List[Union[str, re.Pattern]]] = None
    tag_formatter: Optional[Union["TagFormatterABC", str]] = None
    template_cache_size: Optional[int] = None


# NOTE: Some defaults depend on the Django settings, which may not yet be
# initialized at the time that these settings are generated. For such cases
# we define the defaults as a factory function, and use the `Dynamic` class to
# mark such fields.
@dataclass(frozen=True)
class Dynamic(Generic[T]):
    getter: Callable[[], T]


# This is the source of truth for the settings defaults. If the documentation
# does NOT match it, the documentation should be updated.
#
# NOTE: Because we need to access Django settings to generate default dirs
#       for `COMPONENTS.dirs`, we do it lazily.
# NOTE 2: We show the defaults in the documentation, together with the comments
#        (except for the `Dynamic` instances and comments like `type: ignore`).
#        So `fmt: off` turns off Black formatting and `snippet:defaults` allows
#        us to extract the snippet from the file.
#
# fmt: off
# --snippet:defaults--
defaults = ComponentsSettings(
    autodiscover=True,
    context_behavior=ContextBehavior.DJANGO.value,  # "django" | "isolated"
    # Root-level "components" dirs, e.g. `/path/to/proj/components/`
    dirs=Dynamic(lambda: [Path(settings.BASE_DIR) / "components"]),  # type: ignore[arg-type]
    # App-level "components" dirs, e.g. `[app]/components/`
    app_dirs=["components"],
    dynamic_component_name="dynamic",
    libraries=[],  # E.g. ["mysite.components.forms", ...]
    multiline_tags=True,
    reload_on_file_change=False,
    static_files_allowed=[
        ".css",
        ".js", ".jsx", ".ts", ".tsx",
        # Images
        ".apng", ".png", ".avif", ".gif", ".jpg",
        ".jpeg", ".jfif", ".pjpeg", ".pjp", ".svg",
        ".webp", ".bmp", ".ico", ".cur", ".tif", ".tiff",
        # Fonts
        ".eot", ".ttf", ".woff", ".otf", ".svg",
    ],
    static_files_forbidden=[
        # See https://marketplace.visualstudio.com/items?itemName=junstyle.vscode-django-support
        ".html", ".django", ".dj", ".tpl",
        # Python files
        ".py", ".pyc",
    ],
    tag_formatter="django_components.component_formatter",
    template_cache_size=128,
)
# --endsnippet:defaults--
# fmt: on


class InternalSettings:
    @property
    def _settings(self) -> ComponentsSettings:
        data = getattr(settings, "COMPONENTS", {})
        return ComponentsSettings(**data) if not isinstance(data, ComponentsSettings) else data

    @property
    def AUTODISCOVER(self) -> bool:
        return default(self._settings.autodiscover, cast(bool, defaults.autodiscover))

    @property
    def DIRS(self) -> Sequence[Union[str, PathLike, Tuple[str, str], Tuple[str, PathLike]]]:
        # For DIRS we use a getter, because default values uses Django settings,
        # which may not yet be initialized at the time these settings are generated.
        default_fn = cast(Dynamic[Sequence[Union[str, Tuple[str, str]]]], defaults.dirs)
        default_dirs = default_fn.getter()
        return default(self._settings.dirs, default_dirs)

    @property
    def APP_DIRS(self) -> Sequence[str]:
        return default(self._settings.app_dirs, cast(List[str], defaults.app_dirs))

    @property
    def DYNAMIC_COMPONENT_NAME(self) -> str:
        return default(self._settings.dynamic_component_name, cast(str, defaults.dynamic_component_name))

    @property
    def LIBRARIES(self) -> List[str]:
        return default(self._settings.libraries, cast(List[str], defaults.libraries))

    @property
    def MULTILINE_TAGS(self) -> bool:
        return default(self._settings.multiline_tags, cast(bool, defaults.multiline_tags))

    @property
    def RELOAD_ON_FILE_CHANGE(self) -> bool:
        val = self._settings.reload_on_file_change
        # TODO_REMOVE_IN_V1
        if val is None:
            val = self._settings.reload_on_template_change

        return default(val, cast(bool, defaults.reload_on_file_change))

    @property
    def TEMPLATE_CACHE_SIZE(self) -> int:
        return default(self._settings.template_cache_size, cast(int, defaults.template_cache_size))

    @property
    def STATIC_FILES_ALLOWED(self) -> Sequence[Union[str, re.Pattern]]:
        return default(self._settings.static_files_allowed, cast(List[str], defaults.static_files_allowed))

    @property
    def STATIC_FILES_FORBIDDEN(self) -> Sequence[Union[str, re.Pattern]]:
        val = self._settings.static_files_forbidden
        # TODO_REMOVE_IN_V1
        if val is None:
            val = self._settings.forbidden_static_files

        return default(val, cast(List[str], defaults.static_files_forbidden))

    @property
    def CONTEXT_BEHAVIOR(self) -> ContextBehavior:
        raw_value = cast(str, default(self._settings.context_behavior, defaults.context_behavior))
        return self._validate_context_behavior(raw_value)

    def _validate_context_behavior(self, raw_value: Union[ContextBehavior, str]) -> ContextBehavior:
        try:
            return ContextBehavior(raw_value)
        except ValueError:
            valid_values = [behavior.value for behavior in ContextBehavior]
            raise ValueError(f"Invalid context behavior: {raw_value}. Valid options are {valid_values}")

    @property
    def TAG_FORMATTER(self) -> Union["TagFormatterABC", str]:
        tag_formatter = default(self._settings.tag_formatter, cast(str, defaults.tag_formatter))
        return cast(Union["TagFormatterABC", str], tag_formatter)


app_settings = InternalSettings()
