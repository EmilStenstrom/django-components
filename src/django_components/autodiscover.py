import glob
import importlib
import os
from pathlib import Path
from typing import Callable, List, Optional

from django.conf import settings
from django.template.engine import Engine
from django.utils.module_loading import autodiscover_modules

from django_components.logger import logger
from django_components.template_loader import Loader


def autodiscover(
    components_modules: Optional[List[str]] = None,
    map_components_modules: Optional[Callable[[str], str]] = None,
    skip_component_modules: Optional[bool] = None,
    skip_libraries: Optional[bool] = False,
) -> List[str]:
    """
    Search for component files and import them. Returns a list of module
    paths of imported files.

    Autodiscover searches in the following locations:

    1. Component modules - `[app_name]/components.py` for all apps in the project
    2. Component dirs - As defined by `Loader.get_dirs`
    3. Libraries - Modules listed in `COMPONENTS.libraries`.

    Import of component modules can be skipped, either by setting `skip_component_modules=True`,
    or by setting `COMPONENTS.autodiscover` to `False`.

    Import of libraries can be skipped by setting `skip_libraries=True`.

    You can change the files searched in each app (Component modules) by setting `components_modules`
    to a list of modules (relative to the app). E.g. `components_modules=["components", "nested.components"]`
    will search in each app for `[app_name]/components.py` and `[app_name]/nested/components.py`. Defaults
    to `["components"]`.

    Autodiscover makes it possible to map the component module paths. This serves
    as an escape hatch for when you need to use autodiscover in tests.
    """
    from django_components.app_settings import app_settings

    # Allow users to specify directly whether to do search for component module,
    # but default to AUTODISCOVER settings.
    if skip_component_modules is None:
        skip_component_modules = not app_settings.AUTODISCOVER
    
    if components_modules is None:
        components_modules = ["components"]

    imported_modules: List[str] = []

    if not skip_component_modules:
        # Autodetect a components.py file (or other files) in each app directory
        #
        # TODO1: THIS IS NOT DOCUMENTED!! - Do we want to keep it or not?
        #        Basically it searches for "<app_name1>/components.py" in each app.
        #        Altho I like that it could allow people to dynamically configure which components to import, eg.
        #        ```py
        #        if xyz:
        #            import path.to.component
        #            import path.to.component2
        #        else:
        #            import ...
        #        ```
        #
        # TODO: Maybe we could remove this and modify the logic of `Loader.get_dirs`,
        #       so `<app_name>/components.py` is among the returned files? In which case
        #       the `components_modules` arg in this function could be made into a setting 
        #       `COMPONENTS.component_modules`, and resolved in `Loader.get_dirs`.
        #
        # TODO2: Or maybe we should move `autodiscover_modules` and loading of libraries OUT from autodiscovery?
        autodiscover_modules(*components_modules)

        # Autodetect a <component>.py file in components dirs
        dirs = get_dirs()
        component_filepaths = search_dirs(dirs, "**/*.py")
        logger.debug(f"Autodiscover found {len(component_filepaths)} files in component directories.")

        for path in component_filepaths:
            module_name = _filepath_to_python_module(path)
            if map_components_modules:
                module_name = map_components_modules(module_name)

            # This imports the file and runs it's code. So if the file defines any
            # django components, they will be registered.
            logger.debug(f'Importing module "{module_name}" (derived from path "{path}")')
            importlib.import_module(module_name)
            imported_modules.append(module_name)

    if not skip_libraries:
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


def get_dirs(engine: Optional[Engine] = None) -> List[Path]:
    """
    Helper for using django_component's FilesystemLoader class to obtain a list
    of directories where component python files may be defined.
    """
    current_engine = engine
    if current_engine is None:
        current_engine = Engine.get_default()

    loader = Loader(current_engine)
    return loader.get_dirs()


def search_dirs(dirs: List[Path], search_glob: str) -> List[Path]:
    """
    Search the directories for the given glob pattern. Glob search results are returned
    as a flattened list.
    """
    matched_files: List[Path] = []
    for directory in dirs:
        for path in glob.iglob(str(Path(directory) / search_glob), recursive=True):
            matched_files.append(Path(path))

    return matched_files
