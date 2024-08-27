from django.apps import AppConfig


class ComponentsConfig(AppConfig):
    name = "django_components"

    # This is the code that gets run when user adds django_components
    # to Django's INSTALLED_APPS
    def ready(self) -> None:
        from django_components.app_settings import app_settings
        from django_components.autodiscover import autodiscover, import_libraries, get_dirs, search_dirs
        from django_components.utils import watch_files_for_autoreload

        # Import modules set in `COMPONENTS.libraries` setting
        import_libraries()

        if app_settings.AUTODISCOVER:
            autodiscover()

        # Watch template files for changes, so Django dev server auto-reloads
		# See https://github.com/EmilStenstrom/django-components/discussions/567#discussioncomment-10273632
        # And https://stackoverflow.com/questions/42907285/66673186#66673186
        if app_settings.RELOAD_ON_TEMPLATE_CHANGE:
            dirs = get_dirs()
            component_filepaths = search_dirs(dirs, "**/*")
            watch_files_for_autoreload(component_filepaths)
