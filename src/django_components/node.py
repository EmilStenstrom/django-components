from typing import Callable, List, NamedTuple, Optional

from django.template import Context, Template
from django.template.base import Node, NodeList, TextNode
from django.template.defaulttags import CommentNode
from django.template.loader_tags import ExtendsNode, IncludeNode, construct_relative_path


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


def walk_nodelist(
    nodes: NodeList,
    callback: Callable[[Node], Optional[str]],
    context: Optional[Context] = None,
) -> None:
    """Recursively walk a NodeList, calling `callback` for each Node."""
    node_queue: List[NodeTraverse] = [NodeTraverse(node=node, parent=None) for node in nodes]
    while len(node_queue):
        traverse = node_queue.pop()
        callback(traverse)
        child_nodes = get_node_children(traverse.node, context)
        child_traverses = [NodeTraverse(node=child_node, parent=traverse) for child_node in child_nodes]
        node_queue.extend(child_traverses)


def get_node_children(node: Node, context: Optional[Context] = None) -> NodeList:
    """
    Get child Nodes from Node's nodelist atribute.

    This function is taken from `get_nodes_by_type` method of `django.template.base.Node`.
    """
    # Special case - {% extends %} tag - Load the template and go deeper
    if isinstance(node, ExtendsNode):
        # NOTE: When {% extends %} node is being parsed, it collects all remaining template
        # under node.nodelist.
        # Hence, when we come across ExtendsNode in the template, we:
        # 1. Go over all nodes in the template using `node.nodelist`
        # 2. Go over all nodes in the "parent" template, via `node.get_parent`
        nodes = NodeList()
        nodes.extend(node.nodelist)
        template = node.get_parent(context)
        nodes.extend(template.nodelist)
        return nodes

    # Special case - {% include %} tag - Load the template and go deeper
    elif isinstance(node, IncludeNode):
        template = get_template_for_include_node(node, context)
        return template.nodelist

    nodes = NodeList()
    for attr in node.child_nodelists:
        nodelist = getattr(node, attr, [])
        if nodelist:
            nodes.extend(nodelist)
    return nodes


def get_template_for_include_node(include_node: IncludeNode, context: Context) -> Template:
    """
    This snippet is taken directly from `IncludeNode.render()`. Unfortunately the
    render logic doesn't separate out template loading logic from rendering, so we
    have to copy the method.
    """
    template = include_node.template.resolve(context)
    # Does this quack like a Template?
    if not callable(getattr(template, "render", None)):
        # If not, try the cache and select_template().
        template_name = template or ()
        if isinstance(template_name, str):
            template_name = (
                construct_relative_path(
                    include_node.origin.template_name,
                    template_name,
                ),
            )
        else:
            template_name = tuple(template_name)
        cache = context.render_context.dicts[0].setdefault(include_node, {})
        template = cache.get(template_name)
        if template is None:
            template = context.template.engine.select_template(template_name)
            cache[template_name] = template
    # Use the base.Template of a backends.django.Template.
    elif hasattr(template, "template"):
        template = template.template
    return template
