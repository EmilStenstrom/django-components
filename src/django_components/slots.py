import difflib
import re
from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Generic,
    List,
    Literal,
    Mapping,
    NamedTuple,
    Optional,
    Protocol,
    Set,
    Tuple,
    TypeVar,
    Union,
    cast,
    runtime_checkable,
)

from django.template import Context
from django.template.base import NodeList, TextNode
from django.template.exceptions import TemplateSyntaxError
from django.utils.safestring import SafeString, mark_safe

from django_components.app_settings import ContextBehavior
from django_components.context import (
    _COMPONENT_SLOT_CTX_CONTEXT_KEY,
    _INJECT_CONTEXT_KEY_PREFIX,
    _REGISTRY_CONTEXT_KEY,
    _ROOT_CTX_CONTEXT_KEY,
)
from django_components.expression import RuntimeKwargs, is_identifier
from django_components.node import BaseNode
from django_components.util.logger import trace_msg
from django_components.util.misc import get_last_index

if TYPE_CHECKING:
    from django_components.component_registry import ComponentRegistry

TSlotData = TypeVar("TSlotData", bound=Mapping, contravariant=True)

DEFAULT_SLOT_KEY = "default"
FILL_GEN_CONTEXT_KEY = "_DJANGO_COMPONENTS_GEN_FILL"
SLOT_DATA_KWARG = "data"
SLOT_NAME_KWARG = "name"
SLOT_DEFAULT_KWARG = "default"
SLOT_REQUIRED_KEYWORD = "required"
SLOT_DEFAULT_KEYWORD = "default"


# Public types
SlotResult = Union[str, SafeString]


@runtime_checkable
class SlotFunc(Protocol, Generic[TSlotData]):
    def __call__(self, ctx: Context, slot_data: TSlotData, slot_ref: "SlotRef") -> SlotResult: ...  # noqa E704


SlotContent = Union[SlotResult, SlotFunc[TSlotData], "Slot[TSlotData]"]


@dataclass
class Slot(Generic[TSlotData]):
    """This class holds the slot content function along with related metadata."""

    content_func: SlotFunc[TSlotData]

    def __post_init__(self) -> None:
        if not callable(self.content_func):
            raise ValueError(f"Slot content must be a callable, got: {self.content_func}")

        # Allow passing Slot instances as content functions
        if isinstance(self.content_func, Slot):
            inner_slot = self.content_func
            self.content_func = inner_slot.content_func

    # Allow to treat the instances as functions
    def __call__(self, ctx: Context, slot_data: TSlotData, slot_ref: "SlotRef") -> SlotResult:
        return self.content_func(ctx, slot_data, slot_ref)

    # Make Django pass the instances of this class within the templates without calling
    # the instances as a function.
    @property
    def do_not_call_in_templates(self) -> bool:
        return True


# Internal type aliases
SlotName = str


@dataclass(frozen=True)
class SlotFill(Generic[TSlotData]):
    """
    SlotFill describes what WILL be rendered.

    The fill may be provided by the user from the outside (`is_filled=True`),
    or it may be the default content of the slot (`is_filled=False`).
    """

    name: str
    """Name of the slot."""
    is_filled: bool
    slot: Slot[TSlotData]


class SlotRef:
    """
    SlotRef allows to treat a slot as a variable. The slot is rendered only once
    the instance is coerced to string.

    This is used to access slots as variables inside the templates. When a SlotRef
    is rendered in the template with `{{ my_lazy_slot }}`, it will output the contents
    of the slot.
    """

    def __init__(self, slot: "SlotNode", context: Context):
        self._slot = slot
        self._context = context

    # Render the slot when the template coerces SlotRef to string
    def __str__(self) -> str:
        return mark_safe(self._slot.nodelist.render(self._context))


