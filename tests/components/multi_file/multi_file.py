from typing import Any, Dict

from django.http import HttpResponse

from django_components import Component, register


@register("multi_file_component")
class MultFileComponent(Component):
    template_name = "multi_file/multi_file.html"

    def post(self, request, *args, **kwargs) -> HttpResponse:
        variable = request.POST.get("variable")
        return self.render_to_response({"variable": variable})

    def get(self, request, *args, **kwargs) -> HttpResponse:
        return self.render_to_response({"variable": "GET"})

    def get_context_data(self, variable, *args, **kwargs) -> Dict[str, Any]:
        return {"variable": variable}
