import re
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.template.engine import Engine
from django.test import override_settings

from django_components.template_loader import Loader, get_dirs

from .django_test_setup import setup_test_config
from .testutils import BaseTestCase

setup_test_config({"autodiscover": False})


class TemplateLoaderTest(BaseTestCase):
    @override_settings(
        BASE_DIR=Path(__file__).parent.resolve(),
    )
    def test_get_dirs__base_dir(self):
        current_engine = Engine.get_default()
        loader = Loader(current_engine)
        dirs = sorted(loader.get_dirs())

        apps_dirs = [dirs[0], dirs[2]]
        own_dirs = [dirs[1], *dirs[3:]]

        self.assertEqual(
            own_dirs,
            [
                # Top-level /components dir
                Path(__file__).parent.resolve() / "components",
            ]
        )

        # Apps with a `components` dir
        self.assertEqual(len(apps_dirs), 2)
        self.assertRegex(str(apps_dirs[0]), re.compile(r"\/django_components\/components$"))
        self.assertRegex(str(apps_dirs[1]), re.compile(r"\/tests\/test_app\/components$"))

    @override_settings(
        BASE_DIR=Path(__file__).parent.resolve() / "test_structures" / "test_structure_1",  # noqa
    )
    def test_get_dirs__base_dir__complex(self):
        current_engine = Engine.get_default()
        loader = Loader(current_engine)
        dirs = sorted(loader.get_dirs())

        apps_dirs = dirs[:2]
        own_dirs = dirs[2:]

        # Apps with a `components` dir
        self.assertEqual(len(apps_dirs), 2)
        self.assertRegex(str(apps_dirs[0]), re.compile(r"\/django_components\/components$"))
        self.assertRegex(str(apps_dirs[1]), re.compile(r"\/tests\/test_app\/components$"))

        expected = [
            Path(__file__).parent.resolve() / "test_structures" / "test_structure_1" / "components",
        ]
        self.assertEqual(own_dirs, expected)

    @override_settings(
        BASE_DIR=Path(__file__).parent.resolve(),
        STATICFILES_DIRS=[
            Path(__file__).parent.resolve() / "components",
            ("with_alias", Path(__file__).parent.resolve() / "components"),
            ("too_many", Path(__file__).parent.resolve() / "components", Path(__file__).parent.resolve()),
            ("with_not_str_alias", 3),
        ],  # noqa
    )
    @patch("django_components.template_loader.logger.warning")
    def test_get_dirs__components_dirs(self, mock_warning: MagicMock):
        mock_warning.reset_mock()
        dirs = sorted(get_dirs())

        apps_dirs = [dirs[0], dirs[2]]
        own_dirs = [dirs[1], *dirs[3:]]

        # Apps with a `components` dir
        self.assertEqual(len(apps_dirs), 2)
        self.assertRegex(str(apps_dirs[0]), re.compile(r"\/django_components\/components$"))
        self.assertRegex(str(apps_dirs[1]), re.compile(r"\/tests\/test_app\/components$"))

        self.assertEqual(
            own_dirs,
            [
                # Top-level /components dir
                Path(__file__).parent.resolve() / "components",
            ],
        )

        warn_inputs = [warn.args[0] for warn in mock_warning.call_args_list]
        assert "Got <class 'int'> : 3" in warn_inputs[0]

    @override_settings(
        BASE_DIR=Path(__file__).parent.resolve(),
        COMPONENTS={
            "dirs": [],
        },
    )
    def test_get_dirs__components_dirs__empty(self):
        dirs = sorted(get_dirs())

        apps_dirs = dirs

        # Apps with a `components` dir
        self.assertEqual(len(apps_dirs), 2)
        self.assertRegex(str(apps_dirs[0]), re.compile(r"\/django_components\/components$"))
        self.assertRegex(str(apps_dirs[1]), re.compile(r"\/tests\/test_app\/components$"))

    @override_settings(
        BASE_DIR=Path(__file__).parent.resolve(),
        COMPONENTS={
            "dirs": ["components"],
        },
    )
    def test_get_dirs__componenents_dirs__raises_on_relative_path_1(self):
        current_engine = Engine.get_default()
        loader = Loader(current_engine)
        with self.assertRaisesMessage(ValueError, "COMPONENTS.dirs must contain absolute paths"):
            loader.get_dirs()

    @override_settings(
        BASE_DIR=Path(__file__).parent.resolve(),
        COMPONENTS={
            "dirs": [("with_alias", "components")],
        },
    )
    def test_get_dirs__component_dirs__raises_on_relative_path_2(self):
        current_engine = Engine.get_default()
        loader = Loader(current_engine)
        with self.assertRaisesMessage(ValueError, "COMPONENTS.dirs must contain absolute paths"):
            loader.get_dirs()

    @override_settings(
        BASE_DIR=Path(__file__).parent.resolve(),
        COMPONENTS={
            "app_dirs": ["custom_comps_dir"],
        },
    )
    def test_get_dirs__app_dirs(self):
        current_engine = Engine.get_default()
        loader = Loader(current_engine)
        dirs = sorted(loader.get_dirs())

        apps_dirs = dirs[1:]
        own_dirs = dirs[:1]

        # Apps with a `components` dir
        self.assertEqual(len(apps_dirs), 1)
        self.assertRegex(str(apps_dirs[0]), re.compile(r"\/tests\/test_app\/custom_comps_dir$"))

        self.assertEqual(
            own_dirs,
            [
                # Top-level /components dir
                Path(__file__).parent.resolve() / "components",
            ],
        )

    @override_settings(
        BASE_DIR=Path(__file__).parent.resolve(),
        COMPONENTS={
            "app_dirs": [],
        },
    )
    def test_get_dirs__app_dirs_empty(self):
        current_engine = Engine.get_default()
        loader = Loader(current_engine)
        dirs = sorted(loader.get_dirs())

        own_dirs = dirs

        self.assertEqual(
            own_dirs,
            [
                # Top-level /components dir
                Path(__file__).parent.resolve()
                / "components",
            ],
        )

    @override_settings(
        BASE_DIR=Path(__file__).parent.resolve(),
        COMPONENTS={
            "app_dirs": ["this_dir_does_not_exist"],
        },
    )
    def test_get_dirs__app_dirs_not_found(self):
        current_engine = Engine.get_default()
        loader = Loader(current_engine)
        dirs = sorted(loader.get_dirs())

        own_dirs = dirs

        self.assertEqual(
            own_dirs,
            [
                # Top-level /components dir
                Path(__file__).parent.resolve()
                / "components",
            ],
        )

    @override_settings(
        BASE_DIR=Path(__file__).parent.resolve(),
        INSTALLED_APPS=("django_components", "tests.test_app_nested.app"),
    )
    def test_get_dirs__nested_apps(self):
        current_engine = Engine.get_default()
        loader = Loader(current_engine)
        dirs = sorted(loader.get_dirs())

        apps_dirs = [dirs[0], *dirs[2:]]
        own_dirs = [dirs[1]]

        # Apps with a `components` dir
        self.assertEqual(len(apps_dirs), 2)
        self.assertRegex(str(apps_dirs[0]), re.compile(r"\/django_components\/components$"))
        self.assertRegex(str(apps_dirs[1]), re.compile(r"\/tests\/test_app_nested\/app\/components$"))

        self.assertEqual(
            own_dirs,
            [
                # Top-level /components dir
                Path(__file__).parent.resolve() / "components",
            ],
        )
