import glob
import importlib
import os
from pathlib import Path
from typing import Callable, List, Optional, Union

from django.apps import apps
from django.conf import settings

from django_components.app_settings import app_settings
from django_components.logger import logger
from django_components.template_loader import get_dirs


def autodiscover(
    map_module: Optional[Callable[[str], str]] = None,
) -> List[str]:
    """
    Search for component files and import them. Returns a list of module
    paths of imported files.

    Autodiscover searches in the locations as defined by `Loader.get_dirs`.

    You can map the module paths with `map_module` function. This serves
    as an escape hatch for when you need to use this function in tests.
    """
    dirs = get_dirs(include_apps=False)
    component_filepaths = search_dirs(dirs, "**/*.py")
    logger.debug(f"Autodiscover found {len(component_filepaths)} files in component directories.")

    if hasattr(settings, "BASE_DIR") and settings.BASE_DIR:
        project_root = str(settings.BASE_DIR)
    else:
        # Fallback for getting the root dir, see https://stackoverflow.com/a/16413955/9788634
        project_root = os.path.abspath(os.path.dirname(__name__))

    modules: List[str] = []

    # We handle dirs from `COMPONENTS.dirs` and from individual apps separately.
    #
    # Because for dirs in `COMPONENTS.dirs`, we assume they will be nested under `BASE_DIR`,
    # and that `BASE_DIR` is the current working dir (CWD). So the path relatively to `BASE_DIR`
    # is ALSO the python import path.
    for filepath in component_filepaths:
        module_path = _filepath_to_python_module(filepath, project_root, None)
        # Ignore files starting with dot `.` or files in dirs that start with dot.
        #
        # If any of the parts of the path start with a dot, e.g. the filesystem path
        # is `./abc/.def`, then this gets converted to python module as `abc..def`
        #
        # NOTE: This approach also ignores files:
        #   - with two dots in the middle (ab..cd.py)
        #   - an extra dot at the end (abcd..py)
        #   - files outside of the parent component (../abcd.py).
        # But all these are NOT valid python modules so that's fine.
        if ".." in module_path:
            continue

        modules.append(module_path)

    # For for apps, the directories may be outside of the project, e.g. in case of third party
    # apps. So we have to resolve the python import path relative to the package name / the root
    # import path for the app.
    # See https://github.com/EmilStenstrom/django-components/issues/669
    for conf in apps.get_app_configs():
        for app_dir in app_settings.APP_DIRS:
            comps_path = Path(conf.path).joinpath(app_dir)
            if not comps_path.exists():
                continue
            app_component_filepaths = search_dirs([comps_path], "**/*.py")
            for filepath in app_component_filepaths:
                app_component_module = _filepath_to_python_module(filepath, conf.path, conf.name)
                modules.append(app_component_module)

    return _import_modules(modules, map_module)


def import_libraries(
    map_module: Optional[Callable[[str], str]] = None,
) -> List[str]:
    """
    Import modules set in `COMPONENTS.libraries` setting.

    You can map the module paths with `map_module` function. This serves
    as an escape hatch for when you need to use this function in tests.
    """
    from django_components.app_settings import app_settings

    return _import_modules(app_settings.LIBRARIES, map_module)


def _import_modules(
    modules: List[str],
    map_module: Optional[Callable[[str], str]] = None,
) -> List[str]:
    imported_modules: List[str] = []
    for module_name in modules:
        if map_module:
            module_name = map_module(module_name)

        # This imports the file and runs it's code. So if the file defines any
        # django components, they will be registered.
        logger.debug(f'Importing module "{module_name}"')
        importlib.import_module(module_name)
        imported_modules.append(module_name)
    return imported_modules


def _filepath_to_python_module(
    file_path: Union[Path, str],
    root_fs_path: Union[str, Path],
    root_module_path: Optional[str],
) -> str:
    """
    Derive python import path from the filesystem path.

    Example:
    - If project root is `/path/to/project`
    - And file_path is `/path/to/project/app/components/mycomp.py`
    - Then the path relative to project root is `app/components/mycomp.py`
    - Which we then turn into python import path `app.components.mycomp`
    """
    rel_path = os.path.relpath(file_path, start=root_fs_path)
    rel_path_without_suffix = str(Path(rel_path).with_suffix(""))

    # NOTE: `Path` normalizes paths to use `/` as separator, while `os.path`
    # uses `os.path.sep`.
    sep = os.path.sep if os.path.sep in rel_path_without_suffix else "/"
    module_name = rel_path_without_suffix.replace(sep, ".")

    # Combine with the base module path
    full_module_name = f"{root_module_path}.{module_name}" if root_module_path else module_name
    if full_module_name.endswith(".__init__"):
        full_module_name = full_module_name[:-9]  # Remove the trailing `.__init__

    return full_module_name


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
