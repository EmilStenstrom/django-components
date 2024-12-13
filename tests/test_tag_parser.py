from django_components.util.tag_parser import TagAttr, parse_tag_attrs

from .django_test_setup import setup_test_config
from .testutils import BaseTestCase

setup_test_config({"autodiscover": False})


class TagParserTests(BaseTestCase):
    def test_tag_parser(self):
        _, attrs = parse_tag_attrs("component 'my_comp' key=val key2='val2 two' ")
        self.assertEqual(
            attrs,
            [
                TagAttr(key=None, value="component", start_index=0, quoted=None, spread=False, translation=False),
                TagAttr(key=None, value="my_comp", start_index=10, quoted="'", spread=False, translation=False),
                TagAttr(key="key", value="val", start_index=20, quoted=None, spread=False, translation=False),
                TagAttr(key="key2", value="val2 two", start_index=28, quoted="'", spread=False, translation=False),
            ],
        )

    def test_tag_parser_nested_quotes(self):
        _, attrs = parse_tag_attrs("component 'my_comp' key=val key2='val2 \"two\"' text=\"organisation's\" ")
        self.assertEqual(
            attrs,
            [
                TagAttr(key=None, value="component", start_index=0, quoted=None, spread=False, translation=False),
                TagAttr(key=None, value="my_comp", start_index=10, quoted="'", spread=False, translation=False),
                TagAttr(key="key", value="val", start_index=20, quoted=None, spread=False, translation=False),
                TagAttr(key="key2", value='val2 "two"', start_index=28, quoted="'", spread=False, translation=False),
                TagAttr(
                    key="text", value="organisation's", start_index=46, quoted='"', spread=False, translation=False
                ),
            ],
        )

    def test_tag_parser_trailing_quote_single(self):
        _, attrs = parse_tag_attrs("component 'my_comp' key=val key2='val2 \"two\"' text=\"organisation's\" 'abc")

        self.assertEqual(
            attrs,
            [
                TagAttr(key=None, value="component", start_index=0, quoted=None, spread=False, translation=False),
                TagAttr(key=None, value="my_comp", start_index=10, quoted="'", spread=False, translation=False),
                TagAttr(key="key", value="val", start_index=20, quoted=None, spread=False, translation=False),
                TagAttr(key="key2", value='val2 "two"', start_index=28, quoted="'", spread=False, translation=False),
                TagAttr(
                    key="text", value="organisation's", start_index=46, quoted='"', spread=False, translation=False
                ),
                TagAttr(key=None, value="'abc", start_index=68, quoted=None, spread=False, translation=False),
            ],
        )

    def test_tag_parser_trailing_quote_double(self):
        _, attrs = parse_tag_attrs('component "my_comp" key=val key2="val2 \'two\'" text=\'organisation"s\' "abc')
        self.assertEqual(
            attrs,
            [
                TagAttr(key=None, value="component", start_index=0, quoted=None, spread=False, translation=False),
                TagAttr(key=None, value="my_comp", start_index=10, quoted='"', spread=False, translation=False),
                TagAttr(key="key", value="val", start_index=20, quoted=None, spread=False, translation=False),
                TagAttr(key="key2", value="val2 'two'", start_index=28, quoted='"', spread=False, translation=False),
                TagAttr(
                    key="text", value='organisation"s', start_index=46, quoted="'", spread=False, translation=False
                ),  # noqa: E501
                TagAttr(key=None, value='"abc', start_index=68, quoted=None, spread=False, translation=False),
            ],
        )

    def test_tag_parser_trailing_quote_as_value_single(self):
        _, attrs = parse_tag_attrs(
            "component 'my_comp' key=val key2='val2 \"two\"' text=\"organisation's\" value='abc"
        )
        self.assertEqual(
            attrs,
            [
                TagAttr(key=None, value="component", start_index=0, quoted=None, spread=False, translation=False),
                TagAttr(key=None, value="my_comp", start_index=10, quoted="'", spread=False, translation=False),
                TagAttr(key="key", value="val", start_index=20, quoted=None, spread=False, translation=False),
                TagAttr(key="key2", value='val2 "two"', start_index=28, quoted="'", spread=False, translation=False),
                TagAttr(
                    key="text", value="organisation's", start_index=46, quoted='"', spread=False, translation=False
                ),
                TagAttr(key="value", value="'abc", start_index=68, quoted=None, spread=False, translation=False),
            ],
        )

    def test_tag_parser_trailing_quote_as_value_double(self):
        _, attrs = parse_tag_attrs(
            'component "my_comp" key=val key2="val2 \'two\'" text=\'organisation"s\' value="abc'
        )
        self.assertEqual(
            attrs,
            [
                TagAttr(key=None, value="component", start_index=0, quoted=None, spread=False, translation=False),
                TagAttr(key=None, value="my_comp", start_index=10, quoted='"', spread=False, translation=False),
                TagAttr(key="key", value="val", start_index=20, quoted=None, spread=False, translation=False),
                TagAttr(key="key2", value="val2 'two'", start_index=28, quoted='"', spread=False, translation=False),
                TagAttr(
                    key="text", value='organisation"s', start_index=46, quoted="'", spread=False, translation=False
                ),
                TagAttr(key="value", value='"abc', start_index=68, quoted=None, spread=False, translation=False),
            ],
        )
