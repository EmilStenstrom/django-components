from django_components import component

@component.register("comp1")
class Comp1Component(component.Component):
    template_name = "comp1/comp1.html"

    def get_context_data(self, date):
        return {
        }

    class Media:
        css = "comp1/style.css"
        js = "comp1/script.js"