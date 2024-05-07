"""
Template loader that loads templates from each Django app's "components" directory.
"""

import os
from pathlib import Path
from typing import List, Set

from django.apps import apps
from django.conf import settings
from django.template.loaders.filesystem import Loader as FilesystemLoader

from django_components.logger import logger


# Same as `Path.is_relative_to`, defined as standalone function because `Path.is_relative_to`
# is marked for deprecation.
def path_is_relative_to(child_path: str, parent_path: str) -> bool:
    # If the relative path doesn't start with `..`, then child is descendant of parent
    # See https://stackoverflow.com/a/7288073/9788634
    rel_path = os.path.relpath(child_path, parent_path)
    return not rel_path.startswith("..")


class Loader(FilesystemLoader):
    def get_dirs(self) -> List[Path]:
        # Allow to configure from settings which dirs should be checked for components
        if hasattr(settings, "STATICFILES_DIRS") and len(settings.STATICFILES_DIRS):
            component_dirs = settings.STATICFILES_DIRS
        else:
            component_dirs = ["components"]

        logger.debug(
            "Template loader will search for valid template dirs from following options:\n"
            + "\n".join([f" - {str(d)}" for d in component_dirs])
        )

        directories: Set[Path] = set()
        for component_dir in component_dirs:
            if isinstance(component_dir, (tuple, list)) and len(component_dir) == 2:
                component_dir = component_dir[1]
            try:
                Path(component_dir)
            except TypeError:
                logger.warning(
                    f"STATICFILES_DIRS expected str, bytes or os.PathLike object, or tuple/list of length 2. "
                    f"See Django documentation. Got {type(component_dir)} : {component_dir}"
                )
                continue
            curr_directories: Set[Path] = set()

            # For each dir in `settings.STATICFILES_DIRS`, we go over all Django apps
            # and, for each app, check if the STATICFILES_DIRS dir is within that app dir.
            # If so, we add the dir as a valid source.
            # The for loop is based on Django's `get_app_template_dirs`.
            for app_config in apps.get_app_configs():
                if not app_config.path:
                    continue
                if not Path(component_dir).is_dir():
                    continue

                if path_is_relative_to(component_dir, app_config.path):
                    curr_directories.add(Path(component_dir).resolve())

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

        logger.debug(
            "Template loader matched following template dirs:\n" + "\n".join([f" - {str(d)}" for d in directories])
        )
        return list(directories)
