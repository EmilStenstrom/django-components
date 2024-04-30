from typing import Callable, List, NamedTuple, Optional

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


class NodeTraverse(NamedTuple):
    node: Node
    parent: Optional["NodeTraverse"]


def walk_nodelist(nodes: NodeList, callback: Callable[[Node], Optional[str]]) -> None:
    """Recursively walk a NodeList, calling `callback` for each Node."""
    node_queue: List[NodeTraverse] = [NodeTraverse(node=node, parent=None) for node in nodes]
    while len(node_queue):
        traverse = node_queue.pop()
        callback(traverse)
        child_nodes = get_node_children(traverse.node)
        child_traverses = [NodeTraverse(node=child_node, parent=traverse) for child_node in child_nodes]
        node_queue.extend(child_traverses)


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
