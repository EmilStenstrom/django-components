# flake8: noqa F401
"""Main package for Django Components."""

import django

# Public API
# isort: off
from django_components.app_settings import ContextBehavior as ContextBehavior
from django_components.autodiscover import (
    autodiscover as autodiscover,
    import_libraries as import_libraries,
)
from django_components.component import (
    Component as Component,
    ComponentView as ComponentView,
)
from django_components.component_registry import (
    AlreadyRegistered as AlreadyRegistered,
    ComponentRegistry as ComponentRegistry,
    NotRegistered as NotRegistered,
    RegistrySettings as RegistrySettings,
    register as register,
    registry as registry,
)
from django_components.components import DynamicComponent as DynamicComponent
from django_components.library import TagProtectedError as TagProtectedError
from django_components.slots import (
    SlotContent as SlotContent,
    SlotFunc as SlotFunc,
)
from django_components.tag_formatter import (
    ComponentFormatter as ComponentFormatter,
    ShorthandComponentFormatter as ShorthandComponentFormatter,
    TagFormatterABC as TagFormatterABC,
    TagResult as TagResult,
    component_formatter as component_formatter,
    component_shorthand_formatter as component_shorthand_formatter,
)
from django_components.template import cached_template as cached_template
import django_components.types as types
from django_components.types import (
    EmptyTuple as EmptyTuple,
    EmptyDict as EmptyDict,
)

# isort: on

if django.VERSION < (3, 2):
    default_app_config = "django_components.apps.ComponentsConfig"