class SlotIsFilled(dict):
    """
    Dictionary that returns `True` if the slot is filled (key is found), `False` otherwise.
    """

    def __init__(self, fills: Dict, *args: Any, **kwargs: Any) -> None:
        escaped_fill_names = {_escape_slot_name(fill_name): True for fill_name in fills.keys()}
        super().__init__(escaped_fill_names, *args, **kwargs)

    def __missing__(self, key: Any) -> bool:
        return False


@dataclass
class ComponentSlotContext:
    component_name: str
    template_name: str
    is_dynamic_component: bool
    default_slot: Optional[str]
    fills: Dict[SlotName, Slot]


class SlotNode(BaseNode):
    """Node corresponding to `{% slot %}`"""

    def __init__(
        self,
        nodelist: NodeList,
        trace_id: str,
        node_id: Optional[str] = None,
        kwargs: Optional[RuntimeKwargs] = None,
        is_required: bool = False,
        is_default: bool = False,
    ):
        super().__init__(nodelist=nodelist, args=None, kwargs=kwargs, node_id=node_id)

        self.is_required = is_required
        self.is_default = is_default
        self.trace_id = trace_id

    @property
    def active_flags(self) -> List[str]:
        flags = []
        if self.is_required:
            flags.append("required")
        if self.is_default:
            flags.append("default")
        return flags

    def __repr__(self) -> str:
        return f"<Slot Node: {self.node_id}. Contents: {repr(self.nodelist)}. Options: {self.active_flags}>"

    # NOTE:
    # In the current implementation, the slots are resolved only at the render time.
    # So when we are rendering Django's Nodes, and we come across a SlotNode, only
    # at that point we check if we have the fill for it.
    #
    # That means that we can use variables, and we can place slots in loops.
    #
    # However, because the slot names are dynamic, we cannot know all the slot names
    # that will be rendered ahead of the time.
    #
    # Moreover, user may define a `{% slot %}` whose default content has more nested
    # `{% slot %}` tags inside of it.
    #
    # Previously, there was an error raised if there were unfilled slots or extra fills,
    # or if there was an extra fill for a default slot.
    #
    # But we don't raise those anymore, because:
    # 1. We don't know about ALL slots, just about the rendered ones, so we CANNOT check
    #    for unfilled slots (rendered slots WILL raise an error if the fill is missing).
    # 2. User may provide extra fills, but these may belong to slots we haven't
    #    encountered in this render run. So we CANNOT say which ones are extra.
    def render(self, context: Context) -> SafeString:
        trace_msg("RENDR", "SLOT", self.trace_id, self.node_id)

        if _COMPONENT_SLOT_CTX_CONTEXT_KEY not in context or not context[_COMPONENT_SLOT_CTX_CONTEXT_KEY]:
            raise TemplateSyntaxError(
                "Encountered a SlotNode outside of a ComponentNode context. "
                "Make sure that all {% slot %} tags are nested within {% component %} tags.\n"
                f"SlotNode: {self.__repr__()}"
            )

        component_ctx: ComponentSlotContext = context[_COMPONENT_SLOT_CTX_CONTEXT_KEY]
        slot_name, kwargs = self.resolve_kwargs(context, component_ctx.component_name)

        # Check for errors
        if self.is_default and not component_ctx.is_dynamic_component:
            # Allow one slot to be marked as 'default', or multiple slots but with
            # the same name. If there is multiple 'default' slots with different names, raise.
            default_slot_name = component_ctx.default_slot
            if default_slot_name is not None and slot_name != default_slot_name:
                raise TemplateSyntaxError(
                    "Only one component slot may be marked as 'default', "
                    f"found '{default_slot_name}' and '{slot_name}'. "
                    f"To fix, check template '{component_ctx.template_name}' "
                    f"of component '{component_ctx.component_name}'."
                )

            if default_slot_name is None:
                component_ctx.default_slot = slot_name

            # If the slot is marked as 'default', check if user didn't double-fill it
            # by specifying the fill both by explicit slot name and implicitly as 'default'.
            if (
                slot_name != DEFAULT_SLOT_KEY
                and component_ctx.fills.get(slot_name, False)
                and component_ctx.fills.get(DEFAULT_SLOT_KEY, False)
            ):
                raise TemplateSyntaxError(
                    f"Slot '{slot_name}' of component '{component_ctx.component_name}' was filled twice: "
                    "once explicitly and once implicitly as 'default'."
                )

        # If slot is marked as 'default', we use the name 'default' for the fill,
        # IF SUCH FILL EXISTS. Otherwise, we use the slot's name.
        if self.is_default and DEFAULT_SLOT_KEY in component_ctx.fills:
            fill_name = DEFAULT_SLOT_KEY
        else:
            fill_name = slot_name

        if fill_name in component_ctx.fills:
            slot_fill_fn = component_ctx.fills[fill_name]
            slot_fill = SlotFill(
                name=slot_name,
                is_filled=True,
                slot=slot_fill_fn,
            )
        else:
            # No fill was supplied, render the slot's default content
            slot_fill = SlotFill(
                name=slot_name,
                is_filled=False,
                slot=_nodelist_to_slot_render_func(
                    slot_name=slot_name,
                    nodelist=self.nodelist,
                    data_var=None,
                    default_var=None,
                ),
            )

        # Check: If a slot is marked as 'required', it must be filled.
        #
        # To help with easy-to-overlook typos, we fuzzy match unresolvable fills to
        # those slots for which no matching fill was encountered. In the event of
        # a close match, we include the name of the matched unfilled slot as a
        # hint in the error message.
        #
        # Note: Finding a good `cutoff` value may require further trial-and-error.
        # Higher values make matching stricter. This is probably preferable, as it
        # reduces false positives.
        if self.is_required and not slot_fill.is_filled and not component_ctx.is_dynamic_component:
            msg = (
                f"Slot '{slot_name}' is marked as 'required' (i.e. non-optional), "
                f"yet no fill is provided. Check template.'"
            )
            fill_names = list(component_ctx.fills.keys())
            if fill_names:
                fuzzy_fill_name_matches = difflib.get_close_matches(fill_name, fill_names, n=1, cutoff=0.7)
                if fuzzy_fill_name_matches:
                    msg += f"\nDid you mean '{fuzzy_fill_name_matches[0]}'?"
            raise TemplateSyntaxError(msg)

        extra_context: Dict[str, Any] = {}

        # NOTE: If a user defines a `{% slot %}` tag inside a `{% fill %}` tag, two things
        # may happen based on the context mode:
        # 1. In the "isolated" mode, the context inside the fill is the same as outside of the component
        #    so any slots fill be filled with that same (parent) context.
        # 2. In the "django" mode, the context inside the fill is the same as the one inside the component,
        #
        # The "django" mode is problematic, because if we define a fill with the same name as the slot,
        # then we will enter an endless loop. E.g.:
        # ```django
        # {% component "mycomponent" %}
        #   {% slot "content" %}
        #     {% fill "content" %}
        #       ...
        #     {% endfill %}
        #   {% endslot %}
        # {% endcomponent %}
        # ```
        #
        # Hence, even in the "django" mode, we MUST use slots of the context of the parent component.
        all_ctxs = [d for d in context.dicts if _COMPONENT_SLOT_CTX_CONTEXT_KEY in d]
        if len(all_ctxs) > 1:
            second_to_last_ctx = all_ctxs[-2]
            extra_context[_COMPONENT_SLOT_CTX_CONTEXT_KEY] = second_to_last_ctx[_COMPONENT_SLOT_CTX_CONTEXT_KEY]

        # Irrespective of which context we use ("root" context or the one passed to this
        # render function), pass down the keys used by inject/provide feature. This makes it
        # possible to pass the provided values down the slots, e.g.:
        # {% provide "abc" val=123 %}
        #   {% slot "content" %}{% endslot %}
        # {% endprovide %}
        for key, value in context.flatten().items():
            if key.startswith(_INJECT_CONTEXT_KEY_PREFIX):
                extra_context[key] = value

        slot_ref = SlotRef(self, context)

        # For the user-provided slot fill, we want to use the context of where the slot
        # came from (or current context if configured so)
        used_ctx = self._resolve_slot_context(context, slot_fill)
        with used_ctx.update(extra_context):
            # Render slot as a function
            # NOTE: While `{% fill %}` tag has to opt in for the `default` and `data` variables,
            #       the render function ALWAYS receives them.
            output = slot_fill.slot(used_ctx, kwargs, slot_ref)

        trace_msg("RENDR", "SLOT", self.trace_id, self.node_id, msg="...Done!")
        return output

    def _resolve_slot_context(self, context: Context, slot_fill: "SlotFill") -> Context:
        """Prepare the context used in a slot fill based on the settings."""
        # If slot is NOT filled, we use the slot's default AKA content between
        # the `{% slot %}` tags. These should be evaluated as if the `{% slot %}`
        # tags weren't even there, which means that we use the current context.
        if not slot_fill.is_filled:
            return context

        registry: "ComponentRegistry" = context[_REGISTRY_CONTEXT_KEY]
        if registry.settings.context_behavior == ContextBehavior.DJANGO:
            return context
        elif registry.settings.context_behavior == ContextBehavior.ISOLATED:
            return context[_ROOT_CTX_CONTEXT_KEY]
        else:
            raise ValueError(f"Unknown value for context_behavior: '{registry.settings.context_behavior}'")

    def resolve_kwargs(
        self,
        context: Context,
        component_name: Optional[str] = None,
    ) -> Tuple[str, Dict[str, Optional[str]]]:
        kwargs = self.kwargs.resolve(context)
        name = kwargs.pop(SLOT_NAME_KWARG, None)

        if not name:
            raise RuntimeError(f"Slot tag kwarg 'name' is missing in component {component_name}")

        return (name, kwargs)


