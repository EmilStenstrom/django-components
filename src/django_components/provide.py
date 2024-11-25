from typing import Dict, Optional, Tuple

from django.template import Context
from django.template.base import NodeList
from django.utils.safestring import SafeString

from django_components.context import set_provided_context_var
from django_components.expression import RuntimeKwargs
from django_components.node import BaseNode
from django_components.util.logger import trace_msg
from django_components.util.misc import gen_id

PROVIDE_NAME_KWARG = "name"


class ProvideNode(BaseNode):
    """
    Implementation of the `{% provide %}` tag.
    For more info see `Component.inject`.
    """

    def __init__(
        self,
        nodelist: NodeList,
        trace_id: str,
        node_id: Optional[str] = None,
        kwargs: Optional[RuntimeKwargs] = None,
    ):
        super().__init__(nodelist=nodelist, args=None, kwargs=kwargs, node_id=node_id)

        self.nodelist = nodelist
        self.node_id = node_id or gen_id()
        self.trace_id = trace_id
        self.kwargs = kwargs or RuntimeKwargs({})

    def __repr__(self) -> str:
        return f"<Provide Node: {self.node_id}. Contents: {repr(self.nodelist)}>"

    def render(self, context: Context) -> SafeString:
        trace_msg("RENDR", "PROVIDE", self.trace_id, self.node_id)

        name, kwargs = self.resolve_kwargs(context)

        # NOTE: The "provided" kwargs are meant to be shared privately, meaning that components
        # have to explicitly opt in by using the `Component.inject()` method. That's why we don't
        # add the provided kwargs into the Context.
        with context.update({}):
            # "Provide" the data to child nodes
            set_provided_context_var(context, name, kwargs)

            output = self.nodelist.render(context)

        trace_msg("RENDR", "PROVIDE", self.trace_id, self.node_id, msg="...Done!")
        return output

    def resolve_kwargs(self, context: Context) -> Tuple[str, Dict[str, Optional[str]]]:
        kwargs = self.kwargs.resolve(context)
        name = kwargs.pop(PROVIDE_NAME_KWARG, None)

        if not name:
            raise RuntimeError("Provide tag kwarg 'name' is missing")

        return (name, kwargs)
