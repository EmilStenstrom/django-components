import os
import tempfile
from io import StringIO
from shutil import rmtree

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from .django_test_setup import *  # NOQA


class CreateComponentCommandTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.temp_dir = tempfile.mkdtemp()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        rmtree(cls.temp_dir)

    def test_default_file_names(self):
        component_name = "defaultcomponent"
        call_command("startcomponent", component_name, "--path", self.temp_dir)

        expected_files = [
            os.path.join(self.temp_dir, component_name, "script.js"),
            os.path.join(self.temp_dir, component_name, "style.css"),
            os.path.join(self.temp_dir, component_name, "template.html"),
        ]
        for file_path in expected_files:
            self.assertTrue(os.path.exists(file_path))

    def test_nondefault_creation(self):
        component_name = "testcomponent"
        call_command(
            "startcomponent",
            component_name,
            "--path",
            self.temp_dir,
            "--js",
            "test.js",
            "--css",
            "test.css",
            "--template",
            "test.html",
        )

        expected_files = [
            os.path.join(self.temp_dir, component_name, "test.js"),
            os.path.join(self.temp_dir, component_name, "test.css"),
            os.path.join(self.temp_dir, component_name, "test.html"),
            os.path.join(self.temp_dir, component_name, f"{component_name}.py"),
        ]

        for file_path in expected_files:
            self.assertTrue(os.path.exists(file_path), f"File {file_path} was not created")

    def test_dry_run(self):
        component_name = "dryruncomponent"
        call_command(
            "startcomponent",
            component_name,
            "--path",
            self.temp_dir,
            "--dry-run",
        )

        component_path = os.path.join(self.temp_dir, component_name)
        self.assertFalse(os.path.exists(component_path))

    def test_force_overwrite(self):
        component_name = "existingcomponent"
        component_path = os.path.join(self.temp_dir, component_name)
        os.makedirs(component_path)

        with open(os.path.join(component_path, f"{component_name}.py"), "w") as f:
            f.write("hello world")

        call_command(
            "startcomponent",
            component_name,
            "--path",
            self.temp_dir,
            "--force",
        )

        with open(os.path.join(component_path, f"{component_name}.py"), "r") as f:
            self.assertNotIn("hello world", f.read())

    def test_error_existing_component_no_force(self):
        component_name = "existingcomponent_2"
        component_path = os.path.join(self.temp_dir, component_name)
        os.makedirs(component_path)

        with self.assertRaises(CommandError):
            call_command("startcomponent", component_name, "--path", self.temp_dir)

    def test_verbose_output(self):
        component_name = "verbosecomponent"
        out = StringIO()
        call_command(
            "startcomponent",
            component_name,
            "--path",
            self.temp_dir,
            "--verbose",
            stdout=out,
        )
        output = out.getvalue()
        self.assertIn("component at", output)
