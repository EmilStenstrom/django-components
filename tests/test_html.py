from typing import List, cast

from django.test import TestCase
from selectolax.lexbor import LexborHTMLParser, LexborNode

from django_components.html import is_html_parser_fragment, parse_document_or_nodes, parse_multiroot_html, parse_node

from .django_test_setup import setup_test_config

setup_test_config({"autodiscover": False})


class HtmlTests(TestCase):
    def test_parse_node(self):
        node = parse_node(
            """
            <div class="abc xyz" data-id="123">
                <ul>
                    <li>Hi</li>
                </ul>
            </div>
            """
        )
        node.attrs["id"] = "my-id"  # type: ignore[index]
        node.css("li")[0].attrs["class"] = "item"  # type: ignore[index]

        self.assertHTMLEqual(
            node.html,
            """
            <div class="abc xyz" data-id="123" id="my-id">
                <ul>
                    <li class="item">Hi</li>
                </ul>
            </div>
            """,
        )

    def test_parse_multiroot_html(self):
        html = """
            <div class="abc xyz" data-id="123">
                <ul>
                    <li>Hi</li>
                </ul>
            </div>
            <main id="123" class="one">
                <div>
                    42
                </div>
            </main>
            <span>
                Hello
            </span>
        """
        root, nodes = parse_multiroot_html(html)

        self.assertHTMLEqual(
            root.html,
            f"""
            <root>
                {html}
            </root>
            """,
        )
        self.assertHTMLEqual(
            nodes[0].html,
            """
            <div class="abc xyz" data-id="123">
                <ul>
                    <li>Hi</li>
                </ul>
            </div>
            """,
        )
        self.assertHTMLEqual(
            nodes[1].html,
            """
            <main id="123" class="one">
                <div>
                    42
                </div>
            </main>
            """,
        )
        self.assertHTMLEqual(
            nodes[2].html,
            """
            <span>
                Hello
            </span>
            """,
        )

    def test_is_html_parser_fragment(self):
        fragment_html = """
            <div class="abc xyz" data-id="123">
                <ul>
                    <li>Hi</li>
                </ul>
            </div>
            <main id="123" class="one">
                <div>
                    42
                </div>
            </main>
            <span>
                Hello
            </span>
        """
        fragment_tree = LexborHTMLParser(fragment_html)
        fragment_result = is_html_parser_fragment(fragment_html, fragment_tree)

        self.assertEqual(fragment_result, True)

        doc_html = """
            <!doctype html>
            <html>
              <head>
                <link href="https://..." />
              </head>
              <body>
                <div class="abc xyz" data-id="123">
                    <ul>
                        <li>Hi</li>
                    </ul>
                </div>
              </body>
            </html>
        """
        doc_tree = LexborHTMLParser(doc_html)
        doc_result = is_html_parser_fragment(doc_html, doc_tree)

        self.assertEqual(doc_result, False)

    def test_parse_document_or_nodes__fragment(self):
        fragment_html = """
            <div class="abc xyz" data-id="123">
                <ul>
                    <li>Hi</li>
                </ul>
            </div>
            <main id="123" class="one">
                <div>
                    42
                </div>
            </main>
            <span>
                Hello
            </span>
        """
        fragment_result = cast(List[LexborNode], parse_document_or_nodes(fragment_html))

        self.assertHTMLEqual(
            fragment_result[0].html,
            """
            <div class="abc xyz" data-id="123">
                <ul>
                    <li>Hi</li>
                </ul>
            </div>
            """,
        )
        self.assertHTMLEqual(
            fragment_result[1].html,
            """
            <main id="123" class="one">
                <div>
                    42
                </div>
            </main>
            """,
        )
        self.assertHTMLEqual(
            fragment_result[2].html,
            """
            <span>
                Hello
            </span>
            """,
        )

    def test_parse_document_or_nodes__mixed(self):
        fragment_html = """
            <link href="" />
            <div class="abc xyz" data-id="123">
                <ul>
                    <li>Hi</li>
                </ul>
            </div>
            <main id="123" class="one">
                <div>
                    42
                </div>
            </main>
            <span>
                Hello
            </span>
        """
        fragment_result = cast(List[LexborNode], parse_document_or_nodes(fragment_html))

        self.assertHTMLEqual(
            fragment_result[0].html,
            """
            <link href="" />
            """,
        )
        self.assertHTMLEqual(
            fragment_result[1].html,
            """
            <div class="abc xyz" data-id="123">
                <ul>
                    <li>Hi</li>
                </ul>
            </div>
            """,
        )
        self.assertHTMLEqual(
            fragment_result[2].html,
            """
            <main id="123" class="one">
                <div>
                    42
                </div>
            </main>
            """,
        )
        self.assertHTMLEqual(
            fragment_result[3].html,
            """
            <span>
                Hello
            </span>
            """,
        )

    def test_parse_document_or_nodes__doc(self):
        doc_html = """
            <!doctype html>
            <html>
              <head>
                <link href="https://..." />
              </head>
              <body>
                <div class="abc xyz" data-id="123">
                    <ul>
                        <li>Hi</li>
                    </ul>
                </div>
              </body>
            </html>
        """
        fragment_result = cast(LexborHTMLParser, parse_document_or_nodes(doc_html))

        self.assertHTMLEqual(
            fragment_result.html,
            """
            <!doctype html>
            <html>
              <head>
                <link href="https://..." />
              </head>
              <body>
                <div class="abc xyz" data-id="123">
                    <ul>
                        <li>Hi</li>
                    </ul>
                </div>
              </body>
            </html>
            """,
        )
