import importlib
import importlib.util
import os
from pathlib import Path
from typing import Callable, List, Optional

import django
from django.conf import settings
from django.utils.module_loading import autodiscover_modules

from django_components.logger import logger
from django_components.utils import search

if django.VERSION < (3, 2):
    default_app_config = "django_components.apps.ComponentsConfig"


def autodiscover(map_import_paths: Optional[Callable[[str], str]] = None) -> List[str]:
    """
    Search for component files and import them. Returns a list of module
    paths of imported files.
    """
    from django_components.app_settings import app_settings

    imported_modules: List[str] = []

    if app_settings.AUTODISCOVER:
        # Autodetect a components.py file in each app directory
        autodiscover_modules("components")

        # Autodetect a <component>.py file in a components dir
        component_filepaths = search(search_glob="**/*.py").matched_files
        logger.debug(f"Autodiscover found {len(component_filepaths)} files in component directories.")

        for path in component_filepaths:
            module_name = _filepath_to_python_module(path)
            if map_import_paths:
                module_name = map_import_paths(module_name)

            # This imports the file and runs it's code. So if the file defines any
            # django components, they will be registered.
            logger.debug(f'Importing module "{module_name}" (derived from path "{path}")')
            importlib.import_module(module_name)
            imported_modules.append(module_name)

    for path_lib in app_settings.LIBRARIES:
        importlib.import_module(path_lib)

    return imported_modules


def _filepath_to_python_module(file_path: Path) -> str:
    """
    Derive python import path from the filesystem path.

    Example:
    - If project root is `/path/to/project`
    - And file_path is `/path/to/project/app/components/mycomp.py`
    - Then the path relative to project root is `app/components/mycomp.py`
    - Which we then turn into python import path `app.components.mycomp`
    """
    if hasattr(settings, "BASE_DIR"):
        project_root = str(settings.BASE_DIR)
    else:
        # Fallback for getting the root dir, see https://stackoverflow.com/a/16413955/9788634
        project_root = os.path.abspath(os.path.dirname(__name__))

    rel_path = os.path.relpath(file_path, start=project_root)
    rel_path_without_suffix = str(Path(rel_path).with_suffix(""))

    # NOTE: Path normalizes paths to use `/` as separator, while os.path
    # uses `os.path.sep`.
    sep = os.path.sep if os.path.sep in rel_path_without_suffix else "/"
    module_name = rel_path_without_suffix.replace(sep, ".")

    return module_name
