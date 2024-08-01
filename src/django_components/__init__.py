# flake8: noqa F401
import django

# Public API
# isort: off
from django_components.autodiscover import autodiscover as autodiscover
from django_components.autodiscover import import_libraries as import_libraries
from django_components.component import Component as Component
from django_components.component_registry import AlreadyRegistered as AlreadyRegistered
from django_components.component_registry import ComponentRegistry as ComponentRegistry
from django_components.component_registry import NotRegistered as NotRegistered
from django_components.component_registry import register as register
from django_components.component_registry import registry as registry
import django_components.types as types

# isort: on

if django.VERSION < (3, 2):
    default_app_config = "django_components.apps.ComponentsConfig"
