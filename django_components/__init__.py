import glob
import importlib
import importlib.util
import sys
from pathlib import Path

import django
from django.template.engine import Engine
from django.utils.module_loading import autodiscover_modules

from django_components.template_loader import Loader

if django.VERSION < (3, 2):
    default_app_config = "django_components.apps.ComponentsConfig"


def autodiscover():
    from django_components.app_settings import app_settings

    if app_settings.AUTODISCOVER:
        # Autodetect a components.py file in each app directory
        autodiscover_modules("components")

        # Autodetect a <component>.py file in a components dir
        current_engine = Engine.get_default()
        loader = Loader(current_engine)
        dirs = loader.get_dirs()
        for directory in dirs:
            for path in glob.iglob(str(directory / "**/*.py"), recursive=True):
                import_file(path)

    for path in app_settings.LIBRARIES:
        importlib.import_module(path)


def import_file(path):
    MODULE_PATH = path
    MODULE_NAME = Path(path).stem
    spec = importlib.util.spec_from_file_location(MODULE_NAME, MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
