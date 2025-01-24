"""
Custom HTML lexer / parser. It is used to insert specific HTML attributes like `data-djc-id-...`
to HTML that was rendered by components.

This implementation is somewhat (~20%) faster than using BeautifulSoup,
but it's still about 50x slower than using the Rust parser. In practice, it can
take 5-6s to parse 2MB of HTML.

Thus, django-components by default uses the Rust implementation. And this implementation serves
as a fallback for an edge case if the Rust parser was not available, e.g. if Django was running on a platform
that's not supported by maturin. Maturin supports all major platforms like Linux, musllinux (Alpine Linux),
Windows, and MacOS.

The entrypoint is the `set_html_attributes()` function, which is given an HTML and HTML attributes to be set,
and returns the updated HTML and optionally a record of which tags were modified.
"""

import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Literal, Optional, Sequence, Tuple, Union

from django.utils.safestring import SafeString, mark_safe

HtmlState = Literal[
    "text",
    "comment",
    "cdata",
    "start_tag",
    "script",
    "interpolation",
]

DOCTYPE_START = "<!"
DOCTYPE_END = ">"
COMMENT_START = "<!--"
COMMENT_END = "-->"
CDATA_START = "<![CDATA["
CDATA_END = "]]>"
START_TAG_START = "<"
END_TAG_START = "</"
TAG_END = ">"
TAG_END_SELF_CLOSING = "/>"

TAG_WHITESPACE = (" ", "\t", "\n", "\r", "\f")
TAG_NAME_DELIIMITERS = (*TAG_WHITESPACE, TAG_END, TAG_END_SELF_CLOSING)

# See https://developer.mozilla.org/en-US/docs/Glossary/Void_element
VOID_ELEMENTS = (
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
)


@dataclass
class HTMLTagAttr:
    """E.g. `class="foo bar"` in `<div class="foo bar">...</div>`"""

    key: str
    value: Optional[str]
    start_index: int
    """
    Start index of the attribute (include both key and value),
    relative to the start of the owner HTMLTag.
    """
    quoted: bool
    """Whether the value is quoted (either with single or double quotes)"""

    @property
    def formatted(self) -> str:
        if self.value is None:
            return self.key

        if self.quoted:
            return self.key + '="' + self.value + '"'
        else:
            return self.key + "=" + self.value

    @property
    def length(self) -> int:
        return len(self.formatted)


