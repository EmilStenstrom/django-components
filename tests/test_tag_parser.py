from django_components.util.tag_parser import TagAttr, TagAttrPart, parse_tag_attrs

from .django_test_setup import setup_test_config
from .testutils import BaseTestCase

setup_test_config({"autodiscover": False})


class TagParserTests(BaseTestCase):
    def test_args_kwargs(self):
        _, attrs = parse_tag_attrs("component 'my_comp' key=val key2='val2 two' ")

        expected_attrs = [
            TagAttr(
                key=None,
                start_index=0,
                spread=False,
                parts=[TagAttrPart(value="component", prefix=None, quoted=None, translation=False)],
            ),
            TagAttr(
                key=None,
                start_index=10,
                spread=False,
                parts=[TagAttrPart(value="my_comp", prefix=None, quoted="'", translation=False)],
            ),
            TagAttr(
                key="key",
                start_index=20,
                spread=False,
                parts=[TagAttrPart(value="val", prefix=None, quoted=None, translation=False)],
            ),
            TagAttr(
                key="key2",
                start_index=28,
                spread=False,
                parts=[TagAttrPart(value="val2 two", prefix=None, quoted="'", translation=False)],
            ),
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

    def test_nested_quotes(self):
        _, attrs = parse_tag_attrs("component 'my_comp' key=val key2='val2 \"two\"' text=\"organisation's\" ")

        expected_attrs = [
            TagAttr(
                key=None,
                start_index=0,
                spread=False,
                parts=[TagAttrPart(value="component", prefix=None, quoted=None, translation=False)],
            ),
            TagAttr(
                key=None,
                start_index=10,
                spread=False,
                parts=[TagAttrPart(value="my_comp", prefix=None, quoted="'", translation=False)],
            ),
            TagAttr(
                key="key",
                start_index=20,
                spread=False,
                parts=[TagAttrPart(value="val", prefix=None, quoted=None, translation=False)],
            ),
            TagAttr(
                key="key2",
                start_index=28,
                spread=False,
                parts=[TagAttrPart(value='val2 "two"', prefix=None, quoted="'", translation=False)],
            ),
            TagAttr(
                key="text",
                start_index=46,
                spread=False,
                parts=[TagAttrPart(value="organisation's", prefix=None, quoted='"', translation=False)],
            ),
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

    def test_trailing_quote_single(self):
        _, attrs = parse_tag_attrs("component 'my_comp' key=val key2='val2 \"two\"' text=\"organisation's\" 'abc")

        expected_attrs = [
            TagAttr(
                key=None,
                start_index=0,
                spread=False,
                parts=[TagAttrPart(value="component", prefix=None, quoted=None, translation=False)],
            ),
            TagAttr(
                key=None,
                start_index=10,
                spread=False,
                parts=[TagAttrPart(value="my_comp", prefix=None, quoted="'", translation=False)],
            ),
            TagAttr(
                key="key",
                start_index=20,
                spread=False,
                parts=[TagAttrPart(value="val", prefix=None, quoted=None, translation=False)],
            ),
            TagAttr(
                key="key2",
                start_index=28,
                spread=False,
                parts=[TagAttrPart(value='val2 "two"', prefix=None, quoted="'", translation=False)],
            ),
            TagAttr(
                key="text",
                start_index=46,
                spread=False,
                parts=[TagAttrPart(value="organisation's", prefix=None, quoted='"', translation=False)],
            ),
            TagAttr(
                key=None,
                start_index=68,
                spread=False,
                parts=[TagAttrPart(value="'abc", prefix=None, quoted=None, translation=False)],
            ),
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

    def test_trailing_quote_double(self):
        _, attrs = parse_tag_attrs('component "my_comp" key=val key2="val2 \'two\'" text=\'organisation"s\' "abc')

        expected_attrs = [
            TagAttr(
                key=None,
                start_index=0,
                spread=False,
                parts=[TagAttrPart(value="component", prefix=None, quoted=None, translation=False)],
            ),
            TagAttr(
                key=None,
                start_index=10,
                spread=False,
                parts=[TagAttrPart(value="my_comp", prefix=None, quoted='"', translation=False)],
            ),
            TagAttr(
                key="key",
                start_index=20,
                spread=False,
                parts=[TagAttrPart(value="val", prefix=None, quoted=None, translation=False)],
            ),
            TagAttr(
                key="key2",
                start_index=28,
                spread=False,
                parts=[TagAttrPart(value="val2 'two'", prefix=None, quoted='"', translation=False)],
            ),
            TagAttr(
                key="text",
                start_index=46,
                spread=False,
                parts=[TagAttrPart(value='organisation"s', prefix=None, quoted="'", translation=False)],
            ),
            TagAttr(
                key=None,
                start_index=68,
                spread=False,
                parts=[TagAttrPart(value='"abc', prefix=None, quoted=None, translation=False)],
            ),
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

    def test_trailing_quote_as_value_single(self):
        _, attrs = parse_tag_attrs(
            "component 'my_comp' key=val key2='val2 \"two\"' text=\"organisation's\" value='abc"
        )

        expected_attrs = [
            TagAttr(
                key=None,
                start_index=0,
                spread=False,
                parts=[TagAttrPart(value="component", prefix=None, quoted=None, translation=False)],
            ),
            TagAttr(
                key=None,
                start_index=10,
                spread=False,
                parts=[TagAttrPart(value="my_comp", prefix=None, quoted="'", translation=False)],
            ),
            TagAttr(
                key="key",
                start_index=20,
                spread=False,
                parts=[TagAttrPart(value="val", prefix=None, quoted=None, translation=False)],
            ),
            TagAttr(
                key="key2",
                start_index=28,
                spread=False,
                parts=[TagAttrPart(value='val2 "two"', prefix=None, quoted="'", translation=False)],
            ),
            TagAttr(
                key="text",
                start_index=46,
                spread=False,
                parts=[TagAttrPart(value="organisation's", prefix=None, quoted='"', translation=False)],
            ),
            TagAttr(
                key="value",
                start_index=68,
                spread=False,
                parts=[TagAttrPart(value="'abc", prefix=None, quoted=None, translation=False)],
            ),
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

    def test_trailing_quote_as_value_double(self):
        _, attrs = parse_tag_attrs(
            'component "my_comp" key=val key2="val2 \'two\'" text=\'organisation"s\' value="abc'
        )

        expected_attrs = [
            TagAttr(
                key=None,
                start_index=0,
                spread=False,
                parts=[TagAttrPart(value="component", prefix=None, quoted=None, translation=False)],
            ),
            TagAttr(
                key=None,
                start_index=10,
                spread=False,
                parts=[TagAttrPart(value="my_comp", prefix=None, quoted='"', translation=False)],
            ),
            TagAttr(
                key="key",
                start_index=20,
                spread=False,
                parts=[TagAttrPart(value="val", prefix=None, quoted=None, translation=False)],
            ),
            TagAttr(
                key="key2",
                start_index=28,
                spread=False,
                parts=[TagAttrPart(value="val2 'two'", prefix=None, quoted='"', translation=False)],
            ),
            TagAttr(
                key="text",
                start_index=46,
                spread=False,
                parts=[TagAttrPart(value='organisation"s', prefix=None, quoted="'", translation=False)],
            ),
            TagAttr(
                key="value",
                start_index=68,
                spread=False,
                parts=[TagAttrPart(value='"abc', prefix=None, quoted=None, translation=False)],
            ),
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

    def test_translation(self):
        _, attrs = parse_tag_attrs('component "my_comp" _("one") key=_("two")')

        expected_attrs = [
            TagAttr(
                key=None,
                parts=[TagAttrPart(value="component", prefix=None, quoted=None, translation=False)],
                start_index=0,
                spread=False,
            ),
            TagAttr(
                key=None,
                parts=[TagAttrPart(value="my_comp", prefix=None, quoted='"', translation=False)],
                start_index=10,
                spread=False,
            ),
            TagAttr(
                key=None,
                parts=[TagAttrPart(value="one", prefix=None, quoted='"', translation=True)],
                start_index=20,
                spread=False,
            ),
            TagAttr(
                key="key",
                parts=[TagAttrPart(value="two", prefix=None, quoted='"', translation=True)],
                start_index=29,
                spread=False,
            ),
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

    def test_filter(self):
        _, attrs = parse_tag_attrs(
            'component "my_comp" abc|fil1 key=val|fil2:"one two "|lower|safe "val2 two"|fil3 key2=\'val2 two\'|fil3'
        )

        expected_attrs = [
            TagAttr(
                key=None,
                start_index=0,
                spread=False,
                parts=[TagAttrPart(value="component", prefix=None, quoted=None, translation=False)],
            ),
            TagAttr(
                key=None,
                start_index=10,
                spread=False,
                parts=[TagAttrPart(value="my_comp", prefix=None, quoted='"', translation=False)],
            ),
            TagAttr(
                key=None,
                start_index=20,
                spread=False,
                parts=[
                    TagAttrPart(value="abc", prefix=None, quoted=None, translation=False),
                    TagAttrPart(value="fil1", prefix="|", quoted=None, translation=False),
                ],
            ),
            TagAttr(
                key="key",
                start_index=29,
                spread=False,
                parts=[
                    TagAttrPart(value="val", prefix=None, quoted=None, translation=False),
                    TagAttrPart(value="fil2", prefix="|", quoted=None, translation=False),
                    TagAttrPart(value="one two ", prefix=":", quoted='"', translation=False),
                    TagAttrPart(value="lower", prefix="|", quoted=None, translation=False),
                    TagAttrPart(value="safe", prefix="|", quoted=None, translation=False),
                ],
            ),
            TagAttr(
                key=None,
                start_index=64,
                spread=False,
                parts=[
                    TagAttrPart(value="val2 two", prefix=None, quoted='"', translation=False),
                    TagAttrPart(value="fil3", prefix="|", quoted=None, translation=False),
                ],
            ),
            TagAttr(
                key="key2",
                start_index=80,
                spread=False,
                parts=[
                    TagAttrPart(value="val2 two", prefix=None, quoted="'", translation=False),
                    TagAttrPart(value="fil3", prefix="|", quoted=None, translation=False),
                ],
            ),
        ]

        self.assertEqual(attrs, expected_attrs)
        self.assertEqual(
            [a.formatted() for a in attrs],
            [
                "component",
                '"my_comp"',
                "abc|fil1",
                'key=val|fil2:"one two "|lower|safe',
                '"val2 two"|fil3',
                "key2='val2 two'|fil3",
            ],
        )
