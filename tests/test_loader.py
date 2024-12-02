import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.test import override_settings

from django_components.util.loader import _filepath_to_python_module, get_component_dirs, get_component_files

from .django_test_setup import setup_test_config
from .testutils import BaseTestCase

setup_test_config({"autodiscover": False})


class ComponentDirsTest(BaseTestCase):
    @override_settings(
        BASE_DIR=Path(__file__).parent.resolve(),
    )
    def test_get_dirs__base_dir(self):
        dirs = sorted(get_component_dirs())

        apps_dirs = [dirs[0], dirs[2]]
        own_dirs = [dirs[1], *dirs[3:]]

        self.assertEqual(
            own_dirs,
            [
                # Top-level /components dir
                Path(__file__).parent.resolve()
                / "components",
            ],
        )

        # Apps with a `components` dir
        self.assertEqual(len(apps_dirs), 2)

        # NOTE: Compare parts so that the test works on Windows too
        self.assertTupleEqual(apps_dirs[0].parts[-2:], ("django_components", "components"))
        self.assertTupleEqual(apps_dirs[1].parts[-3:], ("tests", "test_app", "components"))

    @override_settings(
        BASE_DIR=Path(__file__).parent.resolve() / "test_structures" / "test_structure_1",  # noqa
    )
    def test_get_dirs__base_dir__complex(self):
        dirs = sorted(get_component_dirs())

        apps_dirs = dirs[:2]
        own_dirs = dirs[2:]

        # Apps with a `components` dir
        self.assertEqual(len(apps_dirs), 2)

        # NOTE: Compare parts so that the test works on Windows too
        self.assertTupleEqual(apps_dirs[0].parts[-2:], ("django_components", "components"))
        self.assertTupleEqual(apps_dirs[1].parts[-3:], ("tests", "test_app", "components"))

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
    @patch("django_components.util.loader.logger.warning")
    def test_get_dirs__components_dirs(self, mock_warning: MagicMock):
        mock_warning.reset_mock()
        dirs = sorted(get_component_dirs())

        apps_dirs = [dirs[0], dirs[2]]
        own_dirs = [dirs[1], *dirs[3:]]

        # Apps with a `components` dir
        self.assertEqual(len(apps_dirs), 2)

        # NOTE: Compare parts so that the test works on Windows too
        self.assertTupleEqual(apps_dirs[0].parts[-2:], ("django_components", "components"))
        self.assertTupleEqual(apps_dirs[1].parts[-3:], ("tests", "test_app", "components"))

        self.assertEqual(
            own_dirs,
            [
                # Top-level /components dir
                Path(__file__).parent.resolve()
                / "components",
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
        dirs = sorted(get_component_dirs())

        apps_dirs = dirs

        # Apps with a `components` dir
        self.assertEqual(len(apps_dirs), 2)

        # NOTE: Compare parts so that the test works on Windows too
        self.assertTupleEqual(apps_dirs[0].parts[-2:], ("django_components", "components"))
        self.assertTupleEqual(apps_dirs[1].parts[-3:], ("tests", "test_app", "components"))

    @override_settings(
        BASE_DIR=Path(__file__).parent.resolve(),
        COMPONENTS={
            "dirs": ["components"],
        },
    )
    def test_get_dirs__componenents_dirs__raises_on_relative_path_1(self):
        with self.assertRaisesMessage(ValueError, "COMPONENTS.dirs must contain absolute paths"):
            get_component_dirs()

    @override_settings(
        BASE_DIR=Path(__file__).parent.resolve(),
        COMPONENTS={
            "dirs": [("with_alias", "components")],
        },
    )
    def test_get_dirs__component_dirs__raises_on_relative_path_2(self):
        with self.assertRaisesMessage(ValueError, "COMPONENTS.dirs must contain absolute paths"):
            get_component_dirs()

    @override_settings(
        BASE_DIR=Path(__file__).parent.resolve(),
        COMPONENTS={
            "app_dirs": ["custom_comps_dir"],
        },
    )
    def test_get_dirs__app_dirs(self):
        dirs = sorted(get_component_dirs())

        apps_dirs = dirs[1:]
        own_dirs = dirs[:1]

        # Apps with a `components` dir
        self.assertEqual(len(apps_dirs), 1)

        # NOTE: Compare parts so that the test works on Windows too
        self.assertTupleEqual(apps_dirs[0].parts[-3:], ("tests", "test_app", "custom_comps_dir"))

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
            "app_dirs": [],
        },
    )
    def test_get_dirs__app_dirs_empty(self):
        dirs = sorted(get_component_dirs())

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
        dirs = sorted(get_component_dirs())

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
        dirs = sorted(get_component_dirs())

        apps_dirs = [dirs[0], *dirs[2:]]
        own_dirs = [dirs[1]]

        # Apps with a `components` dir
        self.assertEqual(len(apps_dirs), 2)

        # NOTE: Compare parts so that the test works on Windows too
        self.assertTupleEqual(apps_dirs[0].parts[-2:], ("django_components", "components"))
        self.assertTupleEqual(apps_dirs[1].parts[-4:], ("tests", "test_app_nested", "app", "components"))

        self.assertEqual(
            own_dirs,
            [
                # Top-level /components dir
                Path(__file__).parent.resolve()
                / "components",
            ],
        )


