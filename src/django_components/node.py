from typing import Optional

from django.template.base import Node, NodeList

from django_components.util.misc import gen_id
from django_components.util.template_tag import TagParams


class BaseNode(Node):
    """Shared behavior for our subclasses of Django's `Node`"""

    def __init__(
        self,
        params: TagParams,
        nodelist: Optional[NodeList] = None,
        node_id: Optional[str] = None,
    ):
        self.params = params
        self.nodelist = nodelist or NodeList()
        self.node_id = node_id or gen_id()
