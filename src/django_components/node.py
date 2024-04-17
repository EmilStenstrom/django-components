from typing import Callable

from django.template.base import Node, NodeList, TextNode
from django.template.defaulttags import CommentNode


def nodelist_has_content(nodelist: NodeList) -> bool:
    for node in nodelist:
        if isinstance(node, TextNode) and node.s.isspace():
            pass
        elif isinstance(node, CommentNode):
            pass
        else:
            return True
    return False


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
