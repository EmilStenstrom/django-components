from calendarapp.views import calendar
from django.urls import path

from components.greeting import Greeting

urlpatterns = [
    path("", calendar, name="calendar"),
    path("greeting/", Greeting.as_view(), name="calendar"),
]
