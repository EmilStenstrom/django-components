from typing import Dict, Optional

from django.template import Context
from django.template.base import FilterExpression, Node, NodeList
from django.utils.safestring import SafeString

from django_components.context import set_provided_context_var
from django_components.expression import safe_resolve_dict
from django_components.logger import trace_msg
from django_components.template_parser import process_aggregate_kwargs
from django_components.utils import gen_id


class ProvideNode(Node):
    """
    Implementation of the `{% provide %}` tag.
    For more info see `Component.inject`.
    """

    def __init__(
        self,
        name: str,
        nodelist: NodeList,
        node_id: Optional[str] = None,
        provide_kwargs: Optional[Dict[str, FilterExpression]] = None,
    ):
        self.name = name
        self.nodelist = nodelist
        self.node_id = node_id or gen_id()
        self.provide_kwargs = provide_kwargs or {}

    def __repr__(self) -> str:
        return f"<Provide Node: {self.name}. Contents: {repr(self.nodelist)}. Data: {self.provide_kwargs}>"

    def render(self, context: Context) -> SafeString:
        trace_msg("RENDR", "PROVIDE", self.name, self.node_id)

        data = safe_resolve_dict(self.provide_kwargs, context)
        # Allow user to use the var:key=value syntax
        data = process_aggregate_kwargs(data)

        # NOTE: The "provided" kwargs are meant to be shared privately, meaning that components
        # have to explicitly opt in by using the `Component.inject()` method. That's why we don't
        # add the provided kwargs into the Context.
        with context.update({}):
            # "Provide" the data to child nodes
            set_provided_context_var(context, self.name, data)

            output = self.nodelist.render(context)

        trace_msg("RENDR", "PROVIDE", self.name, self.node_id, msg="...Done!")
        return output