class FillNode(BaseNode):
    """Node corresponding to `{% fill %}`"""

    def __init__(
        self,
        nodelist: NodeList,
        kwargs: RuntimeKwargs,
        trace_id: str,
        node_id: Optional[str] = None,
    ):
        super().__init__(nodelist=nodelist, args=None, kwargs=kwargs, node_id=node_id)

        self.trace_id = trace_id

    def render(self, context: Context) -> str:
        if _is_extracting_fill(context):
            self._extract_fill(context)
            return ""

        raise TemplateSyntaxError(
            "FillNode.render() (AKA {% fill ... %} block) cannot be rendered outside of a Component context. "
            "Make sure that the {% fill %} tags are nested within {% component %} tags."
        )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} ID: {self.node_id}. Contents: {repr(self.nodelist)}.>"

    def resolve_kwargs(self, context: Context) -> "FillWithData":
        kwargs = self.kwargs.resolve(context)

        name = self._process_kwarg(kwargs, SLOT_NAME_KWARG, identifier=False)
        default_var = self._process_kwarg(kwargs, SLOT_DEFAULT_KWARG)
        data_var = self._process_kwarg(kwargs, SLOT_DATA_KWARG)

        if not isinstance(name, str):
            raise TemplateSyntaxError(f"Fill tag '{SLOT_NAME_KWARG}' kwarg must resolve to a string, got {name}")

        if data_var is not None and not isinstance(data_var, str):
            raise TemplateSyntaxError(f"Fill tag '{SLOT_DATA_KWARG}' kwarg must resolve to a string, got {data_var}")

        if default_var is not None and not isinstance(default_var, str):
            raise TemplateSyntaxError(
                f"Fill tag '{SLOT_DEFAULT_KWARG}' kwarg must resolve to a string, got {default_var}"
            )

        # data and default cannot be bound to the same variable
        if data_var and default_var and data_var == default_var:
            raise RuntimeError(
                f"Fill '{name}' received the same string for slot default ({SLOT_DEFAULT_KWARG}=...)"
                f" and slot data ({SLOT_DATA_KWARG}=...)"
            )

        return FillWithData(
            fill=self,
            name=name,
            default_var=default_var,
            data_var=data_var,
            extra_context={},
        )

    def _process_kwarg(
        self,
        kwargs: Dict[str, Any],
        key: str,
        identifier: bool = True,
    ) -> Optional[Any]:
        if key not in kwargs:
            return None

        value = kwargs[key]
        if identifier and not is_identifier(value):
            raise RuntimeError(f"Fill tag kwarg '{key}' does not resolve to a valid Python identifier, got '{value}'")

        return value

    def _extract_fill(self, context: Context) -> None:
        # `FILL_GEN_CONTEXT_KEY` is only ever set when we are rendering content between the
        # `{% component %}...{% endcomponent %}` tags. This is done in order to collect all fill tags.
        # E.g.
        #   {% for slot_name in exposed_slots %}
        #     {% fill name=slot_name %}
        #       ...
        #     {% endfill %}
        #   {% endfor %}
        collected_fills: List[FillWithData] = context.get(FILL_GEN_CONTEXT_KEY, None)

        if collected_fills is None:
            return

        # NOTE: It's important that we use the context given to the fill tag, so it accounts
        #       for any variables set via e.g. for-loops.
        data = self.resolve_kwargs(context)

        # To allow using variables which were defined within the template and to which
        # the `{% fill %}` tag has access, we need to capture those variables too.
        #
        # E.g.
        # ```django
        # {% component "three_slots" %}
        #     {% with slot_name="header" %}
        #         {% fill name=slot_name %}
        #             OVERRIDEN: {{ slot_name }}
        #         {% endfill %}
        #     {% endwith %}
        # {% endcomponent %}
        # ```
        #
        # NOTE: We want to capture only variables that were defined WITHIN
        # `{% component %} ... {% endcomponent %}`. Hence we search for the last
        # index of `FILL_GEN_CONTEXT_KEY`.
        index_of_new_layers = get_last_index(context.dicts, lambda d: FILL_GEN_CONTEXT_KEY in d)
        for dict_layer in context.dicts[index_of_new_layers:]:
            for key, value in dict_layer.items():
                if not key.startswith("_"):
                    data.extra_context[key] = value

        # To allow using the variables from the forloops inside the fill tags, we need to
        # capture those variables too.
        #
        # E.g.
        # {% component "three_slots" %}
        #     {% for outer in outer_loop %}
        #         {% for slot_name in the_slots %}
        #             {% fill name=slot_name|add:outer %}
        #                 OVERRIDEN: {{ slot_name }} - {{ outer }}
        #             {% endfill %}
        #         {% endfor %}
        #     {% endfor %}
        # {% endcomponent %}
        #
        # When we get to {% fill %} tag, the {% for %} tags have added extra info to the context.
        # This loop info can be identified by having key `forloop` in it.
        # There will be as many "forloop" dicts as there are for-loops.
        #
        # So `Context.dicts` may look like this:
        # [
        #   {'True': True, 'False': False, 'None': None},  # Default context
        #   {'forloop': {'parentloop': {...}, 'counter0': 2, 'counter': 3, ... }, 'outer': 2},
        #   {'forloop': {'parentloop': {...}, 'counter0': 1, 'counter': 2, ... }, 'slot_name': 'slot2'}
        # ]
        for layer in context.dicts:
            if "forloop" in layer:
                layer = layer.copy()
                layer["forloop"] = layer["forloop"].copy()
                data.extra_context.update(layer)

        collected_fills.append(data)


