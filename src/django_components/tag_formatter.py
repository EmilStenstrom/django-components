import abc
import re
from typing import TYPE_CHECKING, List, NamedTuple

from django.template import TemplateSyntaxError
from django.utils.module_loading import import_string

from django_components.expression import resolve_string
from django_components.template_parser import VAR_CHARS
from django_components.utils import is_str_wrapped_in_quotes

if TYPE_CHECKING:
    from django_components.component_registry import ComponentRegistry


TAG_RE = re.compile(r"^[{chars}]+$".format(chars=VAR_CHARS))


class TagResult(NamedTuple):
    """The return value from `TagFormatter.parse()`"""

    component_name: str
    """Component name extracted from the template tag"""
    tokens: List[str]
    """Remaining tokens (words) that were passed to the tag, with component name removed"""


class TagFormatterABC(abc.ABC):
    @abc.abstractmethod
    def start_tag(self, name: str) -> str:
        """Formats the start tag of a component."""
        ...

    @abc.abstractmethod
    def end_tag(self, name: str) -> str:
        """Formats the end tag of a block component."""
        ...

    @abc.abstractmethod
    def parse(self, tokens: List[str]) -> TagResult:
        """
        Given the tokens (words) of a component start tag, this function extracts
        the component name from the tokens list, and returns `TagResult`, which
        is a tuple of `(component_name, remaining_tokens)`.

        Example:

        Given a component declarations:

        `{% component "my_comp" key=val key2=val2 %}`

        This function receives a list of tokens

        `['component', '"my_comp"', 'key=val', 'key2=val2']`

        `component` is the tag name, which we drop. `"my_comp"` is the component name,
        but we must remove the extra quotes. And we pass remaining tokens unmodified,
        as that's the input to the component.

        So in the end, we return a tuple:

        `('my_comp', ['key=val', 'key2=val2'])`
        """
        ...


class InternalTagFormatter:
    """
    Internal wrapper around user-provided TagFormatters, so that we validate the outputs.
    """

    def __init__(self, tag_formatter: TagFormatterABC):
        self.tag_formatter = tag_formatter

    def start_tag(self, name: str) -> str:
        tag = self.tag_formatter.start_tag(name)
        self._validate_tag(tag, "start_tag")
        return tag

    def end_tag(self, name: str) -> str:
        tag = self.tag_formatter.end_tag(name)
        self._validate_tag(tag, "end_tag")
        return tag

    def parse(self, tokens: List[str]) -> TagResult:
        return self.tag_formatter.parse(tokens)

    # NOTE: We validate the generated tags, so they contain only valid characters (\w - : . @ #)
    # and NO SPACE. Otherwise we wouldn't be able to distinguish a "multi-word" tag from several
    # single-word tags.
    def _validate_tag(self, tag: str, tag_type: str) -> None:
        if not tag:
            raise ValueError(
                f"{self.tag_formatter.__class__.__name__} returned an invalid tag for {tag_type}: '{tag}'."
                f" Tag cannot be empty"
            )

        if not TAG_RE.match(tag):
            raise ValueError(
                f"{self.tag_formatter.__class__.__name__} returned an invalid tag for {tag_type}: '{tag}'."
                f" Tag must contain only following chars: {VAR_CHARS}"
            )


class ComponentFormatter(TagFormatterABC):
    """
    The original django_component's component tag formatter, it uses the `component`
    and `endcomponent` tags, and the component name is gives as the first positional arg.

    Example as block:
    ```django
    {% component "mycomp" abc=123 %}
        {% fill "myfill" %}
            ...
        {% endfill %}
    {% endcomponent %}
    ```

    Example as inlined tag:
    ```django
    {% component "mycomp" abc=123 / %}
    ```
    """

    def __init__(self, tag: str):
        self.tag = tag

    def start_tag(self, name: str) -> str:
        return self.tag

    def end_tag(self, name: str) -> str:
        return f"end{self.tag}"

    def parse(self, tokens: List[str]) -> TagResult:
        tag, *args = tokens

        if not args:
            raise TemplateSyntaxError(f"{self.__class__.__name__}: Component tag did not receive tag name")

        # If the first arg is a kwarg, not a positional arg, then look for the "name" kwarg
        # for component name.
        if "=" in args[0]:
            comp_name = None
            final_args = []
            for kwarg in args:
                if not kwarg.startswith("name="):
                    final_args.append(kwarg)
                    continue

                if comp_name:
                    raise TemplateSyntaxError(
                        f"ComponentFormatter: 'name' kwarg for component '{comp_name}'" " was defined more than once."
                    )

                # NOTE: We intentionally do NOT add to `final_args` here
                # because we want to remove the the `name=` kwarg from args list
                comp_name = kwarg[5:]
        else:
            comp_name = args.pop(0)
            final_args = args

        if not comp_name:
            raise TemplateSyntaxError("Component name must be a non-empty quoted string, e.g. 'my_comp'")

        if not is_str_wrapped_in_quotes(comp_name):
            raise TemplateSyntaxError(f"Component name must be a string 'literal', got: {comp_name}")

        # Remove the quotes
        comp_name = resolve_string(comp_name)

        return TagResult(comp_name, final_args)


class ShorthandComponentFormatter(TagFormatterABC):
    """
    The component tag formatter that uses `<name>` / `end<name>` tags.

    This is similar to django-web-components and django-slippers syntax.

    Example as block:
    ```django
    {% mycomp abc=123 %}
        {% fill "myfill" %}
            ...
        {% endfill %}
    {% endmycomp %}
    ```

    Example as inlined tag:
    ```django
    {% mycomp abc=123 / %}
    ```
    """

    def start_tag(self, name: str) -> str:
        return name

    def end_tag(self, name: str) -> str:
        return f"end{name}"

    def parse(self, tokens: List[str]) -> TagResult:
        tokens = [*tokens]
        name = tokens.pop(0)
        return TagResult(name, tokens)


def get_tag_formatter(registry: "ComponentRegistry") -> InternalTagFormatter:
    """Returns an instance of the currently configured component tag formatter."""
    # Allow users to configure the component TagFormatter
    formatter_cls_or_str = registry.settings.TAG_FORMATTER

    if isinstance(formatter_cls_or_str, str):
        tag_formatter: TagFormatterABC = import_string(formatter_cls_or_str)
    else:
        tag_formatter = formatter_cls_or_str

    return InternalTagFormatter(tag_formatter)


# Default formatters
component_formatter = ComponentFormatter("component")
component_shorthand_formatter = ShorthandComponentFormatter()
