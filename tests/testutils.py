from unittest.mock import Mock

from django.template import Template, Context
from django.template.response import TemplateResponse
from django.test import SimpleTestCase, TestCase

from django_components.middleware import ComponentDependencyMiddleware

# Create middleware instance.  get_response function is not used, so pass a do-nothing lambda
middleware = ComponentDependencyMiddleware(get_response=lambda _: None)


class Django30CompatibleSimpleTestCase(SimpleTestCase):
    def assertHTMLEqual(self, left, right):
        left = left.replace(' type="text/javascript"', '')
        super(Django30CompatibleSimpleTestCase, self).assertHTMLEqual(left, right)


class Django30CompatibleTestCase(TestCase):
    def assertHTMLEqual(self, left, right):
        left = left.replace(' type="text/javascript"', '')
        super(Django30CompatibleTestCase, self).assertHTMLEqual(left, right)


def create_and_process_template_response(template, context=None):
    request = Mock()
    mock_template = Mock()
    mock_template.render = lambda context, _: template.render(context)
    context = context or Context({})
    response = TemplateResponse(request, mock_template, context)
    middleware.process_template_response(request, response)
    response.render()
    return response