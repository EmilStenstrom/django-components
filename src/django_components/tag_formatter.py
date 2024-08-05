import abc
import re
from typing import List, Tuple, Type

from django.template import TemplateSyntaxError
from django.utils.module_loading import import_string

from django_components.app_settings import app_settings
from django_components.expression import resolve_string
from django_components.template_parser import VAR_CHARS
from django_components.utils import is_str_wrapped_in_quotes

TAG_RE = re.compile(r"^[{chars}]+$".format(chars=VAR_CHARS))


class TagFormatterABC(abc.ABC):
    @abc.abstractmethod
    def format_block_start_tag(self, name: str) -> str:
        """Formats the start tag of a block component."""
        ...

    @abc.abstractmethod
    def format_block_end_tag(self, name: str) -> str:
        """Formats the end tag of a block component."""
        ...

    @abc.abstractmethod
    def format_inline_tag(self, name: str) -> str:
        """Formats the start tag of an inline component."""
        ...

    @abc.abstractmethod
    def parse_block_start_tag(self, tokens: List[str]) -> Tuple[str, List[str]]:
        """
        Given the tokens (words) of a component start tag, this function extracts
        the component name from the tokens list, and returns a tuple of
        `(component_name, component_input)`.

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

    @abc.abstractmethod
    def parse_inline_tag(self, tokens: List[str]) -> Tuple[str, List[str]]:
        """
        Given the tokens (words) of a component inline tag, this function extracts
        the component name from the tokens list, and returns a tuple of
        `(component_name, component_input)`.

        Example:

        Given a component declarations:

        `{% #my_comp key=val key2=val2 %}`

        This function receives a list of tokens

        `['#my_comp', 'key=val', 'key2=val2']`

        We drop the leading hash from `#my_comp` to obtain the component name.
        And we pass remaining tokens unmodified, as that's the input to the component.

        So in the end, we return a tuple:

        `('my_comp', ['key=val', 'key2=val2'])`
        """
        ...

    # NOTE: We validate the generated tags, so they contain only valid characters (\w - : . @ #)
    # and NO SPACE. Otherwise we wouldn't be able to distinguish a "multi-word" tag from several
    # single-word tags.
    def validate_tag(self, tag: str, tag_type: str) -> None:
        if not tag:
            raise ValueError(
                f"{self.__class__.__name__} returned an invalid tag for {tag_type}: '{tag}'."
                f" Tag cannot be empty"
            )

        if not TAG_RE.match(tag):
            raise ValueError(
                f"{self.__class__.__name__} returned an invalid tag for {tag_type}: '{tag}'."
                f" Tag must contain only following chars: {VAR_CHARS}"
            )

    def safe_format_block_start_tag(self, name: str) -> str:
        """Formats the start tag of a block component. Raises ValueError if the tag is invalid."""
        tag = self.format_block_start_tag(name)
        self.validate_tag(tag, "block_start_tag")
        return tag

    def safe_format_block_end_tag(self, name: str) -> str:
        """Formats the end tag of a block component. Raises ValueError if the tag is invalid."""
        tag = self.format_block_end_tag(name)
        self.validate_tag(tag, "block_end_tag")
        return tag

    def safe_format_inline_tag(self, name: str) -> str:
        """Formats the start tag of an inline component. Raises ValueError if the tag is invalid."""
        tag = self.format_inline_tag(name)
        self.validate_tag(tag, "inline_tag")
        return tag


# TODO - Update docs that these are names of positional args
# TODO - Add tests
class ComponentTagFormatter(TagFormatterABC):
    """
    The original django_component's component tag formatter, it uses the `component`
    tag name, whereas the component name is gives as a string as the second token.

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
    {% #component "mycomp" abc=123 %}
    ```
    """

    def format_block_start_tag(self, name: str) -> str:
        return "component"

    def format_block_end_tag(self, name: str) -> str:
        return "endcomponent"

    def format_inline_tag(self, name: str) -> str:
        return "#component"

    def parse_block_start_tag(self, tokens: List[str]) -> Tuple[str, List[str]]:
        if tokens[0] != "component":
            raise TemplateSyntaxError(
                f"ComponentTagFormatter: Component block start tag parser received tag '{tokens[0]}',"
                " expected 'component'"
            )
        return self._parse_start_or_inline_tag(tokens)

    def parse_inline_tag(self, tokens: List[str]) -> Tuple[str, List[str]]:
        if tokens[0] != "#component":
            raise TemplateSyntaxError(
                f"ComponentTagFormatter: Component block start tag parser received tag '{tokens[0]}',"
                " expected '#component'"
            )
        return self._parse_start_or_inline_tag(tokens)

    def _parse_start_or_inline_tag(self, tokens: List[str]) -> Tuple[str, List[str]]:
        _, *comp_args = tokens

        if not comp_args:
            raise TemplateSyntaxError(
                "ComponentTagFormatter: Component tag did not receive tag name"
            )

        # First arg is a kwarg, not a positional arg. Hence look for the "name" kwarg
        # for component name.
        if "=" in comp_args[0]:
            comp_name = None
            final_args = []
            for kwarg in comp_args:
                if not kwarg.startswith("name="):
                    final_args.append(kwarg)
                    continue

                if comp_name:
                    raise TemplateSyntaxError(
                        f"ComponentTagFormatter: 'name' kwarg for component '{comp_name}'"
                        " was defined more than once."
                    )

                # NOTE: We intentionally do NOT add to `final_args` here
                # because we want to remove the the `name=` kwarg from args list
                comp_name = kwarg[5:]
        else:
            comp_name = comp_args.pop(0)
            final_args = comp_args

        if not comp_name:
            raise TemplateSyntaxError("Component name must be a non-empty quoted string, e.g. 'my_comp'")

        if not is_str_wrapped_in_quotes(comp_name):
            raise TemplateSyntaxError(f"Component name must be a string 'literal', got: {comp_name}")

        # Remove the quotes
        comp_name = resolve_string(comp_name)

        return comp_name, final_args


# TODO - Add tests
# TODO - UPDATE DOCS FOR EVERYTHING - ShorthandTagFormatter, ComponentTagFormatter, TagFormatterABC, tag_formatter settings
# TODO - DOCUMENT IN README HOW TAG_FORMATTER WORKS
# TODO - DOCUMENT IN README HOW INLINE VS "BLOCK" components work
class ShorthandTagFormatter(TagFormatterABC):
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
    {% #mycomp abc=123 %}
    ```
    """

    def format_block_start_tag(self, name: str) -> str:
        return name

    def format_block_end_tag(self, name: str) -> str:
        return f"end{name}"

    def format_inline_tag(self, name: str) -> str:
        return f"#{name}"

    def parse_block_start_tag(self, tokens: List[str]) -> Tuple[str, List[str]]:
        name = tokens.pop(0)
        if not name:
            raise TemplateSyntaxError(
                "ShorthandTagFormatter: '{name}' is not a valid component name"
            )
        return name, tokens

    def parse_inline_tag(self, tokens: List[str]) -> Tuple[str, List[str]]:
        name = tokens.pop(0)
        if not name.startswith("#"):
            raise TemplateSyntaxError(
                "ShorthandTagFormatter: Component inline tag must start with hash (#),"
                f" got '{tokens[0]}'"
            )

        name = name[1:]
        if not name:
            raise TemplateSyntaxError(
                "ShorthandTagFormatter: '{name}' is not a valid component name"
            )

        return name, tokens


def get_component_tag_formatter() -> TagFormatterABC:
    """Returns an instance of the currently configured component tag formatter."""
    curr_formatter_cls_or_str = app_settings.TAG_FORMATTER
    if isinstance(curr_formatter_cls_or_str, str):
        curr_formatter_cls: Type[TagFormatterABC] = import_string(curr_formatter_cls_or_str)
    else:
        curr_formatter_cls = curr_formatter_cls_or_str

    return curr_formatter_cls()
