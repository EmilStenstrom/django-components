from django.test import TestCase
from typing import List

from django_components.util.html_parser import HTMLTag, _parse_html as parse_html, set_html_attributes

from .django_test_setup import setup_test_config

setup_test_config({"autodiscover": False})


# This same set of tests is also found in djc_html_parser, to ensure that
# this implementation can be replaced with the djc_html_parser's Rust-based implementation
class TestHTMLParser(TestCase):
    def test_basic_transformation(self):
        html = "<div><p>Hello</p></div>"
        result, _ = set_html_attributes(html, root_attributes=["data-root"], all_attributes=["data-all"])
        expected = '<div data-root data-all><p data-all>Hello</p></div>'
        assert result == expected

    def test_multiple_roots(self):
        html = "<div>First</div><span>Second</span>"
        result, _ = set_html_attributes(html, root_attributes=["data-root"], all_attributes=["data-all"])
        expected = '<div data-root data-all>First</div><span data-root data-all>Second</span>'
        assert result == expected

    def test_complex_html(self):
        html = """
            <div class="container" id="main">
                <header class="flex">
                    <h1 title="Main Title">Hello & Welcome</h1>
                    <nav data-existing="true">
                        <a href="/home">Home</a>
                        <a href="/about" class="active">About</a>
                    </nav>
                </header>
                <main>
                    <article data-existing="true">
                        <h2>Article 1</h2>
                        <p>Some text with <strong>bold</strong> and <em>emphasis</em></p>
                        <img src="test.jpg" alt="Test Image"/>
                    </article>
                </main>
            </div>
            <footer id="footer">
                <p>&copy; 2024</p>
            </footer>
        """

        result, _ = set_html_attributes(html, ["data-root"], ["data-all", "data-v-123"])

        expected = """
            <div class="container" id="main" data-root data-all data-v-123>
                <header class="flex" data-all data-v-123>
                    <h1 title="Main Title" data-all data-v-123>Hello & Welcome</h1>
                    <nav data-existing="true" data-all data-v-123>
                        <a href="/home" data-all data-v-123>Home</a>
                        <a href="/about" class="active" data-all data-v-123>About</a>
                    </nav>
                </header>
                <main data-all data-v-123>
                    <article data-existing="true" data-all data-v-123>
                        <h2 data-all data-v-123>Article 1</h2>
                        <p data-all data-v-123>Some text with <strong data-all data-v-123>bold</strong> and <em data-all data-v-123>emphasis</em></p>
                        <img src="test.jpg" alt="Test Image" data-all data-v-123/>
                    </article>
                </main>
            </div>
            <footer id="footer" data-root data-all data-v-123>
                <p data-all data-v-123>&copy; 2024</p>
            </footer>
        """
        assert result == expected

    def test_void_elements(self):
        test_cases = [
            ('<meta charset="utf-8">', '<meta charset="utf-8" data-root data-v-123>'),
            ('<meta charset="utf-8"/>', '<meta charset="utf-8" data-root data-v-123/>'),
            ("<div><br><hr></div>", '<div data-root data-v-123><br data-v-123><hr data-v-123></div>'),
            ('<img src="test.jpg" alt="Test">', '<img src="test.jpg" alt="Test" data-root data-v-123>'),
        ]

        for input_html, expected in test_cases:
            result, _ = set_html_attributes(input_html, ["data-root"], ["data-v-123"])
            assert result == expected

    def test_html_head_with_meta(self):
        html = """
            <head>
                <meta charset="utf-8">
                <title>Test Page</title>
                <link rel="stylesheet" href="style.css">
                <meta name="description" content="Test">
            </head>"""

        result, _ = set_html_attributes(html, ["data-root"], ["data-v-123"])

        expected = """
            <head data-root data-v-123>
                <meta charset="utf-8" data-v-123>
                <title data-v-123>Test Page</title>
                <link rel="stylesheet" href="style.css" data-v-123>
                <meta name="description" content="Test" data-v-123>
            </head>"""
        assert result == expected

    def test_expand_empty_elements(self):
        test_cases = [
            # Non-void elements should expand
            ("<div/>", '<div data-root data-v-123></div>'),
            ("<p/>", '<p data-root data-v-123></p>'),
            ("<div><span/></div>", '<div data-root data-v-123><span data-v-123></span></div>'),
            # Void elements should always be self-closing
            ("<div><img/><br/></div>", '<div data-root data-v-123><img data-v-123/><br data-v-123/></div>'),
        ]

        for input_html, expected in test_cases:
            result, _ = set_html_attributes(input_html, ["data-root"], ["data-v-123"])
            assert result == expected

    def test_watch_attribute(self):
        html = """
            <div data-id="123">
                <p>Regular element</p>
                <span data-id="456">Nested element</span>
                <img data-id="789" src="test.jpg"/>
            </div>"""

        result, captured = set_html_attributes(html, ["data-root"], ["data-v-123"], watch_on_attribute="data-id")
        expected = """
            <div data-id="123" data-root data-v-123>
                <p data-v-123>Regular element</p>
                <span data-id="456" data-v-123>Nested element</span>
                <img data-id="789" src="test.jpg" data-v-123/>
            </div>"""

        assert result == expected

        # Verify attribute capturing
        assert len(captured) == 3

        # Root element should have both root and all attributes
        assert captured["123"] == ["data-root", "data-v-123"]

        # Non-root elements should only have all attributes
        assert captured["456"] == ["data-v-123"]
        assert captured["789"] == ["data-v-123"]

    def test_whitespace_preservation(self):
        html = """<div>
            <p>  Hello  World  </p>
            <span> Text with spaces </span>
        </div>"""

        result, _ = set_html_attributes(html, ["data-root"], ["data-all"])
        expected = """<div data-root data-all>
            <p data-all>  Hello  World  </p>
            <span data-all> Text with spaces </span>
        </div>"""
        assert result == expected


