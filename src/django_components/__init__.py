# flake8: noqa F401
import django

# Public API
from django_components.autodiscover import autodiscover as autodiscover
from django_components.autodiscover import import_libraries as import_libraries
from django_components.component import Component as Component
from django_components.component_registry import AlreadyRegistered as AlreadyRegistered
from django_components.component_registry import ComponentRegistry as ComponentRegistry
from django_components.component_registry import NotRegistered as NotRegistered
from django_components.component_registry import register as register
from django_components.component_registry import registry as registry
from django_components.types import css as css
from django_components.types import django_html as django_html
from django_components.types import js as js

if django.VERSION < (3, 2):
    default_app_config = "django_components.apps.ComponentsConfig"
