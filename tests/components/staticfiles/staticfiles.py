from typing import Any, Dict

from django_components import Component, register


# Used for testing the staticfiles finder in `test_staticfiles.py`
@register("staticfiles_component")
class RelativeFileWithPathObjComponent(Component):
    template_file = "staticfiles.html"

    class Media:
        js = "staticfiles.js"
        css = "staticfiles.css"

    def get_context_data(self, variable, *args, **kwargs) -> Dict[str, Any]:
        return {"variable": variable}
