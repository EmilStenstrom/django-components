from django.test import TestCase

from django_components.html import insert_before_end, parse_node, transform_html_document

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

    def test_insert_before_end(self):
        node = parse_node(
            """
            <div class="abc xyz" data-id="123">
                <ul>
                    <li>Hi</li>
                </ul>
            </div>
            """
        )

        insert_before_end(node, '<script src="abc"></script>')

        self.assertHTMLEqual(
            node.html,
            """
            <div class="abc xyz" data-id="123">
                <ul>
                    <li>Hi</li>
                </ul>
                <script src="abc"></script>
            </div>
            """,
        )

    def test_transform_html_document(self):
        def do_transform(head, body):
            insert_before_end(head, '<link href="abc">')
            insert_before_end(head, '<link href="abc2">')
            insert_before_end(body, '<script src="abc"></script>')
            insert_before_end(body, '<script src="abc2"></script>')

        transformed = transform_html_document(
            """
            <!-- lol -->
            <!DOCTYPE html="5678909876">
            <html>
                <head></head>
                <body class="abc"></body>
            </html>
            dwadaw
            """,
            do_transform,
        )

        self.assertHTMLEqual(
            transformed,
            """
            <!doctype html="5678909876">
            <html>
                <head><link href="abc"></head>
                <body class="abc"><script src="abc"></script></body>
            </html>
            dwadaw
            """,
        )
