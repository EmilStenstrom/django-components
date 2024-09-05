from django_components import Component, register


@register("calendar")
class Calendar(Component):
    # Templates inside `[your apps]/components` dir and `[project root]/components` dir
    # will be automatically found.
    #
    # `template_name` can be relative to dir where `calendar.py` is, or relative to COMPONENTS.dirs
    template_name = "calendar/calendar.html"
    # Or
    # def get_template_name(context):
    #     return f"template-{context['name']}.html"

    # This component takes one parameter, a date string to show in the template
    def get_context_data(self, date):
        return {
            "date": date,
        }

    def get(self, request, *args, **kwargs):
        return self.render_to_response(
            kwargs={
                "date": request.GET.get("date", ""),
            },
        )

    class Media:
        css = "calendar/calendar.css"
        js = "calendar/calendar.js"


@register("calendar_relative")
class CalendarRelative(Component):
    # Templates inside `[your apps]/components` dir and `[project root]/components` dir
    # will be automatically found.
    #
    # `template_name` can be relative to dir where `calendar.py` is, or relative to COMPONENTS.dirs
    template_name = "calendar.html"
    # Or
    # def get_template_name(context):
    #     return f"template-{context['name']}.html"

    # This component takes one parameter, a date string to show in the template
    def get_context_data(self, date):
        return {
            "date": date,
        }

    def get(self, request, *args, **kwargs):
        context = {
            "date": request.GET.get("date", ""),
        }
        return self.render_to_response(context)

    class Media:
        css = "calendar.css"
        js = "calendar.js"
