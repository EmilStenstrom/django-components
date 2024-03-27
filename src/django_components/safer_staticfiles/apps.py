from django.contrib.staticfiles.apps import StaticFilesConfig


class SaferStaticFilesConfig(StaticFilesConfig):
    """
    Extend the `ignore_patterns` class attr of StaticFilesConfig to include Python
    modules and HTML files.

    When this class is registered as an installed app,
    `$ ./manage.py collectstatic` will ignore .py and .html files,
    preventing potentially sensitive backend logic from being leaked
    by the static file server.
    """

    default = True  # Ensure that _this_ app is registered, as opposed to parent cls.
    ignore_patterns = StaticFilesConfig.ignore_patterns + [
        "*.py",
        "*.html",
        "*.pyc",
    ]
