from typing import Any, Dict

from django.conf import settings
from django.http import HttpResponse
from django.template import Context, Template
from django.test import Client
from django.urls import path

# isort: off
from .django_test_setup import *  # noqa
from .testutils import BaseTestCase, parametrize_context_behavior

# isort: on

from django_components import component


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


class TestComponentAsView(BaseTestCase):
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
                    <input type="text" name="variable" value="{{ inner_var }}">
                    <input type="submit">
                </form>
                """

            def get(self, request, *args, **kwargs) -> HttpResponse:
                return self.render_to_response(kwargs={"variable": "GET"})

            def get_context_data(self, variable):
                return {"inner_var": variable}

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
                    <input type="text" name="variable" value="{{ inner_var }}">
                    <input type="submit">
                </form>
                """

            def post(self, request, *args, **kwargs) -> HttpResponse:
                variable = request.POST.get("variable")
                return self.render_to_response(kwargs={"variable": variable})

            def get_context_data(self, variable):
                return {"inner_var": variable}

        client = CustomClient(urlpatterns=[path("test/", MockComponentRequest.as_view())])
        response = client.post("/test/", {"variable": "POST"})
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            b'<input type="text" name="variable" value="POST">',
            response.content,
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_replace_slot_in_view(self):
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

        client = CustomClient(urlpatterns=[path("test_slot/", MockComponentSlot.as_view())])
        response = client.get("/test_slot/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            b"Hey, I'm Bob",
            response.content,
        )
        self.assertIn(
            b"Nice to meet you, Bob",
            response.content,
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_replace_slot_in_view_with_insecure_content(self):
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

        client = CustomClient(urlpatterns=[path("test_slot_insecure/", MockInsecureComponentSlot.as_view())])
        response = client.get("/test_slot_insecure/")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(
            b"<script>",
            response.content,
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_replace_context_in_view(self):
        class TestComponent(component.Component):
            template = """
                {% load component_tags %}
                <div>
                Hey, I'm {{ name }}
                </div>
                """

            def get(self, request, *args, **kwargs) -> HttpResponse:
                return self.render_to_response({"name": "Bob"})

        client = CustomClient(urlpatterns=[path("test_context_django/", TestComponent.as_view())])
        response = client.get("/test_context_django/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            b"Hey, I'm Bob",
            response.content,
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_replace_context_in_view_with_insecure_content(self):
        class MockInsecureComponentContext(component.Component):
            template = """
                {% load component_tags %}
                <div>
                {{ variable }}
                </div>
                """

            def get(self, request, *args, **kwargs) -> HttpResponse:
                return self.render_to_response({"variable": "<script>alert(1);</script>"})

        client = CustomClient(urlpatterns=[path("test_context_insecure/", MockInsecureComponentContext.as_view())])
        response = client.get("/test_context_insecure/")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(
            b"<script>",
            response.content,
        )
