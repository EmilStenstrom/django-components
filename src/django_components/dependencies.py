"""All code related to management of component dependencies (JS and CSS scripts)"""
import re
from abc import ABC, abstractmethod
from functools import lru_cache
from hashlib import md5
from typing import Callable, Dict, Iterable, List, Literal, NamedTuple, Optional, Set, Tuple, Type, TypeVar, Union, cast, TYPE_CHECKING
from weakref import WeakValueDictionary

from asgiref.sync import iscoroutinefunction, markcoroutinefunction
from django.forms import Media
from django.http import HttpRequest, HttpResponse, StreamingHttpResponse, HttpResponseNotFound, HttpResponseNotAllowed
from django.http.response import HttpResponseBase
from django.urls import path, reverse
from django.utils.decorators import sync_and_async_middleware
from django.utils.safestring import mark_safe, SafeString
from django.templatetags.static import static

from django_components.html import parse_node, set_boolean_attribute
from django_components.utils import get_import_path, escape_js_string_literal

if TYPE_CHECKING:
    from django_components.component import Component


ScriptType = Literal['css', 'js']


#########################################################
# 1. Cache the inlined component JS and CSS scripts,
#    so they can be referenced and retrieved later via
#    an ID.
#########################################################

class ComponentMediaCacheABC(ABC):
    @abstractmethod
    def get(self, key: str) -> Optional[str]: ...

    @abstractmethod
    def has(self, key: str) -> bool: ...

    @abstractmethod
    def set(self, key: str, value: str) -> None: ...


class InMemoryComponentMediaCache(ComponentMediaCacheABC):
    def __init__(self) -> None:
        self._data: Dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self._data.get(key, None)

    def has(self, key: str) -> bool:
        return key in self._data

    def set(self, key: str, value: str) -> None:
        self._data[key] = value


comp_media_cache = InMemoryComponentMediaCache()


# NOTE: Initially, we fetched components by their registered name, but that didn't work
# for multiple registries and unregistered components.
#
# To have unique identifiers that works across registries, we rely
# on component class' module import path (e.g. `path.to.my.MyComponent`).
#
# But we also don't want to expose the module import paths to the outside world, as
# that information could be potentially exploited. So, instead, each component is
# associated with a hash that's derived from its module import path, ensuring uniqueness,
# consistency and privacy.
# 
# E.g. `path.to.my.secret.MyComponent` -> `MyComponent_ab01f32`
#
# The associations are defined as WeakValue map, so deleted components can be garbage
# collected and automatically deleted from the dict.
comp_hash_mapping: WeakValueDictionary[str, Type["Component"]] = WeakValueDictionary()


# Convert Component class to something like `TableComp_a91d03`
@lru_cache(None)
def _hash_comp_cls(comp_cls: Type["Component"]) -> str:
    full_name = get_import_path(comp_cls)
    comp_cls_hash = md5(full_name.encode()).hexdigest()[0:6]
    return comp_cls.__name__ + "_" + comp_cls_hash


def _gen_cache_key(
    comp_cls_hash: str,
    script_type: ScriptType,
) -> str:
    return f'__components:{comp_cls_hash}:{script_type}'


def _is_script_in_cache(
    comp_cls: Type["Component"],
    script_type: ScriptType,
) -> bool:
    comp_cls_hash = _hash_comp_cls(comp_cls)
    cache_key = _gen_cache_key(comp_cls_hash, script_type)
    return comp_media_cache.has(cache_key)


def _cache_script(
    comp_cls: Type["Component"],
    script: str,
    script_type: ScriptType,
) -> None:
    """
    Given a component and it's inlined JS or CSS, store the JS/CSS in a cache,
    so it can be retrieved via URL endpoint.
    """
    comp_cls_hash = _hash_comp_cls(comp_cls)

    # E.g. `__components:MyButton:js:df7c6d10`
    if script_type in ("js", "css"):
        cache_key = _gen_cache_key(comp_cls_hash, script_type)
    else:
        raise ValueError(f"Unexpected script_type '{script_type}'")

    # NOTE: By setting the script in the cache, we will be able to retrieve it
    # via the endpoint, e.g. when we make a request to `/components/cache/MyComp_ab0c2d.js`.
    comp_media_cache.set(cache_key, script.strip())


def cache_inlined_js(comp_cls: Type["Component"], content: str) -> None:
    # Prepare the script that's common to all instances of the same component
    # E.g. `my_table.js`
    if not _is_script_in_cache(comp_cls, "js"):
        _cache_script(
            comp_cls=comp_cls,
            script=content,
            script_type="js",
        )


