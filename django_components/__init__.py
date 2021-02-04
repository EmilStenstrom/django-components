from django.utils.module_loading import autodiscover_modules, import_string


def autodiscover():
    # look for "components" module/pkg in each app
    from . import app_settings

    print("running autodiscover", app_settings.AUTODISCOVER, app_settings.LIBRARIES)

    if app_settings.AUTODISCOVER:
        autodiscover_modules("components")
    for path in app_settings.LIBRARIES:
        import_string(path)
