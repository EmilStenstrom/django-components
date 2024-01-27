from django.urls import path

from tests.components.multi_file.multi_file import MultFileComponent
from tests.components.single_file import SingleFileComponent

urlpatterns = [
    path("single/", SingleFileComponent.as_view(), name="single"),
    path("multi/", MultFileComponent.as_view(), name="multi"),
]
