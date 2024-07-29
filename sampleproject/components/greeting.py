from typing import Any, Dict

import django_components as dc


@dc.register("greeting")
class Greeting(dc.Component):
    def get(self, request, *args, **kwargs):
        slots = {"message": "Hello, world!"}
        context = {"name": request.GET.get("name", "")}
        return self.render_to_response(context=context, slots=slots)

    def get_context_data(self, name, *args, **kwargs) -> Dict[str, Any]:
        return {"name": name}

    template: dc.django_html = """
        <div id="greeting">Hello, {{ name }}!</div>
        {% slot "message" %}{% endslot %}
    """

    css: dc.css = """
        #greeting {
            display: inline-block;
            color: blue;
            font-size: 2em;
        }
    """

    js: dc.js = """
        document.getElementById("greeting").addEventListener("click", (event) => {
            alert("Hello!");
        });
    """
