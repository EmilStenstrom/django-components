from typing import Any, Dict

from django.http import HttpResponse

from django_components import Component, ComponentView, register, types


@register("single_file_component")
class SingleFileComponent(Component):
    template: types.django_html = """
        <form method="post">
            {% csrf_token %}
            <input type="text" name="variable" value="{{ variable }}">
            <input type="submit">
        </form>
        """

    def get_context_data(self, variable, *args, **kwargs) -> Dict[str, Any]:
        return {"variable": variable}

    class View(ComponentView):
        def get(self, request, *args, **kwargs):
            return self.component.render_to_response({"variable": "GET"})

        def post(self, request, *args, **kwargs) -> HttpResponse:
            variable = request.POST.get("variable")
            return self.component.render_to_response({"variable": variable})
