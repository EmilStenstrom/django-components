from django.urls import include, path

# isort: off
from .django_test_setup import *  # noqa
from .testutils import Django30CompatibleSimpleTestCase as SimpleTestCase

# isort: on


from django_components import autodiscover, component

urlpatterns = [
    path("", include("tests.components.urls")),
]


class TestAutodiscover(SimpleTestCase):
    def setUp(self):
        settings.SETTINGS_MODULE = "tests.test_autodiscover"  # noqa

    def tearDown(self) -> None:
        del settings.SETTINGS_MODULE  # noqa

    def test_autodiscover_with_components_as_views(self):
        try:
            autodiscover()
        except component.AlreadyRegistered:
            self.fail(
                "Autodiscover should not raise AlreadyRegistered exception"
            )
