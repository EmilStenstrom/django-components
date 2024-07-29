from django.test import override_settings

from django_components.app_settings import app_settings

from .django_test_setup import setup_test_config
from .testutils import BaseTestCase

setup_test_config()


class SettingsTestCase(BaseTestCase):
    @override_settings(COMPONENTS={"context_behavior": "isolated"})
    def test_valid_context_behavior(self):
        self.assertEqual(app_settings.CONTEXT_BEHAVIOR, "isolated")

    @override_settings(COMPONENTS={"context_behavior": "invalid_value"})
    def test_raises_on_invalid_context_behavior(self):
        with self.assertRaises(ValueError):
            app_settings.CONTEXT_BEHAVIOR