#######################################
# EXTRACTING {% fill %} FROM TEMPLATES
#######################################


class FillWithData(NamedTuple):
    fill: FillNode
    name: str
    default_var: Optional[str]
    data_var: Optional[str]
    extra_context: Dict[str, Any]


def resolve_fills(
    context: Context,
    nodelist: NodeList,
    component_name: str,
) -> Dict[SlotName, Slot]:
    """
    Given a component body (`django.template.NodeList`), find all slot fills,
    whether defined explicitly with `{% fill %}` or implicitly.

    So if we have a component body:
    ```django
    {% component "mycomponent" %}
        {% fill "first_fill" %}
            Hello!
        {% endfill %}
        {% fill "second_fill" %}
            Hello too!
        {% endfill %}
    {% endcomponent %}
    ```

    Then this function finds 2 fill nodes: "first_fill" and "second_fill",
    and formats them as slot functions, returning:

    ```python
    {
        "first_fill": SlotFunc(...),
        "second_fill": SlotFunc(...),
    }
    ```

    If no fill nodes are found, then the content is treated as default slot content.

    ```python
    {
        DEFAULT_SLOT_KEY: SlotFunc(...),
    }
    ```

    This function also handles for-loops, if/else statements, or include tags to generate fill tags:

    ```django
    {% component "mycomponent" %}
        {% for slot_name in slots %}
            {% fill name=slot_name %}
                {% slot name=slot_name / %}
            {% endfill %}
        {% endfor %}
    {% endcomponent %}
    ```
    """
    slots: Dict[SlotName, Slot] = {}

    if not nodelist:
        return slots

    maybe_fills = _extract_fill_content(nodelist, context, component_name)

    # The content has no fills, so treat it as default slot, e.g.:
    # {% component "mycomponent" %}
    #   Hello!
    #   {% if True %} 123 {% endif %}
    # {% endcomponent %}
    if maybe_fills is False:
        # Ignore empty content between `{% component %} ... {% endcomponent %}` tags
        nodelist_is_empty = not len(nodelist) or all(
            isinstance(node, TextNode) and not node.s.strip() for node in nodelist
        )

        if not nodelist_is_empty:
            slots[DEFAULT_SLOT_KEY] = _nodelist_to_slot_render_func(
                DEFAULT_SLOT_KEY,
                nodelist,
                data_var=None,
                default_var=None,
            )

    # The content has fills
    else:
        # NOTE: If slot fills are explicitly defined, we use them even if they are empty (or only whitespace).
        #       This is different from the default slot, where we ignore empty content.
        for fill in maybe_fills:
            slots[fill.name] = _nodelist_to_slot_render_func(
                slot_name=fill.name,
                nodelist=fill.fill.nodelist,
                data_var=fill.data_var,
                default_var=fill.default_var,
                extra_context=fill.extra_context,
            )

    return slots


