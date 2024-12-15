from django_components.util.tag_parser import TagAttr, parse_tag_attrs

from .django_test_setup import setup_test_config
from .testutils import BaseTestCase

setup_test_config({"autodiscover": False})


class TagParserTests(BaseTestCase):
    def test_tag_parser(self):
        _, attrs = parse_tag_attrs("component 'my_comp' key=val key2='val2 two' ")

        expected_attrs = [
            TagAttr(key=None, value="component", start_index=0, quoted=None, spread=False, translation=False),
            TagAttr(key=None, value="my_comp", start_index=10, quoted="'", spread=False, translation=False),
            TagAttr(key="key", value="val", start_index=20, quoted=None, spread=False, translation=False),
            TagAttr(key="key2", value="val2 two", start_index=28, quoted="'", spread=False, translation=False),
        ]

        self.assertEqual(attrs, expected_attrs)
        self.assertEqual(
            [a.formatted() for a in attrs],
            [
                "component",
                "'my_comp'",
                "key=val",
                "key2='val2 two'",
            ],
        )

    def test_tag_parser_nested_quotes(self):
        _, attrs = parse_tag_attrs("component 'my_comp' key=val key2='val2 \"two\"' text=\"organisation's\" ")

        expected_attrs = [
            TagAttr(key=None, value="component", start_index=0, quoted=None, spread=False, translation=False),
            TagAttr(key=None, value="my_comp", start_index=10, quoted="'", spread=False, translation=False),
            TagAttr(key="key", value="val", start_index=20, quoted=None, spread=False, translation=False),
            TagAttr(key="key2", value='val2 "two"', start_index=28, quoted="'", spread=False, translation=False),
            TagAttr(key="text", value="organisation's", start_index=46, quoted='"', spread=False, translation=False),
        ]

        self.assertEqual(attrs, expected_attrs)
        self.assertEqual(
            [a.formatted() for a in attrs],
            [
                "component",
                "'my_comp'",
                "key=val",
                "key2='val2 \"two\"'",
                'text="organisation\'s"',
            ],
        )

    def test_tag_parser_trailing_quote_single(self):
        _, attrs = parse_tag_attrs("component 'my_comp' key=val key2='val2 \"two\"' text=\"organisation's\" 'abc")

        expected_attrs = [
            TagAttr(key=None, value="component", start_index=0, quoted=None, spread=False, translation=False),
            TagAttr(key=None, value="my_comp", start_index=10, quoted="'", spread=False, translation=False),
            TagAttr(key="key", value="val", start_index=20, quoted=None, spread=False, translation=False),
            TagAttr(key="key2", value='val2 "two"', start_index=28, quoted="'", spread=False, translation=False),
            TagAttr(key="text", value="organisation's", start_index=46, quoted='"', spread=False, translation=False),
            TagAttr(key=None, value="'abc", start_index=68, quoted=None, spread=False, translation=False),
        ]

        self.assertEqual(attrs, expected_attrs)
        self.assertEqual(
            [a.formatted() for a in attrs],
            [
                "component",
                "'my_comp'",
                "key=val",
                "key2='val2 \"two\"'",
                'text="organisation\'s"',
                "'abc",
            ],
        )

    def test_tag_parser_trailing_quote_double(self):
        _, attrs = parse_tag_attrs('component "my_comp" key=val key2="val2 \'two\'" text=\'organisation"s\' "abc')
        expected_attrs = [
            TagAttr(key=None, value="component", start_index=0, quoted=None, spread=False, translation=False),
            TagAttr(key=None, value="my_comp", start_index=10, quoted='"', spread=False, translation=False),
            TagAttr(key="key", value="val", start_index=20, quoted=None, spread=False, translation=False),
            TagAttr(key="key2", value="val2 'two'", start_index=28, quoted='"', spread=False, translation=False),
            TagAttr(
                key="text", value='organisation"s', start_index=46, quoted="'", spread=False, translation=False
            ),  # noqa: E501
            TagAttr(key=None, value='"abc', start_index=68, quoted=None, spread=False, translation=False),
        ]

        self.assertEqual(attrs, expected_attrs)
        self.assertEqual(
            [a.formatted() for a in attrs],
            [
                "component",
                '"my_comp"',
                "key=val",
                "key2=\"val2 'two'\"",
                "text='organisation\"s'",
                '"abc',
            ],
        )

    def test_tag_parser_trailing_quote_as_value_single(self):
        _, attrs = parse_tag_attrs(
            "component 'my_comp' key=val key2='val2 \"two\"' text=\"organisation's\" value='abc"
        )
        expected_attrs = [
            TagAttr(key=None, value="component", start_index=0, quoted=None, spread=False, translation=False),
            TagAttr(key=None, value="my_comp", start_index=10, quoted="'", spread=False, translation=False),
            TagAttr(key="key", value="val", start_index=20, quoted=None, spread=False, translation=False),
            TagAttr(key="key2", value='val2 "two"', start_index=28, quoted="'", spread=False, translation=False),
            TagAttr(key="text", value="organisation's", start_index=46, quoted='"', spread=False, translation=False),
            TagAttr(key="value", value="'abc", start_index=68, quoted=None, spread=False, translation=False),
        ]

        self.assertEqual(attrs, expected_attrs)
        self.assertEqual(
            [a.formatted() for a in attrs],
            [
                "component",
                "'my_comp'",
                "key=val",
                "key2='val2 \"two\"'",
                'text="organisation\'s"',
                "value='abc",
            ],
        )

    def test_tag_parser_trailing_quote_as_value_double(self):
        _, attrs = parse_tag_attrs(
            'component "my_comp" key=val key2="val2 \'two\'" text=\'organisation"s\' value="abc'
        )
        expected_attrs = [
            TagAttr(key=None, value="component", start_index=0, quoted=None, spread=False, translation=False),
            TagAttr(key=None, value="my_comp", start_index=10, quoted='"', spread=False, translation=False),
            TagAttr(key="key", value="val", start_index=20, quoted=None, spread=False, translation=False),
            TagAttr(key="key2", value="val2 'two'", start_index=28, quoted='"', spread=False, translation=False),
            TagAttr(key="text", value='organisation"s', start_index=46, quoted="'", spread=False, translation=False),
            TagAttr(key="value", value='"abc', start_index=68, quoted=None, spread=False, translation=False),
        ]

        self.assertEqual(attrs, expected_attrs)
        self.assertEqual(
            [a.formatted() for a in attrs],
            [
                "component",
                '"my_comp"',
                "key=val",
                "key2=\"val2 'two'\"",
                "text='organisation\"s'",
                'value="abc',
            ],
        )

    def test_tag_parser_translation(self):
        _, attrs = parse_tag_attrs('component "my_comp" _("one") key=_("two")')

        expected_attrs = [
            TagAttr(key=None, value="component", start_index=0, quoted=None, spread=False, translation=False),
            TagAttr(key=None, value="my_comp", start_index=10, quoted='"', spread=False, translation=False),
            TagAttr(key=None, value="one", start_index=20, quoted='"', spread=False, translation=True),
            TagAttr(key="key", value="two", start_index=29, quoted='"', spread=False, translation=True),
        ]

        self.assertEqual(attrs, expected_attrs)
        self.assertEqual(
            [a.formatted() for a in attrs],
            [
                "component",
                '"my_comp"',
                '_("one")',
                'key=_("two")',
            ],
        )