class ComponentFilesTest(BaseTestCase):
    @override_settings(
        BASE_DIR=Path(__file__).parent.resolve(),
    )
    def test_get_files__py(self):
        files = sorted(get_component_files(".py"))

        dot_paths = [f.dot_path for f in files]
        file_paths = [f.filepath for f in files]

        self.assertEqual(
            dot_paths,
            [
                "components",
                "components.multi_file.multi_file",
                "components.relative_file.relative_file",
                "components.relative_file_pathobj.relative_file_pathobj",
                "components.single_file",
                "components.staticfiles.staticfiles",
                "components.urls",
                "django_components.components",
                "django_components.components.dynamic",
                "tests.test_app.components.app_lvl_comp.app_lvl_comp",
            ],
        )

        # NOTE: Compare parts so that the test works on Windows too
        self.assertTupleEqual(file_paths[0].parts[-3:], ("tests", "components", "__init__.py"))
        self.assertTupleEqual(file_paths[1].parts[-4:], ("tests", "components", "multi_file", "multi_file.py"))
        self.assertTupleEqual(file_paths[2].parts[-4:], ("tests", "components", "relative_file", "relative_file.py"))
        self.assertTupleEqual(
            file_paths[3].parts[-4:], ("tests", "components", "relative_file_pathobj", "relative_file_pathobj.py")
        )
        self.assertTupleEqual(file_paths[4].parts[-3:], ("tests", "components", "single_file.py"))
        self.assertTupleEqual(file_paths[5].parts[-4:], ("tests", "components", "staticfiles", "staticfiles.py"))
        self.assertTupleEqual(file_paths[6].parts[-3:], ("tests", "components", "urls.py"))
        self.assertTupleEqual(file_paths[7].parts[-3:], ("django_components", "components", "__init__.py"))
        self.assertTupleEqual(file_paths[8].parts[-3:], ("django_components", "components", "dynamic.py"))
        self.assertTupleEqual(
            file_paths[9].parts[-5:], ("tests", "test_app", "components", "app_lvl_comp", "app_lvl_comp.py")
        )

    @override_settings(
        BASE_DIR=Path(__file__).parent.resolve(),
    )
    def test_get_files__js(self):
        files = sorted(get_component_files(".js"))

        dot_paths = [f.dot_path for f in files]
        file_paths = [f.filepath for f in files]

        self.assertEqual(
            dot_paths,
            [
                "components.relative_file.relative_file",
                "components.relative_file_pathobj.relative_file_pathobj",
                "components.staticfiles.staticfiles",
                "tests.test_app.components.app_lvl_comp.app_lvl_comp",
            ],
        )

        # NOTE: Compare parts so that the test works on Windows too
        self.assertTupleEqual(file_paths[0].parts[-4:], ("tests", "components", "relative_file", "relative_file.js"))
        self.assertTupleEqual(
            file_paths[1].parts[-4:], ("tests", "components", "relative_file_pathobj", "relative_file_pathobj.js")
        )
        self.assertTupleEqual(file_paths[2].parts[-4:], ("tests", "components", "staticfiles", "staticfiles.js"))
        self.assertTupleEqual(
            file_paths[3].parts[-5:], ("tests", "test_app", "components", "app_lvl_comp", "app_lvl_comp.js")
        )


class TestFilepathToPythonModule(BaseTestCase):
    def test_prepares_path(self):
        base_path = str(settings.BASE_DIR)

        the_path = os.path.join(base_path, "tests.py")
        self.assertEqual(
            _filepath_to_python_module(the_path, base_path, None),
            "tests",
        )

        the_path = os.path.join(base_path, "tests/components/relative_file/relative_file.py")
        self.assertEqual(
            _filepath_to_python_module(the_path, base_path, None),
            "tests.components.relative_file.relative_file",
        )

    def test_handles_nonlinux_paths(self):
        base_path = str(settings.BASE_DIR).replace("/", "//")

        with patch("os.path.sep", new="//"):
            the_path = os.path.join(base_path, "tests.py")
            self.assertEqual(
                _filepath_to_python_module(the_path, base_path, None),
                "tests",
            )

            the_path = os.path.join(base_path, "tests//components//relative_file//relative_file.py")
            self.assertEqual(
                _filepath_to_python_module(the_path, base_path, None),
                "tests.components.relative_file.relative_file",
            )

        base_path = str(settings.BASE_DIR).replace("//", "\\")
        with patch("os.path.sep", new="\\"):
            the_path = os.path.join(base_path, "tests.py")
            self.assertEqual(
                _filepath_to_python_module(the_path, base_path, None),
                "tests",
            )

            the_path = os.path.join(base_path, "tests\\components\\relative_file\\relative_file.py")
            self.assertEqual(
                _filepath_to_python_module(the_path, base_path, None),
                "tests.components.relative_file.relative_file",
            )