# This checks that the parser works irrespective of the main use case
class TestHTMLParserInternal(TestCase):
    def test_parse_simple_tag(self):
        processed_tags = []

        def on_tag(tag: HTMLTag, tag_stack: List[HTMLTag]) -> None:
            processed_tags.append(tag)

        html = "<div>Hello</div>"
        result = parse_html(html, on_tag, expand_shorthand_tags=False)

        self.assertEqual(result, html)
        self.assertEqual(len(processed_tags), 1)
        self.assertEqual(processed_tags[0].name, "div")

    def test_parse_nested_tags(self):
        processed_tags = []

        def on_tag(tag: HTMLTag, tag_stack: List[HTMLTag]) -> None:
            processed_tags.append((tag.name, len(tag_stack)))

        html = "<div><p>Hello</p></div>"
        result = parse_html(html, on_tag, expand_shorthand_tags=False)

        self.assertEqual(result, html)
        self.assertEqual(len(processed_tags), 2)
        self.assertEqual(processed_tags[0], ("p", 2))  # p tag with stack depth 2
        self.assertEqual(processed_tags[1], ("div", 1))  # div tag with stack depth 1

    def test_parse_attributes(self):
        processed_tags = []

        def on_tag(tag: HTMLTag, tag_stack: List[HTMLTag]) -> None:
            processed_tags.append(tag)

        html = '<div class="container" id="main">Hello</div>'
        result = parse_html(html, on_tag, expand_shorthand_tags=False)

        self.assertEqual(result, html)
        self.assertEqual(len(processed_tags), 1)
        self.assertEqual(len(processed_tags[0].attrs), 2)
        self.assertEqual(processed_tags[0].attrs[0].key, "class")
        self.assertEqual(processed_tags[0].attrs[0].value, "container")
        self.assertEqual(processed_tags[0].attrs[1].key, "id")
        self.assertEqual(processed_tags[0].attrs[1].value, "main")

    def test_void_elements(self):
        processed_tags = []

        def on_tag(tag: HTMLTag, tag_stack: List[HTMLTag]) -> None:
            processed_tags.append(tag)

        html = '<img src="test.jpg" />'
        result = parse_html(html, on_tag, expand_shorthand_tags=False)

        self.assertEqual(result, html)
        self.assertEqual(len(processed_tags), 1)
        self.assertEqual(processed_tags[0].name, "img")
        self.assertEqual(processed_tags[0].attrs[0].key, "src")
        self.assertEqual(processed_tags[0].attrs[0].value, "test.jpg")

    def test_add_attr(self):
        def on_tag(tag: HTMLTag, tag_stack: List[HTMLTag]) -> None:
            tag.add_attr("data-test", "value", quoted=True)
            tag.add_attr("hidden", None, quoted=False)

        html = "<div>Content</div>"
        result = parse_html(html, on_tag, expand_shorthand_tags=False)
        self.assertEqual(result, '<div data-test="value" hidden>Content</div>')

    def test_rename_attr(self):
        def on_tag(tag: HTMLTag, tag_stack: List[HTMLTag]) -> None:
            tag.rename_attr("class", "className")

        html = '<div class="test">Content</div>'
        result = parse_html(html, on_tag, expand_shorthand_tags=False)
        self.assertEqual(result, '<div className="test">Content</div>')

    def test_delete_attr(self):
        def on_tag(tag: HTMLTag, tag_stack: List[HTMLTag]) -> None:
            tag.delete_attr("id")

        html = '<div class="test" id="main">Content</div>'
        result = parse_html(html, on_tag, expand_shorthand_tags=False)
        self.assertEqual(result, '<div class="test" >Content</div>')

    def test_clear_attrs(self):
        def on_tag(tag: HTMLTag, tag_stack: List[HTMLTag]) -> None:
            tag.clear_attrs()

        html = '<div class="test" id="main" data-value="123">Content</div>'
        result = parse_html(html, on_tag, expand_shorthand_tags=False)
        self.assertEqual(result, "<div   >Content</div>")

    def test_add_after_clearing_attrs(self):
        def on_tag(tag: HTMLTag, tag_stack: List[HTMLTag]) -> None:
            tag.clear_attrs()
            tag.add_attr("data-test", "value", quoted=True)

        html = '<div class="test" id="main" data-value="123">Content</div>'
        result = parse_html(html, on_tag, expand_shorthand_tags=False)
        self.assertEqual(result, '<div    data-test="value">Content</div>')

    def test_insert_content(self):
        def on_tag(tag: HTMLTag, tag_stack: List[HTMLTag]) -> None:
            tag.insert_content("Start ", 0)
            tag.insert_content(" End", -1)

        html = "<div>Content</div>"
        result = parse_html(html, on_tag, expand_shorthand_tags=False)
        self.assertEqual(result, "<div>Start Content End</div>")

    def test_clear_content(self):
        def on_tag(tag: HTMLTag, tag_stack: List[HTMLTag]) -> None:
            tag.clear_content()

        html = "<div>Original content</div>"
        result = parse_html(html, on_tag, expand_shorthand_tags=False)
        self.assertEqual(result, "<div></div>")

    def test_replace_content(self):
        def on_tag(tag: HTMLTag, tag_stack: List[HTMLTag]) -> None:
            tag.replace_content("New content")

        html = "<div>Original content</div>"
        result = parse_html(html, on_tag, expand_shorthand_tags=False)
        self.assertEqual(result, "<div>New content</div>")

    def test_prepend_append(self):
        def on_tag(tag: HTMLTag, tag_stack: List[HTMLTag]) -> None:
            tag.prepend("Before ")
            tag.append(" after")

        html = "<div>Content</div>"
        result = parse_html(html, on_tag, expand_shorthand_tags=False)
        self.assertEqual(result, "Before <div>Content</div> after")

    def test_wrap(self):
        def on_tag(tag: HTMLTag, tag_stack: List[HTMLTag]) -> None:
            tag.wrap('<section class="wrapper">', "</section>")

        html = "<div>Content</div>"
        result = parse_html(html, on_tag, expand_shorthand_tags=False)
        self.assertEqual(result, '<section class="wrapper"><div>Content</div></section>')

    def test_unwrap(self):
        def on_tag(tag: HTMLTag, tag_stack: List[HTMLTag]) -> None:
            if tag.name == "span":
                tag.unwrap()

        html = "<div><span>Content</span></div>"
        result = parse_html(html, on_tag, expand_shorthand_tags=False)
        self.assertEqual(result, "<div>Content</div>")

    def test_rename_tag(self):
        def on_tag(tag: HTMLTag, tag_stack: List[HTMLTag]) -> None:
            tag.rename_tag("article")

        html = "<div>Content</div>"
        result = parse_html(html, on_tag, expand_shorthand_tags=False)
        self.assertEqual(result, "<article>Content</article>")

    def test_get_attr_has_attr(self):
        def on_tag(tag: HTMLTag, tag_stack: List[HTMLTag]) -> None:
            assert tag.has_attr("class")
            assert not tag.has_attr("id")
            attr = tag.get_attr("class")
            assert attr is not None and attr.value == "test"
            assert tag.get_attr("id") is None

        html = '<div class="test">Content</div>'
        result = parse_html(html, on_tag, expand_shorthand_tags=False)
        self.assertEqual(result, html)

    def test_tag_manipulation_complex(self):
        def on_tag(tag: HTMLTag, tag_stack: List[HTMLTag]) -> None:
            if tag.name == "div":
                # Test add_attr
                tag.add_attr("data-new", "value", quoted=True)

                # Test rename_attr
                tag.rename_attr("class", "className")

                # Test delete_attr
                tag.delete_attr("id")

                # Test insert_content
                tag.insert_content("<span>Start</span>", 0)
                tag.insert_content("<span>End</span>", -1)

                # Test wrap
                tag.wrap("<section>", "</section>")

            elif tag.name == "p":
                # Test get_attr and has_attr
                assert tag.has_attr("class")
                attr = tag.get_attr("class")
                assert attr is not None and attr.value == "inner"

                # Test clear_attrs
                tag.clear_attrs()

                # Test clear_content and replace_content
                tag.clear_content()
                tag.replace_content("New content")

                # Test prepend and append
                tag.prepend("Before ")
                tag.append(" after")

                # Test rename_tag
                tag.rename_tag("article")

                # Test unwrap
                tag.unwrap()

        html = '<div class="test" id="main"><p class="inner">Original content</p></div>'
        expected = '<section><div className="test"  data-new="value"><span>Start</span>Before New content after<span>End</span></div></section>'
        result = parse_html(html, on_tag, expand_shorthand_tags=True)

        self.assertEqual(result, expected)

    def test_expand_shorthand_tags(self):
        html = '<div class="test"><p class="inner"/></div>'
        result = parse_html(html, on_tag=lambda *args, **kwargs: None, expand_shorthand_tags=True)
        self.assertEqual(result, '<div class="test"><p class="inner"></p></div>')

    def test_complex_html(self):
        processed_tags = []

        def on_tag(tag: HTMLTag, tag_stack: List[HTMLTag]) -> None:
            processed_tags.append(tag)
            if tag.name == "body":
                # Test attribute manipulation
                tag.add_attr("data-modified", "true", quoted=True)
                tag.rename_attr("class", "className")

            elif tag.name == "div":
                # Test content manipulation
                tag.insert_content("<!-- Modified -->", 0)
                tag.wrap('<div class="wrapper">', "</div>")

            elif tag.name == "p":
                # Test attribute without value
                tag.add_attr("hidden", None, quoted=False)

        html = """<!DOCTYPE html>
        <html lang="en" data-theme="light">
            <!-- Header section -->
            <head>
                <meta charset="UTF-8"/>
                <title>Complex Test</title>
                <link rel="stylesheet" href="style.css">
                <script type="text/javascript">
                    // Single line comment with tags: <div></div>
                    /* Multi-line comment
                       </script> 
                    */
                    const template = `<div>${value}</div>`;
                    console.log('</script>');
                </script>
            </head>
            <body class="main" id="content" data-loaded>
                <![CDATA[
                    Some CDATA content with <tags> that should be preserved
                ]]>
                <div class="container" style="display: flex">
                    <img src="test.jpg" alt="Test Image"/>
                    <p>Hello <strong>World</strong>!</p>
                    <input type="text" disabled value="test"/>
                </div>
            </body>
        </html>"""

        expected = """<!DOCTYPE html>
        <html lang="en" data-theme="light">
            <!-- Header section -->
            <head>
                <meta charset="UTF-8"/>
                <title>Complex Test</title>
                <link rel="stylesheet" href="style.css">
                <script type="text/javascript">
                    // Single line comment with tags: <div></div>
                    /* Multi-line comment
                       </script> 
                    */
                    const template = `<div>${value}</div>`;
                    console.log('</script>');
                </script>
            </head>
            <body className="main" id="content" data-loaded data-modified="true">
                <![CDATA[
                    Some CDATA content with <tags> that should be preserved
                ]]>
                <div class="wrapper"><div class="container" style="display: flex"><!-- Modified -->
                    <img src="test.jpg" alt="Test Image"/>
                    <p hidden>Hello <strong>World</strong>!</p>
                    <input type="text" disabled value="test"/>
                </div></div>
            </body>
        </html>"""

        result = parse_html(html, on_tag, expand_shorthand_tags=False)

        self.assertEqual(result, expected)

        # Verify the structure of processed tags
        self.assertEqual(len(processed_tags), 12)  # Count all non-void elements

        # Verify specific tag attributes
        html_tag = next(tag for tag in processed_tags if tag.name == "html")
        self.assertEqual(len(html_tag.attrs), 2)
        self.assertEqual(html_tag.attrs[0].key, "lang")
        self.assertEqual(html_tag.attrs[0].value, "en")
        self.assertEqual(html_tag.attrs[1].key, "data-theme")
        self.assertEqual(html_tag.attrs[1].value, "light")

        # Verify void elements
        img_tag = next(tag for tag in processed_tags if tag.name == "img")
        self.assertEqual(len(img_tag.attrs), 2)
        self.assertEqual(img_tag.attrs[0].key, "src")
        self.assertEqual(img_tag.attrs[0].value, "test.jpg")

        # Verify attribute without value
        body_tag = next(tag for tag in processed_tags if tag.name == "body")
        data_loaded_attr = next(attr for attr in body_tag.attrs if attr.key == "data-loaded")
        self.assertIsNone(data_loaded_attr.value)

        # Verify modified attributes
        self.assertTrue(any(attr.key == "data-modified" and attr.value == "true" for attr in body_tag.attrs))
        self.assertTrue(any(attr.key == "className" and attr.value == "main" for attr in body_tag.attrs))

        # Verify p tag modifications
        p_tag = next(tag for tag in processed_tags if tag.name == "p")
        self.assertTrue(any(attr.key == "hidden" and attr.value is None for attr in p_tag.attrs))
