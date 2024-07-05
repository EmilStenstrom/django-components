from django.apps import AppConfig


class ComponentsConfig(AppConfig):
    name = "django_components"

    # This is the code that gets run when user adds django_components
    # to Django's INSTALLED_APPS
    def ready(self) -> None:
        from django_components.app_settings import app_settings
        from django_components.autodiscover import autodiscover, import_libraries

        # Import modules set in `COMPONENTS.libraries` setting
        import_libraries()

        if app_settings.AUTODISCOVER:
            autodiscover()