@dataclass
class HTMLTag:
    """E.g. `<div class="foo bar">...</div>`"""

    name: str
    open_tag_start_index: int
    open_tag_length: int
    close_tag_start_index: int
    close_tag_length: int
    # length: int
    is_root: bool
    attrs: List[HTMLTagAttr]
    _html: Optional[str]

    # NOTE: Two values are equal ONLY if they are the same object.
    def __hash__(self) -> int:
        return id(self)

    def __eq__(self, other: Any) -> bool:
        return self is other

    def get_attr(self, key: Union[str, re.Pattern]) -> Optional[HTMLTagAttr]:
        """
        Get an attribute from the tag.

        Given `<div data-id="123">...</div>`

        ```python
        get_attr("data-id")  # HTMLTagAttr(key="data-id", value="123", ...)
        get_attr(re.compile(r"^data-.*"))  # HTMLTagAttr(key="data-id", value="123", ...)
        get_attr("data-djc-id-123")  # None
        ```
        """
        for attr in self.attrs:
            if isinstance(key, str):
                if attr.key == key:
                    return attr
            elif key.match(attr.key):
                return attr
        return None

    def has_attr(self, key: Union[str, re.Pattern]) -> bool:
        """
        Check if the tag has a specific attribute.
        To check for multiple patterns you can pass a regex.

        Given `<div data-id="123">...</div>`

        ```python
        has_attr("data-id")  # True
        has_attr(re.compile(r"^data-.*"))  # True
        has_attr("data-djc-id-123")  # False
        ```
        """
        for attr in self.attrs:
            if isinstance(key, str):
                if attr.key == key:
                    return True
            elif key.match(attr.key):
                return True
        return False

    def rename_attr(self, old_key: str, new_key: str) -> None:
        """
        Rename an attribute in the tag.

        Given `<div data-id="123">...</div>`

        ```python
        rename_attr("data-id", "data-id-new")  # <div data-id-new="123">...</div>
        ```
        """
        if self._html is None:
            raise ValueError("HTML is not set")

        found_index = -1
        for index, attr in enumerate(self.attrs):
            if attr.key == old_key:
                found_index = index
                break

        if found_index == -1:
            raise KeyError(f"Attribute with key '{old_key}' not found")

        # The attributes up to the renamed one are not affected.
        # For the rest, we need to adjust the start indices.
        attrs_len = len(self.attrs)
        found_attr = self.attrs[found_index]
        old_attr_length = found_attr.length

        # Update the attribute
        found_attr.key = new_key

        # Update the given HTML - omit the slice containing the attribute
        attr_start_index = self.open_tag_start_index + found_attr.start_index

        self._html = (
            self._html[:attr_start_index]  # noqa: E203
            + found_attr.formatted  # noqa: E203
            + self._html[attr_start_index + old_attr_length :]  # noqa: E203
        )  # fmt: skip

        # Update the indices
        key_size_change = len(new_key) - len(old_key)
        self.open_tag_length += key_size_change
        self.close_tag_start_index += key_size_change

        # Iterate only over the remaining attributes
        for index in range(found_index, attrs_len - 1):
            attr = self.attrs[index]
            attr.start_index += key_size_change

    def delete_attr(self, key: str) -> None:
        """
        Remove an attribute from the tag.

        Given `<div data-id="123">...</div>`

        ```python
        delete_attr("data-id")  # <div>...</div>
        ```
        """
        if self._html is None:
            raise ValueError("HTML is not set")

        found_index = -1
        for index, attr in enumerate(self.attrs):
            if attr.key == key:
                found_index = index
                break

        if found_index == -1:
            raise KeyError(f"Attribute with key '{key}' not found")

        # The attributes up to the removed one are not affected.
        # For the rest, we need to adjust the start index.
        attrs_len = len(self.attrs)
        found_attr = self.attrs.pop(found_index)

        self.open_tag_length -= found_attr.length
        self.close_tag_start_index -= found_attr.length

        # Iterate only over the remaining attributes
        for index in range(found_index, attrs_len - 1):
            attr = self.attrs[index]
            attr.start_index -= found_attr.length

        # Update the given HTML - omit the slice containing the attribute
        attr_start_index = self.open_tag_start_index + found_attr.start_index
        self._html = (
            self._html[:attr_start_index]  # noqa: E203
            + self._html[attr_start_index + found_attr.length :]  # noqa: E203
        )

    def add_attr(self, key: str, value: Optional[str], quoted: bool) -> None:
        """
        Add an attribute to the tag.

        Given `<div data-id="123">...</div>`

        ```python
        add_attr("data-djc-id", "123", True)  # <div data-id="123" data-djc-id="123">...</div>
        add_attr("data-djc-id", "123", False)  # <div data-id="123" data-djc-id=123>...</div>
        add_attr("data-djc-id-123", None, False)  # <div data-id="123" data-djc-id-123>...</div>
        ```
        """
        if self._html is None:
            raise ValueError("HTML is not set")

        new_attr = HTMLTagAttr(
            key=key,
            value=value,
            start_index=self.open_tag_length - 1,
            quoted=quoted,
        )
        self.attrs.append(new_attr)

        # Update the given HTML
        self.open_tag_length += new_attr.length + 1  # +1 for the space
        self.close_tag_start_index += new_attr.length + 1

        # Account for `/>`, in which case we have to insert the attribute BEFORE the `/>`
        is_self_closing = self._html[self.open_tag_start_index + new_attr.start_index - 1] == "/"
        self_closing_offset = -1 if is_self_closing else 0

        self._html = (
            self._html[: self.open_tag_start_index + new_attr.start_index + self_closing_offset]  # noqa: E203
            + " "
            + new_attr.formatted
            + self._html[self.open_tag_start_index + new_attr.start_index + self_closing_offset :]  # noqa: E203
        )

    def clear_attrs(self) -> None:
        """
        Remove all attributes from the tag.

        Given `<div class="foo bar">...</div>`

        ```python
        clear_attrs()  # <div>...</div>
        ```
        """
        while len(self.attrs):
            self.delete_attr(self.attrs[-1].key)

    def insert_content(self, content: str, index: int) -> None:
        """
        Insert content inside the tag at the given index.

        Given `<div>Hello</div>`

        ```python
        insert_content("World", 0)  # <div>World Hello</div>
        insert_content("World", -1)  # <div>Hello World</div>
        ```
        """
        if self._html is None:
            raise ValueError("HTML is not set")

        if index < 0:
            # +1 to offset for the end of the tag
            position = self.close_tag_start_index + index + 1
        else:
            position = self.open_tag_start_index + self.open_tag_length + index

        self._html = self._html[:position] + content + self._html[position:]
        self.close_tag_start_index += len(content)

    def clear_content(self) -> None:
        """
        Remove the tag's content.

        Given `<div>Hello</div>`

        ```python
        clear_content()  # <div></div>
        ```
        """
        if self._html is None:
            raise ValueError("HTML is not set")

        self._html = (
            self._html[: self.open_tag_start_index + self.open_tag_length]  # noqa: E203
            + self._html[self.close_tag_start_index :]  # noqa: E203
        )
        self.close_tag_start_index = self.open_tag_start_index + self.open_tag_length

    def replace_content(self, content: str) -> None:
        """
        Replace the tag's content with the given content.

        Given `<div>Hello</div>`

        ```python
        replace_content("World")  # <div>World</div>
        ```
        """
        self.clear_content()
        self.insert_content(content, index=0)

    def prepend(self, content: str) -> None:
        """
        Prepend content BEFORE the tag.

        Given `<div>Hello</div>`

        ```python
        prepend("World")  # World<div>Hello</div>
        ```
        """
        if self._html is None:
            raise ValueError("HTML is not set")

        self._html = (
            self._html[: self.open_tag_start_index]  # noqa: E203
            + content
            + self._html[self.open_tag_start_index :]  # noqa: E203
        )
        self.open_tag_start_index += len(content)
        self.close_tag_start_index += len(content)

    def append(self, content: str) -> None:
        """
        Append content AFTER the tag.

        Given `<div>Hello</div>`

        ```python
        append("World")  # <div>Hello</div>World
        ```
        """
        if self._html is None:
            raise ValueError("HTML is not set")

        end_index = self.close_tag_start_index + self.close_tag_length
        self._html = self._html[:end_index] + content + self._html[end_index:]

    def wrap(self, start_tag: str, end_tag: str) -> None:
        """
        Wrap the tag with the given start and end tags.

        Given `<div>Hello</div>`

        ```python
        wrap("<span>", "</span>")  # <span><div>Hello</div></span>
        ```
        """
        if self._html is None:
            raise ValueError("HTML is not set")

        content_end_index = self.close_tag_start_index + self.close_tag_length

        self._html = (
            self._html[: self.open_tag_start_index]  # noqa: E203
            + start_tag
            + self._html[self.open_tag_start_index : content_end_index]  # noqa: E203
            + end_tag
            + self._html[content_end_index:]  # noqa: E203
        )

        # NOTE: Attributes' indices are relative to the start tag, so they don't need updating
        self.open_tag_start_index += len(start_tag)
        self.close_tag_start_index += len(start_tag)

    def unwrap(self) -> None:
        """
        Remove opening and closing tags, leaving only the content.

        Given `<span><div>Hello</div></span>`

        ```python
        unwrap()  # <div>Hello</div>
        ```
        """
        if self._html is None:
            raise ValueError("HTML is not set")

        self._html = (
            # Text BEFORE the opening tag
            self._html[: self.open_tag_start_index]  # noqa: E203
            # Content
            + self._html[self.open_tag_start_index + self.open_tag_length : self.close_tag_start_index]  # noqa: E203
            # Text AFTER the closing tag
            + self._html[self.close_tag_start_index + self.close_tag_length :]  # noqa: E203
        )

    def rename_tag(self, new_tag_name: str) -> None:
        """
        Rename the tag.

        Given `<div>Hello</div>`

        ```python
        rename_tag("span")  # <span>Hello</span>
        ```
        """
        if self._html is None:
            raise ValueError("HTML is not set")

        size_change = len(new_tag_name) - len(self.name)

        tag_name_start_index = self.open_tag_start_index + 1
        tag_name_length = len(self.name)

        # Rename start tag
        self._html = (
            self._html[:tag_name_start_index]  # +1 to offset for the `<`
            + new_tag_name
            + self._html[tag_name_start_index + tag_name_length :]  # noqa: E203
        )

        # Offset for the change in tag name in START tag
        self.close_tag_start_index += size_change
        self.open_tag_length += size_change

        # Rename end tag
        self._html = (
            # +2 to offset for the `</`
            self._html[: self.close_tag_start_index + 2]  # noqa: E203
            + new_tag_name
            # -1 to offset for the `>`
            + self._html[self.close_tag_start_index + self.close_tag_length - 1 :]  # noqa: E203
        )

        self.name = new_tag_name

        # Offset for the change in tag name in END tag
        self.close_tag_length += size_change


