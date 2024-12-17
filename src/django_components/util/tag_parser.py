from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple, Union

TAG_WHITESPACES = (" ", "\t", "\n", "\r", "\f")
TAG_QUOTES = ("'", '"', '_("', "_('")
TAG_FILTER_JOINERS = ("|", ":")
TAG_SPREAD = "..."


@dataclass
class TagAttrPart:
    """
    Django tag attributes may consist of multiple parts, being separated by filter pipes (`|`)
    or filter arguments (`:`). This class represents a single part of the attribute value.

    E.g. in the following tag:
    ```django
    {% component "my_comp" key="my val's" key2=val2|filter1:"one" %}
    ```

    The `key2` attribute has three parts: `val2`, `filter1` and `"one"`.
    """

    value: str
    """The actual value of the part, e.g. `val2` in `key2=val2` or `my string` in `_("my string")`."""
    prefix: Optional[str]
    """
    If this part is filter or filter arguent, `prefix` is the string that connects it to the previous part.
    E.g. the `|` and `:` in `key2=val2|filter1:"one"`.
    """
    quoted: Optional[str]
    """Whether the value is quoted, and the character that's used for the quotation"""
    translation: bool
    """Whether the value is a translation string, e.g. `_("my string")`"""

    def __post_init__(self) -> None:
        if self.translation and not self.quoted:
            raise ValueError("Translation value must be quoted")

    def formatted(self) -> str:
        """
        Format the part as a string that can be used in a Django template tag.
        E.g. `val2`, `|filter1:"one"`, `_("my string")`.
        """
        value = f"{self.quoted}{self.value}{self.quoted}" if self.quoted else self.value
        if self.translation:
            value = f"_({value})"
        if self.prefix:
            value = f"{self.prefix}{value}"
        return value


@dataclass
class TagAttr:
    key: Optional[str]
    parts: List[TagAttrPart]
    start_index: int
    """
    Start index of the attribute (include both key and value),
    relative to the start of the owner Tag.
    """
    spread: bool
    """Whether the value is a spread syntax, e.g. `...my_var`"""

    def formatted_value(self) -> str:
        value = "".join(part.formatted() for part in self.parts)
        if self.spread:
            value = f"{TAG_SPREAD}{value}"
        return value

    def formatted(self) -> str:
        s = self.formatted_value()
        if self.key:
            return f"{self.key}={s}"
        return s


