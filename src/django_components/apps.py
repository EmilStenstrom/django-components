import re
from pathlib import Path
from typing import Any

from django.apps import AppConfig
from django.utils.autoreload import file_changed, trigger_reload


class ComponentsConfig(AppConfig):
    name = "django_components"

    # This is the code that gets run when user adds django_components
    # to Django's INSTALLED_APPS
    def ready(self) -> None:
        from django_components.app_settings import app_settings
        from django_components.autodiscovery import autodiscover, import_libraries
        from django_components.component_registry import registry
        from django_components.components.dynamic import DynamicComponent

        # Import modules set in `COMPONENTS.libraries` setting
        import_libraries()

        if app_settings.AUTODISCOVER:
            autodiscover()

        # Auto-reload Django dev server when any component files changes
        # See https://github.com/EmilStenstrom/django-components/discussions/567#discussioncomment-10273632
        if app_settings.RELOAD_ON_FILE_CHANGE:
            _watch_component_files_for_autoreload()

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


# See https://github.com/EmilStenstrom/django-components/issues/586#issue-2472678136
def _watch_component_files_for_autoreload() -> None:
    from django_components.util.loader import get_component_dirs

    component_dirs = set(get_component_dirs())

    def template_changed(sender: Any, file_path: Path, **kwargs: Any) -> None:
        # Reload dev server if any of the files within `COMPONENTS.dirs` or `COMPONENTS.app_dirs` changed
        for dir_path in file_path.parents:
            if dir_path in component_dirs:
                trigger_reload(file_path)
                return

    file_changed.connect(template_changed)