def cache_inlined_css(comp_cls: Type["Component"], content: str) -> None:
    # Prepare the script that's common to all instances of the same component
    if not _is_script_in_cache(comp_cls, "css"):
        # E.g. `my_table.css`
        _cache_script(
            comp_cls=comp_cls,
            script=content,
            script_type="css",
        )


#########################################################
# 2. Modify the HTML to use the same IDs defined in previous
#    step for the inlined CSS and JS scripts, so the scripts
#    can be applied to the correct HTML elements. And embed
#    component + JS/CSS relationships as HTML comments.
#########################################################


class Dependencies(NamedTuple):
    # NOTE: We pass around the component CLASS, so the dependencies logic is not
    # dependent on ComponentRegistries
    component_cls: Type["Component"]
    component_id: str


def _insert_component_comment(
    content: str,
    deps: Dependencies,
) -> str:
    """
    Given some textual content, prepend it with a short string that
    will be used by the ComponentDependencyMiddleware to collect all
    declared JS / CSS scripts.
    """
    # Add components to the cache
    comp_cls_hash = _hash_comp_cls(deps.component_cls)
    comp_hash_mapping[comp_cls_hash] = deps.component_cls

    data = f'{comp_cls_hash},{deps.component_id}'

    # NOTE: It's important that we put the comment BEFORE the content, so we can
    # use the order of comments to evaluate components' instance JS code in the correct order.
    output = COMPONENT_DEPS_COMMENT.format(data=data) + content
    return output


# Anything and everything that needs to be done with a Component's HTML
# script in order to support running JS and CSS per-instance.
def postprocess_component_html(
    component_cls: Type["Component"],
    component_id: str,
    html_content: str,
    render_deps: bool,
) -> str:
    # NOTE: To better understand the next section, consider this:
    #
    # We define and cache the component's JS and CSS at the same time as
    # when we render the HTML. However, the resulting HTML MAY OR MAY NOT
    # be used in another component.
    #
    # IF the component's HTML IS used in another component, and the other
    # component want to render the JS or CSS dependencies (e.g. inside <head>),
    # then it's only at that point when we want to access the data about
    # which JS and CSS scripts is the component's HTML associated with.
    #
    # This happens AFTER the rendering context, so there's no Context to rely on.
    # 
    # Hence, we store the info about associated JS and CSS right in the HTML itself.
    # As an HTML comment `<!-- -->`. Thus, the inner component can be used as many times
    # and in different components, and they will all know to fetch also JS and CSS of the
    # inner components.

    # Mark the generated HTML so that we will know which JS and CSS
    # scripts are associated with it.
    output = _insert_component_comment(
        html_content,
        Dependencies(
            component_cls=component_cls,
            component_id=component_id,
        ),
    )

    if render_deps:
        output = render_dependencies(output, kind="document")

    return output


#########################################################
# 3. Given a FINAL HTML composed of MANY components,
#    process all the HTML dependency comments (created in
#    previous step), obtaining ALL JS and CSS scripts
#    required by this HTML document. And post-process them,
#    so the scripts are either inlined into the HTML, or
#    fetched when the HTML is loaded in the browser.
#########################################################


TContent = TypeVar("TContent", bound=Union[bytes, str])


CSS_DEPENDENCY_PLACEHOLDER = '<link name="CSS_PLACEHOLDER">'
JS_DEPENDENCY_PLACEHOLDER = '<script name="JS_PLACEHOLDER"></script>'

CSS_PLACEHOLDER_BYTES = bytes(CSS_DEPENDENCY_PLACEHOLDER, encoding="utf-8")
JS_PLACEHOLDER_BYTES = bytes(JS_DEPENDENCY_PLACEHOLDER, encoding="utf-8")

COMPONENT_DEPS_COMMENT = "<!-- _RENDERED {data} -->"
# E.g. `<!-- _RENDERED table,123 -->`
COMPONENT_COMMENT_REGEX = re.compile(rb"<!-- _RENDERED (?P<data>[\w\-,/]+?) -->")
# E.g. `table,123`
SCRIPT_NAME_REGEX = re.compile(rb"^(?P<comp_cls_hash>[\w\-\./]+?),(?P<id>[\w]+?)$")
PLACEHOLDER_REGEX = re.compile(
    r'{css_placeholder}|{js_placeholder}'.format(
        css_placeholder=CSS_DEPENDENCY_PLACEHOLDER,
        js_placeholder=JS_DEPENDENCY_PLACEHOLDER,
    ).encode()
)


