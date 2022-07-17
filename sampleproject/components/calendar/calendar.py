from django_components import component


@component.register("calendar")
class Calendar(component.Component):
    # Note that Django will look for templates inside `[your app]/components` dir
    # To customize which template to use based on context override get_template_name instead
    template_name = "calendar/calendar.html"

    # This component takes one parameter, a date string to show in the template
    def get_context_data(self, date):
        return {
            "date": date,
        }

    class Media:
        css = "calendarapp/components/calendar/calendar.css"
        js = "calendarapp/components/calendar/calendar.js"
