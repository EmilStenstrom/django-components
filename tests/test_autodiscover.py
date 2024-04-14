from pathlib import Path

from django.template.engine import Engine
from django.urls import include, path

# isort: off
from .django_test_setup import settings
from .testutils import Django30CompatibleSimpleTestCase as SimpleTestCase

# isort: on

from django_components import autodiscover, component, import_file, component_registry
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
        self.assertEqual(
            sorted(dirs),
            sorted(
                [
                    Path(__file__).parent.resolve() / "components",
                ]
            ),
        )

    def test_complex_settings_module(self):
        settings.SETTINGS_MODULE = "tests.test_structures.test_structure_1.config.settings"  # noqa

        current_engine = Engine.get_default()
        loader = Loader(current_engine)
        dirs = loader.get_dirs()
        self.assertEqual(
            sorted(dirs),
            sorted(
                [
                    Path(__file__).parent.resolve() / "test_structures" / "test_structure_1" / "components",
                ]
            ),
        )

    def test_complex_settings_module_2(self):
        settings.SETTINGS_MODULE = "tests.test_structures.test_structure_2.project.settings.production"  # noqa

        current_engine = Engine.get_default()
        loader = Loader(current_engine)
        dirs = loader.get_dirs()
        self.assertEqual(
            sorted(dirs),
            sorted(
                [
                    Path(__file__).parent.resolve()
                    / "test_structures"
                    / "test_structure_2"
                    / "project"
                    / "components",
                ]
            ),
        )

    def test_complex_settings_module_3(self):
        settings.SETTINGS_MODULE = "tests.test_structures.test_structure_3.project.settings.production"  # noqa

        current_engine = Engine.get_default()
        loader = Loader(current_engine)
        dirs = loader.get_dirs()
        expected = [
            Path(__file__).parent.resolve() / "test_structures" / "test_structure_3" / "components",
            Path(__file__).parent.resolve() / "test_structures" / "test_structure_3" / "project" / "components",
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
        expected = [
            Path(__file__).parent.resolve() / "test_structures" / "test_structure_1" / "components",
        ]
        self.assertEqual(sorted(dirs), sorted(expected))


class TestAutodiscoverFileImport(SimpleTestCase):
    def setUp(self):
        settings.SETTINGS_MODULE = "tests.test_structures.test_structure_1.config.settings"  # noqa

    def tearDown(self) -> None:
        del settings.SETTINGS_MODULE  # noqa

    def test_imports_valid_file(self):
        all_components_before = component_registry.registry.all().copy()
        self.assertNotIn("relative_file_component", all_components_before)

        import_file("tests/components/relative_file/relative_file.py")

        all_components_after = component_registry.registry.all().copy()
        imported_components_count = len(all_components_after) - len(all_components_before)
        self.assertEqual(imported_components_count, 1)
        self.assertIn("relative_file_component", all_components_after)

    def test_raises_import_error_on_invalid_file(self):
        with self.assertRaises(ImportError):
            import_file("tests/components/relative_file/nonexist.py")
        with self.assertRaises(ImportError):
            import_file("tests/components/relative_file/nonexist")
