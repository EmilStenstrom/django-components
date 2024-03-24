from django.apps import AppConfig


class ComponentsConfig(AppConfig):
    name = "django_components"

    def ready(self):
        self.module.autodiscover()
