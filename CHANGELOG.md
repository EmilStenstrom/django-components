# Release notes

## v0.115

#### Fix

- Fix integration with ManifestStaticFilesStorage on Windows by resolving component filepaths 
 (like `Component.template_name`) to POSIX paths.

## v0.114

#### Fix

- Prevent rendering Slot tags during fill discovery stage to fix a case when a component inside a slot
  fill tried to access provided data too early.

## v0.113

#### Fix

- Ensure consistent order of scripts in `Component.Media.js`

## v0.112

#### Fix

- Allow components to accept default fill even if no default slot was encountered during rendering

## v0.111

#### Fix

- Prevent rendering Component tags during fill discovery stage to fix a case when a component inside the default slot
  tried to access provided data too early.

## 🚨📢 v0.110

### General

#### 🚨📢 BREAKING CHANGES

- Installation changes:

    - If your components include JS or CSS, you now must use the middleware and add django-components' URLs to your `urlpatterns`
    (See "[Adding support for JS and CSS](https://github.com/EmilStenstrom/django-components#adding-support-for-js-and-css)")

- Component typing signature changed from

    ```py
    Component[Args, Kwargs, Data, Slots]
    ```

    to

    ```py
    Component[Args, Kwargs, Slots, Data, JsData, CssData]
    ```

- If you rendered a component A with `Component.render()` and then inserted that into another component B, now you must pass `render_dependencies=False` to component A:

    ```py
    prerendered_a = CompA.render(
        args=[...],
        kwargs={...},
        render_dependencies=False,
    )

    html = CompB.render(
        kwargs={
            content=prerendered_a,
        },
    )
    ```

#### Feat

- Intellisense and mypy validation for settings:
  
  Instead of defining the `COMPONENTS` settings as a plain dict, you can use `ComponentsSettings`:

  ```py
  # settings.py
  from django_components import ComponentsSettings

  COMPONENTS = ComponentsSettings(
      autodiscover=True,
      ...
  )
  ```

- Use `get_component_dirs()` and `get_component_files()` to get the same list of dirs / files that would be imported by `autodiscover()`, but without actually
importing them.

#### Refactor

