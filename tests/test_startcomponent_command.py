"""
This module contains test cases for the `startcomponent` command of a Django project.
The `StartComponentTestCase` class tests the functionality of creating a new component with different options.
It tests creating a component with default and custom filenames, creating a component with an existing directory,
creating a component with verbose and dry-run options, and running the command with output.
"""
import os
import shutil
import tempfile
from django.conf import settings
from django.core.management import call_command
from django.test import TestCase


"""
This module contains test cases for the `startcomponent` command of the Django Components app.
The `StartComponentTestCase` class contains methods to test the creation of a component with different options.
"""
class StartComponentTestCase(TestCase):
    def setUp(self):
        """
        Set up a temporary directory and change the BASE_DIR setting to it.
        """
        self.tmp_dir = tempfile.mkdtemp()
        self.old_base_dir = settings.BASE_DIR
        settings.BASE_DIR = self.tmp_dir

    def tearDown(self):
        """
        Remove the temporary directory and restore the original BASE_DIR setting.
        """
        shutil.rmtree(self.tmp_dir)
        settings.BASE_DIR = self.old_base_dir

    def test_create_component(self):
        """
        Test creating a component with default filenames.
        """
        component_name = "test_component"
        call_command("startcomponent", component_name, path=self.tmp_dir)

        component_path = os.path.join(self.tmp_dir, "components", component_name)
        self.assertTrue(os.path.exists(component_path))
        self.assertTrue(os.path.exists(os.path.join(component_path, "script.js")))
        self.assertTrue(os.path.exists(os.path.join(component_path, "style.css")))
        self.assertTrue(os.path.exists(os.path.join(component_path, "template.html")))
        self.assertTrue(os.path.exists(os.path.join(component_path, f"{component_name}.py")))

    def test_create_component_with_custom_filenames(self):
        """
        Test creating a component with custom filenames.
        """
        component_name = "test_component"
        js_filename = "custom.js"
        css_filename = "custom.css"
        template_filename = "custom.html"
        call_command(
            "startcomponent",
            component_name,
            path=self.tmp_dir,
            js=js_filename,
            css=css_filename,
            template=template_filename,
        )

        component_path = os.path.join(self.tmp_dir, "components", component_name)
        self.assertTrue(os.path.exists(component_path))
        self.assertTrue(os.path.exists(os.path.join(component_path, js_filename)))
        self.assertTrue(os.path.exists(os.path.join(component_path, css_filename)))
        self.assertTrue(os.path.exists(os.path.join(component_path, template_filename)))
        self.assertTrue(os.path.exists(os.path.join(component_path, f"{component_name}.py")))

    def test_create_component_with_existing_directory(self):
        """
        Test creating a component with an existing directory.
        """
        component_name = "test_component"
        component_path = os.path.join(self.tmp_dir, "components", component_name)
        os.makedirs(component_path)

        with self.assertRaisesRegex(
            Exception,
            f'The component "{component_name}" already exists at {component_path}. Use --force to overwrite.',
        ):
            call_command("startcomponent", component_name, path=self.tmp_dir)

    def test_create_component_with_existing_directory_and_force(self):
        """
        Test creating a component with an existing directory and the --force option.
        """
        component_name = "test_component"
        component_path = os.path.join(self.tmp_dir, "components", component_name)
        os.makedirs(component_path)

        call_command("startcomponent", component_name, path=self.tmp_dir, force=True)

        self.assertTrue(os.path.exists(component_path))
        self.assertTrue(os.path.exists(os.path.join(component_path, "script.js")))
        self.assertTrue(os.path.exists(os.path.join(component_path, "style.css")))
        self.assertTrue(os.path.exists(os.path.join(component_path, "template.html")))
        self.assertTrue(os.path.exists(os.path.join(component_path, f"{component_name}.py")))

    def test_create_component_with_verbose(self):
        """
        Test creating a component with the --verbose option.
        """
        component_name = "test_component"
        out = self._run_command_with_output(
            "startcomponent", component_name, path=self.tmp_dir, verbose=True
        )

        self.assertIn(f'The component "{component_name}" is created at', out)

    def test_create_component_with_dry_run(self):
        """
        Test creating a component with the --dry-run option.
        """
        component_name = "test_component"
        out = self._run_command_with_output(
            "startcomponent", component_name, path=self.tmp_dir, dry_run=True
        )

        self.assertIn(f'The component "{component_name}" is created at', out)
        component_path = os.path.join(self.tmp_dir, "components", component_name)
        self.assertFalse(os.path.exists(component_path))

    def _run_command_with_output(self, *args, **kwargs):
        """
        Run a management command and capture its output.

        Args:
            *args: Positional arguments to pass to call_command.
            **kwargs: Keyword arguments to pass to call_command.

        Returns:
            str: The output of the command.
        """
        from io import StringIO
        from django.core.management import CommandError

        out = StringIO()
        try:
            call_command(*args, stdout=out, stderr=out, **kwargs)
        except CommandError as e:
            out.write(str(e))
        return out.getvalue()