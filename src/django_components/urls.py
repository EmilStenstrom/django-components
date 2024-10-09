from django.urls import include, path

urlpatterns = [
    path("components/", include("django_components.dependencies")),
]
