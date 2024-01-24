from calendarapp.views import calendar
from django.urls import path

urlpatterns = [
    path("", calendar, name="calendar"),
]