# HTML Parser that accepts a callback that is called for each element tag (e.g. <div>, <span>, etc.)
# From within this callback, you can modify the tag's attributes and content,
# being able to add / remove attributes, prepend / append content, etc.
#
# For context, see https://github.com/django-components/django-components/issues/14#issuecomment-2604123744
#
# =================================
#
# NOTES:
#
# ```html
# <!doctype html>
# <html>
#   <head>
#     <title>Test</title>
#   </head>
#   <body>
#     <!-- "-->" -->
#     <div x="<!-- -->" y='adw' z=`dwada`>
#       <link />
#     </div>
#     <script type="text/javascript">
#       // <![CDATA[
#         console.log("</script>");
#       // ]]>
#     </script>
#   </body>
# </html>
# ```
#
# States:
# 1. Text (can enter tag, comment, CDATA)
# 2. Inside HTML comment (will end at `-- >`)
# 3. Inside CDATA (will end at `]]>`)
# 4. Inside start tag (can enter attribute, will end at `>` or `/>`)
#    - If either `/>` reached, or the tag is a void element, then the tag ends immediately
#    - Otherwise, at `>`, we enter the tag's content (the "text" state)
# 5. Inside tag content (will end at `</tagname >`)
# 6. Inside attribute (will end at `"` or `'`, escaped quotes do nothing)
#
# Rules:
# 1. HTML comments
#   1.1. Comments allowed only as content (NOT inside tags or attributes)
#   1.2. If in HTML comment, comment WILL end at `-- >` (without space). Quotes or backslash do nothing
#
# 2. CDATA
#   2.1. CDATA allowed only as content (NOT inside tags or attributes)
#   1.2. If in CDATA, it WILL end at `]]>`. Quotes or backslash do nothing.
#
# 3. Tags
#   3.1. Tags allowed only as content (NOT inside tags or attributes)
#   3.2. If we come across tag, ignore any content inside its attributes (<div x="" y='adw'>)
#   3.2. If in tag, tag WILL end at `>`. Quotes or backslash do nothing.
#
# 4. Attributes
#   4.1. Attributes allowed only inside tags
#   4.2. If in attribute, attribute WILL end at `"` or `'`. Escaped quotes do nothing.
#
# 5. Text
#   5.1. Text allowed only as content (NOT inside tags or attributes)
#   5.2. If in text, text WILL end at `<` (start of start tag), `</` (start of end tag),
#        `<!--` (start of comment), `<![CDATA[` (start of CDATA)
def _parse_html(
    text: str,
    on_tag: Callable[[HTMLTag, List[HTMLTag]], None],
) -> str:
    # State
    state: HtmlState = "text"

    total_len = len(text)
    index = 0
    normalized_index = 0
    tokens: List[str] = []  # Store tokens here instead of concatenating

    tag_stack: List[HTMLTag] = []

    # Pre-compile regex patterns for token matching
    # Escape special regex characters in tokens
    DOCTYPE_START_RE = re.escape(DOCTYPE_START)
    COMMENT_START_RE = re.escape(COMMENT_START)
    CDATA_START_RE = re.escape(CDATA_START)
    START_TAG_START_RE = re.escape(START_TAG_START)
    END_TAG_START_RE = re.escape(END_TAG_START)
    TAG_END_RE = re.escape(TAG_END)
    TAG_END_SELF_CLOSING_RE = re.escape(TAG_END_SELF_CLOSING)

    # Regex for script-specific tokens
    script_pattern = "|".join(
        [
            re.escape("//"),
            re.escape("/*"),
            re.escape("*/"),
            re.escape("'"),
            re.escape('"'),
            re.escape("`"),
            END_TAG_START_RE + "script",
        ]
    )
    SCRIPT_TOKENS_RE = re.compile("(" + script_pattern + ")")

    # Main regex pattern for all tokens in text state
    text_pattern = "|".join([DOCTYPE_START_RE, COMMENT_START_RE, CDATA_START_RE, END_TAG_START_RE, START_TAG_START_RE])
    TEXT_TOKENS_RE = re.compile("(" + text_pattern + ")")

    # Regex for tag-specific tokens
    tag_pattern = "|".join([TAG_END_RE, TAG_END_SELF_CLOSING_RE])
    TAG_TOKENS_RE = re.compile("(" + tag_pattern + ")")

    def add_token(token: str) -> None:
        nonlocal index
        nonlocal normalized_index

        tokens.append(token)
        token_len = len(token)
        index += token_len
        normalized_index += token_len

    def replace_next(length: int, replacement: str) -> None:
        nonlocal index
        nonlocal normalized_index

        tokens.append(replacement)
        index += length
        normalized_index += len(replacement)

    def taken_n(n: int) -> str:
        nonlocal index
        result = text[index : index + n]  # noqa: E203
        add_token(result)
        return result

    def take_until(
        tokens: Sequence[str],
        ignore: Optional[Sequence[str]] = None,
    ) -> str:
        nonlocal index
        nonlocal text

        # Process ignore tokens
        ignore_dict: Dict[str, Optional[str]] = {}
        if ignore is not None:
            for ignore_token in ignore:
                ignore_dict[ignore_token] = None

        # Find all token positions at once
        token_positions = []
        for token in tokens:
            pos = text.find(token, index)
            if pos != -1:
                token_positions.append((token, pos))

        # Find all ignore positions at once
        ignore_positions = []
        for token in ignore_dict:
            pos = text.find(token, index)
            if pos != -1:
                ignore_positions.append((token, pos))

        # No tokens found
        if not token_positions and not ignore_positions:
            # Take the rest of the text
            chunk = text[index:]
            add_token(chunk)
            index = total_len
            return chunk

        # Only regular tokens found
        if not ignore_positions:
            next_token, next_pos = min(token_positions, key=lambda x: x[1])
            if next_pos == index:
                return ""
            # Take text up to the token
            chunk = text[index:next_pos]
            add_token(chunk)
            index = next_pos
            return chunk

        # Only ignore tokens found
        if not token_positions:
            next_ignore, next_pos = min(ignore_positions, key=lambda x: x[1])
            if next_pos > index:
                # Take text up to the ignore token
                chunk = text[index:next_pos]
                add_token(chunk)
                index = next_pos
                result = chunk
            else:
                result = ""
            # Handle the ignore token
            replacement = ignore_dict[next_ignore]
            if replacement is not None:
                replace_next(len(next_ignore), replacement)
                result += replacement
            else:
                add_token(next_ignore)
                result += next_ignore
            index += len(next_ignore)
            return result

        # Both types of tokens found - take the nearest one
        next_token, token_pos = min(token_positions, key=lambda x: x[1])
        next_ignore, ignore_pos = min(ignore_positions, key=lambda x: x[1])

        if ignore_pos < token_pos:
            # Handle ignore token first
            if ignore_pos > index:
                chunk = text[index:ignore_pos]
                add_token(chunk)
                result = chunk
            else:
                result = ""
            replacement = ignore_dict[next_ignore]
            if replacement is not None:
                replace_next(len(next_ignore), replacement)
                result += replacement
            else:
                add_token(next_ignore)
                result += next_ignore
            index += len(next_ignore)
            return result
        else:
            # Found a regular token
            if token_pos == index:
                return ""
            chunk = text[index:token_pos]
            add_token(chunk)
            index = token_pos
            return chunk

    def take_while(tokens: Sequence[str]) -> str:
        nonlocal index
        nonlocal text

        token_chars: set[str] = set(tokens)
        start = index
        current = start

        # Find the longest sequence of matching characters
        while current < total_len:
            if text[current] not in token_chars:
                break
            current += 1

        if current > start:
            result = text[start:current]
            add_token(result)
            index = current
            return result

        return ""

    def peek_ahead(n: int) -> str:
        nonlocal index
        nonlocal text
        return text[index : index + n]  # noqa: E203

    # Find the longest token we need to check for
    max_token_len = max(
        len("".join(t) if isinstance(t, tuple) else t)
        for t in [
            COMMENT_START,
            COMMENT_END,
            CDATA_START,
            CDATA_END,
            DOCTYPE_START,
            DOCTYPE_END,
            START_TAG_START,
            END_TAG_START,
            TAG_END,
            TAG_END_SELF_CLOSING,
            "//",
            "/*",
            "*/",
            "'",
            '"',
            "`",
            "\\'",
        ]
    )

    def find_next_token() -> Optional[Tuple[str, int]]:
        """Find the next token based on current state"""
        nonlocal index
        nonlocal text

        if state == "text":
            match = TEXT_TOKENS_RE.search(text, index)
            if match:
                return match.group(0), match.start()
        elif state == "start_tag":
            match = TAG_TOKENS_RE.search(text, index)
            if match:
                return match.group(0), match.start()
        elif state == "script":
            match = SCRIPT_TOKENS_RE.search(text, index)
            if match:
                return match.group(0), match.start()
        return None

    # Case: Self-closing tag (e.g. `<div />`) or void element (e.g. `<input />`)
    # NOTE: If the tag is a void element, then it doesn't have a closing tag.
    #       If any other tag is using self-closing syntax, then it's technically invalid.
    #       See https://developer.mozilla.org/en-US/docs/Glossary/Void_element
    def process_self_closing_tag(token: str) -> None:
        nonlocal tokens
        nonlocal state
        nonlocal normalized_index

        tag = tag_stack[-1]

        add_token(token)
        # Mark the end of the start tag
        tag.open_tag_length = normalized_index - tag.open_tag_start_index

        normalized = "".join(tokens)  # Join tokens for on_tag callback
        tag._html = normalized
        on_tag(tag, tag_stack)
        normalized = tag._html
        tag._html = None
        tokens = [normalized]  # Replace tokens with the result
        normalized_index = len(normalized)

        # NOTE: When we pop, we enter "text" state, because only there we can enter tags.
        tag_stack.pop()
        state = "text"

    while index < total_len:
        char = text[index]
        curr_tag_name = tag_stack[-1].name if tag_stack else None

        # Find next token based on current state
        next_token = find_next_token()

        # Handle states that need exact token matches
        if state == "comment" and text[index : index + len(COMMENT_END)] == COMMENT_END:  # noqa: E203
            add_token(COMMENT_END)
            state = "text"
            continue
        elif state == "cdata" and text[index : index + len(CDATA_END)] == CDATA_END:  # noqa: E203
            add_token(CDATA_END)
            state = "text"
            continue

        # Handle current character if no token found or not at token position
        if next_token is None or next_token[1] > index:
            if state in ("comment", "cdata", "script", "text"):
                add_token(char)
                continue
            elif state == "start_tag":
                # Parse attributes
                if char in TAG_WHITESPACE:
                    add_token(char)
                    continue
                else:
                    # Start attribute parsing
                    tag = tag_stack[-1]
                    attrs: List[HTMLTagAttr] = []
                    while True:
                        take_while(TAG_WHITESPACE)
                        next_chars = peek_ahead(max_token_len)

                        # End of attributes
                        if next_chars.startswith(TAG_END) or next_chars.startswith(TAG_END_SELF_CLOSING):
                            break

                        attr_start_index = normalized_index - tag.open_tag_start_index
                        key = take_until(["=", *TAG_WHITESPACE, TAG_END, TAG_END_SELF_CLOSING])

                        # Has value
                        next_chars = peek_ahead(max_token_len)
                        if next_chars.startswith("="):
                            add_token("=")
                            next_chars = peek_ahead(max_token_len)
                            # E.g. `height="20"`
                            if next_chars.startswith("'") or next_chars.startswith('"'):
                                quote_char = taken_n(1)
                                value = take_until([quote_char])
                                add_token(quote_char)
                                quoted = True
                            # E.g. `height=20`
                            else:
                                value = take_until(TAG_NAME_DELIIMITERS)
                                quoted = False
                        else:
                            value = None
                            quoted = False

                        attrs.append(
                            HTMLTagAttr(
                                key=key,
                                value=value,
                                start_index=attr_start_index,
                                quoted=quoted,
                            )
                        )

                    tag.attrs = attrs
                    continue

        # At this point we know next_token is not None
        token, token_pos = next_token  # type: ignore

        # Comments, CDATA and DOCTYPE are all handled similarly - take the content until the end of the token
        if token == COMMENT_START and state == "text":
            add_token(COMMENT_START)
            state = "comment"
            continue
        elif token == CDATA_START and state == "text":
            add_token(CDATA_START)
            state = "cdata"
            continue
        elif token == DOCTYPE_START and state == "text":
            add_token(DOCTYPE_START)
            take_until([DOCTYPE_END])
            add_token(DOCTYPE_END)
            continue

        # Start StartTag
        elif token == START_TAG_START and state == "text" and not text[index:].startswith(END_TAG_START):
            start_index = normalized_index

            add_token(START_TAG_START)
            state = "start_tag"
            new_tag_name = take_until(TAG_NAME_DELIIMITERS).strip()
            if not new_tag_name:
                raise ValueError(f"Start tag MUST have a tag name (around index {index})")

            tag = HTMLTag(
                name=new_tag_name,
                open_tag_start_index=start_index,
                open_tag_length=0,
                close_tag_start_index=0,
                close_tag_length=0,
                attrs=[],
                is_root=not tag_stack,
                _html=None,
            )
            tag_stack.append(tag)
            continue

        # End StartTag (regular)
        elif state == "start_tag" and token == TAG_END:
            if not curr_tag_name:
                raise ValueError(f"Invalid state: Reached end of start tag without a tag name at index {index}")

            # Void elements may omit the `/` in the closing tag e.g. `<input >` instead of `<input />`
            if curr_tag_name.lower() in VOID_ELEMENTS:
                process_self_closing_tag(token)
                continue

            add_token(TAG_END)

            # Mark the end of the start tag
            if not tag_stack:
                raise ValueError(f"Invalid state: No tag in the stack at index {index}")
            tag = tag_stack[-1]
            tag.open_tag_length = normalized_index - tag.open_tag_start_index

            # NOTE: Inside a <script> tag, there may be nested tags as comments or strings
            # e.g.
            # ```html
            # <script>
            #  // <div></div>
            # console.log("</script>");
            # </script>
            # ```
            if curr_tag_name.lower() == "script":
                state = "script"
            else:
                state = "text"

            continue

        # End StartTag (self-closing)
        elif state == "start_tag" and token == TAG_END_SELF_CLOSING:
            if not curr_tag_name:
                raise ValueError("Invalid state: Reached self-closing tag without a tag name")

            process_self_closing_tag(token)
            continue

        # EndTag
        elif state == "text" and token == END_TAG_START:
            if not tag_stack:
                raise ValueError(f"Invalid state: Found end tag without matching start tag at index {index}")
            tag = tag_stack[-1]

            tag.close_tag_start_index = normalized_index

            add_token(END_TAG_START)
            tag_name = take_until([TAG_END]).strip()
            add_token(TAG_END)

            tag.close_tag_length = normalized_index - tag.close_tag_start_index

            if not tag_name:
                raise ValueError(f"End tag MUST have a tag name (around index {index})")

            if curr_tag_name is None or tag_name != curr_tag_name:
                raise ValueError(
                    f"End tag '{tag_name}' does not match the current tag '{curr_tag_name}' at index {index}"
                )

            normalized = "".join(tokens)  # Join tokens for on_tag callback
            tag._html = normalized
            on_tag(tag, tag_stack)
            normalized = tag._html
            tag._html = None
            tokens = [normalized]  # Replace tokens with the result
            normalized_index = len(normalized)

            # NOTE: When we pop, we enter "text" state, because only there we can enter tags.
            tag_stack.pop()
            state = "text"
            continue

        # Inside script tag
        elif state == "script":
            # Handle `//` JS comments
            if token == "//":
                add_token("//")
                take_until(["\n", "\r\n"])
                next_chars = peek_ahead(max_token_len)
                if next_chars.startswith("\r\n"):
                    add_token("\r\n")
                else:
                    add_token("\n")
                continue

            # Handle `/**/` JS comments
            elif token == "/*":
                add_token("/*")
                take_until(["*/"])
                add_token("*/")
                continue

            # Handle strings
            elif token == "'":
                add_token("'")
                take_until(["'"], ignore=["\\'"])
                add_token("'")
                continue

            elif token == '"':
                add_token('"')
                take_until(['"'], ignore=['\\"'])
                add_token('"')
                continue

            elif token == "`":
                add_token("`")
                take_until(["`"], ignore=["\\`"])
                add_token("`")
                continue

            # e.g. `</script`
            elif token == END_TAG_START + "script":
                # We've reached the end of the script tag, so delegate back to the "text" state
                state = "text"
                continue

            # Any other characters
            else:
                add_token(char)
                continue

        # Regular text
        elif state == "text":
            add_token(char)
            continue

        else:
            raise ValueError(f"Invalid state '{state}' with character '{char}' at index {index} in text '{text}'")

    return "".join(tokens)  # Join all tokens at the end


