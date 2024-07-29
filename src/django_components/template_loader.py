"""
Template loader that loads templates from each Django app's "components" directory.
"""

from pathlib import Path
from typing import List, Set

from django.conf import settings
from django.template.loaders.filesystem import Loader as FilesystemLoader

from django_components.logger import logger


class Loader(FilesystemLoader):
    def get_dirs(self) -> List[Path]:
        """
        Prepare directories that may contain component files:

        Searches for dirs set in `STATICFILES_DIRS` settings. If none set, defaults to searching
        for a "components" app. The dirs in `STATICFILES_DIRS` must be absolute paths.

        Paths are accepted only if they resolve to a directory.
        E.g. `/path/to/django_project/my_app/components/`.

        If `STATICFILES_DIRS` is not set or empty, then `BASE_DIR` is required.
        """
        # Allow to configure from settings which dirs should be checked for components
        if hasattr(settings, "STATICFILES_DIRS") and settings.STATICFILES_DIRS:
            component_dirs = settings.STATICFILES_DIRS
        else:
            component_dirs = [settings.BASE_DIR / "components"]

        logger.debug(
            "Template loader will search for valid template dirs from following options:\n"
            + "\n".join([f" - {str(d)}" for d in component_dirs])
        )

        directories: Set[Path] = set()
        for component_dir in component_dirs:
            # Consider tuples for STATICFILES_DIRS (See #489)
            # See https://docs.djangoproject.com/en/5.0/ref/settings/#prefixes-optional
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

            if not Path(component_dir).is_absolute():
                raise ValueError(f"STATICFILES_DIRS must contain absolute paths, got '{component_dir}'")
            else:
                directories.add(Path(component_dir).resolve())

        logger.debug(
            "Template loader matched following template dirs:\n" + "\n".join([f" - {str(d)}" for d in directories])
        )
        return list(directories)
