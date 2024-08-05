# flake8: noqa F401
import django

# Public API
# isort: off
from django_components.autodiscover import (
    autodiscover as autodiscover,
    import_libraries as import_libraries,
)
from django_components.component import Component as Component
from django_components.component_registry import (
    AlreadyRegistered as AlreadyRegistered,
    ComponentRegistry as ComponentRegistry,
    NotRegistered as NotRegistered,
    register as register,
    registry as registry,
)
from django_components.tag_formatter import (
    ComponentTagFormatter as ComponentTagFormatter,
    ShorthandTagFormatter as ShorthandTagFormatter,
    TagFormatterABC as TagFormatterABC,
)
import django_components.types as types

# isort: on

if django.VERSION < (3, 2):
    default_app_config = "django_components.apps.ComponentsConfig"
