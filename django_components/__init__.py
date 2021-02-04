from django.utils.module_loading import autodiscover_modules, import_string


def autodiscover():
    # look for "components" module/pkg in each app
    from . import app_settings

    if app_settings.AUTODISCOVER:
        autodiscover_modules("components")
    for path in app_settings.LIBRARIES:
        import_string(path)
