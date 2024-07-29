from typing import Any, Dict

import django_components as dc


# Used for testing the safer_staticfiles app in `test_safer_staticfiles.py`
@dc.register("safer_staticfiles_component")
class RelativeFileWithPathObjComponent(dc.Component):
    template_name = "safer_staticfiles.html"

    class Media:
        js = "safer_staticfiles.js"
        css = "safer_staticfiles.css"

    def get_context_data(self, variable, *args, **kwargs) -> Dict[str, Any]:
        return {"variable": variable}
