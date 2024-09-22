from selectolax.lexbor import LexborHTMLParser, LexborNode


def parse_node(html: str) -> LexborNode:
    parser = LexborHTMLParser(html)
    # NOTE: The parser automatically places <style> tags inside <head>
    # while <script> tags are inside <body>.
    return parser.body.child or parser.head.child  # type: ignore[union-attr, return-value]


def set_boolean_attribute(node: LexborNode, attr: str, value: bool) -> None:
    if value:
        # NOTE: Empty string as value to signify a truthy boolean attribute
        #       See https://developer.mozilla.org/en-US/docs/Glossary/Boolean/HTML
        node.attrs[attr] = ""  # type: ignore[index]
    else:
        if attr in node.attrs:  # type: ignore[operator]
            del node.attrs[attr]  # type: ignore[attr-defined]
