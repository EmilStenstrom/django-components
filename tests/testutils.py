import contextlib
import functools
import sys
from typing import Any, List, Tuple, Union
from unittest.mock import Mock

from django.template import Context, Node
from django.template.loader import engines
from django.template.response import TemplateResponse
from django.test import SimpleTestCase, override_settings

from django_components import autodiscover
from django_components.app_settings import ContextBehavior
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

    @classmethod
    def tearDownClass(cls) -> None:
        super().tearDownClass()
        registry.clear()


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


ContextBehStr = Union[ContextBehavior, str]
ContextBehParam = Union[ContextBehStr, Tuple[ContextBehStr, Any]]


def parametrize_context_behavior(cases: List[ContextBehParam]):
    """
    Use this decorator to run a test function with django_component's
    context_behavior settings set to given values.

    You can set only a single mode:
    ```py
    @parametrize_context_behavior(["isolated"])
    def test_bla_bla(self):
        # do something with app_settings.CONTEXT_BEHAVIOR set
        # to "isolated"
        ...
    ```

    Or you can set a test to run in both modes:
    ```py
    @parametrize_context_behavior(["django", "isolated"])
    def test_bla_bla(self):
        # Runs this test function twice. Once with
        # app_settings.CONTEXT_BEHAVIOR set to "django",
        # the other time set to "isolated"
        ...
    ```

    If you need to pass parametrized data to the tests,
    pass a tuple of (mode, data) instead of plain string.
    To access the data as a fixture, add `context_behavior_data`
    as a function argument:
    ```py
    @parametrize_context_behavior([
        ("django", "result for django"),
        ("isolated", "result for isolated"),
    ])
    def test_bla_bla(self, context_behavior_data):
        # Runs this test function twice. Once with
        # app_settings.CONTEXT_BEHAVIOR set to "django",
        # the other time set to "isolated".
        #
        # `context_behavior_data` will first have a value
        # of "result for django", then of "result for isolated"
        print(context_behavior_data)
        ...
    ```

    NOTE: Use only on functions and methods. This decorator was NOT tested on classes
    """

    def decorator(test_func):
        # NOTE: Ideally this decorator would parametrize the test function
        # with `pytest.mark.parametrize`, so all test cases would be treated as separate
        # tests and thus isolated. But I wasn't able to get it to work. Hence,
        # as a workaround, we run multiple test cases within the same test run.
        # Because of this, we need to clear the loader cache, and, on error, we need to
        # propagate the info on which test case failed.
        @functools.wraps(test_func)
        def wrapper(*args, **kwargs):
            for case in cases:
                # Clear loader cache, see https://stackoverflow.com/a/77531127/9788634
                for engine in engines.all():
                    engine.engine.template_loaders[0].reset()

                case_has_data = not isinstance(case, str)

                if isinstance(case, str):
                    context_beh, fixture = case, None
                else:
                    context_beh, fixture = case

                with override_settings(COMPONENTS={"context_behavior": context_beh}):
                    # Call the test function with the fixture as an argument
                    try:
                        if case_has_data:
                            test_func(*args, context_behavior_data=fixture, **kwargs)
                        else:
                            test_func(*args, **kwargs)
                    except Exception as err:
                        # Give a hint on which iteration the test failed
                        raise RuntimeError(
                            f"An error occured in test function '{test_func.__name__}' with"
                            f" context_behavior='{context_beh}'. See the original error above."
                        ) from err

        return wrapper

    return decorator
