from pathlib import Path
from typing import Dict, Optional

import django
from django.conf import settings


def setup_test_config(
    components: Optional[Dict] = None,
    extra_settings: Optional[Dict] = None,
):
    if settings.configured:
        return
    
    default_settings = {
        "BASE_DIR": Path(__file__).resolve().parent,
        "INSTALLED_APPS": ("django_components", "tests.test_app"),
        "TEMPLATES": [
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "DIRS": [
                    "tests/templates/",
                    "tests/components/",  # Required for template relative imports in tests
                ],
            }
        ],
        "COMPONENTS": {
            "template_cache_size": 128,
            **(components or {}),
        },
        "MIDDLEWARE": ["django_components.middleware.ComponentDependencyMiddleware"],
        "DATABASES": {
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": ":memory:",
            }
        },
        "SECRET_KEY": "secret",
    }

    settings.configure(**{
        **default_settings,
        **(extra_settings or {}),
    })

    django.setup()
