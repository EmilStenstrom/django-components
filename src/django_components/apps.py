from django.apps import AppConfig


class ComponentsConfig(AppConfig):
    name = "django_components"

    def ready(self) -> None:
        # This is the code that gets run when user adds django_components to Django's INSTALLED_APPS
        #
        # TODO - Allow only if autodiscovery is true?
        #        Because right now it's kinda weird that we import the COMPONENTS.libraries
        #        Even if autodiscovery is off.
        self.module.autodiscover()
