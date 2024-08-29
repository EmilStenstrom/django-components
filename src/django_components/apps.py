import re

from django.apps import AppConfig


class ComponentsConfig(AppConfig):
    name = "django_components"

    # This is the code that gets run when user adds django_components
    # to Django's INSTALLED_APPS
    def ready(self) -> None:
        from django_components.app_settings import app_settings
        from django_components.autodiscover import autodiscover, get_dirs, import_libraries, search_dirs
        from django_components.component_registry import registry
        from django_components.components.dynamic import DynamicComponent
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

        # Allow tags to span multiple lines. This makes it easier to work with
        # components inside Django templates, allowing us syntax like:
        # ```html
        #   {% component "icon"
        #     icon='outline_chevron_down'
        #     size=16
        #     color="text-gray-400"
        #     attrs:class="ml-2"
        #   %}{% endcomponent %}
        # ```
        #
        # See https://stackoverflow.com/a/54206609/9788634
        if app_settings.MULTILINE_TAGS:
            from django.template import base

            base.tag_re = re.compile(base.tag_re.pattern, re.DOTALL)

        # Register the dynamic component under the name as given in settings
        registry.register(app_settings.DYNAMIC_COMPONENT_NAME, DynamicComponent)
