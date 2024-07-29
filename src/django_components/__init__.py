# flake8: noqa F401
import django

# Public API
from django_components.autodiscover import autodiscover as autodiscover  # NOQA
from django_components.autodiscover import import_libraries as import_libraries  # NOQA
from django_components.component import Component as Component  # NOQA
from django_components.component_registry import AlreadyRegistered as AlreadyRegistered  # NOQA
from django_components.component_registry import ComponentRegistry as ComponentRegistry  # NOQA
from django_components.component_registry import NotRegistered as NotRegistered  # NOQA
from django_components.component_registry import register as register  # NOQA
from django_components.component_registry import registry as registry  # NOQA
from django_components.types import css as css  # NOQA
from django_components.types import django_html as django_html  # NOQA
from django_components.types import js as js

if django.VERSION < (3, 2):
    default_app_config = "django_components.apps.ComponentsConfig"
