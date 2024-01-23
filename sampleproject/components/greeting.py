from typing import Any, Dict

from django.http import HttpResponse

from django_components import component


@component.register("greeting")
class Greeting(component.Component):
    def get(self, request, *args, **kwargs):
        slots = {"message": "Hello, world!"}
        context = {"name": request.GET.get("name", "")}
        rendered_component = self.render(
            context_data=context, slots_data=slots
        )
        return HttpResponse(rendered_component)

    def get_context_data(self, name, *args, **kwargs) -> Dict[str, Any]:
        return {"name": name}

    template = """
        <div id="greeting">Hello, {{ name }}!</div>
        {% slot "message" %}{% endslot %}
    """

    css = """
        #greeting {
            display: inline-block;
            color: blue;
            font-size: 2em;
        }
    """

    js = """
        document.getElementById("greeting").addEventListener("click", (event) => {
            alert("Hello!");
        });
    """
