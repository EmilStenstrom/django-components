from django.conf import settings

from .django_test_setup import *  # NOQA
from .testutils import Django30CompatibleSimpleTestCase as SimpleTestCase


class ValidateWrongContextBehaviorValueTestCase(SimpleTestCase):
    def setUp(self) -> None:
        settings.COMPONENTS["context_behavior"] = "invalid_value"
        return super().setUp()

    def tearDown(self) -> None:
        del settings.COMPONENTS["context_behavior"]
        return super().tearDown()

    def test_valid_context_behavior(self):
        from django_components.app_settings import app_settings

        with self.assertRaises(ValueError):
            app_settings.CONTEXT_BEHAVIOR.value
