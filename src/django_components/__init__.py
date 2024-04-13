import importlib
import importlib.util
import os
from pathlib import Path

import django
from django.utils.module_loading import autodiscover_modules

from django_components.utils import search

if django.VERSION < (3, 2):
    default_app_config = "django_components.apps.ComponentsConfig"


def autodiscover() -> None:
    from django_components.app_settings import app_settings

    if app_settings.AUTODISCOVER:
        # Autodetect a components.py file in each app directory
        autodiscover_modules("components")

        # Autodetect a <component>.py file in a components dir
        component_filepaths = search(search_glob="**/*.py").matched_files
        for path in component_filepaths:
            import_file(path)

    for path_lib in app_settings.LIBRARIES:
        importlib.import_module(path_lib)


def import_file(file_path: Path) -> None:
    # Get the root dir, see https://stackoverflow.com/a/16413955/9788634
    project_root = os.path.abspath(os.path.dirname(__name__))

    # Derive python import path from the filesystem path
    # Example:
    # If project root is `/path/to/project`
    # And file_path is `/path/to/project/app/components/mycomp.py`
    # Then the path relative to project root is `app/components/mycomp.py`
    # Which we then turn into python import path `app.components.mycomp`
    rel_path = os.path.relpath(file_path, start=project_root)
    rel_path_without_suffix = str(Path(rel_path).with_suffix(""))
    module_name = rel_path_without_suffix.replace(os.sep, ".")
    
    # This imports the file and runs it's code. So if the file defines any
    # django components, they will be registered.
    importlib.import_module(module_name)