# Parse the content of a Django template tag like this:
#
# ```django
# {% component "my_comp" key="my val's" key2=val2 %}
# ```
#
# into a tag name and a list of attributes:
#
# ```python
# {
#     "component": "component",
# }
# ```
def parse_tag_attrs(text: str) -> Tuple[str, List[TagAttr]]:
    index = 0
    normalized = ""

    def add_token(token: Union[str, Tuple[str, ...]]) -> None:
        nonlocal normalized
        nonlocal index

        text = "".join(token)
        normalized += text
        index += len(text)

    def is_next_token(*tokens: Union[str, Tuple[str, ...]]) -> bool:
        if not tokens:
            raise ValueError("No tokens provided")

        def is_token_match(token: Union[str, Tuple[str, ...]]) -> bool:
            if not token:
                raise ValueError("Empty token")

            for token_index, token_char in enumerate(token):
                text_char = text[index + token_index] if index + token_index < len(text) else None
                if text_char is None or text_char != token_char:
                    return False
            return True

        for token in tokens:
            is_match = is_token_match(token)
            if is_match:
                return True
        return False

    def taken_n(n: int) -> str:
        nonlocal index
        result = text[index : index + n]  # noqa: E203
        add_token(result)
        return result

    # tag_name = take_until([" ", "\t", "\n", "\r", "\f", ">", "/>"])
    def take_until(
        tokens: Sequence[Union[str, Tuple[str, ...]]],
        ignore: Optional[Sequence[Union[str, Tuple[str, ...]],]] = None,
    ) -> str:
        nonlocal index
        nonlocal text

        result = ""
        while index < len(text):
            char = text[index]

            ignore_token_match: Optional[Union[str, Tuple[str, ...]]] = None
            for ignore_token in ignore or []:
                if is_next_token(ignore_token):
                    ignore_token_match = ignore_token

            if ignore_token_match:
                result += "".join(ignore_token_match)
                add_token(ignore_token_match)
                continue

            if any(is_next_token(token) for token in tokens):
                return result

            result += char
            add_token(char)
        return result

    # tag_name = take_while([" ", "\t", "\n", "\r", "\f"])
    def take_while(tokens: Sequence[Union[str, Tuple[str, ...]]]) -> str:
        nonlocal index
        nonlocal text

        result = ""
        while index < len(text):
            char = text[index]

            if any(is_next_token(token) for token in tokens):
                result += char
                add_token(char)
            else:
                return result

        return result

    def parse_attr_parts() -> List[TagAttrPart]:
        parts: List[TagAttrPart] = []

        while index < len(text) and not is_next_token("=", *TAG_WHITESPACES):
            is_translation = False
            value: str = ""
            quoted: Optional[str] = None
            prefix: Optional[str] = None

            if is_next_token(*TAG_FILTER_JOINERS):
                prefix = taken_n(1)  # | or :

            # E.g. `height="20"` or `height=_("my_text")` or `height="my_text"|fil1:"one"`
            if is_next_token(*TAG_QUOTES):
                # NOTE: Strings may be wrapped in `_()` to allow for translation.
                # See https://docs.djangoproject.com/en/5.1/topics/i18n/translation/#string-literals-passed-to-tags-and-filters  # noqa: E501
                if is_next_token("_("):
                    taken_n(2)  # _(
                    is_translation = True

                # NOTE: We assume no space between the translation syntax and the quote.
                quote_char = taken_n(1)  # " or '

                # NOTE: Handle escaped quotes like \" or \', and continue until we reach the closing quote.
                value = take_until([quote_char], ignore=["\\" + quote_char])
                # Handle the case when there is a trailing quote, e.g. when a text value is not closed.
                # `{% component 'my_comp' text="organis %}`

                if is_next_token(quote_char):
                    add_token(quote_char)
                    if is_translation:
                        taken_n(1)  # )
                    quoted = quote_char
                else:
                    quoted = None
                    value = quote_char + value
            # E.g. `height=20` or `height=my_var` or or `height=my_var|fil1:"one"`
            else:
                value = take_until(["=", *TAG_WHITESPACES, *TAG_FILTER_JOINERS])
                quoted = None

            parts.append(
                TagAttrPart(
                    value=value,
                    prefix=prefix,
                    quoted=quoted,
                    translation=is_translation,
                )
            )

        return parts

    # Parse attributes
    attrs: List[TagAttr] = []
    while index < len(text):
        # Skip whitespace
        take_while(TAG_WHITESPACES)

        start_index = len(normalized)
        key = None

        # If token starts with a quote, we assume it's a value without key part.
        # e.g. `component 'my_comp'`
        # Otherwise, parse the key.
        if is_next_token(*TAG_QUOTES, TAG_SPREAD):
            key = None
        else:
            parts = parse_attr_parts()

            # We've reached the end of the text
            if not parts:
                break

            # Has value
            if is_next_token("="):
                add_token("=")
                key = "".join(part.formatted() for part in parts)
            else:
                # Actually was a value without key part
                key = None
                attrs.append(
                    TagAttr(
                        key=key,
                        parts=parts,
                        start_index=start_index,
                        spread=False,
                    )
                )
                continue

        # Move the spread syntax out of the way, so that we properly handle what's next.
        is_spread = is_next_token(TAG_SPREAD)
        if is_spread:
            taken_n(len(TAG_SPREAD))  # ...

        parts = parse_attr_parts()

        attrs.append(
            TagAttr(
                key=key,
                parts=parts,
                start_index=start_index,
                spread=is_spread,
            )
        )

    return normalized, attrs
