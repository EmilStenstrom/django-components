from typing import List, Optional

from django.template.base import Node, NodeList

from django_components.expression import Expression, RuntimeKwargs
from django_components.util.misc import gen_id


class BaseNode(Node):
    """Shared behavior for our subclasses of Django's `Node`"""

    def __init__(
        self,
        nodelist: Optional[NodeList] = None,
        node_id: Optional[str] = None,
        args: Optional[List[Expression]] = None,
        kwargs: Optional[RuntimeKwargs] = None,
    ):
        self.nodelist = nodelist or NodeList()
        self.node_id = node_id or gen_id()
        self.args = args or []
        self.kwargs = kwargs or RuntimeKwargs({})
