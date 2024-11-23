from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple, Union

TAG_WHITESPACE = (" ", "\t", "\n", "\r", "\f")


@dataclass
class TagAttr:
    key: Optional[str]
    value: str
    start_index: int
    """
    Start index of the attribute (include both key and value),
    relative to the start of the owner Tag.
    """
    quoted: bool
    """Whether the value is quoted (either with single or double quotes)"""


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

    # Parse
    attrs: List[TagAttr] = []
    while index < len(text):
        # Skip whitespace
        take_while(TAG_WHITESPACE)

        start_index = len(normalized)

        # If token starts with a quote, we assume it's a value without key part.
        # e.g. `component 'my_comp'`
        # Otherwise, parse the key.
        if is_next_token("'", '"', '_("', "_('"):
            key = None
        else:
            key = take_until(["=", *TAG_WHITESPACE])

            # We've reached the end of the text
            if not key:
                break

            # Has value
            if is_next_token("="):
                add_token("=")
            else:
                # Actually was a value without key part
                attrs.append(
                    TagAttr(
                        key=None,
                        value=key,
                        start_index=start_index,
                        quoted=False,
                    )
                )
                continue

        # Parse the value
        #
        # E.g. `height="20"`
        # NOTE: We don't need to parse the attributes fully. We just need to account
        # for the quotes.
        if is_next_token("'", '"', '_("', "_('"):
            # NOTE: Strings may be wrapped in `_()` to allow for translation.
            # See https://docs.djangoproject.com/en/5.1/topics/i18n/translation/#string-literals-passed-to-tags-and-filters  # noqa: E501
            if is_next_token("_("):
                taken_n(2)  # _(
                is_translation = True
            else:
                is_translation = False

            # NOTE: We assume no space between the translation syntax and the quote.
            quote_char = taken_n(1)  # " or '

            # NOTE: Handle escaped quotes like \" or \', and continue until we reach the closing quote.
            value = take_until([quote_char], ignore=["\\" + quote_char])
            # Handle the case when there is a trailing quote, e.g. when a text value is not closed.
            # `{% component 'my_comp' text="organis %}`

            if is_next_token(quote_char):
                add_token(quote_char)
                if is_translation:
                    value += taken_n(1)  # )
                quoted = True
            else:
                quoted = False
                value = quote_char + value
                if is_translation:
                    value = "_(" + value
        # E.g. `height=20`
        else:
            value = take_until(TAG_WHITESPACE)
            quoted = False

        attrs.append(
            TagAttr(
                key=key,
                value=value,
                start_index=start_index,
                quoted=quoted,
            )
        )

    return normalized, attrs
