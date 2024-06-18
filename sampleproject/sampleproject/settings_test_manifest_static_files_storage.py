import os

from .settings import *  # noqa: F401, F403

DEBUG = False
STATIC_ROOT = os.path.expanduser('~/static_root/')
MEDIA_ROOT = os.path.expanduser('~/media_root/')
MEDIA_URL = '/media/'
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'
