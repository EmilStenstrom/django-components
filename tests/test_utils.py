from django_components.utils import is_str_wrapped_in_quotes

from .django_test_setup import setup_test_config
from .testutils import BaseTestCase

setup_test_config({"autodiscover": False})


class UtilsTest(BaseTestCase):
    def test_is_str_wrapped_in_quotes(self):
        self.assertEqual(is_str_wrapped_in_quotes("word"), False)
        self.assertEqual(is_str_wrapped_in_quotes('word"'), False)
        self.assertEqual(is_str_wrapped_in_quotes('"word'), False)
        self.assertEqual(is_str_wrapped_in_quotes('"word"'), True)
        self.assertEqual(is_str_wrapped_in_quotes("\"word'"), False)
        self.assertEqual(is_str_wrapped_in_quotes('"word" '), False)
        self.assertEqual(is_str_wrapped_in_quotes('"'), False)
        self.assertEqual(is_str_wrapped_in_quotes(""), False)
        self.assertEqual(is_str_wrapped_in_quotes('""'), True)
        self.assertEqual(is_str_wrapped_in_quotes("\"'"), False)
