from typing import Any, Dict

from django_components import component


# Used for testing the safer_staticfiles app in `test_safer_staticfiles.py`
@component.register("safer_staticfiles_component")
class RelativeFileWithPathObjComponent(component.Component):
    template_name = "safer_staticfiles.html"

    class Media:
        js = "safer_staticfiles.js"
        css = "safer_staticfiles.css"

    def get_context_data(self, variable, *args, **kwargs) -> Dict[str, Any]:
        return {"variable": variable}