def render_dependencies(content: TContent, kind: Literal["document"]) -> TContent:
    if isinstance(content, str):
        content_ = content.encode()
    else:
        content_ = cast(bytes, content)

    content_, js_dependencies, css_dependencies = _process_dep_declarations(content_, kind)

    # Replace the placeholders with the actual content
    def on_replace_match(match: "re.Match[bytes]") -> bytes:
        if match[0] == CSS_PLACEHOLDER_BYTES:
            replacement = css_dependencies
        elif match[0] == JS_PLACEHOLDER_BYTES:
            replacement = js_dependencies
        else:
            raise RuntimeError(
                "Unexpected error: Regex for component dependencies processing"
                f" matched unknown string '{match[0].decode()}'"
            )
        return replacement

    content_ = PLACEHOLDER_REGEX.sub(on_replace_match, content_)

    output = content_.decode() if isinstance(content, str) else content_
    return cast(TContent, output)


def _process_dep_declarations(content: bytes, kind: Literal["document"]) -> Tuple[bytes, bytes, bytes]:
    """
    Process a textual content that may include metadata on rendered components.
    The metadata has format like this

    `<!-- _RENDERED component_name,component_id -->`

    E.g.

    `<!-- _RENDERED table_10bac31,123 -->`
    """
    # Extract all matched instances of `<!-- _RENDERED ... -->` while also removing them from the text
    all_parts: List[bytes] = list()
    def on_replace_match(match: "re.Match[bytes]") -> bytes:
        all_parts.append(match.group("data"))
        return b""

    content = COMPONENT_COMMENT_REGEX.sub(on_replace_match, content)

    comp_hashes: Set[str] = set()

    # Process individual parts. Each part is like a CSV row of `name,id`.
    # E.g. something like this:
    # `table_10bac31,1234`
    for part in all_parts:
        part_match = SCRIPT_NAME_REGEX.match(part)

        if not part_match:
            raise RuntimeError("Malformed dependencies data")

        comp_cls_hash = part_match.group("comp_cls_hash").decode("utf-8")
        comp_hashes.add(comp_cls_hash)

    (
        to_load_component_js_urls,
        to_load_component_css_urls,
        inlined_component_js_tags,
        inlined_component_css_tags,
        loaded_component_js_urls,
        loaded_component_css_urls,
    ) = _prepare_tags_and_urls(comp_hashes, kind, omit_scoped_css=True)

    def get_component_media(comp_cls_hash: str) -> Media:
        comp_cls = comp_hash_mapping[comp_cls_hash]
        # NOTE: We instantiate the component classes so the `Media` are processed into `media`
        comp = comp_cls()
        return comp.media

    all_medias = [
        # JS / CSS files from Component.Media.js/css.
        *[get_component_media(comp_cls_hash) for comp_cls_hash in comp_hashes],

        # All the inlined scripts that we plan to fetch / load
        Media(
            js=to_load_component_js_urls,
            css={"all": to_load_component_css_urls},
        ),
    ]

    joint_media = _join_media(all_medias)

    # Once we have ALL JS and CSS URLs that we want to fetch, we can convert them to
    # <script> and <link> tags. Note that this is done by the user-provided Media class.
    to_load_css_tags = list(joint_media.render_css())
    to_load_js_tags = list(joint_media.render_js())

    loaded_css_urls = [
        *loaded_component_css_urls,
        # NOTE: Unlike JS, the initial CSS is loaded outside of the dependency
        # manager, and only marked as loaded, to avoid a flash of unstyled content.
        *[parse_node(tag).attrs['href'] for tag in to_load_css_tags],  # type: ignore[index]
    ]

    exec_script = _gen_exec_script(
        to_load_js_tags=to_load_js_tags,
        to_load_css_tags=to_load_css_tags,
        loaded_js_urls=loaded_component_js_urls,
        loaded_css_urls=loaded_css_urls,
    )

    # Core scripts without which the rest wouldn't work
    core_script_tags = Media(
        js=[static("django_components/django_components.min.js")],
    ).render_js()

    def mark_tag(tag: str) -> str:
        node = parse_node(tag)
        set_boolean_attribute(node, "data-component-dep", True)
        return node.html

    final_script_tags = b"".join([
        *[tag.encode("utf-8") for tag in map(mark_tag, core_script_tags)],
        *[tag.encode("utf-8") for tag in map(mark_tag, inlined_component_js_tags)],
        mark_tag(exec_script).encode("utf-8"),
    ])

    final_css_tags = b"".join([
        *[tag.encode("utf-8") for tag in map(mark_tag, inlined_component_css_tags)],
        # NOTE: Unlike JS, the initial CSS is loaded outside of the dependency
        # manager, and only marked as loaded, to avoid a flash of unstyled content.
        *[tag.encode("utf-8") for tag in map(mark_tag, to_load_css_tags)],
    ])

    return content, final_script_tags, final_css_tags


