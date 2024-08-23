from typing import Optional

from django.template import Context
from django.template.base import NodeList
from django.utils.safestring import SafeString

from django_components.context import set_provided_context_var
from django_components.expression import RuntimeKwargs
from django_components.logger import trace_msg
from django_components.node import BaseNode
from django_components.utils import gen_id


class ProvideNode(BaseNode):
    """
    Implementation of the `{% provide %}` tag.
    For more info see `Component.inject`.
    """

    def __init__(
        self,
        name: str,
        nodelist: NodeList,
        node_id: Optional[str] = None,
        kwargs: Optional[RuntimeKwargs] = None,
    ):
        super().__init__(nodelist=nodelist, args=None, kwargs=kwargs, node_id=node_id)

        self.name = name
        self.nodelist = nodelist
        self.node_id = node_id or gen_id()
        self.kwargs = kwargs or RuntimeKwargs({})

    def __repr__(self) -> str:
        return f"<Provide Node: {self.name}. Contents: {repr(self.nodelist)}. Data: {self.provide_kwargs.kwargs}>"

    def render(self, context: Context) -> SafeString:
        trace_msg("RENDR", "PROVIDE", self.name, self.node_id)

        kwargs = self.kwargs.resolve(context)

        # NOTE: The "provided" kwargs are meant to be shared privately, meaning that components
        # have to explicitly opt in by using the `Component.inject()` method. That's why we don't
        # add the provided kwargs into the Context.
        with context.update({}):
            # "Provide" the data to child nodes
            set_provided_context_var(context, self.name, kwargs)

            output = self.nodelist.render(context)

        trace_msg("RENDR", "PROVIDE", self.name, self.node_id, msg="...Done!")
        return output