def _extract_fill_content(
    nodes: NodeList,
    context: Context,
    component_name: str,
) -> Union[List[FillWithData], Literal[False]]:
    # When, during rendering of this tree, we encounter a {% fill %} node, instead of rendering content,
    # it will add itself into captured_fills, because `FILL_GEN_CONTEXT_KEY` is defined.
    captured_fills: List[FillWithData] = []
    with context.update({FILL_GEN_CONTEXT_KEY: captured_fills}):
        content = mark_safe(nodes.render(context).strip())

    # If we did not encounter any fills (not accounting for those nested in other
    # {% componenet %} tags), then we treat the content as default slot.
    if not captured_fills:
        return False

    elif content:
        raise TemplateSyntaxError(
            f"Illegal content passed to component '{component_name}'. "
            "Explicit 'fill' tags cannot occur alongside other text. "
            "The component body rendered content: {content}"
        )

    # Check for any duplicates
    seen_names: Set[str] = set()
    for fill in captured_fills:
        if fill.name in seen_names:
            raise TemplateSyntaxError(
                f"Multiple fill tags cannot target the same slot name in component '{component_name}': "
                f"Detected duplicate fill tag name '{fill.name}'."
            )
        seen_names.add(fill.name)

    return captured_fills


#######################################
# MISC
#######################################


