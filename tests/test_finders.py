import re
from pathlib import Path

from django.contrib.staticfiles.management.commands.collectstatic import Command
from django.test import SimpleTestCase, override_settings

from .django_test_setup import setup_test_config

setup_test_config({"autodiscover": False})


# This subclass allows us to call the `collectstatic` command from within Python.
# We call the `collect` method, which returns info about what files were collected.
#
# The methods below are overriden to ensure we don't make any filesystem changes
# (copy/delete), as the original command copies files. Thus we can safely test that
# our app works as intended.
class MockCollectstaticCommand(Command):
    # NOTE: We do not expect this to be called
    def clear_dir(self, path):
        raise NotImplementedError()

    # NOTE: We do not expect this to be called
    def link_file(self, path, prefixed_path, source_storage):
        raise NotImplementedError()

    def copy_file(self, path, prefixed_path, source_storage):
        # Skip this file if it was already copied earlier
        if prefixed_path in self.copied_files:
            return self.log("Skipping '%s' (already copied earlier)" % path)
        # Delete the target file if needed or break
        if not self.delete_file(path, prefixed_path, source_storage):
            return
        # The full path of the source file
        source_path = source_storage.path(path)
        # Finally start copying
        if self.dry_run:
            self.log("Pretending to copy '%s'" % source_path, level=1)
        else:
            self.log("Copying '%s'" % source_path, level=2)
            # ############# OUR CHANGE ##############
            # with source_storage.open(path) as source_file:
            #     self.storage.save(prefixed_path, source_file)
            # ############# OUR CHANGE ##############
        self.copied_files.append(prefixed_path)


def do_collect():
    cmd = MockCollectstaticCommand()
    cmd.set_options(
        interactive=False,
        verbosity=1,
        link=False,
        clear=False,
        dry_run=False,
        ignore_patterns=[],
        use_default_ignore_patterns=True,
        post_process=True,
    )
    collected = cmd.collect()
    return collected


common_settings = {
    "STATIC_URL": "static/",
    "STATIC_ROOT": "staticfiles",
    "ROOT_URLCONF": __name__,
    "INSTALLED_APPS": ("django_components", "django.contrib.staticfiles"),
}
COMPONENTS = {
    "dirs": [Path(__file__).resolve().parent / "components"],
}


class StaticFilesFinderTests(SimpleTestCase):
    @override_settings(
        **common_settings,
        COMPONENTS=COMPONENTS,
        STATICFILES_FINDERS=[
            # Default finders
            "django.contrib.staticfiles.finders.FileSystemFinder",
            "django.contrib.staticfiles.finders.AppDirectoriesFinder",
        ],
    )
    def test_python_and_html_included(self):
        collected = do_collect()

        # Check that the component files are NOT loaded when our finder is NOT added
        self.assertNotIn("staticfiles/staticfiles.css", collected["modified"])
        self.assertNotIn("staticfiles/staticfiles.js", collected["modified"])
        self.assertNotIn("staticfiles/staticfiles.html", collected["modified"])
        self.assertNotIn("staticfiles/staticfiles.py", collected["modified"])

        self.assertListEqual(collected["unmodified"], [])
        self.assertListEqual(collected["post_processed"], [])

    @override_settings(
        **common_settings,
        COMPONENTS=COMPONENTS,
        STATICFILES_FINDERS=[
            # Default finders
            "django.contrib.staticfiles.finders.FileSystemFinder",
            "django.contrib.staticfiles.finders.AppDirectoriesFinder",
            # Django components
            "django_components.finders.ComponentsFileSystemFinder",
        ],
    )
    def test_python_and_html_omitted(self):
        collected = do_collect()

        # Check that our staticfiles_finder finds the files and OMITS .py and .html files
        self.assertIn("staticfiles/staticfiles.css", collected["modified"])
        self.assertIn("staticfiles/staticfiles.js", collected["modified"])
        self.assertNotIn("staticfiles/staticfiles.html", collected["modified"])
        self.assertNotIn("staticfiles/staticfiles.py", collected["modified"])

        self.assertListEqual(collected["unmodified"], [])
        self.assertListEqual(collected["post_processed"], [])

    @override_settings(
        **common_settings,
        COMPONENTS={
            **COMPONENTS,
            "static_files_allowed": [
                ".js",
            ],
            "forbidden_static_files": [],
        },
        STATICFILES_FINDERS=[
            # Default finders
            "django.contrib.staticfiles.finders.FileSystemFinder",
            "django.contrib.staticfiles.finders.AppDirectoriesFinder",
            # Django components
            "django_components.finders.ComponentsFileSystemFinder",
        ],
    )
    def test_set_static_files_allowed(self):
        collected = do_collect()

        # Check that our staticfiles_finder finds the files and OMITS .py and .html files
        self.assertNotIn("staticfiles/staticfiles.css", collected["modified"])
        self.assertIn("staticfiles/staticfiles.js", collected["modified"])
        self.assertNotIn("staticfiles/staticfiles.html", collected["modified"])
        self.assertNotIn("staticfiles/staticfiles.py", collected["modified"])

        self.assertListEqual(collected["unmodified"], [])
        self.assertListEqual(collected["post_processed"], [])

    @override_settings(
        **common_settings,
        COMPONENTS={
            **COMPONENTS,
            "static_files_allowed": [
                re.compile(r".*"),
            ],
            "forbidden_static_files": [
                re.compile(r"\.(?:js)$"),
            ],
        },
        STATICFILES_FINDERS=[
            # Default finders
            "django.contrib.staticfiles.finders.FileSystemFinder",
            "django.contrib.staticfiles.finders.AppDirectoriesFinder",
            # Django components
            "django_components.finders.ComponentsFileSystemFinder",
        ],
    )
    def test_set_forbidden_files(self):
        collected = do_collect()

        # Check that our staticfiles_finder finds the files and OMITS .py and .html files
        self.assertIn("staticfiles/staticfiles.css", collected["modified"])
        self.assertNotIn("staticfiles/staticfiles.js", collected["modified"])
        self.assertIn("staticfiles/staticfiles.html", collected["modified"])
        self.assertIn("staticfiles/staticfiles.py", collected["modified"])

        self.assertListEqual(collected["unmodified"], [])
        self.assertListEqual(collected["post_processed"], [])

    @override_settings(
        **common_settings,
        COMPONENTS={
            **COMPONENTS,
            "static_files_allowed": [
                ".js",
                ".css",
            ],
            "forbidden_static_files": [
                ".js",
            ],
        },
        STATICFILES_FINDERS=[
            # Default finders
            "django.contrib.staticfiles.finders.FileSystemFinder",
            "django.contrib.staticfiles.finders.AppDirectoriesFinder",
            # Django components
            "django_components.finders.ComponentsFileSystemFinder",
        ],
    )
    def test_set_both_allowed_and_forbidden_files(self):
        collected = do_collect()

        # Check that our staticfiles_finder finds the files and OMITS .py and .html files
        self.assertIn("staticfiles/staticfiles.css", collected["modified"])
        self.assertNotIn("staticfiles/staticfiles.js", collected["modified"])
        self.assertNotIn("staticfiles/staticfiles.html", collected["modified"])
        self.assertNotIn("staticfiles/staticfiles.py", collected["modified"])

        self.assertListEqual(collected["unmodified"], [])
        self.assertListEqual(collected["post_processed"], [])
