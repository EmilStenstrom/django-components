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
    # TODO - Look deeper into how this function works
    #      -> Are STATICFILES_DIRS absolute paths or relative to project root? README suggest absolute,
    #         but the default suggests relative, and code suggests both. Document all the supported cases.
    #      -> Why do we add settings directory?
    #      -> Could we merge this with `autodiscover_modules()` in `autodiscover.py`, since there we also
    #         look for `[app_name]/components`, or do these two accomplish different things?
    def get_dirs(self) -> List[Path]:
        """
        Prepare directories that may contain component files:

        Searches for dirs set in `STATICFILES_DIRS` settings. If none set, defaults to searching
        for a "components" dir. These dirs are tested as both relative and absolute paths.

        Absolute paths are accepted only if they resolve to a directory and point to within one
        of the apps. E.g. `/path/to/django_project/[app_name]/nested/components/`.

        Relative paths are resolved relative to `BASE_DIR`, e.g. `[BASE_DIR]/components/`.
        
        Relative paths are also tested against the settings dir. Settings dir is the parent
        directory of where `SETTINGS_MODULE` points, if set.
        """
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
            # Consider tuples for STATICFILES_DIRS (See #489)
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

                # NOTE: This applies only to absolute paths
                if path_is_relative_to(component_dir, app_config.path) and Path(component_dir).is_dir():
                    curr_directories.add(Path(component_dir).resolve())

            # NOTE: This applies only to relative paths
            if hasattr(settings, "BASE_DIR"):
                path: Path = (Path(settings.BASE_DIR) / component_dir).resolve()
                if path.is_dir():
                    curr_directories.add(path)

            # Add the directory that holds the settings file
            # NOTE: This applies only to relative paths
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
