from django.apps import AppConfig


class ComponentsConfig(AppConfig):
    name = "django_components"

    def ready(self) -> None:
        self.module.autodiscover()
