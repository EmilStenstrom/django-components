from django.urls import path
from greeting import Greeting

urlpatterns = [
    path("greeting/", Greeting.as_view(), name="greeting"),
]
