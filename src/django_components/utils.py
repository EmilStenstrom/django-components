import glob
import random
from pathlib import Path
from typing import Callable, List, NamedTuple, Optional

from django.template.base import Node, NodeList
from django.template.engine import Engine

from django_components.template_loader import Loader


class SearchResult(NamedTuple):
    searched_dirs: List[Path]
    matched_files: List[Path]


def search(search_glob: Optional[str] = None, engine: Optional[Engine] = None) -> SearchResult:
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
        return SearchResult(searched_dirs=dirs, matched_files=[])

    component_filenames: List[Path] = []
    for directory in dirs:
        for path in glob.iglob(str(Path(directory) / search_glob), recursive=True):
            component_filenames.append(Path(path))

    return SearchResult(searched_dirs=dirs, matched_files=component_filenames)


def walk_nodelist(nodes: NodeList, callback: Callable[[Node], None]) -> None:
    """Recursively walk a NodeList, calling `callback` for each Node."""
    node_queue = [*nodes]
    while len(node_queue):
        node: Node = node_queue.pop()
        callback(node)
        node_queue.extend(get_node_children(node))


def get_node_children(node: Node) -> NodeList:
    """
    Get child Nodes from Node's nodelist atribute.

    This function is taken from `get_nodes_by_type` method of `django.template.base.Node`.
    """
    nodes = NodeList()
    for attr in node.child_nodelists:
        nodelist = getattr(node, attr, [])
        if nodelist:
            nodes.extend(nodelist)
    return nodes


def gen_id(length: int = 5) -> str:
    # Generate random value
    # See https://stackoverflow.com/questions/2782229
    value = random.randrange(16**length)

    # Signed hexadecimal (lowercase).
    # See https://docs.python.org/3/library/stdtypes.html#printf-style-string-formatting
    return f"{value:x}"
