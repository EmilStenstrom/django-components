"""Main package for Django Components."""

import django

from django_components.autodiscover import autodiscover as autodiscover  # NOQA
from django_components.autodiscover import import_libraries as import_libraries  # NOQA

if django.VERSION < (3, 2):
    default_app_config = "django_components.apps.ComponentsConfig"
