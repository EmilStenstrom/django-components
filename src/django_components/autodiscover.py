import glob
import importlib
import os
from pathlib import Path
from typing import Callable, List, Optional, Union

from django.conf import settings

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
    dirs = get_dirs()
    component_filepaths = search_dirs(dirs, "**/*.py")
    logger.debug(f"Autodiscover found {len(component_filepaths)} files in component directories.")

    modules: List[str] = []
    for filepath in component_filepaths:
        module_path = _filepath_to_python_module(filepath)
        # Ignore relative paths that are outside of the project root
        if not module_path.startswith(".."):
            modules.append(module_path)

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


def _filepath_to_python_module(file_path: Union[Path, str]) -> str:
    """
    Derive python import path from the filesystem path.

    Example:
    - If project root is `/path/to/project`
    - And file_path is `/path/to/project/app/components/mycomp.py`
    - Then the path relative to project root is `app/components/mycomp.py`
    - Which we then turn into python import path `app.components.mycomp`
    """
    if hasattr(settings, "BASE_DIR") and settings.BASE_DIR:
        project_root = str(settings.BASE_DIR)
    else:
        # Fallback for getting the root dir, see https://stackoverflow.com/a/16413955/9788634
        project_root = os.path.abspath(os.path.dirname(__name__))

    rel_path = os.path.relpath(file_path, start=project_root)
    rel_path_without_suffix = str(Path(rel_path).with_suffix(""))

    # NOTE: `Path` normalizes paths to use `/` as separator, while `os.path`
    # uses `os.path.sep`.
    sep = os.path.sep if os.path.sep in rel_path_without_suffix else "/"
    module_name = rel_path_without_suffix.replace(sep, ".")

    return module_name


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
