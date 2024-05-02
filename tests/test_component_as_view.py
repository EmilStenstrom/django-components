from typing import Any, Dict

from django.http import HttpResponse
from django.template import Context, Template
from django.test import Client
from django.urls import include, path

# isort: off
from .django_test_setup import *  # noqa
from .testutils import BaseTestCase

# isort: on

from django_components import component

#########################
# COMPONENTS
#########################

class MockComponentSlot(component.Component):
    template = """
        {% load component_tags %}
        <div>
        {% slot "first_slot" %}
            Hey, I'm {{ name }}
        {% endslot %}
        {% slot "second_slot" %}
        {% endslot %}
        </div>
        """

    def get(self, request, *args, **kwargs) -> HttpResponse:
        return self.render_to_response({"name": "Bob"}, {"second_slot": "Nice to meet you, Bob"})


class MockInsecureComponentContext(component.Component):
    template = """
        {% load component_tags %}
        <div>
        {{ variable }}
        </div>
        """

    def get(self, request, *args, **kwargs) -> HttpResponse:
        return self.render_to_response({"variable": "<script>alert(1);</script>"})


class MockInsecureComponentSlot(component.Component):
    template = """
        {% load component_tags %}
        <div>
        {% slot "test_slot" %}
        {% endslot %}
        </div>
        """

    def get(self, request, *args, **kwargs) -> HttpResponse:
        return self.render_to_response({}, {"test_slot": "<script>alert(1);</script>"})


components_urlpatterns = [
    path("test_slot/", MockComponentSlot.as_view()),
    path("test_context_insecure/", MockInsecureComponentContext.as_view()),
    path("test_slot_insecure/", MockInsecureComponentSlot.as_view()),
]


urlpatterns = [
    path("", include(components_urlpatterns)),
]


class CustomClient(Client):
    def __init__(self, urlpatterns=None, *args, **kwargs):
        import types
        if urlpatterns:
            urls_module = types.ModuleType("urls")
            urls_module.urlpatterns = urlpatterns  # type: ignore
            settings.ROOT_URLCONF = urls_module
        else:
            settings.ROOT_URLCONF = __name__
        settings.SECRET_KEY = "secret"  # noqa
        super().__init__(*args, **kwargs)


#########################
# TESTS
#########################


class TestComponentAsView(BaseTestCase):
    @classmethod
    def setUpClass(self):
        component.registry.register("testcomponent_slot", MockComponentSlot)
        component.registry.register("testcomponent_context_insecure", MockInsecureComponentContext)
        component.registry.register("testcomponent_slot_insecure", MockInsecureComponentSlot)

    def setUp(self):
        self.client = CustomClient()

    def test_render_component_from_template(self):
        @component.register("testcomponent")
        class MockComponentRequest(component.Component):
            template = """
                <form method="post">
                    {% csrf_token %}
                    <input type="text" name="variable" value="{{ variable }}">
                    <input type="submit">
                </form>
                """

            def post(self, request, *args, **kwargs) -> HttpResponse:
                variable = request.POST.get("variable")
                return self.render_to_response({"variable": variable})

            def get(self, request, *args, **kwargs) -> HttpResponse:
                return self.render_to_response({"variable": "GET"})

            def get_context_data(self, variable, *args, **kwargs) -> Dict[str, Any]:
                return {"variable": variable}

        def render_template_view(request):
            template = Template(
                """
                {% load component_tags %}
                {% component "testcomponent" variable="TEMPLATE" %}{% endcomponent %}
                """
            )
            return HttpResponse(template.render(Context({})))

        client = CustomClient(urlpatterns=[path("test_template/", render_template_view)])
        response = client.get("/test_template/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            b'<input type="text" name="variable" value="TEMPLATE">',
            response.content,
        )

    def test_get_request(self):
        class MockComponentRequest(component.Component):
            template = """
                <form method="post">
                    {% csrf_token %}
                    <input type="text" name="variable" value="{{ variable }}">
                    <input type="submit">
                </form>
                """

            def get(self, request, *args, **kwargs) -> HttpResponse:
                return self.render_to_response({"variable": "GET"})

            def get_context_data(self, variable, *args, **kwargs) -> Dict[str, Any]:
                return {"variable": variable}

        client = CustomClient(urlpatterns=[path("test/", MockComponentRequest.as_view())])
        response = client.get("/test/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            b'<input type="text" name="variable" value="GET">',
            response.content,
        )

    def test_post_request(self):
        class MockComponentRequest(component.Component):
            template = """
                <form method="post">
                    {% csrf_token %}
                    <input type="text" name="variable" value="{{ variable }}">
                    <input type="submit">
                </form>
                """

            def post(self, request, *args, **kwargs) -> HttpResponse:
                variable = request.POST.get("variable")
                return self.render_to_response({"variable": variable})

            def get_context_data(self, variable, *args, **kwargs) -> Dict[str, Any]:
                return {"variable": variable}

        client = CustomClient(urlpatterns=[path("test/", MockComponentRequest.as_view())])
        response = client.post("/test/", {"variable": "POST"})
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            b'<input type="text" name="variable" value="POST">',
            response.content,
        )

    def test_replace_slot_in_view(self):
        response = self.client.get("/test_slot/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            b"Hey, I'm Bob",
            response.content,
        )
        self.assertIn(
            b"Nice to meet you, Bob",
            response.content,
        )

    def test_replace_slot_in_view_with_insecure_content(self):
        response = self.client.get("/test_slot_insecure/")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(
            b"<script>",
            response.content,
        )

    def test_replace_context_in_view_with_insecure_content(self):
        response = self.client.get("/test_context_insecure/")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(
            b"<script>",
            response.content,
        )