def _prepare_tags_and_urls(
    data: Iterable[str],
    kind: Literal["document"],
    omit_scoped_css: bool,
) -> Tuple[List[str], List[str], List[str], List[str], List[str], List[str]]:
    to_load_js_urls: List[str] = []
    to_load_css_urls: List[str] = []
    inlined_js_tags: List[str] = []
    inlined_css_tags: List[str] = []
    loaded_js_urls: List[str] = []
    loaded_css_urls: List[str] = []

    # When `kind="document"`, we insert the actual <script> and <style> tags into the HTML.
    # But even in that case we still need to call `Components.manager.markScriptLoaded`,
    # so the client knows NOT to fetch them again.
    # So in that case we populate both `inlined` and `loaded` lists
    for comp_cls_hash in data:
        # NOTE: When CSS is scoped, then EVERY component instance will have different
        # copy of the style, because each copy will have component's ID embedded.
        # So, in that case we inline the style into the HTML (See `_link_dependencies_with_component_html`),
        # which means that we are NOT going to load / inline it again.
        comp_cls = comp_hash_mapping[comp_cls_hash]

        should_skip_css = omit_scoped_css and comp_cls.css_scoped

        if kind == "document":
            inlined_js_tags.append(
                _get_script("js", comp_cls, type="tag")
            )

            if not should_skip_css:
                inlined_css_tags.append(
                    _get_script("css", comp_cls, type="tag")
                )

            loaded_js_urls.append(
                _get_script("js", comp_cls, type="url")
            )
            loaded_css_urls.append(
                _get_script("css", comp_cls, type="url")
            )
        # When NOT a document (AKA is a fragment), then scripts are NOT inserted into
        # the HTML, and instead we fetch and load them all via our JS dependency manager.
        else:
            to_load_js_urls.append(
                _get_script("js", comp_cls, type="url")
            )

            if not should_skip_css:
                to_load_css_urls.append(
                    _get_script("css", comp_cls, type="url")
                )

            # Mark the inlined scoped CSS as already-loaded
            if should_skip_css:
                loaded_css_urls.append(
                    _get_script("css", comp_cls, type="url")
                )
    
    return (
        to_load_js_urls,
        to_load_css_urls,
        inlined_js_tags,
        inlined_css_tags,
        loaded_js_urls,
        loaded_css_urls,
    )


def _get_script(
    script_type: ScriptType,
    comp_cls: Type["Component"],
    type: Literal["url", "tag"],
) -> Union[str, SafeString]:
    comp_cls_hash = _hash_comp_cls(comp_cls)

    if type == "url":
        # NOTE: To make sure that Media object won't modify the URLs, we need to
        # resolve the full path (`/abc/def/etc`), not just the file name.
        script = reverse(CACHE_ENDPOINT_NAME, kwargs={
            "comp_cls_hash": comp_cls_hash,
            "script_type": script_type,
        })
    else:
        cache_key = _gen_cache_key(comp_cls_hash, script_type)
        script = comp_media_cache.get(cache_key)

        if script_type == 'js':
            script = mark_safe(f'<script>{_escape_js(script)}</script>')
        elif script_type == 'css':
            script = mark_safe(f'<style>{script}</style>')
    return script


