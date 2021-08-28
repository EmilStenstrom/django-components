"""
Wrapper for loading templates from "components" directories in INSTALLED_APPS
packages.
"""

from django.template.loaders.filesystem import Loader as FilesystemLoader
from django.template.utils import get_app_template_dirs


class Loader(FilesystemLoader):
    def get_dirs(self):
        return get_app_template_dirs('components')
