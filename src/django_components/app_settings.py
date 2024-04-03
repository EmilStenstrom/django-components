from enum import Enum
from typing import List

from django.conf import settings


class ContextBehavior(str, Enum):
    GLOBAL = "global"
    ISOLATED = "isolated"


class AppSettings:
    def __init__(self) -> None:
        self.settings = getattr(settings, "COMPONENTS", {})

    @property
    def AUTODISCOVER(self) -> bool:
        return self.settings.setdefault("autodiscover", True)

    @property
    def LIBRARIES(self) -> List:
        return self.settings.setdefault("libraries", [])

    @property
    def TEMPLATE_CACHE_SIZE(self) -> int:
        return self.settings.setdefault("template_cache_size", 128)

    @property
    def CONTEXT_BEHAVIOR(self) -> ContextBehavior:
        raw_value = self.settings.setdefault("context_behavior", ContextBehavior.GLOBAL.value)
        return self._validate_context_behavior(raw_value)

    def _validate_context_behavior(self, raw_value: ContextBehavior) -> ContextBehavior:
        try:
            return ContextBehavior(raw_value)
        except ValueError:
            valid_values = [behavior.value for behavior in ContextBehavior]
            raise ValueError(f"Invalid context behavior: {raw_value}. Valid options are {valid_values}")


app_settings = AppSettings()
