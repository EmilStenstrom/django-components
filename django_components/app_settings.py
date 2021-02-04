import sys

from django.conf import settings


class AppSettings:
    def __init__(self):
        self.settings = getattr(settings, "COMPONENTS", {})

    @property
    def AUTODISCOVER(self):
        return self.settings.setdefault("autodiscover", True)

    @property
    def LIBRARIES(self):
        return self.settings.setdefault("libraries", [])


app_settings = AppSettings()
app_settings.__name__ = __name__
sys.modules[__name__] = app_settings
