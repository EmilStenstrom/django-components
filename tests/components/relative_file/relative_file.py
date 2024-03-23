from typing import Any, Dict

from django.http import HttpResponse

from django_components import component


@component.register("relative_file_component")
class RelativeFileComponent(component.Component):
    template_name = "relative_file.html"

    class Media:
        js = "relative_file.js"
        css = "relative_file.css"

    def post(self, request, *args, **kwargs) -> HttpResponse:
        variable = request.POST.get("variable")
        return self.render_to_response({"variable": variable})

    def get(self, request, *args, **kwargs) -> HttpResponse:
        return self.render_to_response({"variable": "GET"})

    def get_context_data(self, variable, *args, **kwargs) -> Dict[str, Any]:
        return {"variable": variable}
