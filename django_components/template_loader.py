"""
Template loader that loads templates from each Django app's "components" directory.
"""

from pathlib import Path
from typing import Set

from django.conf import settings
from django.template.loaders.filesystem import Loader as FilesystemLoader
from django.template.utils import get_app_template_dirs


class Loader(FilesystemLoader):
    def get_dirs(self):
        # Allow to configure from settings which dirs should be checked for components
        if hasattr(settings, "STATICFILES_DIRS"):
            component_dirs = settings.STATICFILES_DIRS
        else:
            component_dirs = ["components"]

        directories: Set[str] = set()
        for component_dir in component_dirs:
            curr_directories = set(get_app_template_dirs(component_dir))

            if hasattr(settings, "BASE_DIR"):
                path = (Path(settings.BASE_DIR) / component_dir).resolve()
                if path.is_dir():
                    curr_directories.add(path)

            # Add the directory that holds the settings file
            if settings.SETTINGS_MODULE:
                module_parts = settings.SETTINGS_MODULE.split(".")
                module_path = Path(*module_parts)

                # - If len() == 2, then path to settings file is <app_name>/<settings_file>.py
                # - If len() > 2, then we assume that settings file is in a settings directory,
                #   e.g. <app_name>/settings/<settings_file>.py
                if len(module_parts) > 2:
                    module_path = Path(*module_parts[:-1])

                # Get the paths for the nested settings dir like `<app_name>/settings`,
                # or for non-nested dir like `<app_name>`
                # 
                # NOTE: Use list() for < Python 3.9
                for parent in list(module_path.parents)[:2]:
                    path = (parent / component_dir).resolve()
                    if path.is_dir():
                        curr_directories.add(path)

            directories.update(curr_directories)

        return list(directories)
