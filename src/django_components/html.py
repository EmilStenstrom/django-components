from typing import List, Union

from selectolax.lexbor import LexborHTMLParser, LexborNode


def parse_node(html: str) -> LexborNode:
    """
    Use this when you know the given HTML is a single node like

    `<div> Hi </div>`
    """
    tree = LexborHTMLParser(html)
    # NOTE: The parser automatically places <style> tags inside <head>
    # while <script> tags are inside <body>.
    return tree.body.child or tree.head.child  # type: ignore[union-attr, return-value]


def parse_document_or_nodes(html: str) -> Union[List[LexborNode], LexborHTMLParser]:
    """
    Use this if you do NOT know whether the given HTML is a full document
    with `<html>`, `<head>`, and `<body>` tags, or an HTML fragment.
    """
    html = html.strip()
    tree = LexborHTMLParser(html)
    is_fragment = is_html_parser_fragment(html, tree)

    if is_fragment:
        nodes = parse_multiroot_html(html)
        return nodes
    else:
        return tree


def parse_multiroot_html(html: str) -> List[LexborNode]:
    """
    Use this when you know the given HTML is a multiple nodes like

    `<div> Hi </div> <span> Hello </span>`
    """
    # NOTE: HTML / XML MUST have a single root. So, to support multiple
    # top-level elements, we wrap them in a dummy singular root.
    parser = LexborHTMLParser(f"<root>{html}</root>")

    # Get all contents of the root
    root_elem = parser.css_first("root")
    elems = [*root_elem.iter()] if root_elem else []
    return elems


def is_html_parser_fragment(html: str, tree: LexborHTMLParser) -> bool:
    # If we pass only an HTML fragment to the parser, like `<div>123</div>`, then
    # the parser automatically wraps it in `<html>`, `<head>`, and `<body>` tags.
    #
    # <html>
    #   <head>
    #   </head>
    #   <body>
    #     <div>123</div>
    #   </body>
    # </html>
    #
    # But also, as described in Lexbor (https://github.com/lexbor/lexbor/issues/183#issuecomment-1611975340),
    # if the parser first comes across HTML tags that could go into the `<head>`,
    # it will put them there, and then put the rest in `<body>`.
    #
    # So `<link href="..." /><div></div>` will be parsed as
    #
    # <html>
    #   <head>
    #     <link href="..." />
    #   </head>
    #   <body>
    #     <div>123</div>
    #   </body>
    # </html>
    #
    # BUT, if we're dealing with a fragment, we want to parse it correctly as
    # a multi-root fragment:
    #
    # <link href="..." />
    # <div>123</div>
    #
    # The way do so is that we:
    # 1. Take the original HTML string
    # 2. Subtract the content of parsed `<head>` from the START of the original HTML
    # 3. Subtract the content of parsed `<body>` from the END of the original HTML
    # 4. Then, if we have an HTML fragment, we should be left with empty string (maybe whitespace?).
    # 5. But if we have an HTML document, then the "space between" should contain text,
    #    because we didn't account for the length of `<html>`, `<head>`, `<body>` tags.
    #
    # TODO: Replace with fragment parser?
    #       See https://github.com/rushter/selectolax/issues/74#issuecomment-2404470344
    parsed_head_html: str = tree.head.html  # type: ignore
    parsed_body_html: str = tree.body.html  # type: ignore
    head_content = parsed_head_html[len("<head>") : -len("</head>")]  # noqa: E203
    body_content = parsed_body_html[len("<body>") : -len("</body>")]  # noqa: E203
    between_content = html[len(head_content) : -len(body_content)].strip()  # noqa: E203

    is_fragment = not html or not between_content
    return is_fragment
