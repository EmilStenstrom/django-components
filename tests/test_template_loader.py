from pathlib import Path
from unittest.mock import MagicMock, patch

from django.template.engine import Engine
from django.test import override_settings

from django_components.template_loader import Loader

from .django_test_setup import setup_test_config
from .testutils import BaseTestCase

setup_test_config({"autodiscover": False})


@override_settings(
    BASE_DIR=Path(__file__).parent.resolve(),
)
class TemplateLoaderTest(BaseTestCase):
    def test_get_dirs__base_dir(self):
        current_engine = Engine.get_default()
        loader = Loader(current_engine)
        dirs = loader.get_dirs()
        self.assertEqual(
            sorted(dirs),
            sorted(
                [
                    # Top-level /components dir
                    Path(__file__).parent.resolve() / "components",
                    # App-level /components dir
                    Path(__file__).parent.resolve() / "test_app" / "components",
                ]
            ),
        )

    @override_settings(
        BASE_DIR=Path(__file__).parent.resolve() / "test_structures" / "test_structure_1",  # noqa
    )
    def test_get_dirs__base_dir__complex(self):
        current_engine = Engine.get_default()
        loader = Loader(current_engine)
        dirs = loader.get_dirs()
        expected = [
            Path(__file__).parent.resolve() / "test_structures" / "test_structure_1" / "components",
        ]
        self.assertEqual(sorted(dirs), sorted(expected))

    @override_settings(
        STATICFILES_DIRS=[
            Path(__file__).parent.resolve() / "components",
            ("with_alias", Path(__file__).parent.resolve() / "components"),
            ("too_many", Path(__file__).parent.resolve() / "components", Path(__file__).parent.resolve()),
            ("with_not_str_alias", 3),
        ]  # noqa
    )
    @patch("django_components.template_loader.logger.warning")
    def test_get_dirs__components_dirs(self, mock_warning: MagicMock):
        mock_warning.reset_mock()
        current_engine = Engine.get_default()
        Loader(current_engine).get_dirs()

        warn_inputs = [warn.args[0] for warn in mock_warning.call_args_list]
        assert "Got <class 'int'> : 3" in warn_inputs[0]

    @override_settings(
        COMPONENTS={
            "dirs": ["components"],
        }
    )
    def test_get_dirs__componenents_dirs__raises_on_relative_path_1(self):
        current_engine = Engine.get_default()
        loader = Loader(current_engine)
        with self.assertRaisesMessage(ValueError, "COMPONENTS.dirs must contain absolute paths"):
            loader.get_dirs()

    @override_settings(
        COMPONENTS={
            "dirs": [("with_alias", "components")],
        }
    )
    def test_get_dirs__component_dirs__raises_on_relative_path_2(self):
        current_engine = Engine.get_default()
        loader = Loader(current_engine)
        with self.assertRaisesMessage(ValueError, "COMPONENTS.dirs must contain absolute paths"):
            loader.get_dirs()
