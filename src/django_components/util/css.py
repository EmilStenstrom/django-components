import re
from typing import TYPE_CHECKING, Optional, Type

from django_components.util.misc import hash_comp_cls

if TYPE_CHECKING:
    from django_components.component import Component

# TODO
# TODO - INSTEAD USE https://doc.courtbouillon.org/tinycss2/stable/api_reference.html#tinycss2.ast.Node
#      - SO WE HANDLE ALSOS NESTED @media blocks AND COMMENTS
# TODO

# Regex to capture top-level CSS rules in the form:
# `selector { declarations }`
#
# This won't handle nested @media blocks or other complex cases.
# DOTALL so we can capture multiline declarations.
CSS_RULE_PATTERN = re.compile(r"([^{}]+)\{([^}]*)\}", re.DOTALL)


def scope_css(css_code: str, scope_id: str) -> str:
    """
    Inspired by Vue's implementation, this function will scope CSS selectors
    by appending a given `scope_id` to every top-level selector.

    This is a naive approach that doesn't handle nested @media blocks nor comments
    or other complex cases.

    For example, given the CSS:

    ```css
    .foo .bar > a, .baz:hover {
      color: red;
    }
    ```

    And a `scope_id` of '[data-djc-scope-abc123]', this function will return:

    ```css
    .foo[data-djc-scope-abc123] .bar[data-djc-scope-abc123] > a[data-djc-scope-abc123], .baz[data-djc-scope-abc123]:hover {
      color: red;
    }
    ```

    To opt-out of CSS scoping, you can prepend individual selectors with `:root`:

    ```css
    :root .foo .bar > a, .baz:hover {
      color: red;
    }
    ```
    """  # noqa: E501

    def transform_selector_block(selector_block: str) -> str:
        # Split on commas to handle grouped selectors
        selectors = [s.strip() for s in selector_block.split(",")]

        # Do a simple sub: for each chunk of non-whitespace or "combinator" (space, >, +, ~) chars,
        # we append the scope_id.
        #
        # This means ".foo .bar:hover" => ".foo[data-djc-xxx] .bar:hover[data-dj-xxx]"
        def _append_scope(m: re.Match[str]) -> str:
            token = m.group(0)
            return token + scope_id

        transformed_selectors = []
        for selector in selectors:
            # If the selector starts with ':root', skip rewriting entirely
            # E.g. ':root .escape' remains ':root .escape'
            if selector.startswith(":root"):
                transformed_selectors.append(selector)
                continue

            # Replace every chunk of non-combinator characters:
            # [^>+~\s]+  means "one or more chars that are not > + ~ or whitespace"
            selector_with_scope = re.sub(r"[^>+~\s]+", _append_scope, selector)

            transformed_selectors.append(selector_with_scope)

        return ", ".join(transformed_selectors)

    # 1) Remove CSS block comments:
    comment_pattern = re.compile(r"/\*.*?\*/", re.DOTALL)
    css_code = comment_pattern.sub("", css_code)

    # 2) Match top-level rules:  selector { declarations }
    #    We’ll then rebuild the entire CSS by substituting each {selector}{body} match
    result = []
    last_pos = 0
    for match in CSS_RULE_PATTERN.finditer(css_code):
        selector_block, body_block = match.group(1), match.group(2)
        start, end = match.span()

        # Everything between last_pos and the start of this rule is untouched
        result.append(css_code[last_pos:start])

        # Transform the selector portion
        new_selectors = transform_selector_block(selector_block.strip())

        # Rebuild the rule
        result.append(f"{new_selectors} {{ {body_block} }}")

        last_pos = end

    # Append any leftover text (e.g. after the last rule)
    result.append(css_code[last_pos:])

    return "\n".join(result)


def gen_css_scope_id(comp_cls: Type["Component"]) -> Optional[str]:
    if not comp_cls.css_scoped or not comp_cls.css:
        return None
    return hash_comp_cls(comp_cls, include_name=False)
