from pathlib import Path

from django.template.engine import Engine
from django.urls import include, path

# isort: off
from .django_test_setup import settings
from .testutils import Django30CompatibleSimpleTestCase as SimpleTestCase

# isort: on

from django_components import autodiscover, component
from django_components.template_loader import Loader

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
            self.fail("Autodiscover should not raise AlreadyRegistered exception")


class TestLoaderSettingsModule(SimpleTestCase):
    def tearDown(self) -> None:
        del settings.SETTINGS_MODULE  # noqa

    def test_get_dirs(self):
        settings.SETTINGS_MODULE = "tests.test_autodiscover"  # noqa
        current_engine = Engine.get_default()
        loader = Loader(current_engine)
        dirs = loader.get_dirs()
        self.assertEqual(dirs, [Path(__file__).parent.resolve() / "components"])

    def test_complex_settings_module(self):
        settings.SETTINGS_MODULE = "tests.test_structures.test_structure_1.config.settings"  # noqa

        current_engine = Engine.get_default()
        loader = Loader(current_engine)
        dirs = loader.get_dirs()
        self.assertEqual(
            dirs,
            [Path(__file__).parent.resolve() / "test_structures" / "test_structure_1" / "components"],
        )

    def test_complex_settings_module_2(self):
        settings.SETTINGS_MODULE = "tests.test_structures.test_structure_2.project.settings.production"  # noqa

        current_engine = Engine.get_default()
        loader = Loader(current_engine)
        dirs = loader.get_dirs()
        self.assertEqual(
            dirs,
            [Path(__file__).parent.resolve() / "test_structures" / "test_structure_2" / "project" / "components"],
        )

    def test_complex_settings_module_3(self):
        settings.SETTINGS_MODULE = "tests.test_structures.test_structure_3.project.settings.production"  # noqa

        current_engine = Engine.get_default()
        loader = Loader(current_engine)
        dirs = loader.get_dirs()
        expected = [
            (Path(__file__).parent.resolve() / "test_structures" / "test_structure_3" / "components"),
            (Path(__file__).parent.resolve() / "test_structures" / "test_structure_3" / "project" / "components"),
        ]
        self.assertEqual(
            sorted(dirs),
            sorted(expected),
        )


class TestBaseDir(SimpleTestCase):
    def setUp(self):
        settings.BASE_DIR = Path(__file__).parent.resolve() / "test_structures" / "test_structure_1"  # noqa
        settings.SETTINGS_MODULE = "tests_fake.test_autodiscover_fake"  # noqa

    def tearDown(self) -> None:
        del settings.BASE_DIR  # noqa
        del settings.SETTINGS_MODULE  # noqa

    def test_base_dir(self):
        current_engine = Engine.get_default()
        loader = Loader(current_engine)
        dirs = loader.get_dirs()
        expected = [Path(__file__).parent.resolve() / "test_structures" / "test_structure_1" / "components"]
        self.assertEqual(dirs, expected)
