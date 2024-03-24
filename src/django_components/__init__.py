import importlib
import importlib.util
import sys
from pathlib import Path
from typing import Union

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
        component_filepaths = search(search_glob="**/*.py")
        for path in component_filepaths:
            import_file(path)

    for path_lib in app_settings.LIBRARIES:
        importlib.import_module(path_lib)


def import_file(path: Union[str, Path]) -> None:
    MODULE_PATH = path
    MODULE_NAME = Path(path).stem
    spec = importlib.util.spec_from_file_location(MODULE_NAME, MODULE_PATH)
    if spec is None:
        raise ValueError(f"Cannot import file '{path}' - invalid path")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)  # type: ignore