def set_html_attributes(
    html: str,
    root_attributes: List[str],
    all_attributes: List[str],
    *,
    watch_on_attribute: Optional[str] = None,
) -> Tuple[str, Dict[str, List[str]]]:
    """
    Transform HTML (multi-root) by adding attributes to root and all elements.

    Args:
        html (str): The HTML string to transform. Can be a fragment or full document.
        root_attributes (List[str]): List of attribute names to add to root elements only.
        all_attributes (List[str]): List of attribute names to add to all elements.
        watch_on_attribute (Optional[str]): If set, captures which attributes were added to
            elements with this attribute.

    Returns:
        A tuple containing:
            - The transformed HTML string
            - A list of tuples, each containing:
                - The value of the watched attribute
                - List of attributes that were added to that element

    Example:
        >>> html = '<div><p>Hello</p></div>'
        >>> transform_html(html, ['data-root-id'], ['data-v-123'])
        '<div data-root-id="" data-v-123=""><p data-v-123="">Hello</p></div>'

    Raises:
        ValueError: If the HTML is malformed or cannot be parsed.
    """
    # We keep track of which top-level child components there are, and which HTML attributes
    # should be set on them. We do so for performance reasons, to avoid having to re-parse the HTML
    # just to find the extra HTML attributes.
    #
    # NOTE: This is NOT the full list of child components. Those that are NOT top-level are
    # NOT captured here. For those non-top-level components, we know that we don't have to
    # add any extra HTML attributes.
    watched_entries: Dict[str, List[str]] = {}

    # NOTE: Non-element entities (comments, text, doctype, etc.) are automatically ignored.
    def on_tag(tag: HTMLTag, tag_stack: List[HTMLTag]) -> None:
        attrs_set_on_this_tag: List[str] = []
        watched_attr_value: Optional[str] = None

        # Set up watching if enabled
        if watch_on_attribute is not None:
            watched_attr = tag.get_attr(watch_on_attribute)
            if watched_attr is not None:
                watched_attr_value = watched_attr.value

            if watched_attr_value is not None:
                watched_entries[watched_attr_value] = attrs_set_on_this_tag

        # Root tags
        if tag.is_root:
            for root_attr_name in root_attributes:
                tag.add_attr(root_attr_name, None, quoted=False)
                attrs_set_on_this_tag.append(root_attr_name)

        # All tags
        for all_attr_name in all_attributes:
            tag.add_attr(all_attr_name, None, quoted=False)
            attrs_set_on_this_tag.append(all_attr_name)

    is_safestring = isinstance(html, SafeString)
    updated_html = _parse_html(html, on_tag)
    updated_html = mark_safe(updated_html) if is_safestring else updated_html

    return updated_html, watched_entries
