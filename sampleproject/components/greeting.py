from django_components import component


@component.register("greeting")
class greeting(component.Component):
    def get_context_data(self, greet, *args, **kwargs):
        return {"greet": greet}

    template = """
        <div id="greeting">{{ greet }}</div>
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
