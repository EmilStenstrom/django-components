import django
from django.conf import settings

if not settings.configured:
    settings.configure(
        INSTALLED_APPS=("django_components",),
        TEMPLATES=[
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "DIRS": [
                    "tests/templates/",
                    "tests/components/",  # Required for template relative imports in tests
                ],
            }
        ],
        COMPONENTS={"template_cache_size": 128},
        MIDDLEWARE=["django_components.middleware.ComponentDependencyMiddleware"],
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": ":memory:",
            }
        },
    )

    django.setup()
