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
        directories = list(get_app_template_dirs(component_dir))

        if settings.SETTINGS_MODULE:
            settings_path = Path(*settings.SETTINGS_MODULE.split("."))

            path = (settings_path / ".." / component_dir).resolve()
            if path.is_dir():
                directories.append(path)

            path = (settings_path / ".." / ".." / component_dir).resolve()
            if path.is_dir():
                directories.append(path)

        return directories
