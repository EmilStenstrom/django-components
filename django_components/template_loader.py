"""
Template loader that loads templates from each Django app's "components" directory.
"""

from pathlib import Path

from django.conf import settings
from django.template.loaders.filesystem import Loader as FilesystemLoader
from django.template.utils import get_app_template_dirs


class Loader(FilesystemLoader):
    def get_dirs(self):
        component_dir = "components"
        directories = set(get_app_template_dirs(component_dir))

        if hasattr(settings, "BASE_DIR"):
            path = (settings.BASE_DIR / component_dir).resolve()
            if path.is_dir():
                directories.add(path)

        if settings.SETTINGS_MODULE:
            module_parts = settings.SETTINGS_MODULE.split(".")
            module_path = Path(*module_parts)

            if len(module_parts) > 2:
                module_path = Path(*module_parts[:-1])

            # Use list() for < Python 3.9
            for parent in list(module_path.parents)[:2]:
                path = (parent / component_dir).resolve()
                if path.is_dir():
                    directories.add(path)

        return list(directories)
