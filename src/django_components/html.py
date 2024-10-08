import re
from typing import Dict, Optional, Protocol, Union, cast

from selectolax.lexbor import LexborHTMLParser, LexborNode


def parse_node(html: str) -> LexborNode:
    parser = LexborHTMLParser(html)
    # NOTE: The parser automatically places <style> tags inside <head>
    # while <script> tags are inside <body>.
    return parser.body.child or parser.head.child  # type: ignore[union-attr, return-value]


# NOTE: While Selectolax offers way to insert a node before or after
# a current one, it doesn't allow to insert one node into another.
# See https://github.com/rushter/selectolax/issues/126
def html_insert_before_end(html: str, insert_html: str) -> str:
    regex = re.compile(r"<\/\w+>$")
    return regex.sub(
        lambda m: insert_html + m[0],
        html.strip(),
    )


def insert_before_end(node: LexborNode, insert: Union[LexborNode, str]) -> None:
    the_insert = insert.html or "" if isinstance(insert, LexborNode) else insert
    new_node_html = html_insert_before_end(node.html or "", the_insert)
    new_node = parse_node(new_node_html)
    node.replace_with(new_node)  # type: ignore[arg-type]
    node.insert_before(new_node)  # type: ignore[arg-type]


HTML_ROOT_TAGS_REGEX = re.compile(
    r"<!doctype|<html|</html|<head|</head|<body|</body",
    re.IGNORECASE,
)

HTML_ROOT_TAGS_REVERSE_REGEX = re.compile(
    r"<doctype_|<html_|</html_|<head_|</head_|<body_|</body_",
    re.IGNORECASE,
)


html_tag_escapes: Dict[str, str] = {
    "<!doctype": "<doctype_",
    "<html": "<html_",
    "</html": "</html_",
    "<head": "<head_",
    "</head": "</head_",
    "<body": "<body_",
    "</body": "</body_",
}
html_tag_escapes_reverse = {val: key for key, val in html_tag_escapes.items()}


class TransformHtmlCallback(Protocol):
    def __call__(self, head: Optional[LexborNode], body: Optional[LexborNode]) -> None: ...  # noqa: #704


def transform_html_document(html: str, transform: TransformHtmlCallback) -> str:
    # Escape <!doctype>, <html>, <head>, and <body> tags, because Selectolax treats them
    # specially, which makes it impossible to edit them.
    def on_replace_match(match: "re.Match[str]") -> str:
        match_str = match[0].lower()
        return html_tag_escapes[match_str]

    escaped_html = HTML_ROOT_TAGS_REGEX.sub(on_replace_match, html)

    # Selectolax now treats the escaped tags as custom tags, and so Selectolax wraps
    # the whole content in extra <html><head></head><body> CONTENT </body></html>.
    # So the actual HTML is under `.body.child`
    wrapper_tree = LexborHTMLParser(escaped_html).body
    escaped_tree = wrapper_tree.child if wrapper_tree else None
    if escaped_tree:
        body_matches = escaped_tree.css("body_")
        head_matches = escaped_tree.css("head_")
        body = body_matches[0] if body_matches else None
        head = head_matches[0] if head_matches else None
    else:
        body = None
        head = None

    # Finally, we can pass the actual <head> and <body> tags to be transformed
    # The transformations happen in-place in Selectolax.
    transform(head, body)
    transformed_html = cast(str, escaped_tree.html) if escaped_tree else ""

    # After the transformations are applied, we need to un-escape the <doctype_>, <head_>, etc tags
    def on_reverse_replace_match(match: "re.Match[str]") -> str:
        match_str = match[0].lower()
        return html_tag_escapes_reverse[match_str]

    final_html = HTML_ROOT_TAGS_REVERSE_REGEX.sub(on_reverse_replace_match, transformed_html)

    # NOTE: Because of how we work around selectolax to enable modifying the <body> and <head>
    # tags, selectolax also adds `</doctype_>` at the end of the content when we serialize the HTML.
    # So we have to remove that.
    return final_html[: -len("</doctype_>")]
