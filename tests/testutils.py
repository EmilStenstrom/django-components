import contextlib
import sys
from typing import List
from unittest.mock import Mock

from django.template import Context, Node
from django.template.response import TemplateResponse
from django.test import SimpleTestCase

from django_components import autodiscover
from django_components.component_registry import registry
from django_components.middleware import ComponentDependencyMiddleware

# Create middleware instance
response_stash = None
middleware = ComponentDependencyMiddleware(get_response=lambda _: response_stash)


class BaseTestCase(SimpleTestCase):
    @classmethod
    def setUpClass(self) -> None:
        registry.clear()
        return super().setUpClass()


request = Mock()
mock_template = Mock()


def create_and_process_template_response(template, context=None, use_middleware=True):
    context = context if context is not None else Context({})
    mock_template.render = lambda context, _: template.render(context)
    response = TemplateResponse(request, mock_template, context)
    if use_middleware:
        response.render()
        global response_stash
        response_stash = response
        response = middleware(request)
    else:
        response.render()
    return response.content.decode("utf-8")


def print_nodes(nodes: List[Node], indent=0) -> None:
    """
    Render a Nodelist, inlining child nodes with extra on separate lines and with
    extra indentation.
    """
    for node in nodes:
        child_nodes: List[Node] = []
        for attr in node.child_nodelists:
            attr_child_nodes = getattr(node, attr, None) or []
            if attr_child_nodes:
                child_nodes.extend(attr_child_nodes)

        repr = str(node)
        repr = "\n".join([(" " * 4 * indent) + line for line in repr.split("\n")])
        print(repr)
        if child_nodes:
            print_nodes(child_nodes, indent=indent + 1)


# TODO: Make sure that this is done before/after each test automatically?
@contextlib.contextmanager
def autodiscover_with_cleanup(*args, **kwargs):
    """
    Use this in place of regular `autodiscover` in test files to ensure that
    the autoimport does not pollute the global state.
    """
    imported_modules = autodiscover(*args, **kwargs)
    try:
        yield imported_modules
    finally:
        # Teardown - delete autoimported modules, so the module is executed also the
        # next time one of the tests calls `autodiscover`.
        for mod in imported_modules:
            del sys.modules[mod]
