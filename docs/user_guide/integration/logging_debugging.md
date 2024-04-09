# Logging and debugging

Django components supports [logging with Django](https://docs.djangoproject.com/en/5.0/howto/logging/#logging-how-to). This can help with troubleshooting.

To configure logging for Django components, set the `django_components` logger in `LOGGING` in `settings.py` (below).

Also see the [`settings.py` file in sampleproject](https://github.com/EmilStenstrom/django-components/tree/master/sampleproject/sampleproject/settings.py) for a real-life example.

```py
import logging
import sys

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    "handlers": {
        "console": {
            'class': 'logging.StreamHandler',
            'stream': sys.stdout,
        },
    },
    "loggers": {
        "django_components": {
            "level": logging.DEBUG,
            "handlers": ["console"],
        },
    },
}
```
