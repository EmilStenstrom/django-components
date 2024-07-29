from typing import Any, Dict

from django.templatetags.static import static
from django.utils.html import format_html, html_safe

import django_components as dc


# Format as mentioned in https://github.com/EmilStenstrom/django-components/issues/522#issuecomment-2173577094
@html_safe
class PathObj:
    def __init__(self, static_path: str) -> None:
        self.static_path = static_path
        self.throw_on_calling_str = True

    def __str__(self):
        # This error will notify us when we've hit __str__ when we shouldn't have
        if self.throw_on_calling_str:
            raise RuntimeError("__str__ method of 'relative_file_pathobj_component' was triggered when not allow to")

        return format_html('<script type="module" src="{}"></script>', static(self.static_path))


@dc.register("relative_file_pathobj_component")
class RelativeFileWithPathObjComponent(dc.Component):
    template_name = "relative_file_pathobj.html"

    class Media:
        js = PathObj("relative_file_pathobj.js")
        css = PathObj("relative_file_pathobj.css")

    def get_context_data(self, variable, *args, **kwargs) -> Dict[str, Any]:
        return {"variable": variable}