- For advanced use cases, use can omit the middleware and instead manage component JS and CSS dependencies yourself with [`render_dependencies`](https://github.com/EmilStenstrom/django-components#render_dependencies-and-deep-dive-into-rendering-js--css-without-the-middleware)

- The [`ComponentRegistry`](../api#django_components.ComponentRegistry) settings [`RegistrySettings`](../api#django_components.RegistrySettings)
  were lowercased to align with the global settings:
  - `RegistrySettings.CONTEXT_BEHAVIOR` -> `RegistrySettings.context_behavior`
  - `RegistrySettings.TAG_FORMATTER` -> `RegistrySettings.tag_formatter`

  The old uppercase settings `CONTEXT_BEHAVIOR` and `TAG_FORMATTER` are deprecated and will be removed in v1.

- The setting `reload_on_template_change` was renamed to
  [`reload_on_file_change`](../settings#django_components.app_settings.ComponentsSettings#reload_on_file_change).
  And now it properly triggers server reload when any file in the component dirs change. The old name `reload_on_template_change`
  is deprecated and will be removed in v1.

- The setting `forbidden_static_files` was renamed to
  [`static_files_forbidden`](../settings#django_components.app_settings.ComponentsSettings#static_files_forbidden)
  to align with [`static_files_allowed`](../settings#django_components.app_settings.ComponentsSettings#static_files_allowed)
  The old name `forbidden_static_files` is deprecated and will be removed in v1.

### Tags

#### 🚨📢 BREAKING CHANGES

- `{% component_dependencies %}` tag was removed. Instead, use `{% component_js_dependencies %}` and `{% component_css_dependencies %}`

    - The combined tag was removed to encourage the best practice of putting JS scripts at the end of `<body>`, and CSS styles inside `<head>`.

        On the other hand, co-locating JS script and CSS styles can lead to
        a [flash of unstyled content](https://en.wikipedia.org/wiki/Flash_of_unstyled_content),
        as either JS scripts will block the rendering, or CSS will load too late.

- The undocumented keyword arg `preload` of `{% component_js_dependencies %}` and `{% component_css_dependencies %}` tags was removed.
  This will be replaced with HTML fragment support.

#### Fix

- Allow using forward slash (`/`) when defining custom TagFormatter,
  e.g. `{% MyComp %}..{% /MyComp %}`.

#### Refactor

- `{% component_dependencies %}` tags are now OPTIONAL - If your components use JS and CSS, but you don't use `{% component_dependencies %}` tags, the JS and CSS will now be, by default, inserted at the end of `<body>` and at the end of `<head>` respectively.

### Slots

#### Feat

- Fills can now be defined within loops (`{% for %}`) or other tags (like `{% with %}`),
  or even other templates using `{% include %}`.
  
  Following is now possible

  ```django
  {% component "table" %}
    {% for slot_name in slots %}
      {% fill name=slot_name %}
      {% endfill %}
    {% endfor %}
  {% endcomponent %}
  ```

- If you need to access the data or the default content of a default fill, you can
  set the `name` kwarg to `"default"`.

  Previously, a default fill would be defined simply by omitting the `{% fill %}` tags:

  ```django
  {% component "child" %}
    Hello world
  {% endcomponent %}
  ```

  But in that case you could not access the slot data or the default content, like it's possible
  for named fills:
  
  ```django
  {% component "child" %}
    {% fill name="header" data="data" %}
      Hello {{ data.user.name }}
    {% endfill %}
  {% endcomponent %}
  ```

  Now, you can specify default tag by using `name="default"`:

  ```django
  {% component "child" %}
    {% fill name="default" data="data" %}
      Hello {{ data.user.name }}
    {% endfill %}
  {% endcomponent %}
  ```

- When inside `get_context_data()` or other component methods, the default fill
  can now be accessed as `Component.input.slots["default"]`, e.g.:

  ```py
  class MyTable(Component):
      def get_context_data(self, *args, **kwargs):
          default_slot = self.input.slots["default"]
          ...
  ```

- You can now dynamically pass all slots to a child component. This is similar to
  [passing all slots in Vue](https://vue-land.github.io/faq/forwarding-slots#passing-all-slots):

  ```py
  class MyTable(Component):
      def get_context_data(self, *args, **kwargs):
          return {
              "slots": self.input.slots,
          }

      template: """
        <div>
          {% component "child" %}
            {% for slot_name in slots %}
              {% fill name=slot_name data="data" %}
                {% slot name=slot_name ...data / %}
              {% endfill %}
            {% endfor %}
          {% endcomponent %}
        </div>
      """
  ```

#### Fix

- Slots defined with `{% fill %}` tags are now properly accessible via `self.input.slots` in `get_context_data()`

- Do not raise error if multiple slots with same name are flagged as default

- Slots can now be defined within loops (`{% for %}`) or other tags (like `{% with %}`),
  or even other templates using `{% include %}`.
  
  Previously, following would cause the kwarg `name` to be an empty string:

  ```django
  {% for slot_name in slots %}
    {% slot name=slot_name %}
  {% endfor %}
  ```

#### Refactor

- When you define multiple slots with the same name inside a template,
  you now have to set the `default` and `required` flags individually.
  
  ```htmldjango
  <div class="calendar-component">
      <div class="header">
          {% slot "image" default required %}Image here{% endslot %}
      </div>
      <div class="body">
          {% slot "image" default required %}Image here{% endslot %}
      </div>
  </div>
  ```
  
  This means you can also have multiple slots with the same name but
  different conditions.

  E.g. in this example, we have a component that renders a user avatar
  - a small circular image with a profile picture of name initials.

  If the component is given `image_src` or `name_initials` variables,
  the `image` slot is optional. But if neither of those are provided,
  you MUST fill the `image` slot.

  ```htmldjango
  <div class="avatar">
      {% if image_src %}
          {% slot "image" default %}
              <img src="{{ image_src }}" />
          {% endslot %}
      {% elif name_initials %}
          {% slot "image" default required %}
              <div style="
                  border-radius: 25px;
                  width: 50px;
                  height: 50px;
                  background: blue;
              ">
                  {{ name_initials }}
              </div>
          {% endslot %}
      {% else %}
          {% slot "image" default required / %}
      {% endif %}
  </div>
  ```

- The slot fills that were passed to a component and which can be accessed as `Component.input.slots`
  can now be passed through the Django template, e.g. as inputs to other tags.

  Internally, django-components handles slot fills as functions.

  Previously, if you tried to pass a slot fill within a template, Django would try to call it as a function.

  Now, something like this is possible:

  ```py
  class MyTable(Component):
      def get_context_data(self, *args, **kwargs):
          return {
              "child_slot": self.input.slots["child_slot"],
          }

      template: """
        <div>
          {% component "child" content=child_slot / %}
        </div>
      """
  ```

  NOTE: Using `{% slot %}` and `{% fill %}` tags is still the preferred method, but the approach above
  may be necessary in some complex or edge cases.

- The `is_filled` variable (and the `{{ component_vars.is_filled }}` context variable) now returns
  `False` when you try to access a slot name which has not been defined:

  Before:

  ```django
  {{ component_vars.is_filled.header }} -> True
  {{ component_vars.is_filled.footer }} -> False
  {{ component_vars.is_filled.nonexist }} -> "" (empty string)
  ```

  After:
  ```django
  {{ component_vars.is_filled.header }} -> True
  {{ component_vars.is_filled.footer }} -> False
  {{ component_vars.is_filled.nonexist }} -> False
  ```

- Components no longer raise an error if there are extra slot fills

- Components will raise error when a slot is doubly-filled. 

  E.g. if we have a component with a default slot:

  ```django
  {% slot name="content" default / %}
  ```

  Now there is two ways how we can target this slot: Either using `name="default"`
  or `name="content"`.

  In case you specify BOTH, the component will raise an error:

  ```django
  {% component "child" %}
    {% fill slot="default" %}
      Hello from default slot
    {% endfill %}
    {% fill slot="content" data="data" %}
      Hello from content slot
    {% endfill %}
  {% endcomponent %}
  ```

## 🚨📢 v0.100

#### BREAKING CHANGES

- `django_components.safer_staticfiles` app was removed. It is no longer needed.

- Installation changes:

    - Instead of defining component directories in `STATICFILES_DIRS`, set them to [`COMPONENTS.dirs`](https://github.com/EmilStenstrom/django-components#dirs).
    - You now must define `STATICFILES_FINDERS`

    - [See here how to migrate your settings.py](https://github.com/EmilStenstrom/django-components/blob/master/docs/migrating_from_safer_staticfiles.md)

#### Feat

- Beside the top-level `/components` directory, you can now define also app-level components dirs, e.g. `[app]/components`
  (See [`COMPONENTS.app_dirs`](https://github.com/EmilStenstrom/django-components#app_dirs)).

#### Refactor

- When you call `as_view()` on a component instance, that instance will be passed to `View.as_view()`

## v0.97

#### Fix

- Fixed template caching. You can now also manually create cached templates with [`cached_template()`](https://github.com/EmilStenstrom/django-components#template_cache_size---tune-the-template-cache)

#### Refactor

- The previously undocumented `get_template` was made private.

- In it's place, there's a new `get_template`, which supersedes `get_template_string` (will be removed in v1). The new `get_template` is the same as `get_template_string`, except
  it allows to return either a string or a Template instance.

- You now must use only one of `template`, `get_template`, `template_name`, or `get_template_name`.

## v0.96

#### Feat

- Run-time type validation for Python 3.11+ - If the `Component` class is typed, e.g. `Component[Args, Kwargs, ...]`, the args, kwargs, slots, and data are validated against the given types. (See [Runtime input validation with types](https://github.com/EmilStenstrom/django-components#runtime-input-validation-with-types))

- Render hooks - Set `on_render_before` and `on_render_after` methods on `Component` to intercept or modify the template or context before rendering, or the rendered result afterwards. (See [Component hooks](https://github.com/EmilStenstrom/django-components#component-hooks))

- `component_vars.is_filled` context variable can be accessed from within `on_render_before` and `on_render_after` hooks as `self.is_filled.my_slot`

## 0.95

#### Feat

- Added support for dynamic components, where the component name is passed as a variable. (See [Dynamic components](https://github.com/EmilStenstrom/django-components#dynamic-components))

#### Refactor

- Changed `Component.input` to raise `RuntimeError` if accessed outside of render context. Previously it returned `None` if unset.

## v0.94

#### Feat

- django_components now automatically configures Django to support multi-line tags. (See [Multi-line tags](https://github.com/EmilStenstrom/django-components#multi-line-tags))

- New setting `reload_on_template_change`. Set this to `True` to reload the dev server on changes to component template files. (See [Reload dev server on component file changes](https://github.com/EmilStenstrom/django-components#reload-dev-server-on-component-file-changes))

## v0.93

#### Feat

- Spread operator `...dict` inside template tags. (See [Spread operator](https://github.com/EmilStenstrom/django-components#spread-operator))

- Use template tags inside string literals in component inputs. (See [Use template tags inside component inputs](https://github.com/EmilStenstrom/django-components#use-template-tags-inside-component-inputs))

- Dynamic slots, fills and provides - The `name` argument for these can now be a variable, a template expression, or via spread operator

- Component library authors can now configure `CONTEXT_BEHAVIOR` and `TAG_FORMATTER` settings independently from user settings.

## 🚨📢 v0.92

#### BREAKING CHANGES

- `Component` class is no longer a subclass of `View`. To configure the `View` class, set the `Component.View` nested class. HTTP methods like `get` or `post` can still be defined directly on `Component` class, and `Component.as_view()` internally calls `Component.View.as_view()`. (See [Modifying the View class](https://github.com/EmilStenstrom/django-components#modifying-the-view-class))

#### Feat

- The inputs (args, kwargs, slots, context, ...) that you pass to `Component.render()` can be accessed from within `get_context_data`, `get_template` and `get_template_name` via `self.input`. (See [Accessing data passed to the component](https://github.com/EmilStenstrom/django-components#accessing-data-passed-to-the-component))

- Typing: `Component` class supports generics that specify types for `Component.render` (See [Adding type hints with Generics](https://github.com/EmilStenstrom/django-components#adding-type-hints-with-generics))

## v0.90

#### Feat

- All tags (`component`, `slot`, `fill`, ...) now support "self-closing" or "inline" form, where you can omit the closing tag:

    ```django
    {# Before #}
    {% component "button" %}{% endcomponent %}
    {# After #}
    {% component "button" / %}
    ```

- All tags now support the "dictionary key" or "aggregate" syntax (`kwarg:key=val`):

    ```django
    {% component "button" attrs:class="hidden" %}
    ```

- You can change how the components are written in the template with [TagFormatter](https://github.com/EmilStenstrom/django-components#customizing-component-tags-with-tagformatter).

    The default is `django_components.component_formatter`:

    ```django
    {% component "button" href="..." disabled %}
        Click me!
    {% endcomponent %}
    ```

    While `django_components.shorthand_component_formatter` allows you to write components like so:

    ```django
    {% button href="..." disabled %}
        Click me!
    {% endbutton %}
    ```

## 🚨📢 v0.85

#### BREAKING CHANGES

- Autodiscovery module resolution changed. Following undocumented behavior was removed:

    - Previously, autodiscovery also imported any `[app]/components.py` files, and used `SETTINGS_MODULE` to search for component dirs.

        To migrate from:

        - `[app]/components.py` - Define each module in `COMPONENTS.libraries` setting,
            or import each module inside the `AppConfig.ready()` hook in respective `apps.py` files.

        - `SETTINGS_MODULE` - Define component dirs using `STATICFILES_DIRS`

    - Previously, autodiscovery handled relative files in `STATICFILES_DIRS`. To align with Django, `STATICFILES_DIRS` now must be full paths ([Django docs](https://docs.djangoproject.com/en/5.0/ref/settings/#std-setting-STATICFILES_DIRS)).

## 🚨📢 v0.81

#### BREAKING CHANGES

- The order of arguments to `render_to_response` has changed, to align with the (now public) `render` method of `Component` class.

#### Feat

- `Component.render()` is public and documented

- Slots passed `render_to_response` and `render` can now be rendered also as functions.

## v0.80

#### Feat

- Vue-like provide/inject with the `{% provide %}` tag and `inject()` method.

## 🚨📢 v0.79

#### BREAKING CHANGES

- Default value for the `COMPONENTS.context_behavior` setting was changes from `"isolated"` to `"django"`. If you did not set this value explicitly before, this may be a breaking change. See the rationale for change [here](https://github.com/EmilStenstrom/django-components/issues/498).

## 🚨📢 v0.77

#### BREAKING

- The syntax for accessing default slot content has changed from

    ```django
    {% fill "my_slot" as "alias" %}
        {{ alias.default }}
    {% endfill %}

    ```

    to

    ```django
    {% fill "my_slot" default="alias" %}
        {{ alias }}
    {% endfill %}
    ```

## v0.74

#### Feat

- `{% html_attrs %}` tag for formatting data as HTML attributes

- `prefix:key=val` construct for passing dicts to components

## 🚨📢 v0.70

#### BREAKING CHANGES

- `{% if_filled "my_slot" %}` tags were replaced with `{{ component_vars.is_filled.my_slot }}` variables.

- Simplified settings - `slot_context_behavior` and `context_behavior` were merged. See the [documentation](https://github.com/EmilStenstrom/django-components#context-behavior) for more details.

## v0.67

#### Refactor

- Changed the default way how context variables are resolved in slots. See the [documentation](https://github.com/EmilStenstrom/django-components/tree/0.67#isolate-components-slots) for more details.

## 🚨📢 v0.50

#### BREAKING CHANGES

- `{% component_block %}` is now `{% component %}`, and `{% component %}` blocks need an ending `{% endcomponent %}` tag.

    The new `python manage.py upgradecomponent` command can be used to upgrade a directory (use `--path` argument to point to each dir) of templates that use components to the new syntax automatically.

    This change is done to simplify the API in anticipation of a 1.0 release of django_components. After 1.0 we intend to be stricter with big changes like this in point releases.

## v0.34

#### Feat

- Components as views, which allows you to handle requests and render responses from within a component. See the [documentation](https://github.com/EmilStenstrom/django-components#use-components-as-views) for more details.

## v0.28

#### Feat

- 'implicit' slot filling and the `default` option for `slot` tags.

## v0.27

#### Feat

- A second installable app `django_components.safer_staticfiles`. It provides the same behavior as `django.contrib.staticfiles` but with extra security guarantees (more info below in [Security Notes](https://github.com/EmilStenstrom/django-components#security-notes)).

## 🚨📢 v0.26

#### BREAKING CHANGES

- Changed the syntax for `{% slot %}` tags. From now on, we separate defining a slot (`{% slot %}`) from filling a slot with content (`{% fill %}`). This means you will likely need to change a lot of slot tags to fill.

    We understand this is annoying, but it's the only way we can get support for nested slots that fill in other slots, which is a very nice feature to have access to. Hoping that this will feel worth it!

## v0.22

#### Feat

- All files inside components subdirectores are autoimported to simplify setup.

    An existing project might start to get `AlreadyRegistered` errors because of this. To solve this, either remove your custom loading of components, or set `"autodiscover": False` in `settings.COMPONENTS`.

## v0.17

#### BREAKING CHANGES

- Renamed `Component.context` and `Component.template` to `get_context_data` and `get_template_name`. The old methods still work, but emit a deprecation warning.

    This change was done to sync naming with Django's class based views, and make using django-components more familiar to Django users. `Component.context` and `Component.template` will be removed when version 1.0 is released.
