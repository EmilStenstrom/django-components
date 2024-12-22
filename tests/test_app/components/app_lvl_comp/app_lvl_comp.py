from typing import Any, Dict

from django_components import Component, register


# Used for testing the template_loader
@register("app_lvl_comp")
class AppLvlCompComponent(Component):
    template_name = "app_lvl_comp.html"
    js_file = "app_lvl_comp.js"
    css_file = "app_lvl_comp.css"

    class Media:
        js = "app_lvl_comp.js"
        css = "app_lvl_comp.css"

    def get_context_data(self, variable, *args, **kwargs) -> Dict[str, Any]:
        return {"variable": variable}
