from importlib import import_module

import django
from django.utils.module_loading import autodiscover_modules

if django.VERSION < (3, 2):
    default_app_config = "django_components.apps.ComponentsConfig"


def autodiscover():
    # look for "components" module/pkg in each app
    from . import app_settings

    if app_settings.AUTODISCOVER:
        autodiscover_modules("components")
    for path in app_settings.LIBRARIES:
        import_module(path)
