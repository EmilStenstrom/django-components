from django.test import TestCase

from django_components.util.html import SoupNode
from .django_test_setup import setup_test_config

setup_test_config({"autodiscover": False})


class HtmlTests(TestCase):
    def test_beautifulsoup_impl(self):
        nodes = SoupNode.from_fragment(
            """
            <div class="abc xyz" data-id="123">
                <ul>
                    <li>Hi</li>
                </ul>
            </div>
            <!-- I'M COMMENT -->
            <button>
                Click me!
            </button>
            """.strip()
        )

        # Items: <div>, whitespace, comment, whitespace, <button>
        self.assertEqual(len(nodes), 5)

        self.assertHTMLEqual(
            nodes[0].to_html(),
            """
            <div class="abc xyz" data-id="123">
                <ul>
                    <li>Hi</li>
                </ul>
            </div>
            """
        )
        self.assertHTMLEqual(
            nodes[2].to_html(),
            "<!-- I&#x27;M COMMENT -->",
        )
        self.assertHTMLEqual(
            nodes[4].to_html(),
            """
            <button>
                Click me!
            </button>
            """
        )

        self.assertEqual(nodes[0].name(), "div")
        self.assertEqual(nodes[4].name(), "button")

        self.assertEqual(nodes[0].is_element(), True)
        self.assertEqual(nodes[2].is_element(), False)
        self.assertEqual(nodes[4].is_element(), True)

        self.assertEqual(nodes[0].get_attr("class"), "abc xyz")
        self.assertEqual(nodes[4].get_attr("class"), None)

        nodes[0].set_attr("class", "123 456")
        nodes[4].set_attr("class", "abc def")
        self.assertEqual(nodes[0].get_attr("class"), "123 456")
        self.assertEqual(nodes[4].get_attr("class"), "abc def")

        self.assertHTMLEqual(
            nodes[0].to_html(),
            """
            <div class="123 456" data-id="123">
                <ul>
                    <li>Hi</li>
                </ul>
            </div>
            """
        )
        self.assertHTMLEqual(
            nodes[4].to_html(),
            """
            <button class="abc def">
                Click me!
            </button>
            """
        )

        # Setting attr to `True` will set it to boolean attribute,
        # while setting it to `False` will remove the attribute.
        nodes[4].set_attr("disabled", True)
        self.assertHTMLEqual(
            nodes[4].to_html(),
            """
            <button class="abc def" disabled>
                Click me!
            </button>
            """
        )
        nodes[4].set_attr("disabled", False)
        self.assertHTMLEqual(
            nodes[4].to_html(),
            """
            <button class="abc def">
                Click me!
            </button>
            """
        )

        # Return self
        self.assertEqual(nodes[0].node, nodes[0].find_tag("div").node)
        # Return descendant
        li = nodes[0].find_tag("li")
        self.assertHTMLEqual(li.to_html(), "<li>Hi</li>")
        # Return None when not found
        self.assertEqual(nodes[0].find_tag("main"), None)

        # Insert children
        li.append_children([nodes[4]])
        self.assertHTMLEqual(
            li.to_html(),
            """
            <li>
                Hi
                <button class="abc def">
                    Click me!
                </button>
            </li>
            """,
        )
