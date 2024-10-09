from django.test import TestCase

from django_components.html import parse_multiroot_html, parse_node

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
