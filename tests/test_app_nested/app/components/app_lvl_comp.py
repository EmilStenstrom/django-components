from typing import Any, Dict

from django_components import Component, register


# Used for testing the template_loader
@register("nested_app_lvl_comp")
class AppLvlCompComponent(Component):
    template = """
        {{ variable }}
    """

    def get_context_data(self, variable, *args, **kwargs) -> Dict[str, Any]:
        return {"variable": variable}
