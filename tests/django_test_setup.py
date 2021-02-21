import django
from django.conf import settings

if not settings.configured:
    # Django 1.8 changes how you set up templates, so use different
    # settings for different Django versions
    if django.VERSION >= (1, 8):
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
    else:
        settings.configure(
            INSTALLED_APPS=('django_components',),
            TEMPLATE_DIRS=["tests/templates/"],
        )

    django.setup()
