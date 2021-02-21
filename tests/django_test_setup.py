import django
from django.conf import settings

if not settings.configured:
    settings.configure(
        INSTALLED_APPS=('django_components',),
        TEMPLATES=[{
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'DIRS': ["tests/templates/"],
        }],
        COMPONENTS={
            'TEMPLATE_CACHE_SIZE': 128
        },
            MIDDLEWARE = ['django_components.middleware.ComponentDependencyMiddleware'],
            DATABASES = {},
    )

    django.setup()
