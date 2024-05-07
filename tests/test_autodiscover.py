from pathlib import Path
from unittest import mock
from unittest.mock import MagicMock, patch

from django.template.engine import Engine
from django.urls import include, path

# isort: off
from .django_test_setup import settings
from .testutils import BaseTestCase

# isort: on

from django_components import _filepath_to_python_module, autodiscover, component, component_registry
from django_components.template_loader import Loader

urlpatterns = [
    path("", include("tests.components.urls")),
]


class TestAutodiscover(BaseTestCase):
    def setUp(self):
        settings.SETTINGS_MODULE = "tests.test_autodiscover"  # noqa

    def tearDown(self) -> None:
        del settings.SETTINGS_MODULE  # noqa

    def test_autodiscover_with_components_as_views(self):
        all_components_before = component_registry.registry.all().copy()

        try:
            autodiscover()
        except component.AlreadyRegistered:
            self.fail("Autodiscover should not raise AlreadyRegistered exception")

        all_components_after = component_registry.registry.all().copy()
        imported_components_count = len(all_components_after) - len(all_components_before)
        self.assertEqual(imported_components_count, 1)


class TestLoaderSettingsModule(BaseTestCase):
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


class TestBaseDir(BaseTestCase):
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


class TestStaticFilesDirs(BaseTestCase):
    def setUp(self):
        settings.STATICFILES_DIRS = [
            "components",
            ("with_alias", "components"),
            ("too_many", "items", "components"),
            ("with_not_str_alias", 3),
        ]  # noqa

    def tearDown(self) -> None:
        del settings.STATICFILES_DIRS  # noqa

    @patch("django_components.template_loader.logger.warning")
    def test_static_files_dirs(self, mock_warning: MagicMock):
        mock_warning.reset_mock()
        current_engine = Engine.get_default()
        Loader(current_engine).get_dirs()

        warn_inputs = [warn.args[0] for warn in mock_warning.call_args_list]
        assert "Got <class 'tuple'> : ('too_many', 'items', 'components')" in warn_inputs[0]
        assert "Got <class 'int'> : 3" in warn_inputs[1]


class TestFilepathToPythonModule(BaseTestCase):
    def test_prepares_path(self):
        self.assertEqual(
            _filepath_to_python_module(Path("tests.py")),
            "tests",
        )
        self.assertEqual(
            _filepath_to_python_module(Path("tests/components/relative_file/relative_file.py")),
            "tests.components.relative_file.relative_file",
        )

    def test_handles_nonlinux_paths(self):
        with mock.patch("os.path.sep", new="//"):
            self.assertEqual(
                _filepath_to_python_module(Path("tests.py")),
                "tests",
            )

            self.assertEqual(
                _filepath_to_python_module(Path("tests//components//relative_file//relative_file.py")),
                "tests.components.relative_file.relative_file",
            )

        with mock.patch("os.path.sep", new="\\"):
            self.assertEqual(
                _filepath_to_python_module(Path("tests.py")),
                "tests",
            )

            self.assertEqual(
                _filepath_to_python_module(Path("tests\\components\\relative_file\\relative_file.py")),
                "tests.components.relative_file.relative_file",
            )
