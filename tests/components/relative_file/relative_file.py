from typing import Any, Dict

from django.http import HttpResponse

from django_components import Component, ComponentView, register


@register("relative_file_component")
class RelativeFileComponent(Component):
    template_name = "relative_file.html"

    class Media:
        js = "relative_file.js"
        css = "relative_file.css"

    def get_context_data(self, variable, *args, **kwargs) -> Dict[str, Any]:
        return {"variable": variable}

    class View(ComponentView):
        def get(self, request, *args, **kwargs):
            return self.component.render_to_response({"variable": "GET"})

        def post(self, request, *args, **kwargs) -> HttpResponse:
            variable = request.POST.get("variable")
            return self.component.render_to_response({"variable": variable})
