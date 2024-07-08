import inspect
import types
from typing import Any, ClassVar, Dict, List, Mapping, Optional, Tuple, Type, Union

from django.core.exceptions import ImproperlyConfigured
from django.forms.widgets import Media
from django.http import HttpResponse
from django.template.base import FilterExpression, Node, NodeList, Template, TextNode
from django.template.context import Context
from django.template.exceptions import TemplateSyntaxError
from django.template.loader import get_template
from django.template.loader_tags import BLOCK_CONTEXT_KEY
from django.utils.html import conditional_escape
from django.utils.safestring import SafeString, mark_safe
from django.views import View

from django_components.component_media import ComponentMediaInput, MediaMeta

# Global registry var and register() function moved to separate module.
# Defining them here made little sense, since 1) component_tags.py and component.py
# rely on them equally, and 2) it made it difficult to avoid circularity in the
# way the two modules depend on one another.
from django_components.component_registry import AlreadyRegistered as AlreadyRegistered  # NOQA
from django_components.component_registry import ComponentRegistry as ComponentRegistry  # NOQA
from django_components.component_registry import NotRegistered as NotRegistered  # NOQA
from django_components.component_registry import register as register  # NOQA
from django_components.component_registry import registry  # NOQA
from django_components.context import (
    _FILLED_SLOTS_CONTENT_CONTEXT_KEY,
    _PARENT_COMP_CONTEXT_KEY,
    _ROOT_CTX_CONTEXT_KEY,
    get_injected_context_var,
    make_isolated_context_copy,
    prepare_context,
)
from django_components.expression import safe_resolve_dict, safe_resolve_list
from django_components.logger import trace_msg
from django_components.middleware import is_dependency_middleware_active
from django_components.slots import (
    DEFAULT_SLOT_KEY,
    FillContent,
    FillNode,
    SlotContent,
    SlotName,
    SlotRef,
    SlotRenderedContent,
    _nodelist_to_slot_render_func,
    resolve_slots,
)
from django_components.template_parser import process_aggregate_kwargs
from django_components.utils import gen_id

RENDERED_COMMENT_TEMPLATE = "<!-- _RENDERED {name} -->"


class ComponentMeta(MediaMeta):
    def __new__(mcs, name: str, bases: Tuple[Type, ...], attrs: Dict[str, Any]) -> Type:
        # NOTE: Skip template/media file resolution when then Component class ITSELF
        # is being created.
        if "__module__" in attrs and attrs["__module__"] == "django_components.component":
            return super().__new__(mcs, name, bases, attrs)

        return super().__new__(mcs, name, bases, attrs)


