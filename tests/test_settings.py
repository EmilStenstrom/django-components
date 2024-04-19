from django.conf import settings

from .django_test_setup import *  # NOQA
from .testutils import BaseTestCase


class ValidateWrongContextBehaviorValueTestCase(BaseTestCase):
    def setUp(self) -> None:
        settings.COMPONENTS["context_behavior"] = "invalid_value"
        return super().setUp()

    def tearDown(self) -> None:
        del settings.COMPONENTS["context_behavior"]
        return super().tearDown()

    def test_valid_context_behavior(self):
        from django_components.app_settings import app_settings

        with self.assertRaises(ValueError):
            app_settings.CONTEXT_BEHAVIOR


class ValidateCorrectContextBehaviorValueTestCase(BaseTestCase):
    def setUp(self) -> None:
        settings.COMPONENTS["context_behavior"] = "isolated"
        return super().setUp()

    def tearDown(self) -> None:
        del settings.COMPONENTS["context_behavior"]
        return super().tearDown()

    def test_valid_context_behavior(self):
        from django_components.app_settings import app_settings

        self.assertEqual(app_settings.CONTEXT_BEHAVIOR, "isolated")
