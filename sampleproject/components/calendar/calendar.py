from django_components import Component, ComponentView, register


@register("calendar")
class Calendar(Component):
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

    class View(ComponentView):
        def get(self, request, *args, **kwargs):
            context = {
                "date": request.GET.get("date", ""),
            }
            return self.component.render_to_response(context)



@register("calendar_relative")
class CalendarRelative(Component):
    # Note that Django will look for templates inside `[your apps]/components` dir and
    # `[project root]/components` dir. To customize which template to use based on context
    # you can override def get_template_name() instead of specifying the below variable.
    template_name = "calendar.html"

    # This component takes one parameter, a date string to show in the template
    def get_context_data(self, date):
        return {
            "date": date,
        }

    class Media:
        css = "calendar.css"
        js = "calendar.js"

    class View(ComponentView):
        def get(self, request, *args, **kwargs):
            context = {
                "date": request.GET.get("date", ""),
            }
            return self.component.render_to_response(context)