class Component(View, metaclass=ComponentMeta):
    # Either template_name or template must be set on subclass OR subclass must implement get_template() with
    # non-null return.
    _class_hash: ClassVar[int]

    template_name: ClassVar[Optional[str]] = None
    """Relative filepath to the Django template associated with this component."""
    template: Optional[str] = None
    """Inlined Django template associated with this component."""
    js: Optional[str] = None
    """Inlined JS associated with this component."""
    css: Optional[str] = None
    """Inlined CSS associated with this component."""
    media: Media
    """
    Normalized definition of JS and CSS media files associated with this component.

    NOTE: This field is generated from Component.Media class.
    """
    media_class: Media = Media
    response_class = HttpResponse
    """This allows to configure what class is used to generate response from `render_to_response`"""

    Media = ComponentMediaInput
    """Defines JS and CSS media files associated with this component."""

    def __init__(
        self,
        registered_name: Optional[str] = None,
        component_id: Optional[str] = None,
        outer_context: Optional[Context] = None,
        fill_content: Optional[Dict[str, FillContent]] = None,
    ):
        self.registered_name: Optional[str] = registered_name
        self.outer_context: Context = outer_context or Context()
        self.fill_content = fill_content or {}
        self.component_id = component_id or gen_id()
        self._context: Optional[Context] = None

        # When user first instantiates the component class before calling
        # `render` or `render_to_response`, then we want to allow the render
        # function to make use of the instantiated object.
        #
        # So while `MyComp.render()` creates a new instance of MyComp internally,
        # if we do `MyComp(registered_name="abc").render()`, then we use the
        # already-instantiated object.
        #
        # To achieve that, we want to re-assign the class methods as instance methods.
        # For that we have to "unwrap" the class methods via __func__.
        # See https://stackoverflow.com/a/76706399/9788634
        self.render_to_response = types.MethodType(self.__class__.render_to_response.__func__, self)  # type: ignore
        self.render = types.MethodType(self.__class__.render.__func__, self)  # type: ignore

    def __init_subclass__(cls, **kwargs: Any) -> None:
        cls._class_hash = hash(inspect.getfile(cls) + cls.__name__)

    @property
    def name(self) -> str:
        return self.registered_name or self.__class__.__name__

    def get_context_data(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        return {}

    def get_template_name(self, context: Context) -> Optional[str]:
        return self.template_name

    def get_template_string(self, context: Context) -> Optional[str]:
        return self.template

    # NOTE: When the template is taken from a file (AKA specified via `template_name`),
    # then we leverage Django's template caching. This means that the same instance
    # of Template is reused. This is important to keep in mind, because the implication
    # is that we should treat Templates AND their nodelists as IMMUTABLE.
    def get_template(self, context: Context) -> Template:
        template_string = self.get_template_string(context)
        if template_string is not None:
            return Template(template_string)

        template_name = self.get_template_name(context)
        if template_name is not None:
            return get_template(template_name).template

        raise ImproperlyConfigured(
            f"Either 'template_name' or 'template' must be set for Component {type(self).__name__}."
            f"Note: this attribute is not required if you are overriding the class's `get_template*()` methods."
        )

    def render_dependencies(self) -> SafeString:
        """Helper function to render all dependencies for a component."""
        dependencies = []

        css_deps = self.render_css_dependencies()
        if css_deps:
            dependencies.append(css_deps)

        js_deps = self.render_js_dependencies()
        if js_deps:
            dependencies.append(js_deps)

        return mark_safe("\n".join(dependencies))

    def render_css_dependencies(self) -> SafeString:
        """Render only CSS dependencies available in the media class or provided as a string."""
        if self.css is not None:
            return mark_safe(f"<style>{self.css}</style>")
        return mark_safe("\n".join(self.media.render_css()))

    def render_js_dependencies(self) -> SafeString:
        """Render only JS dependencies available in the media class or provided as a string."""
        if self.js is not None:
            return mark_safe(f"<script>{self.js}</script>")
        return mark_safe("\n".join(self.media.render_js()))

    def inject(self, key: str, default: Optional[Any] = None) -> Any:
        """
        Use this method to retrieve the data that was passed to a `{% provide %}` tag
        with the corresponding key.

        To retrieve the data, `inject()` must be called inside a component that's
        inside the `{% provide %}` tag.

        You may also pass a default that will be used if the `provide` tag with given
        key was NOT found.

        This method mut be used inside the `get_context_data()` method and raises
        an error if called elsewhere.

        Example:

        Given this template:
        ```django
        {% provide "provider" hello="world" %}
            {% component "my_comp" %}
            {% endcomponent %}
        {% endprovide %}
        ```

        And given this definition of "my_comp" component:
        ```py
        @component.register("my_comp")
        class MyComp(component.Component):
            template = "hi {{ data.hello }}!"
            def get_context_data(self):
                data = self.inject("provider")
                return {"data": data}
        ```

        This renders into:
        ```
        hi world!
        ```

        As the `{{ data.hello }}` is taken from the "provider".
        """
        if self._context is None:
            raise RuntimeError(
                f"Method 'inject()' of component '{self.name}' was called outside of 'get_context_data()'"
            )

        return get_injected_context_var(self.name, self._context, key, default)

    @classmethod
    def render_to_response(
        cls,
        context: Union[Dict[str, Any], Context] = None,
        slots: Optional[Mapping[SlotName, SlotContent]] = None,
        escape_slots_content: bool = True,
        args: Optional[Union[List, Tuple]] = None,
        kwargs: Optional[Dict[str, Any]] = None,
        *response_args: Any,
        **response_kwargs: Any,
    ) -> HttpResponse:
        """
        Render the component and wrap the content in the response class.

        The response class is taken from `Component.response_class`. Defaults to `django.http.HttpResponse`.

        This is the interface for the `django.views.View` class which allows us to
        use components as Django views with `component.as_view()`.

        Inputs:
        - `args` - Positional args for the component. This is the same as calling the component
          as `{% component "my_comp" arg1 arg2 ... %}`
        - `kwargs` - Kwargs for the component. This is the same as calling the component
          as `{% component "my_comp" key1=val1 key2=val2 ... %}`
        - `slots` - Component slot fills. This is the same as pasing `{% fill %}` tags to the component.
            Accepts a dictionary of `{ slot_name: slot_content }` where `slot_content` can be a string
            or render function.
        - `escape_slots_content` - Whether the content from `slots` should be escaped.
        - `context` - A context (dictionary or Django's Context) within which the component
          is rendered. The keys on the context can be accessed from within the template.
            - NOTE: In "isolated" mode, context is NOT accessible, and data MUST be passed via
              component's args and kwargs.

        Any additional args and kwargs are passed to the `response_class`.

        Example:
        ```py
        MyComponent.render_to_response(
            args=[1, "two", {}],
            kwargs={
                "key": 123,
            },
            slots={
                "header": 'STATIC TEXT HERE',
                "footer": lambda ctx, slot_kwargs, slot_ref: f'CTX: {ctx['hello']} SLOT_DATA: {slot_kwargs['abc']}',
            },
            escape_slots_content=False,
            # HttpResponse input
            status=201,
            headers={...},
        )
        # HttpResponse(content=..., status=201, headers=...)
        ```
        """
        content = cls.render(
            args=args,
            kwargs=kwargs,
            context=context,
            slots=slots,
            escape_slots_content=escape_slots_content,
        )
        return cls.response_class(content, *response_args, **response_kwargs)

    @classmethod
    def render(
        cls,
        context: Optional[Union[Dict[str, Any], Context]] = None,
        args: Optional[Union[List, Tuple]] = None,
        kwargs: Optional[Dict[str, Any]] = None,
        slots: Optional[Mapping[SlotName, SlotContent]] = None,
        escape_slots_content: bool = True,
    ) -> str:
        """
        Render the component into a string.

        Inputs:
        - `args` - Positional args for the component. This is the same as calling the component
          as `{% component "my_comp" arg1 arg2 ... %}`
        - `kwargs` - Kwargs for the component. This is the same as calling the component
          as `{% component "my_comp" key1=val1 key2=val2 ... %}`
        - `slots` - Component slot fills. This is the same as pasing `{% fill %}` tags to the component.
            Accepts a dictionary of `{ slot_name: slot_content }` where `slot_content` can be a string
            or render function.
        - `escape_slots_content` - Whether the content from `slots` should be escaped.
        - `context` - A context (dictionary or Django's Context) within which the component
          is rendered. The keys on the context can be accessed from within the template.
            - NOTE: In "isolated" mode, context is NOT accessible, and data MUST be passed via
              component's args and kwargs.

        Example:
        ```py
        MyComponent.render(
            args=[1, "two", {}],
            kwargs={
                "key": 123,
            },
            slots={
                "header": 'STATIC TEXT HERE',
                "footer": lambda ctx, slot_kwargs, slot_ref: f'CTX: {ctx['hello']} SLOT_DATA: {slot_kwargs['abc']}',
            },
            escape_slots_content=False,
        )
        ```
        """
        # This method may be called as class method or as instance method.
        # If called as class method, create a new instance.
        if isinstance(cls, Component):
            comp: Component = cls
        else:
            comp = cls()

        return comp._render(context, args, kwargs, slots, escape_slots_content)

    # This is the internal entrypoint for the render function
    def _render(
        self,
        context: Union[Dict[str, Any], Context] = None,
        args: Optional[Union[List, Tuple]] = None,
        kwargs: Optional[Dict[str, Any]] = None,
        slots: Optional[Mapping[SlotName, SlotContent]] = None,
        escape_slots_content: bool = True,
    ) -> str:
        try:
            return self._render_impl(context, args, kwargs, slots, escape_slots_content)
        except Exception as err:
            raise type(err)(f"An error occured while rendering component '{self.name}':\n{repr(err)}") from err

    def _render_impl(
        self,
        context: Union[Dict[str, Any], Context] = None,
        args: Optional[Union[List, Tuple]] = None,
        kwargs: Optional[Dict[str, Any]] = None,
        slots: Optional[Mapping[SlotName, SlotContent]] = None,
        escape_slots_content: bool = True,
    ) -> str:
        # Allow to provide no args/kwargs
        args = args or []
        kwargs = kwargs or {}

        # Allow to provide no Context, so we can render component just with args + kwargs
        context_was_given = True
        if context is None:
            context = Context()
            context_was_given = False

        # Allow to provide a dict instead of Context
        # NOTE: This if/else is important to avoid nested Contexts,
        # See https://github.com/EmilStenstrom/django-components/issues/414
        context = context if isinstance(context, Context) else Context(context)
        prepare_context(context, self.component_id)

        # Temporarily populate _context so user can call `self.inject()` from
        # within `get_context_data()`
        self._context = context
        context_data = self.get_context_data(*args, **kwargs)
        self._context = None

        with context.update(context_data):
            template = self.get_template(context)
            _monkeypatch_template(template)
            if not context_was_given:
                # Associate the newly-created Context with a Template, otherwise we get
                # an error when we try to use `{% include %}` tag inside the template?
                context.template = template
                context.template_name = template.name

            # Set `Template._dc_is_component_nested` based on whether we're currently INSIDE
            # the `{% extends %}` tag.
            # Part of fix for https://github.com/EmilStenstrom/django-components/issues/508
            template._dc_is_component_nested = bool(context.render_context.get(BLOCK_CONTEXT_KEY))

            # Support passing slots explicitly to `render` method
            if slots:
                fill_content = self._fills_from_slots_data(slots, escape_slots_content)
            else:
                fill_content = self.fill_content

            # If this is top-level component and it has no parent, use outer context instead
            slot_context_data = context_data
            if not context[_PARENT_COMP_CONTEXT_KEY]:
                slot_context_data = self.outer_context.flatten()

            slots, resolved_fills = resolve_slots(
                context,
                template,
                component_name=self.name,
                context_data=slot_context_data,
                fill_content=fill_content,
            )

            # Available slot fills - this is internal to us
            updated_slots = {
                **context.get(_FILLED_SLOTS_CONTENT_CONTEXT_KEY, {}),
                **resolved_fills,
            }

            # For users, we expose boolean variables that they may check
            # to see if given slot was filled, e.g.:
            # `{% if variable > 8 and component_vars.is_filled.header %}`
            slot_bools = {slot_fill.escaped_name: slot_fill.is_filled for slot_fill in resolved_fills.values()}

            with context.update(
                {
                    _ROOT_CTX_CONTEXT_KEY: self.outer_context,
                    _FILLED_SLOTS_CONTENT_CONTEXT_KEY: updated_slots,
                    # NOTE: Public API for variables accessible from within a component's template
                    # See https://github.com/EmilStenstrom/django-components/issues/280#issuecomment-2081180940
                    "component_vars": {
                        "is_filled": slot_bools,
                    },
                }
            ):
                rendered_component = template.render(context)

        if is_dependency_middleware_active():
            output = RENDERED_COMMENT_TEMPLATE.format(name=self.name) + rendered_component
        else:
            output = rendered_component

        return output

    def _fills_from_slots_data(
        self,
        slots_data: Mapping[SlotName, SlotContent],
        escape_content: bool = True,
    ) -> Dict[SlotName, FillContent]:
        """Fill component slots outside of template rendering."""
        slot_fills = {}
        for slot_name, content in slots_data.items():
            if isinstance(content, (str, SafeString)):
                content_func = _nodelist_to_slot_render_func(
                    NodeList([TextNode(conditional_escape(content) if escape_content else content)])
                )
            else:

                def content_func(ctx: Context, kwargs: Dict[str, Any], slot_ref: SlotRef) -> SlotRenderedContent:
                    rendered = content(ctx, kwargs, slot_ref)
                    return conditional_escape(rendered) if escape_content else rendered

            slot_fills[slot_name] = FillContent(
                content_func=content_func,
                slot_default_var=None,
                slot_data_var=None,
            )
        return slot_fills


class ComponentNode(Node):
    """Django.template.Node subclass that renders a django-components component"""

    def __init__(
        self,
        name_fexp: FilterExpression,
        context_args: List[FilterExpression],
        context_kwargs: Mapping[str, FilterExpression],
        isolated_context: bool = False,
        fill_nodes: Optional[List[FillNode]] = None,
        component_id: Optional[str] = None,
    ) -> None:
        self.component_id = component_id or gen_id()
        self.name_fexp = name_fexp
        self.context_args = context_args or []
        self.context_kwargs = context_kwargs or {}
        self.isolated_context = isolated_context
        self.fill_nodes = fill_nodes or []
        self.nodelist = NodeList(fill_nodes)

    def __repr__(self) -> str:
        return "<ComponentNode: {}. Contents: {!r}>".format(
            self.name_fexp,
            getattr(self, "nodelist", None),  # 'nodelist' attribute only assigned later.
        )

    def render(self, context: Context) -> str:
        trace_msg("RENDR", "COMP", self.name_fexp, self.component_id)

        resolved_component_name = self.name_fexp.resolve(context)
        component_cls: Type[Component] = registry.get(resolved_component_name)

        # Resolve FilterExpressions and Variables that were passed as args to the
        # component, then call component's context method
        # to get values to insert into the context
        resolved_context_args = safe_resolve_list(self.context_args, context)
        resolved_context_kwargs = safe_resolve_dict(self.context_kwargs, context)
        resolved_context_kwargs = process_aggregate_kwargs(resolved_context_kwargs)

        is_default_slot = len(self.fill_nodes) == 1 and self.fill_nodes[0].is_implicit
        if is_default_slot:
            fill_content: Dict[str, FillContent] = {
                DEFAULT_SLOT_KEY: FillContent(
                    content_func=_nodelist_to_slot_render_func(self.fill_nodes[0].nodelist),
                    slot_data_var=None,
                    slot_default_var=None,
                ),
            }
        else:
            fill_content = {}
            for fill_node in self.fill_nodes:
                # Note that outer component context is used to resolve variables in
                # fill tag.
                resolved_name = fill_node.name_fexp.resolve(context)
                if resolved_name in fill_content:
                    raise TemplateSyntaxError(
                        f"Multiple fill tags cannot target the same slot name: "
                        f"Detected duplicate fill tag name '{resolved_name}'."
                    )

                resolved_slot_default_var = fill_node.resolve_slot_default(context, resolved_component_name)
                resolved_slot_data_var = fill_node.resolve_slot_data(context, resolved_component_name)
                fill_content[resolved_name] = FillContent(
                    content_func=_nodelist_to_slot_render_func(fill_node.nodelist),
                    slot_default_var=resolved_slot_default_var,
                    slot_data_var=resolved_slot_data_var,
                )

        component: Component = component_cls(
            registered_name=resolved_component_name,
            outer_context=context,
            fill_content=fill_content,
            component_id=self.component_id,
        )

        # Prevent outer context from leaking into the template of the component
        if self.isolated_context:
            context = make_isolated_context_copy(context)

        output = component._render(
            context=context,
            args=resolved_context_args,
            kwargs=resolved_context_kwargs,
        )

        trace_msg("RENDR", "COMP", self.name_fexp, self.component_id, "...Done!")
        return output


def _monkeypatch_template(template: Template) -> None:
    # Modify `Template.render` to set `isolated_context` kwarg of `push_state`
    # based on our custom `Template._dc_is_component_nested`.
    #
    # Part of fix for https://github.com/EmilStenstrom/django-components/issues/508
    #
    # NOTE 1: While we could've subclassed Template, then we would need to either
    # 1) ask the user to change the backend, so all templates are of our subclass, or
    # 2) copy the data from user's Template class instance to our subclass instance,
    # which could lead to doubly parsing the source, and could be problematic if users
    # used more exotic subclasses of Template.
    #
    # Instead, modifying only the `render` method of an already-existing instance
    # should work well with any user-provided custom subclasses of Template, and it
    # doesn't require the source to be parsed multiple times. User can pass extra args/kwargs,
    # and can modify the rendering behavior by overriding the `_render` method.
    #
    # NOTE 2: Instead of setting `Template._dc_is_component_nested`, alternatively we could
    # have passed the value to `_monkeypatch_template` directly. However, we intentionally
    # did NOT do that, so the monkey-patched method is more robust, and can be e.g. copied
    # to other.
    if hasattr(template, "_dc_patched"):
        # Do not patch if done so already. This helps us avoid RecursionError
        return

    def _template_render(self: Template, context: Context, *args: Any, **kwargs: Any) -> str:
        #  ---------------- OUR CHANGES START ----------------
        # We parametrized `isolated_context`, which was `True` in the original method.
        if not hasattr(self, "_dc_is_component_nested"):
            isolated_context = True
        else:
            # MUST be `True` for templates that are NOT import with `{% extends %}` tag,
            # and `False` otherwise.
            isolated_context = not self._dc_is_component_nested
        #  ---------------- OUR CHANGES END ----------------

        with context.render_context.push_state(self, isolated_context=isolated_context):
            if context.template is None:
                with context.bind_template(self):
                    context.template_name = self.name
                    return self._render(context, *args, **kwargs)
            else:
                return self._render(context, *args, **kwargs)

    # See https://stackoverflow.com/a/42154067/9788634
    template.render = types.MethodType(_template_render, template)
