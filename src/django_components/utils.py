import glob
from pathlib import Path
from typing import List, Optional, Union

from django.template.engine import Engine

from django_components.template_loader import Loader


def search(search_glob: Optional[str] = None, engine: Optional[Engine] = None) -> Union[List[str], List[Path]]:
    """
    Search for directories that may contain components.

    If `search_glob` is given, the directories are searched for said glob pattern,
    and glob search results are returned as a flattened list.
    """
    current_engine = engine
    if current_engine is None:
        current_engine = Engine.get_default()

    loader = Loader(current_engine)
    dirs = loader.get_dirs()

    if search_glob is None:
        return dirs

    component_filenames: List[str] = []
    for directory in dirs:
        for path in glob.iglob(str(Path(directory) / search_glob), recursive=True):
            component_filenames.append(path)

    return component_filenames
