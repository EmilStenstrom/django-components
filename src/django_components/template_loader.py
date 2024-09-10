"""
Template loader that loads templates from each Django app's "components" directory.
"""

from pathlib import Path
from typing import List, Optional, Set

from django.apps import apps
from django.conf import settings
from django.template.engine import Engine
from django.template.loaders.filesystem import Loader as FilesystemLoader

from django_components.app_settings import app_settings
from django_components.logger import logger


# Similar to `Path.is_relative_to`, which is missing in 3.8
def is_relative_to(path: Path, other: Path) -> bool:
    try:
        path.relative_to(other)
        return True
    except ValueError:
        return False


# This is the heart of all features that deal with filesystem and file lookup.
# Autodiscovery, Django template resolution, static file resolution - They all
# depend on this loader.
class Loader(FilesystemLoader):
    def get_dirs(self) -> List[Path]:
        """
        Prepare directories that may contain component files:

        Searches for dirs set in `COMPONENTS.dirs` settings. If none set, defaults to searching
        for a "components" app. The dirs in `COMPONENTS.dirs` must be absolute paths.

        In addition to that, also all apps are checked for `[app]/components` dirs.

        Paths are accepted only if they resolve to a directory.
        E.g. `/path/to/django_project/my_app/components/`.

        `BASE_DIR` setting is required.
        """
        # Allow to configure from settings which dirs should be checked for components
        component_dirs = app_settings.DIRS

        # TODO_REMOVE_IN_V1
        is_legacy_paths = (
            # Use value of `STATICFILES_DIRS` ONLY if `COMPONENT.dirs` not set
            not getattr(settings, "COMPONENTS", {}).get("dirs", None) is not None
            and hasattr(settings, "STATICFILES_DIRS")
            and settings.STATICFILES_DIRS
        )
        if is_legacy_paths:
            # NOTE: For STATICFILES_DIRS, we use the defaults even for empty list.
            # We don't do this for COMPONENTS.dirs, so user can explicitly specify "NO dirs".
            component_dirs = settings.STATICFILES_DIRS or [settings.BASE_DIR / "components"]
        source = "STATICFILES_DIRS" if is_legacy_paths else "COMPONENTS.dirs"

        logger.debug(
            "Template loader will search for valid template dirs from following options:\n"
            + "\n".join([f" - {str(d)}" for d in component_dirs])
        )

        # Add `[app]/[APP_DIR]` to the directories. This is, by default `[app]/components`
        app_paths: List[Path] = []
        for conf in apps.get_app_configs():
            for app_dir in app_settings.APP_DIRS:
                comps_path = Path(conf.path).joinpath(app_dir)
                if comps_path.exists() and is_relative_to(comps_path, settings.BASE_DIR):
                    app_paths.append(comps_path)

        directories: Set[Path] = set(app_paths)

        # Validate and add other values from the config
        for component_dir in component_dirs:
            # Consider tuples for STATICFILES_DIRS (See #489)
            # See https://docs.djangoproject.com/en/5.0/ref/settings/#prefixes-optional
            if isinstance(component_dir, (tuple, list)):
                component_dir = component_dir[1]
            try:
                Path(component_dir)
            except TypeError:
                logger.warning(
                    f"{source} expected str, bytes or os.PathLike object, or tuple/list of length 2. "
                    f"See Django documentation for STATICFILES_DIRS. Got {type(component_dir)} : {component_dir}"
                )
                continue

            if not Path(component_dir).is_absolute():
                raise ValueError(f"{source} must contain absolute paths, got '{component_dir}'")
            else:
                directories.add(Path(component_dir).resolve())

        logger.debug(
            "Template loader matched following template dirs:\n" + "\n".join([f" - {str(d)}" for d in directories])
        )
        return list(directories)


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
