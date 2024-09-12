import re
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Tuple, Union

from django.conf import settings

if TYPE_CHECKING:
    from django_components.tag_formatter import TagFormatterABC


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


class AppSettings:
    @property
    def settings(self) -> Dict:
        return getattr(settings, "COMPONENTS", {})

    @property
    def AUTODISCOVER(self) -> bool:
        return self.settings.get("autodiscover", True)

    @property
    def DIRS(self) -> List[Union[str, Tuple[str, str]]]:
        base_dir_path = Path(settings.BASE_DIR)
        return self.settings.get("dirs", [base_dir_path / "components"])

    @property
    def APP_DIRS(self) -> List[str]:
        return self.settings.get("app_dirs", ["components"])

    @property
    def DYNAMIC_COMPONENT_NAME(self) -> str:
        return self.settings.get("dynamic_component_name", "dynamic")

    @property
    def LIBRARIES(self) -> List[str]:
        return self.settings.get("libraries", [])

    @property
    def MULTILINE_TAGS(self) -> bool:
        return self.settings.get("multiline_tags", True)

    @property
    def RELOAD_ON_TEMPLATE_CHANGE(self) -> bool:
        return self.settings.get("reload_on_template_change", False)

    @property
    def TEMPLATE_CACHE_SIZE(self) -> int:
        return self.settings.get("template_cache_size", 128)

    @property
    def STATIC_FILES_ALLOWED(self) -> List[Union[str, re.Pattern]]:
        default_static_files = [
            ".css",
            ".js",
            # Images - See https://developer.mozilla.org/en-US/docs/Web/Media/Formats/Image_types#common_image_file_types  # noqa: E501
            ".apng",
            ".png",
            ".avif",
            ".gif",
            ".jpg",
            ".jpeg",
            ".jfif",
            ".pjpeg",
            ".pjp",
            ".svg",
            ".webp",
            ".bmp",
            ".ico",
            ".cur",
            ".tif",
            ".tiff",
            # Fonts - See https://stackoverflow.com/q/30572159/9788634
            ".eot",
            ".ttf",
            ".woff",
            ".otf",
            ".svg",
        ]
        return self.settings.get("static_files_allowed", default_static_files)

    @property
    def STATIC_FILES_FORBIDDEN(self) -> List[Union[str, re.Pattern]]:
        default_forbidden_static_files = [
            ".html",
            # See https://marketplace.visualstudio.com/items?itemName=junstyle.vscode-django-support
            ".django",
            ".dj",
            ".tpl",
            # Python files
            ".py",
            ".pyc",
        ]
        return self.settings.get("forbidden_static_files", default_forbidden_static_files)

    @property
    def CONTEXT_BEHAVIOR(self) -> ContextBehavior:
        raw_value = self.settings.get("context_behavior", ContextBehavior.DJANGO.value)
        return self._validate_context_behavior(raw_value)

    def _validate_context_behavior(self, raw_value: ContextBehavior) -> ContextBehavior:
        try:
            return ContextBehavior(raw_value)
        except ValueError:
            valid_values = [behavior.value for behavior in ContextBehavior]
            raise ValueError(f"Invalid context behavior: {raw_value}. Valid options are {valid_values}")

    @property
    def TAG_FORMATTER(self) -> Union["TagFormatterABC", str]:
        return self.settings.get("tag_formatter", "django_components.component_formatter")


app_settings = AppSettings()
