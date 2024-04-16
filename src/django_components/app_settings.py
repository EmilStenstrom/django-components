from enum import Enum
from typing import Dict, List

from django.conf import settings


class ContextBehavior(str, Enum):
    GLOBAL = "global"
    ISOLATED = "isolated"


class SlotContextBehavior(str, Enum):
    ALLOW_OVERRIDE = "allow_override"
    """
    Components CAN override the slot context variables passed from the outer scopes.
    Contexts of deeper components take precedence over shallower ones.

    Example:

    Given this template

    ```txt
    {% component 'my_comp' %}
      {{ my_var }}
    {% endcomponent %}
    ```

    and this context passed to the render function (AKA root context)
    ```py
    { "my_var": 123 }
    ```

    Then if component "my_comp" defines context
    ```py
    { "my_var": 456 }
    ```

    Then since "my_comp" overrides the varialbe "my_var", so `{{ my_var }}` will equal `456`.
    """

    PREFER_ROOT = "prefer_root"
    """
    This is the same as "allow_override", except any variables defined in the root context
    take precedence over anything else.

    So if a variable is found in the root context, then root context is used.
    Otherwise, the context of the component where the slot fill is located is used.

    Example:

    Given this template

    ```txt
    {% component 'my_comp' %}
      {{ my_var_one }}
      {{ my_var_two }}
    {% endcomponent %}
    ```

    and this context passed to the render function (AKA root context)
    ```py
    { "my_var_one": 123 }
    ```

    Then if component "my_comp" defines context
    ```py
    { "my_var": 456, "my_var_two": "abc" }
    ```

    Then the rendered `{{ my_var_one }}` will equal to `123`, and `{{ my_var_two }}`
    will equal to "abc".
    """

    ISOLATED = "isolated"
    """
    This setting makes the slots behave similar to Vue or React, where
    the slot uses EXCLUSIVELY the root context, and nested components CANNOT
    override context variables inside the slots.

    Example:

    Given this template

    ```txt
    {% component 'my_comp' %}
      {{ my_var }}
    {% endcomponent %}
    ```

    and this context passed to the render function (AKA root context)
    ```py
    { "my_var": 123 }
    ```

    Then if component "my_comp" defines context
    ```py
    { "my_var": 456 }
    ```

    Then the rendered `{{ my_var }}` will equal `123`.
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
        raw_value = self.settings.get("context_behavior", ContextBehavior.GLOBAL.value)
        return self._validate_context_behavior(raw_value)

    def _validate_context_behavior(self, raw_value: ContextBehavior) -> ContextBehavior:
        try:
            return ContextBehavior(raw_value)
        except ValueError:
            valid_values = [behavior.value for behavior in ContextBehavior]
            raise ValueError(f"Invalid context behavior: {raw_value}. Valid options are {valid_values}")

    @property
    def SLOT_CONTEXT_BEHAVIOR(self) -> SlotContextBehavior:
        raw_value = self.settings.get("slot_context_behavior", SlotContextBehavior.PREFER_ROOT.value)
        return self._validate_slot_context_behavior(raw_value)

    def _validate_slot_context_behavior(self, raw_value: SlotContextBehavior) -> SlotContextBehavior:
        try:
            return SlotContextBehavior(raw_value)
        except ValueError:
            valid_values = [behavior.value for behavior in SlotContextBehavior]
            raise ValueError(f"Invalid slot context behavior: {raw_value}. Valid options are {valid_values}")


app_settings = AppSettings()
