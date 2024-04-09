# Release notes

🚨📢 **Version 0.5** CHANGES THE SYNTAX for components.

 `component_block` is now `component`, and `component` blocks need an ending `endcomponent` tag. The new `python manage.py upgradecomponent` command can be used to upgrade a directory (use --path argument to point to each dir) of components to the new syntax automatically.

This change is done to simplify the API in anticipation of a 1.0 release of django_components. After 1.0 we intend to be stricter with big changes like this in point releases.

**Version 0.34** adds components as views, which allows you to handle requests and render responses from within a component. See the [documentation](user_guide/creating_using_components/using_slots.md#components-as-views) for more details.

**Version 0.28** introduces 'implicit' slot filling and the `default` option for `slot` tags.

**Version 0.27** adds a second installable app: *django_components.safer_staticfiles*. It provides the same behavior as *django.contrib.staticfiles* but with extra security guarantees (more info below in Security Notes).

**Version 0.26** changes the syntax for `{% slot %}` tags. From now on, we separate defining a slot (`{% slot %}`) from filling a slot with content (`{% fill %}`). This means you will likely need to change a lot of slot tags to fill. We understand this is annoying, but it's the only way we can get support for nested slots that fill in other slots, which is a very nice featuPpre to have access to. Hoping that this will feel worth it!

**Version 0.22** starts autoimporting all files inside components subdirectores, to simplify setup. An existing project might start to get AlreadyRegistered-errors because of this. To solve this, either remove your custom loading of components, or set "autodiscover": False in settings.COMPONENTS.

**Version 0.17** renames `Component.context` and `Component.template` to `get_context_data` and `get_template_name`. The old methods still work, but emit a deprecation warning. This change was done to sync naming with Django's class based views, and make using django-components more familiar to Django users. `Component.context` and `Component.template` will be removed when version 1.0 is released.
