from enum import Enum
from typing import Dict, List

from django.conf import settings


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
    def LIBRARIES(self) -> List:
        return self.settings.get("libraries", [])

    @property
    def TEMPLATE_CACHE_SIZE(self) -> int:
        return self.settings.get("template_cache_size", 128)

    @property
    def CONTEXT_BEHAVIOR(self) -> ContextBehavior:
        raw_value = self.settings.get("context_behavior", ContextBehavior.ISOLATED.value)
        return self._validate_context_behavior(raw_value)

    def _validate_context_behavior(self, raw_value: ContextBehavior) -> ContextBehavior:
        try:
            return ContextBehavior(raw_value)
        except ValueError:
            valid_values = [behavior.value for behavior in ContextBehavior]
            raise ValueError(f"Invalid context behavior: {raw_value}. Valid options are {valid_values}")


app_settings = AppSettings()
