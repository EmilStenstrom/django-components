from components.calendar.calendar import Calendar, CalendarRelative
from components.greeting import Greeting
from django.urls import path

urlpatterns = [
    path("greeting/", Greeting.as_view(), name="greeting"),
    path("calendar/", Calendar.as_view(), name="calendar"),
    path("calendar-relative/", CalendarRelative.as_view(), name="calendar-relative"),
]