name_escape_re = re.compile(r"[^\w]")


def _escape_slot_name(name: str) -> str:
    """
    Users may define slots with names which are invalid identifiers like 'my slot'.
    But these cannot be used as keys in the template context, e.g. `{{ component_vars.is_filled.'my slot' }}`.
    So as workaround, we instead use these escaped names which are valid identifiers.

    So e.g. `my slot` should be escaped as `my_slot`.
    """
    # NOTE: Do a simple substitution where we replace all non-identifier characters with `_`.
    # Identifiers consist of alphanum (a-zA-Z0-9) and underscores.
    # We don't check if these escaped names conflict with other existing slots in the template,
    # we leave this obligation to the user.
    escaped_name = name_escape_re.sub("_", name)
    return escaped_name


def _nodelist_to_slot_render_func(
    slot_name: str,
    nodelist: NodeList,
    data_var: Optional[str] = None,
    default_var: Optional[str] = None,
    extra_context: Optional[Dict[str, Any]] = None,
) -> Slot:
    if data_var:
        if not data_var.isidentifier():
            raise TemplateSyntaxError(
                f"Slot data alias in fill '{slot_name}' must be a valid identifier. Got '{data_var}'"
            )

    if default_var:
        if not default_var.isidentifier():
            raise TemplateSyntaxError(
                f"Slot default alias in fill '{slot_name}' must be a valid identifier. Got '{default_var}'"
            )

    def render_func(ctx: Context, slot_data: Dict[str, Any], slot_ref: SlotRef) -> SlotResult:
        # Expose the kwargs that were passed to the `{% slot %}` tag. These kwargs
        # are made available through a variable name that was set on the `{% fill %}`
        # tag.
        if data_var:
            ctx[data_var] = slot_data

        # If slot fill is using `{% fill "myslot" default="abc" %}`, then set the "abc" to
        # the context, so users can refer to the default slot from within the fill content.
        if default_var:
            ctx[default_var] = slot_ref

        # NOTE: If a `{% fill %}` tag inside a `{% component %}` tag is inside a forloop,
        # the `extra_context` contains the forloop variables. We want to make these available
        # to the slot fill content.
        #
        # However, we cannot simply append the `extra_context` to the Context as the latest stack layer
        # because then the forloop variables override the slot fill variables. Instead, we have to put
        # the `extra_context` into the correct layer.
        #
        # Currently the `extra_context` is set only in `FillNode._extract_fill()` method
        # that is run when we render a `{% component %}` tag inside a template, and we need
        # to extract the fills from the tag's body.
        #
        # Thus, when we get here and `extra_context` is not None, it means that the component
        # is being rendered from within the template. And so we know that we're inside `Component._render()`.
        # And that means that the context MUST contain our internal context keys like `_ROOT_CTX_CONTEXT_KEY`.
        #
        # And so we want to put the `extra_context` into the same layer that contains `_ROOT_CTX_CONTEXT_KEY`.
        #
        # HOWEVER, the layer with `_ROOT_CTX_CONTEXT_KEY` also contains user-defined data from `get_context_data()`.
        # Data from `get_context_data()` should take precedence over `extra_context`. So we have to insert
        # the forloop variables BEFORE that.
        index_of_last_component_layer = get_last_index(ctx.dicts, lambda d: _ROOT_CTX_CONTEXT_KEY in d)
        if index_of_last_component_layer is None:
            index_of_last_component_layer = 0

        # TODO: Currently there's one more layer before the `_ROOT_CTX_CONTEXT_KEY` layer, which is
        #       pushed in `_prepare_template()` in `component.py`.
        #       That layer should be removed when `Component.get_template()` is removed, after which
        #       the following line can be removed.
        index_of_last_component_layer -= 1

        # Insert the `extra_context` into the correct layer of the context stack
        ctx.dicts.insert(index_of_last_component_layer, extra_context or {})

        rendered = nodelist.render(ctx)

        # After the rendering is done, remove the `extra_context` from the context stack
        ctx.dicts.pop(index_of_last_component_layer)

        return rendered

    return Slot(content_func=cast(SlotFunc, render_func))


def _is_extracting_fill(context: Context) -> bool:
    return context.get(FILL_GEN_CONTEXT_KEY, None) is not None
