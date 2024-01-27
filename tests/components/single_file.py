from typing import Any, Dict

from django.http import HttpResponse

from django_components import component


@component.register("single_file_component")
class SingleFileComponent(component.Component):
    template = """
        <form method="post">
            {% csrf_token %}
            <input type="text" name="variable" value="{{ variable }}">
            <input type="submit">
        </form>
        """

    def post(self, request, *args, **kwargs) -> HttpResponse:
        variable = request.POST.get("variable")
        return self.render_to_response({"variable": variable})

    def get(self, request, *args, **kwargs) -> HttpResponse:
        return self.render_to_response({"variable": "GET"})

    def get_context_data(self, variable, *args, **kwargs) -> Dict[str, Any]:
        return {"variable": variable}