def _gen_exec_script(
    to_load_js_tags: List[str],
    to_load_css_tags: List[str],
    loaded_js_urls: List[str],
    loaded_css_urls: List[str],
) -> str:
    # Generate JS expression like so:
    # ```js
    # await Promise.all([
    #   Components.manager.loadScript("js", '<script src="/abc/def1">...</script>'),
    #   Components.manager.loadScript("js", '<script src="/abc/def2">...</script>'),
    #   Components.manager.loadScript("js", '<script src="/abc/def3">...</script>'),
    # ]);
    # ```
    #
    # or
    #
    # ```js
    # await Promise.all([
    #   Components.manager.markScriptLoaded("css", "/abc/def1"),
    #   Components.manager.markScriptLoaded("css", "/abc/def2"),
    #   Components.manager.markScriptLoaded("css", "/abc/def3"),
    # ]);
    # ```
    #
    # NOTE: It would be better to pass only the URL itself for `loadScript`, instead of a whole tag.
    # But because we allow users to specify the Media class, and thus users can
    # configure how the `<link>` or `<script>` tags are rendered, we need pass the whole tag.
    def gen_loader_expr(
        script_type: ScriptType,
        loaded_urls: List[str],
        to_load_tags: List[str],
    ) -> str:
        loaded_expr_parts: List[str] = []
        for url in loaded_urls:
            loaded_expr_parts.append(f"""
                Components.manager.markScriptLoaded("{script_type}", "{url}");
            """)
        loaded_exprs = '\n'.join(loaded_expr_parts)

        to_load_expr_parts: List[str] = []
        for tag in to_load_tags:
            to_load_expr_parts.append(f"""
                Components.manager.loadScript(
                    "{script_type}",
                    {_escape_js(tag, eval=False)},
                ),
            """)
        to_load_exprs = '\n'.join(to_load_expr_parts)

        # NOTE: We must NOT await for this Promise, otherwise we create a deadlock
        # where the script loaded with `loadScript` (loadee) is inserted AFTER the script with `loadScript` (loader).
        # But the loader will NOT finish, because it's waiting for loadee, which cannot start before loader ends.
        return f"""
            {loaded_exprs}
            Promise.all([
                {to_load_exprs}
            ]).catch(console.error);
        """

    exec_script = "\n".join([
        # We load all the JS and CSS files from `Media.js/css` in parallel
        # using the `await Promise.all(...)`.
        # We are assuming that they don't have to wait for each other.
        gen_loader_expr("js", loaded_js_urls, to_load_js_tags),
        "",
        gen_loader_expr("css", loaded_css_urls, to_load_css_tags),
        "",
    ])

    # Wrap script body in <script> tags and self-executing async function
    exec_script = _escape_js(f"""
    (async () => {{
        {exec_script}
    }})();
    """)
    exec_script = f"<script>{exec_script}</script>"

    return exec_script


def _join_media(medias: Iterable[Media]) -> Media:
    """Return combined media object for iterable of components."""
    # NOTE: It is possible to use `sum()` because Media class overrides the addition
    # operation (`__add__`). And `sum()` effective does `reduce(lambda a, b: a + b)`.
    return sum(medias, Media())


def _escape_js(js: str, eval: bool = True) -> str:
    escaped_js = escape_js_string_literal(js)
    # `unescapeJs` is the function we call in the browser to parse the escaped JS
    escaped_js = f"Components.unescapeJs(`{escaped_js}`)"
    return f"eval({escaped_js})" if eval else escaped_js


#########################################################
# 4. Endpoints for fetching the JS / CSS scripts from within
#    the browser, as defined from previous steps.
#########################################################


CACHE_ENDPOINT_NAME = "components_cached_script"
_CONTENT_TYPES = {
    "js": "text/javascript",
    "css": "text/css"
}


def _get_content_types(script_type: ScriptType) -> str:
    if script_type not in _CONTENT_TYPES:
        raise ValueError(f"Unknown script_type '{script_type}'")
    
    return _CONTENT_TYPES[script_type]


def cached_script_view(
    req: HttpRequest,
    comp_cls_hash: str,
    script_type: ScriptType,
) -> HttpResponse:
    if req.method != "GET":
        return HttpResponseNotAllowed(["GET"])

    # Otherwise check if the file is among the dynamically generated files in the cache
    cache_key = _gen_cache_key(comp_cls_hash, script_type)
    script = comp_media_cache.get(cache_key)

    if script is None:
        return HttpResponseNotFound()

    content_type = _get_content_types(script_type)
    return HttpResponse(content=script, content_type=content_type)


urlpatterns = [
    # E.g. `/components/cache/table.js/`
    path("cache/<str:comp_cls_hash>.<str:script_type>/", cached_script_view, name=CACHE_ENDPOINT_NAME),
]


#########################################################
# 5. Middleware that automatically applies the dependency-
#    aggregating logic on all HTML responses.
#########################################################


@sync_and_async_middleware
class ComponentDependencyMiddleware:
    """
    Middleware that inserts CSS/JS dependencies for all rendered
    components at points marked with template tags.
    """

    def __init__(self, get_response: "Callable[[HttpRequest], HttpResponse]") -> None:
        self.get_response = get_response

        # NOTE: Required to work with async
        if iscoroutinefunction(self.get_response):
            markcoroutinefunction(self)

    def __call__(self, request: HttpRequest) -> HttpResponseBase:
        if iscoroutinefunction(self):
            return self.__acall__(request)

        response = self.get_response(request)
        response = self.process_response(response)
        return response

    # NOTE: Required to work with async
    async def __acall__(self, request: HttpRequest) -> HttpResponseBase:
        response = await self.get_response(request)
        response = self.process_response(response)
        return response

    def process_response(self, response: HttpResponse) -> HttpResponse:
        if (
            not isinstance(response, StreamingHttpResponse)
            and response.get("Content-Type", "").startswith("text/html")
        ):
            response.content = render_dependencies(response.content, kind="document")

        return response
