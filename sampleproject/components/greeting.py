from typing import Any, Dict

from django_components import Component, ComponentView, register, types


@register("greeting")
class Greeting(Component):
    def get_context_data(self, name, *args, **kwargs) -> Dict[str, Any]:
        return {"name": name}

    template: types.django_html = """
        <div id="greeting">Hello, {{ name }}!</div>
        {% slot "message" %}{% endslot %}
    """

    css: types.css = """
        #greeting {
            display: inline-block;
            color: blue;
            font-size: 2em;
        }
    """

    js: types.js = """
        document.getElementById("greeting").addEventListener("click", (event) => {
            alert("Hello!");
        });
    """

    class View(ComponentView):
        def get(self, request, *args, **kwargs):
            slots = {"message": "Hello, world!"}
            context = {"name": request.GET.get("name", "")}
            return self.component.render_to_response(context=context, slots=slots)
