import re
from collections.abc import Callable
from typing import TYPE_CHECKING, Iterable

from asgiref.sync import iscoroutinefunction, markcoroutinefunction
from django.conf import settings
from django.forms import Media
from django.http import HttpRequest, HttpResponse, StreamingHttpResponse
from django.http.response import HttpResponseBase
from django.utils.decorators import sync_and_async_middleware

from django_components.component_registry import registry

if TYPE_CHECKING:
    from django_components.component import Component

RENDERED_COMPONENTS_CONTEXT_KEY = "_COMPONENT_DEPENDENCIES"
CSS_DEPENDENCY_PLACEHOLDER = '<link name="CSS_PLACEHOLDER">'
JS_DEPENDENCY_PLACEHOLDER = '<script name="JS_PLACEHOLDER"></script>'

SCRIPT_TAG_REGEX = re.compile("<script")
COMPONENT_COMMENT_REGEX = re.compile(rb"<!-- _RENDERED (?P<name>[\w\-/]+?) -->")
PLACEHOLDER_REGEX = re.compile(
    rb"<!-- _RENDERED (?P<name>[\w\-/]+?) -->"
    rb'|<link name="CSS_PLACEHOLDER">'
    rb'|<script name="JS_PLACEHOLDER"></script>'
)


@sync_and_async_middleware
class ComponentDependencyMiddleware:
    """Middleware that inserts CSS/JS dependencies for all rendered components at points marked with template tags."""

    dependency_regex = COMPONENT_COMMENT_REGEX

    def __init__(self, get_response: "Callable[[HttpRequest], HttpResponse]") -> None:
        self.get_response = get_response

        if iscoroutinefunction(self.get_response):
            markcoroutinefunction(self)

    def __call__(self, request: HttpRequest) -> HttpResponseBase:

        if iscoroutinefunction(self):
            return self.__acall__(request)

        response = self.get_response(request)
        response = self.process_response(response)
        return response

    async def __acall__(self, request: HttpRequest) -> HttpResponseBase:

        response = await self.get_response(request)
        response = self.process_response(response)
        return response

    def process_response(self, response: HttpResponse) -> HttpResponse:
        if (
            getattr(settings, "COMPONENTS", {}).get("RENDER_DEPENDENCIES", False)
            and not isinstance(response, StreamingHttpResponse)
            and response.get("Content-Type", "").startswith("text/html")
        ):
            response.content = process_response_content(response.content)

        return response


def process_response_content(content: bytes) -> bytes:
    component_names_seen = {match.group("name") for match in COMPONENT_COMMENT_REGEX.finditer(content)}
    all_components = [registry.get(name.decode("utf-8"))("") for name in component_names_seen]
    all_media = join_media(all_components)
    js_dependencies = b"".join(media.encode("utf-8") for media in all_media.render_js())
    css_dependencies = b"".join(media.encode("utf-8") for media in all_media.render_css())
    return PLACEHOLDER_REGEX.sub(DependencyReplacer(css_dependencies, js_dependencies), content)


def add_module_attribute_to_scripts(scripts: str) -> str:
    return re.sub(SCRIPT_TAG_REGEX, '<script type="module"', scripts)


class DependencyReplacer:
    """Replacer for use in re.sub that replaces the first placeholder CSS and JS
    tags it encounters and removes any subsequent ones."""

    CSS_PLACEHOLDER = bytes(CSS_DEPENDENCY_PLACEHOLDER, encoding="utf-8")
    JS_PLACEHOLDER = bytes(JS_DEPENDENCY_PLACEHOLDER, encoding="utf-8")

    def __init__(self, css_string: bytes, js_string: bytes) -> None:
        self.js_string = js_string
        self.css_string = css_string

    def __call__(self, match: "re.Match[bytes]") -> bytes:
        if match[0] == self.CSS_PLACEHOLDER:
            replacement, self.css_string = self.css_string, b""
        elif match[0] == self.JS_PLACEHOLDER:
            replacement, self.js_string = self.js_string, b""
        else:
            replacement = b""
        return replacement


def join_media(components: Iterable["Component"]) -> Media:
    """Return combined media object for iterable of components."""

    return sum([component.media for component in components], Media())


def is_dependency_middleware_active() -> bool:
    return getattr(settings, "COMPONENTS", {}).get("RENDER_DEPENDENCIES", False)
