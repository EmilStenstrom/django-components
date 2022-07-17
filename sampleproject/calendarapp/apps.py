from django.apps import AppConfig


class CalendarappConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "calendarapp"

    def ready(self):
        from components.calendar import calendar  # NOQA
