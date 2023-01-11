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

    @property
    def TEMPLATE_CACHE_SIZE(self):
        return self.settings.setdefault("template_cache_size", 128)

    @property
    def STRICT_SLOTS(self):
        """If True, component slots that are declared must be explicitly filled; else
        a TemplateSyntaxError is raised."""
        return self.settings.setdefault("strict_slots", False)


app_settings = AppSettings()
