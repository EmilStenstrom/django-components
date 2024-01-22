from calendarapp.views import calendar
from components.greeting import Greeting
from django.urls import path

urlpatterns = [
    path("", calendar, name="calendar"),
    path("greeting/", Greeting.as_view(), name="calendar"),
]
