from django.urls import include, path
from django.http import HttpResponse

from testserver.views import single_component_view, multiple_components_view

urlpatterns = [
    path("single/", single_component_view, name="single"),
    path("multi/", multiple_components_view, name="multi"),
    path("", include('django_components.urls')),
    # Empty response with status 200 to notify other systems when the server has started
    path("poll/", lambda *args, **kwargs: HttpResponse("")),
]
