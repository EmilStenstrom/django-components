from unittest.mock import Mock

from django.template import Context
from django.template.response import TemplateResponse
from django.test import SimpleTestCase, TestCase

from django_components.middleware import ComponentDependencyMiddleware

# Create middleware instance
response_stash = None
middleware = ComponentDependencyMiddleware(
    get_response=lambda _: response_stash
)


class Django30CompatibleSimpleTestCase(SimpleTestCase):
    def assertHTMLEqual(self, left, right):
        left = left.replace(' type="text/javascript"', "")
        left = left.replace(' type="text/css"', "")
        right = right.replace(' type="text/javascript"', "")
        right = right.replace(' type="text/css"', "")
        super(Django30CompatibleSimpleTestCase, self).assertHTMLEqual(
            left, right
        )

    def assertInHTML(self, needle, haystack, count=None, msg_prefix=""):
        haystack = haystack.replace(' type="text/javascript"', "")
        haystack = haystack.replace(' type="text/css"', "")
        super().assertInHTML(needle, haystack, count, msg_prefix)


class Django30CompatibleTestCase(Django30CompatibleSimpleTestCase, TestCase):
    pass


request = Mock()
mock_template = Mock()


def create_and_process_template_response(
    template, context=None, use_middleware=True
):
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
