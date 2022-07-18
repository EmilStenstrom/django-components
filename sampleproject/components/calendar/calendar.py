from django_components import component


@component.register("calendar")
class Calendar(component.Component):
    # Note that Django will look for templates inside `[your apps]/components` dir and
    # `[project root]/components` dir. To customize which template to use based on context
    # you can override def get_template_name() instead of specifying the below variable.
    template_name = "calendar/calendar.html"

    # This component takes one parameter, a date string to show in the template
    def get_context_data(self, date):
        return {
            "date": date,
        }

    class Media:
        css = "calendar/calendar.css"
        js = "calendar/calendar.js"
