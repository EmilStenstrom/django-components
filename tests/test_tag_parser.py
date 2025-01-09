from django.template import TemplateSyntaxError
from django_components.util.tag_parser import TagAttr, TagValue, TagValuePart, TagValueStruct, parse_tag

from .django_test_setup import setup_test_config
from .testutils import BaseTestCase

setup_test_config({"autodiscover": False})


class TagParserTests(BaseTestCase):
    def test_args_kwargs(self):
        _, attrs = parse_tag("component 'my_comp' key=val key2='val2 two' ")

        expected_attrs = [
            TagAttr(
                key=None,
                start_index=0,
                value=TagValueStruct(
                    type="simple",
                    meta={},
                    spread=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
            ),
            TagAttr(
                key=None,
                start_index=10,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="my_comp", quoted="'", spread=None, translation=False, filter=None)
                            ]
                        )
                    ],
                ),
            ),
            TagAttr(
                key="key",
                start_index=20,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[TagValuePart(value="val", quoted=None, spread=None, translation=False, filter=None)]
                        )
                    ],
                ),
            ),
            TagAttr(
                key="key2",
                start_index=28,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="val2 two", quoted="'", spread=None, translation=False, filter=None)
                            ]
                        )
                    ],
                ),
            ),
        ]

        self.assertEqual(attrs, expected_attrs)
        self.assertEqual(
            [a.serialize() for a in attrs],
            [
                "component",
                "'my_comp'",
                "key=val",
                "key2='val2 two'",
            ],
        )

    def test_nested_quotes(self):
        _, attrs = parse_tag("component 'my_comp' key=val key2='val2 \"two\"' text=\"organisation's\" ")

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=0,
            ),
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="my_comp", quoted="'", spread=None, translation=False, filter=None)
                            ]
                        )
                    ],
                ),
                start_index=10,
            ),
            TagAttr(
                key="key",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[TagValuePart(value="val", quoted=None, spread=None, translation=False, filter=None)]
                        )
                    ],
                ),
                start_index=20,
            ),
            TagAttr(
                key="key2",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value='val2 "two"', quoted="'", spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=28,
            ),
            TagAttr(
                key="text",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="organisation's", quoted='"', spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=46,
            ),
        ]

        self.assertEqual(attrs, expected_attrs)
        self.assertEqual(
            [a.serialize() for a in attrs],
            [
                "component",
                "'my_comp'",
                "key=val",
                "key2='val2 \"two\"'",
                'text="organisation\'s"',
            ],
        )

    def test_trailing_quote_single(self):
        _, attrs = parse_tag("component 'my_comp' key=val key2='val2 \"two\"' text=\"organisation's\" 'abc")

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    meta={},
                    spread=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=0,
            ),
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="my_comp", quoted="'", spread=None, translation=False, filter=None)
                            ]
                        )
                    ],
                ),
                start_index=10,
            ),
            TagAttr(
                key="key",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[TagValuePart(value="val", quoted=None, spread=None, translation=False, filter=None)]
                        )
                    ],
                ),
                start_index=20,
            ),
            TagAttr(
                key="key2",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value='val2 "two"', quoted="'", spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=28,
            ),
            TagAttr(
                key="text",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="organisation's", quoted='"', spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=46,
            ),
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="'abc", quoted=None, spread=None, translation=False, filter=None)
                            ]
                        )
                    ],
                ),
                start_index=68,
            ),
        ]

        self.assertEqual(attrs, expected_attrs)
        self.assertEqual(
            [a.serialize() for a in attrs],
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
        _, attrs = parse_tag('component "my_comp" key=val key2="val2 \'two\'" text=\'organisation"s\' "abc')

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=0,
            ),
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="my_comp", quoted='"', spread=None, translation=False, filter=None)
                            ]
                        )
                    ],
                ),
                start_index=10,
            ),
            TagAttr(
                key="key",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[TagValuePart(value="val", quoted=None, spread=None, translation=False, filter=None)]
                        )
                    ],
                ),
                start_index=20,
            ),
            TagAttr(
                key="key2",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="val2 'two'", quoted='"', spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=28,
            ),
            TagAttr(
                key="text",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value='organisation"s', quoted="'", spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=46,
            ),  # noqa: E501
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value='"abc', quoted=None, spread=None, translation=False, filter=None)
                            ]
                        )
                    ],
                ),
                start_index=68,
            ),
        ]

        self.assertEqual(attrs, expected_attrs)
        self.assertEqual(
            [a.serialize() for a in attrs],
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
        _, attrs = parse_tag("component 'my_comp' key=val key2='val2 \"two\"' text=\"organisation's\" value='abc")

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=0,
            ),
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="my_comp", quoted="'", spread=None, translation=False, filter=None)
                            ]
                        )
                    ],
                ),
                start_index=10,
            ),
            TagAttr(
                key="key",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[TagValuePart(value="val", quoted=None, spread=None, translation=False, filter=None)]
                        )
                    ],
                ),
                start_index=20,
            ),
            TagAttr(
                key="key2",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value='val2 "two"', quoted="'", spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=28,
            ),
            TagAttr(
                key="text",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="organisation's", quoted='"', spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=46,
            ),
            TagAttr(
                key="value",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="'abc", quoted=None, spread=None, translation=False, filter=None)
                            ]
                        )
                    ],
                ),
                start_index=68,
            ),
        ]

        self.assertEqual(attrs, expected_attrs)
        self.assertEqual(
            [a.serialize() for a in attrs],
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
        _, attrs = parse_tag('component "my_comp" key=val key2="val2 \'two\'" text=\'organisation"s\' value="abc')

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=0,
            ),
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="my_comp", quoted='"', spread=None, translation=False, filter=None)
                            ]
                        )
                    ],
                ),
                start_index=10,
            ),
            TagAttr(
                key="key",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[TagValuePart(value="val", quoted=None, spread=None, translation=False, filter=None)]
                        )
                    ],
                ),
                start_index=20,
            ),
            TagAttr(
                key="key2",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="val2 'two'", quoted='"', spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=28,
            ),
            TagAttr(
                key="text",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value='organisation"s', quoted="'", spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=46,
            ),
            TagAttr(
                key="value",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value='"abc', quoted=None, spread=None, translation=False, filter=None)
                            ]
                        )
                    ],
                ),
                start_index=68,
            ),
        ]

        self.assertEqual(attrs, expected_attrs)
        self.assertEqual(
            [a.serialize() for a in attrs],
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
        _, attrs = parse_tag('component "my_comp" _("one") key=_("two")')

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=0,
            ),
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="my_comp", quoted='"', spread=None, translation=False, filter=None)
                            ]
                        )
                    ],
                ),
                start_index=10,
            ),
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[TagValuePart(value="one", quoted='"', spread=None, translation=True, filter=None)]
                        )
                    ],
                ),
                start_index=20,
            ),
            TagAttr(
                key="key",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[TagValuePart(value="two", quoted='"', spread=None, translation=True, filter=None)]
                        )
                    ],
                ),
                start_index=29,
            ),
        ]

        self.assertEqual(attrs, expected_attrs)
        self.assertEqual(
            [a.serialize() for a in attrs],
            [
                "component",
                '"my_comp"',
                '_("one")',
                'key=_("two")',
            ],
        )

    def test_tag_parser_filters(self):
        _, attrs = parse_tag('component "my_comp" value|lower key=val|yesno:"yes,no" key2=val2|default:"N/A"|upper')

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=0,
            ),
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="my_comp", quoted='"', spread=None, translation=False, filter=None)
                            ]
                        )
                    ],
                ),
                start_index=10,
            ),
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="value", quoted=None, spread=None, translation=False, filter=None),
                                TagValuePart(value="lower", quoted=None, spread=None, translation=False, filter="|"),
                            ]
                        )
                    ],
                ),
                start_index=20,
            ),
            TagAttr(
                key="key",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="val", quoted=None, spread=None, translation=False, filter=None),
                                TagValuePart(value="yesno", quoted=None, spread=None, translation=False, filter="|"),
                                TagValuePart(value="yes,no", quoted='"', spread=None, translation=False, filter=":"),
                            ]
                        )
                    ],
                ),
                start_index=32,
            ),
            TagAttr(
                key="key2",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="val2", quoted=None, spread=None, translation=False, filter=None),
                                TagValuePart(value="default", quoted=None, spread=None, translation=False, filter="|"),
                                TagValuePart(value="N/A", quoted='"', spread=None, translation=False, filter=":"),
                                TagValuePart(value="upper", quoted=None, spread=None, translation=False, filter="|"),
                            ]
                        )
                    ],
                ),
                start_index=55,
            ),
        ]

        self.assertEqual(attrs, expected_attrs)
        self.assertEqual(
            [a.serialize() for a in attrs],
            [
                "component",
                '"my_comp"',
                "value|lower",
                'key=val|yesno:"yes,no"',
                'key2=val2|default:"N/A"|upper',
            ],
        )

    def test_translation_whitespace(self):
        _, attrs = parse_tag('component value=_(  "test"  )')

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=0,
            ),
            TagAttr(
                key="value",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="test", quoted='"', spread=None, translation=True, filter=None),
                            ]
                        )
                    ],
                ),
                start_index=10,
            ),
        ]
        self.assertEqual(attrs, expected_attrs)

    def test_filter_whitespace(self):
        _, attrs = parse_tag("component value  |  lower    key=val  |  upper    key2=val2")

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=0,
            ),
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="value", quoted=None, spread=None, translation=False, filter=None),
                                TagValuePart(value="lower", quoted=None, spread=None, translation=False, filter="|"),
                            ]
                        )
                    ],
                ),
                start_index=10,
            ),
            TagAttr(
                key="key",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="val", quoted=None, spread=None, translation=False, filter=None),
                                TagValuePart(value="upper", quoted=None, spread=None, translation=False, filter="|"),
                            ]
                        )
                    ],
                ),
                start_index=29,
            ),
            TagAttr(
                key="key2",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="val2", quoted=None, spread=None, translation=False, filter=None),
                            ]
                        )
                    ],
                ),
                start_index=50,
            ),
        ]

        self.assertEqual(attrs, expected_attrs)

    def test_dict_simple(self):
        _, attrs = parse_tag('component data={ "key": "val" }')

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=0,
            ),
            TagAttr(
                key="data",
                value=TagValueStruct(
                    type="dict",
                    meta={},
                    spread=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="key", quoted='"', spread=None, translation=False, filter=None
                                ),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="val", quoted='"', spread=None, translation=False, filter=None
                                ),
                            ]
                        ),
                    ],
                ),
                start_index=10,
            ),
        ]

        self.assertEqual(attrs, expected_attrs)

    def test_dict_trailing_comma(self):
        _, attrs = parse_tag('component data={ "key": "val", }')

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=0,
            ),
            TagAttr(
                key="data",
                value=TagValueStruct(
                    type="dict",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="key", quoted='"', spread=None, translation=False, filter=None
                                ),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="val", quoted='"', spread=None, translation=False, filter=None
                                ),
                            ]
                        ),
                    ],
                ),
                start_index=10,
            ),
        ]

        self.assertEqual(attrs, expected_attrs)

    def test_dict_missing_colon(self):
        with self.assertRaisesMessage(TemplateSyntaxError, "Dictionary key is missing a value"):
            parse_tag('component data={ "key" }')

    def test_dict_missing_colon_2(self):
        with self.assertRaisesMessage(TemplateSyntaxError, "Dictionary key is missing a value"):
            parse_tag('component data={ "key", "val" }')

    def test_dict_extra_colon(self):
        with self.assertRaisesMessage(TemplateSyntaxError, "Unexpected colon"):
            _, attrs = parse_tag("component data={ key:: key }")

    def test_dict_spread(self):
        _, attrs = parse_tag("component data={ **spread }")

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=0,
            ),
            TagAttr(
                key="data",
                value=TagValueStruct(
                    type="dict",
                    meta={},
                    spread=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="spread", quoted=None, spread="**", translation=False, filter=None
                                ),
                            ]
                        )
                    ],
                ),
                start_index=10,
            ),
        ]

        self.assertEqual(attrs, expected_attrs)

    def test_dict_spread_between_key_value_pairs(self):
        _, attrs = parse_tag('component data={ "key": val, **spread, "key2": val2 }')

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=0,
            ),
            TagAttr(
                key="data",
                value=TagValueStruct(
                    type="dict",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="key", quoted='"', spread=None, translation=False, filter=None
                                ),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="val", quoted=None, spread=None, translation=False, filter=None
                                ),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="spread", quoted=None, spread="**", translation=False, filter=None
                                ),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="key2", quoted='"', spread=None, translation=False, filter=None
                                ),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="val2", quoted=None, spread=None, translation=False, filter=None
                                ),
                            ]
                        ),
                    ],
                ),
                start_index=10,
            ),
        ]

        self.assertEqual(attrs, expected_attrs)

    # Test that dictionary keys cannot have filter arguments - The `:` is parsed as dictionary key separator
    # So instead, the content below will be parsed as key `"key"|filter`, and value `"arg":"value"`
    def test_colon_in_dictionary_keys(self):
        _, attrs = parse_tag('component data={"key"|filter:"arg": "value"}')

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    meta={},
                    spread=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                ),
                            ]
                        )
                    ],
                ),
                start_index=0,
            ),
            TagAttr(
                key="data",
                value=TagValueStruct(
                    type="dict",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="key", quoted='"', spread=None, translation=False, filter=None
                                ),
                                TagValuePart(
                                    value="filter", quoted=None, spread=None, translation=False, filter="|"
                                ),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="arg", quoted='"', spread=None, translation=False, filter=None
                                ),
                                TagValuePart(
                                    value="value", quoted='"', spread=None, translation=False, filter=":"
                                ),
                            ]
                        ),
                    ],
                ),
                start_index=10,
            ),
        ]
        self.assertEqual(attrs, expected_attrs)

    def test_list_simple(self):
        _, attrs = parse_tag("component data=[1, 2, 3]")

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    meta={},
                    spread=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                ),
                            ]
                        )
                    ],
                ),
                start_index=0,
            ),
            TagAttr(
                key="data",
                value=TagValueStruct(
                    type="list",
                    meta={},
                    spread=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="1", quoted=None, spread=None, translation=False, filter=None
                                ),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="2", quoted=None, spread=None, translation=False, filter=None
                                ),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="3", quoted=None, spread=None, translation=False, filter=None
                                ),
                            ]
                        ),
                    ],
                ),
                start_index=10,
            ),
        ]

        self.assertEqual(attrs, expected_attrs)

    def test_list_trailing_comma(self):
        _, attrs = parse_tag("component data=[1, 2, 3, ]")

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    meta={},
                    spread=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                ),
                            ]
                        )
                    ],
                ),
                start_index=0,
            ),
            TagAttr(
                key="data",
                value=TagValueStruct(
                    type="list",
                    meta={},
                    spread=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="1", quoted=None, spread=None, translation=False, filter=None
                                ),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="2", quoted=None, spread=None, translation=False, filter=None
                                ),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="3", quoted=None, spread=None, translation=False, filter=None
                                ),
                            ]
                        ),
                    ],
                ),
                start_index=10,
            ),
        ]

        self.assertEqual(attrs, expected_attrs)

    def test_tag_parser_lists(self):
        _, attrs = parse_tag(
            """
                component
                nums=[
                    1,
                    2|add:3,
                    *spread
                ]
                items=[
                    "a"|upper,
                    'b'|lower,
                    c|default:"d"
                ]
                mixed=[
                    1,
                    [*nested],
                    {"key": "val"}
                ]
            """
        )

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                ),
                            ]
                        )
                    ],
                ),
                start_index=17,
            ),
            TagAttr(
                key="nums",
                value=TagValueStruct(
                    type="list",
                    meta={},
                    spread=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="1", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="2", quoted=None, spread=None, translation=False, filter=None
                                ),
                                TagValuePart(
                                    value="add", quoted=None, spread=None, translation=False, filter="|"
                                ),
                                TagValuePart(
                                    value="3", quoted=None, spread=None, translation=False, filter=":"
                                ),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="spread", quoted=None, spread="*", translation=False, filter=None
                                )
                            ]
                        ),
                    ],
                ),
                start_index=43,
            ),
            TagAttr(
                key="items",
                value=TagValueStruct(
                    type="list",
                    meta={},
                    spread=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="a", quoted='"', spread=None, translation=False, filter=None
                                ),
                                TagValuePart(
                                    value="upper", quoted=None, spread=None, translation=False, filter="|"
                                ),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="b", quoted="'", spread=None, translation=False, filter=None
                                ),
                                TagValuePart(
                                    value="lower", quoted=None, spread=None, translation=False, filter="|"
                                ),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="c", quoted=None, spread=None, translation=False, filter=None
                                ),
                                TagValuePart(
                                    value="default", quoted=None, spread=None, translation=False, filter="|"
                                ),
                                TagValuePart(
                                    value="d", quoted='"', spread=None, translation=False, filter=":"
                                ),
                            ]
                        ),
                    ],
                ),
                start_index=164,
            ),
            TagAttr(
                key="mixed",
                value=TagValueStruct(
                    type="list",
                    meta={},
                    spread=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="1", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        ),
                        TagValueStruct(
                            type="list",
                            meta={},
                            spread=None,
                            entries=[
                                TagValue(
                                    parts=[
                                        TagValuePart(
                                            value="nested",
                                            quoted=None,
                                            spread="*",
                                            translation=False,
                                            filter=None,
                                        )
                                    ]
                                ),
                            ],
                        ),
                        TagValueStruct(
                            type="dict",
                            meta={},
                            spread=None,
                            entries=[
                                TagValue(
                                    parts=[
                                        TagValuePart(
                                            value="key",
                                            quoted='"',
                                            spread=None,
                                            translation=False,
                                            filter=None,
                                        )
                                    ]
                                ),
                                TagValue(
                                    parts=[
                                        TagValuePart(
                                            value="val",
                                            quoted='"',
                                            spread=None,
                                            translation=False,
                                            filter=None,
                                        )
                                    ]
                                ),
                            ],
                        ),
                    ],
                ),
                start_index=302,
            ),
        ]

        self.assertEqual(attrs, expected_attrs)
        self.assertEqual(
            [a.serialize() for a in attrs],
            [
                "component",
                "nums=[1, 2|add:3, *spread]",
                'items=["a"|upper, \'b\'|lower, c|default:"d"]',
                'mixed=[1, [*nested], {"key": "val"}]',
            ],
        )

    def test_tag_parser_dicts(self):
        # NOTE: The case `c|default:"d": "e"|yesno:"yes,no"` tests that the first `:`
        # is interpreted as a separator between key and value, not as a filter.
        # So it's as if we wrote `c|default: "d":"e"|yesno:"yes,no"`
        _, attrs = parse_tag(
            """
            component
            simple={
                "a": 1|add:2
            }
            nested={
                "key"|upper: val|lower,
                **spread,
                "obj": {"x": 1|add:2}
            }
            filters={
                "a"|lower: "b"|upper,
                c|default:"d": "e"|yesno:"yes,no"
            }
            """
        )

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                ),
                            ]
                        ),
                    ],
                ),
                start_index=13,
            ),
            TagAttr(
                key="simple",
                value=TagValueStruct(
                    type="dict",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="a", quoted='"', spread=None, translation=False, filter=None
                                )
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="1", quoted=None, spread=None, translation=False, filter=None
                                ),
                                TagValuePart(
                                    value="add", quoted=None, spread=None, translation=False, filter="|"
                                ),
                                TagValuePart(
                                    value="2", quoted=None, spread=None, translation=False, filter=":"
                                ),
                            ]
                        ),
                    ],
                ),
                start_index=35,
            ),
            TagAttr(
                key="nested",
                value=TagValueStruct(
                    type="dict",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="key", quoted='"', spread=None, translation=False, filter=None
                                ),
                                TagValuePart(
                                    value="upper", quoted=None, spread=None, translation=False, filter="|"
                                ),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="val", quoted=None, spread=None, translation=False, filter=None
                                ),
                                TagValuePart(
                                    value="lower", quoted=None, spread=None, translation=False, filter="|"
                                ),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="spread", quoted=None, spread="**", translation=False, filter=None
                                )
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="obj", quoted='"', spread=None, translation=False, filter=None
                                )
                            ]
                        ),
                        TagValueStruct(
                            type="dict",
                            meta={},
                            spread=None,
                            entries=[
                                TagValue(
                                    parts=[
                                        TagValuePart(
                                            value="x", quoted='"', spread=None, translation=False, filter=None
                                        )
                                    ]
                                ),
                                TagValue(
                                    parts=[
                                        TagValuePart(
                                            value="1", quoted=None, spread=None, translation=False, filter=None
                                        ),
                                        TagValuePart(
                                            value="add",
                                            quoted=None,
                                            spread=None,
                                            translation=False,
                                            filter="|",
                                        ),
                                        TagValuePart(
                                            value="2", quoted=None, spread=None, translation=False, filter=":"
                                        ),
                                    ]
                                ),
                            ],
                        ),
                    ],
                ),
                start_index=99,
            ),
            TagAttr(
                key="filters",
                value=TagValueStruct(
                    type="dict",
                    meta={},
                    spread=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="a", quoted='"', spread=None, translation=False, filter=None
                                ),
                                TagValuePart(
                                    value="lower", quoted=None, spread=None, translation=False, filter="|"
                                ),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="b", quoted='"', spread=None, translation=False, filter=None
                                ),
                                TagValuePart(
                                    value="upper", quoted=None, spread=None, translation=False, filter="|"
                                ),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="c", quoted=None, spread=None, translation=False, filter=None
                                ),
                                TagValuePart(
                                    value="default", quoted=None, spread=None, translation=False, filter="|"
                                ),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="d", quoted='"', spread=None, translation=False, filter=None
                                ),
                                TagValuePart(
                                    value="e", quoted='"', spread=None, translation=False, filter=":"
                                ),
                                TagValuePart(
                                    value="yesno", quoted=None, spread=None, translation=False, filter="|"
                                ),
                                TagValuePart(
                                    value="yes,no", quoted='"', spread=None, translation=False, filter=":"
                                ),
                            ]
                        ),
                    ],
                ),
                start_index=238,
            ),
        ]

        self.assertEqual(attrs, expected_attrs)
        self.assertEqual(
            [a.serialize() for a in attrs],
            [
                "component",
                'simple={"a": 1|add:2}',
                'nested={"key"|upper: val|lower, **spread, "obj": {"x": 1|add:2}}',
                'filters={"a"|lower: "b"|upper, c|default: "d":"e"|yesno:"yes,no"}',
            ],
        )

    def test_tag_parser_complex(self):
        _, attrs = parse_tag(
            """
            component
            data={
                "items": [
                    1|add:2,
                    {"x"|upper: 2|add:3},
                    *spread_items|default:""
                ],
                "nested": {
                    "a": [
                        1|add:2,
                        *nums|default:""
                    ],
                    "b": {
                        "x": [
                            *more|default:""
                        ]
                    }
                },
                **rest|default,
                "key": _('value')|upper
            }
            """
        )

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                ),
                            ]
                        ),
                    ],
                ),
                start_index=13,
            ),
            TagAttr(
                key="data",
                value=TagValueStruct(
                    type="dict",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="items", quoted='"', spread=None, translation=False, filter=None
                                )
                            ]
                        ),
                        TagValueStruct(
                            type="list",
                            spread=None,
                            meta={},
                            entries=[
                                TagValue(
                                    parts=[
                                        TagValuePart(
                                            value="1", quoted=None, spread=None, translation=False, filter=None
                                        ),
                                        TagValuePart(
                                            value="add",
                                            quoted=None,
                                            spread=None,
                                            translation=False,
                                            filter="|",
                                        ),
                                        TagValuePart(
                                            value="2", quoted=None, spread=None, translation=False, filter=":"
                                        ),
                                    ]
                                ),
                                TagValueStruct(
                                    type="dict",
                                    spread=None,
                                    meta={},
                                    entries=[
                                        TagValue(
                                            parts=[
                                                TagValuePart(
                                                    value="x",
                                                    quoted='"',
                                                    spread=None,
                                                    translation=False,
                                                    filter=None,
                                                ),
                                                TagValuePart(
                                                    value="upper",
                                                    quoted=None,
                                                    spread=None,
                                                    translation=False,
                                                    filter="|",
                                                ),
                                            ]
                                        ),
                                        TagValue(
                                            parts=[
                                                TagValuePart(
                                                    value="2",
                                                    quoted=None,
                                                    spread=None,
                                                    translation=False,
                                                    filter=None,
                                                ),
                                                TagValuePart(
                                                    value="add",
                                                    quoted=None,
                                                    spread=None,
                                                    translation=False,
                                                    filter="|",
                                                ),
                                                TagValuePart(
                                                    value="3",
                                                    quoted=None,
                                                    spread=None,
                                                    translation=False,
                                                    filter=":",
                                                ),
                                            ]
                                        ),
                                    ],
                                ),
                                TagValue(
                                    parts=[
                                        TagValuePart(
                                            value="spread_items",
                                            quoted=None,
                                            spread="*",
                                            translation=False,
                                            filter=None,
                                        ),
                                        TagValuePart(
                                            value="default",
                                            quoted=None,
                                            spread=None,
                                            translation=False,
                                            filter="|",
                                        ),
                                        TagValuePart(
                                            value="", quoted='"', spread=None, translation=False, filter=":"
                                        ),
                                    ]
                                ),
                            ],
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="nested", quoted='"', spread=None, translation=False, filter=None
                                )
                            ]
                        ),
                        TagValueStruct(
                            type="dict",
                            meta={},
                            spread=None,
                            entries=[
                                TagValue(
                                    parts=[
                                        TagValuePart(
                                            value="a", quoted='"', spread=None, translation=False, filter=None
                                        )
                                    ]
                                ),
                                TagValueStruct(
                                    type="list",
                                    spread=None,
                                    meta={},
                                    entries=[
                                        TagValue(
                                            parts=[
                                                TagValuePart(
                                                    value="1",
                                                    quoted=None,
                                                    spread=None,
                                                    translation=False,
                                                    filter=None,
                                                ),
                                                TagValuePart(
                                                    value="add",
                                                    quoted=None,
                                                    spread=None,
                                                    translation=False,
                                                    filter="|",
                                                ),
                                                TagValuePart(
                                                    value="2",
                                                    quoted=None,
                                                    spread=None,
                                                    translation=False,
                                                    filter=":",
                                                ),
                                            ],
                                        ),
                                        TagValue(
                                            parts=[
                                                TagValuePart(
                                                    value="nums",
                                                    quoted=None,
                                                    spread="*",
                                                    translation=False,
                                                    filter=None,
                                                ),
                                                TagValuePart(
                                                    value="default",
                                                    quoted=None,
                                                    spread=None,
                                                    translation=False,
                                                    filter="|",
                                                ),
                                                TagValuePart(
                                                    value="",
                                                    quoted='"',
                                                    spread=None,
                                                    translation=False,
                                                    filter=":",
                                                ),
                                            ]
                                        ),
                                    ],
                                ),
                                TagValue(
                                    parts=[
                                        TagValuePart(
                                            value="b", quoted='"', spread=None, translation=False, filter=None
                                        )
                                    ]
                                ),
                                TagValueStruct(
                                    type="dict",
                                    meta={},
                                    spread=None,
                                    entries=[
                                        TagValue(
                                            parts=[
                                                TagValuePart(
                                                    value="x",
                                                    quoted='"',
                                                    spread=None,
                                                    translation=False,
                                                    filter=None,
                                                )
                                            ]
                                        ),
                                        TagValueStruct(
                                            type="list",
                                            meta={},
                                            spread=None,
                                            entries=[
                                                TagValue(
                                                    parts=[
                                                        TagValuePart(
                                                            value="more",
                                                            quoted=None,
                                                            spread="*",
                                                            translation=False,
                                                            filter=None,
                                                        ),
                                                        TagValuePart(
                                                            value="default",
                                                            quoted=None,
                                                            spread=None,
                                                            translation=False,
                                                            filter="|",
                                                        ),
                                                        TagValuePart(
                                                            value="",
                                                            quoted='"',
                                                            spread=None,
                                                            translation=False,
                                                            filter=":",
                                                        ),
                                                    ]
                                                ),
                                            ],
                                        ),
                                    ],
                                ),
                            ],
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="rest", quoted=None, spread="**", translation=False, filter=None
                                ),
                                TagValuePart(
                                    value="default", quoted=None, spread=None, translation=False, filter="|"
                                ),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="key", quoted='"', spread=None, translation=False, filter=None
                                )
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="value", quoted="'", spread=None, translation=True, filter=None
                                ),
                                TagValuePart(
                                    value="upper", quoted=None, spread=None, translation=False, filter="|"
                                ),
                            ]
                        ),
                    ],
                ),
                start_index=35,
            ),
        ]

        self.assertEqual(attrs, expected_attrs)
        self.assertEqual(
            [a.serialize() for a in attrs],
            [
                "component",
                'data={"items": [1|add:2, {"x"|upper: 2|add:3}, *spread_items|default:""], "nested": {"a": [1|add:2, *nums|default:""], "b": {"x": [*more|default:""]}}, **rest|default, "key": _(\'value\')|upper}',  # noqa: E501
            ],
        )

    # Test that spread operator cannot be used as dictionary value
    def test_spread_as_dictionary_value(self):
        with self.assertRaisesMessage(
            TemplateSyntaxError,
            "Spread syntax cannot be used in place of a dictionary value",
        ):
            parse_tag('component data={"key": **spread}')

    def test_spread_with_colon_interpreted_as_key(self):
        with self.assertRaisesMessage(
            TemplateSyntaxError,
            "Spread syntax cannot be used in place of a dictionary key",
        ):
            _, attrs = parse_tag("component data={**spread|abc: 123 }")

    def test_spread_in_filter_position(self):
        with self.assertRaisesMessage(
            TemplateSyntaxError,
            "Spread syntax cannot be used inside of a filter",
        ):
            _, attrs = parse_tag("component data=val|...spread|abc }")

    def test_spread_whitespace(self):
        # NOTE: Separating `...` from its variable is NOT valid, and will result in error.
        with self.assertRaisesMessage(
            TemplateSyntaxError,
            "Spread syntax '...' is missing a value",
        ):
            _, attrs = parse_tag("component ... attrs")

        _, attrs = parse_tag('component dict={"a": "b", ** my_attr} list=["a", * my_list]')

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                ),
                            ]
                        ),
                    ],
                ),
                start_index=0,
            ),
            TagAttr(
                key="dict",
                value=TagValueStruct(
                    type="dict",
                    spread=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="a", quoted='"', spread=None, translation=False, filter=None
                                ),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="b", quoted='"', spread=None, translation=False, filter=None
                                ),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="my_attr", quoted=None, spread="**", translation=False, filter=None
                                ),
                            ]
                        ),
                    ],
                ),
                start_index=10,
            ),
            TagAttr(
                key="list",
                value=TagValueStruct(
                    type="list",
                    meta={},
                    spread=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="a", quoted='"', spread=None, translation=False, filter=None
                                ),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="my_list", quoted=None, spread="*", translation=False, filter=None
                                ),
                            ]
                        ),
                    ],
                ),
                start_index=38,
            ),
        ]
        self.assertEqual(attrs, expected_attrs)

    # Test that one cannot use e.g. `...`, `**`, `*` in wrong places
    def test_spread_incorrect_syntax(self):
        with self.assertRaisesMessage(
            TemplateSyntaxError,
            "Spread syntax '*' found outside of a list",
        ):
            _, attrs = parse_tag('component dict={"a": "b", *my_attr}')

        with self.assertRaisesMessage(
            TemplateSyntaxError,
            "Spread syntax '...' found in dict. It must be used on tag attributes only",
        ):
            _, attrs = parse_tag('component dict={"a": "b", ...my_attr}')

        with self.assertRaisesMessage(
            TemplateSyntaxError,
            "Spread syntax '**' found outside of a dictionary",
        ):
            _, attrs = parse_tag('component list=["a", "b", **my_list]')

        with self.assertRaisesMessage(
            TemplateSyntaxError,
            "Spread syntax '...' found in list. It must be used on tag attributes only",
        ):
            _, attrs = parse_tag('component list=["a", "b", ...my_list]')

        with self.assertRaisesMessage(
            TemplateSyntaxError,
            "Spread syntax '*' found outside of a list",
        ):
            _, attrs = parse_tag("component *attrs")

        with self.assertRaisesMessage(
            TemplateSyntaxError,
            "Spread syntax '**' found outside of a dictionary",
        ):
            _, attrs = parse_tag("component **attrs")

        with self.assertRaisesMessage(
            TemplateSyntaxError,
            "Spread syntax '*' found outside of a list",
        ):
            _, attrs = parse_tag("component key=*attrs")

        with self.assertRaisesMessage(
            TemplateSyntaxError,
            "Spread syntax '**' found outside of a dictionary",
        ):
            _, attrs = parse_tag("component key=**attrs")

    # Test that one cannot do `key=...{"a": "b"}`
    def test_spread_onto_key(self):
        with self.assertRaisesMessage(
            TemplateSyntaxError,
            "Spread syntax '...' cannot follow a key ('key=...attrs')",
        ):
            _, attrs = parse_tag('component key=...{"a": "b"}')

        with self.assertRaisesMessage(
            TemplateSyntaxError,
            "Spread syntax '...' cannot follow a key ('key=...attrs')",
        ):
            _, attrs = parse_tag('component key=...["a", "b"]')

        with self.assertRaisesMessage(
            TemplateSyntaxError,
            "Spread syntax '...' cannot follow a key ('key=...attrs')",
        ):
            _, attrs = parse_tag("component key=...attrs")

    def test_spread_dict_literal_nested(self):
        _, attrs = parse_tag('component { **{"key": val2}, "key": val1 }')

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                    spread=None,
                    meta={},
                ),
                start_index=0,
            ),
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="dict",
                    spread=None,
                    meta={},
                    entries=[
                        TagValueStruct(
                            type="dict",
                            spread="**",
                            meta={},
                            entries=[
                                TagValue(
                                    parts=[
                                        TagValuePart(
                                            value="key",
                                            quoted='"',
                                            spread=None,
                                            translation=False,
                                            filter=None,
                                        )
                                    ]
                                ),
                                TagValue(
                                    parts=[
                                        TagValuePart(
                                            value="val2",
                                            quoted=None,
                                            spread=None,
                                            translation=False,
                                            filter=None,
                                        )
                                    ]
                                ),
                            ],
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="key", quoted='"', spread=None, translation=False, filter=None
                                )
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="val1", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        ),
                    ],
                ),
                start_index=10,
            ),
        ]
        self.assertEqual(attrs, expected_attrs)

        self.assertEqual(
            [a.serialize() for a in attrs],
            [
                "component",
                '{**{"key": val2}, "key": val1}',
            ],
        )

    def test_spread_dict_literal_as_attribute(self):
        _, attrs = parse_tag('component ...{"key": val2}')

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                    spread=None,
                    meta={},
                ),
                start_index=0,
            ),
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="dict",
                    spread="...",
                    meta={},
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="key", quoted='"', spread=None, translation=False, filter=None
                                )
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="val2", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        ),
                    ],
                ),
                start_index=10,
            ),
        ]
        self.assertEqual(attrs, expected_attrs)

        self.assertEqual(
            [a.serialize() for a in attrs],
            [
                "component",
                '...{"key": val2}',
            ],
        )

    def test_spread_list_literal_nested(self):
        _, attrs = parse_tag("component [ *[val1], val2 ]")

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                    spread=None,
                    meta={},
                ),
                start_index=0,
            ),
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="list",
                    spread=None,
                    meta={},
                    entries=[
                        TagValueStruct(
                            type="list",
                            spread="*",
                            meta={},
                            entries=[
                                TagValue(
                                    parts=[
                                        TagValuePart(
                                            value="val1",
                                            quoted=None,
                                            spread=None,
                                            translation=False,
                                            filter=None,
                                        )
                                    ]
                                ),
                            ],
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="val2", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        ),
                    ],
                ),
                start_index=10,
            ),
        ]
        self.assertEqual(attrs, expected_attrs)

        self.assertEqual(
            [a.serialize() for a in attrs],
            [
                "component",
                "[*[val1], val2]",
            ],
        )

    def test_spread_list_literal_as_attribute(self):
        _, attrs = parse_tag("component ...[val1]")

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                    spread=None,
                    meta={},
                ),
                start_index=0,
            ),
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="list",
                    spread="...",
                    meta={},
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="val1", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        ),
                    ],
                ),
                start_index=10,
            ),
        ]
        self.assertEqual(attrs, expected_attrs)

        self.assertEqual(
            [a.serialize() for a in attrs],
            [
                "component",
                "...[val1]",
            ],
        )
