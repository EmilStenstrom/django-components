from typing import Any, Dict

from django.http import HttpResponse

from django_components import component


@component.register("greeting")
class Greeting(component.Component):
    def get(self, request, *args, **kwargs):
        context = self.get_context_data(request, *args, **kwargs)
        rendered_component = self.render(context)
        return HttpResponse(rendered_component)

    def get_context_data(self, request=None, **kwargs) -> Dict[str, Any]:
        if request:
            name = request.GET.get("name", "") if request else ""
        else:
            name = kwargs.get("name", "")
        return {"name": name}

    template = """
        <div id="greeting">Hello, {{ name }}!</div>
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
