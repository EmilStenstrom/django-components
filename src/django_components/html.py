from typing import List, Tuple, cast

from selectolax.lexbor import LexborHTMLParser, LexborNode


def parse_node(html: str) -> LexborNode:
    parser = LexborHTMLParser(html)
    # NOTE: The parser automatically places <style> tags inside <head>
    # while <script> tags are inside <body>.
    return parser.body.child or parser.head.child  # type: ignore[union-attr, return-value]


def parse_multiroot_html(html: str) -> Tuple[LexborNode, List[LexborNode]]:
    # NOTE: HTML / XML MUST have a single root. So, to support multiple
    # top-level elements, we wrap them in a dummy singular root.
    parser = LexborHTMLParser(f"<root>{html}</root>")

    # Get all contents of the root
    root_elem = parser.css_first("root")
    elems = [*root_elem.iter()] if root_elem else []
    return cast(LexborNode, root_elem), elems
