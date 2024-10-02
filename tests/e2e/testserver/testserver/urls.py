from django.http import HttpResponse
from django.urls import include, path
from testserver.views import multiple_components_view, single_component_view

urlpatterns = [
    path("single/", single_component_view, name="single"),
    path("multi/", multiple_components_view, name="multi"),
    path("", include("django_components.urls")),
    # Empty response with status 200 to notify other systems when the server has started
    path("poll/", lambda *args, **kwargs: HttpResponse("")),
]
