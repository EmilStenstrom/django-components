import django

from django_components.autodiscover import autodiscover as autodiscover

if django.VERSION < (3, 2):
    default_app_config = "django_components.apps.ComponentsConfig"
