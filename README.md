# <img src="https://raw.githubusercontent.com/EmilStenstrom/django-components/master/logo/logo-black-on-white.svg" alt="django-components" style="max-width: 100%; background: white; color: black;">

[![PyPI - Version](https://img.shields.io/pypi/v/django-components)](https://pypi.org/project/django-components/) [![PyPI - Python Version](https://img.shields.io/pypi/pyversions/django-components)](https://pypi.org/project/django-components/) [![PyPI - License](https://img.shields.io/pypi/l/django-components)](https://EmilStenstrom.github.io/django-components/latest/license/) [![PyPI - Downloads](https://img.shields.io/pypi/dm/django-components)](https://pypistats.org/packages/django-components) [![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/EmilStenstrom/django-components/tests.yml)](https://github.com/EmilStenstrom/django-components/actions/workflows/tests.yml)

[**Docs (Work in progress)**](https://EmilStenstrom.github.io/django-components/latest/)

Django-components is a package that introduces component-based architecture to Django's server-side rendering. It aims to combine Django's templating system with the modularity seen in modern frontend frameworks.

## Features

1. 🧩 **Reusability:** Allows creation of self-contained, reusable UI elements.
2. 📦 **Encapsulation:** Each component can include its own HTML, CSS, and JavaScript.
3. 🚀 **Server-side rendering:** Components render on the server, improving initial load times and SEO.
4. 🐍 **Django integration:** Works within the Django ecosystem, using familiar concepts like template tags.
5. ⚡ **Asynchronous loading:** Components can render independently opening up for integration with JS frameworks like HTMX or AlpineJS.

Potential benefits:

- 🔄 Reduced code duplication
- 🛠️ Improved maintainability through modular design
- 🧠 Easier management of complex UIs
- 🤝 Enhanced collaboration between frontend and backend developers

Django-components can be particularly useful for larger Django projects that require a more structured approach to UI development, without necessitating a shift to a separate frontend framework.

## Quickstart

django-components lets you create reusable blocks of code needed to generate the front end code you need for a modern app. 

Define a component in `components/calendar/calendar.py` like this:
```python
@register("calendar")
class Calendar(Component):
    template_name = "template.html"

    def get_context_data(self, date):
        return {"date": date}
```

With this `template.html` file:

```htmldjango
<div class="calendar-component">Today's date is <span>{{ date }}</span></div>
```

Use the component like this:

```htmldjango
{% component "calendar" date="2024-11-06" %}{% endcomponent %}
```

And this is what gets rendered:

```html
<div class="calendar-component">Today's date is <span>2024-11-06</span></div>
```

Read on to learn about all the exciting details and configuration possibilities!

(If you instead prefer to jump right into the code, [check out the example project](https://github.com/EmilStenstrom/django-components/tree/master/sampleproject))

## Table of Contents

- [Release notes](#release-notes)
- [Security notes 🚨](#security-notes-)
- [Installation](#installation)
- [Compatibility](#compatibility)
- [Create your first component](#create-your-first-component)
- [Using single-file components](#using-single-file-components)
- [Use components in templates](#use-components-in-templates)
- [Use components outside of templates](#use-components-outside-of-templates)
- [Use components as views](#use-components-as-views)
- [Typing and validating components](#typing-and-validating-components)
- [Pre-defined components](#pre-defined-components)
- [Registering components](#registering-components)
- [Autodiscovery](#autodiscovery)
- [Using slots in templates](#using-slots-in-templates)
- [Accessing data passed to the component](#accessing-data-passed-to-the-component)
- [Rendering HTML attributes](#rendering-html-attributes)
- [Template tag syntax](#template-tag-syntax)
- [Prop drilling and dependency injection (provide / inject)](#prop-drilling-and-dependency-injection-provide--inject)
- [Component hooks](#component-hooks)
- [Component context and scope](#component-context-and-scope)
- [Pre-defined template variables](#pre-defined-template-variables)
- [Customizing component tags with TagFormatter](#customizing-component-tags-with-tagformatter)
- [Defining HTML/JS/CSS files](#defining-htmljscss-files)
- [Rendering JS/CSS dependencies](#rendering-jscss-dependencies)
- [Available settings](#available-settings)
- [Running with development server](#running-with-development-server)
- [Logging and debugging](#logging-and-debugging)
- [Management Command](#management-command)
- [Writing and sharing component libraries](#writing-and-sharing-component-libraries)
- [Community examples](#community-examples)
- [Running django-components project locally](#running-django-components-project-locally)
- [Development guides](#development-guides)

## Release notes

Read the [Release Notes](https://github.com/EmilStenstrom/django-components/tree/master/CHANGELOG.md)
to see the latest features and fixes.

## Security notes 🚨

_It is strongly recommended to read this section before using django-components in production._

### Static files

Components can be organized however you prefer.
That said, our prefered way is to keep the files of a component close together by bundling them in the same directory.

This means that files containing backend logic, such as Python modules and HTML templates, live in the same directory as static files, e.g. JS and CSS.

From v0.100 onwards, we keep component files (as defined by [`COMPONENTS.dirs`](#dirs) and [`COMPONENTS.app_dirs`](#app_dirs)) separate from the rest of the static
files (defined by `STATICFILES_DIRS`). That way, the Python and HTML files are NOT exposed by the server. Only the static JS, CSS, and [other common formats](#static_files_allowed).

> NOTE: If you need to expose different file formats, you can configure these with [`COMPONENTS.static_files_allowed`](#static_files_allowed)
and [`COMPONENTS.static_files_forbidden`](#static_files_forbidden).

<!-- # TODO_REMOVE_IN_V1 - Remove mentions of safer_staticfiles in V1 -->
#### Static files prior to v0.100

Prior to v0.100, if your were using _django.contrib.staticfiles_ to collect static files, no distinction was made between the different kinds of files.

As a result, your Python code and templates may inadvertently become available on your static file server.
You probably don't want this, as parts of your backend logic will be exposed, posing a **potential security vulnerability**.

From _v0.27_ until _v0.100_, django-components shipped with an additional installable app _django_components.**safer_staticfiles**_.
It was a drop-in replacement for _django.contrib.staticfiles_.
Its behavior is 100% identical except it ignores .py and .html files, meaning these will not end up on your static files server.
To use it, add it to INSTALLED_APPS and remove _django.contrib.staticfiles_.

```python
INSTALLED_APPS = [
    # 'django.contrib.staticfiles',   # <-- REMOVE
    'django_components',
    'django_components.safer_staticfiles'  # <-- ADD
]
```

If you are on an older version of django-components, your alternatives are a) passing `--ignore <pattern>` options to the _collecstatic_ CLI command, or b) defining a subclass of StaticFilesConfig.
Both routes are described in the official [docs of the _staticfiles_ app](https://docs.djangoproject.com/en/4.2/ref/contrib/staticfiles/#customizing-the-ignored-pattern-list).

Note that `safer_staticfiles` excludes the `.py` and `.html` files for [collectstatic command](https://docs.djangoproject.com/en/5.0/ref/contrib/staticfiles/#collectstatic):

```sh
python manage.py collectstatic
```

but it is ignored on the [development server](https://docs.djangoproject.com/en/5.0/ref/django-admin/#runserver):

```sh
python manage.py runserver
```

For a step-by-step guide on deploying production server with static files,
[see the demo project](https://github.com/EmilStenstrom/django-components/tree/master/sampleproject).

## Installation

1. Install `django_components` into your environment:

   > `pip install django_components`

2. Load `django_components` into Django by adding it into `INSTALLED_APPS` in settings.py:

   ```python
   INSTALLED_APPS = [
      ...,
      'django_components',
   ]
   ```

3. `BASE_DIR` setting is required. Ensure that it is defined in settings.py:

   ```py
   BASE_DIR = Path(__file__).resolve().parent.parent
   ```

4. Add / modify [`COMPONENTS.dirs`](#dirs) and / or [`COMPONENTS.app_dirs`](#app_dirs) so django_components knows where to find component HTML, JS and CSS files:

   ```python
   COMPONENTS = {
       "dirs": [
            ...,
            os.path.join(BASE_DIR, "components"),
        ],
   }
   ```

   If `COMPONENTS.dirs` is omitted, django-components will by default look for a top-level `/components` directory,
   `{BASE_DIR}/components`.

   In addition to `COMPONENTS.dirs`, django_components will also load components from app-level directories, such as `my-app/components/`.
   The directories within apps are configured with [`COMPONENTS.app_dirs`](#app_dirs), and the default is `[app]/components`.

   NOTE: The input to `COMPONENTS.dirs` is the same as for `STATICFILES_DIRS`, and the paths must be full paths. [See Django docs](https://docs.djangoproject.com/en/5.0/ref/settings/#staticfiles-dirs).


5. Next, to make Django load component HTML files as Django templates, modify `TEMPLATES` section of settings.py as follows:

   - _Remove `'APP_DIRS': True,`_
      - NOTE: Instead of APP_DIRS, for the same effect, we will use [`django.template.loaders.app_directories.Loader`](https://docs.djangoproject.com/en/5.1/ref/templates/api/#django.template.loaders.app_directories.Loader)
   - Add `loaders` to `OPTIONS` list and set it to following value:

   ```python
   TEMPLATES = [
      {
         ...,
         'OPTIONS': {
               'context_processors': [
                  ...
               ],
               'loaders':[(
                  'django.template.loaders.cached.Loader', [
                     # Default Django loader
                     'django.template.loaders.filesystem.Loader',
                     # Inluding this is the same as APP_DIRS=True
                     'django.template.loaders.app_directories.Loader',
                     # Components loader
                     'django_components.template_loader.Loader',
                  ]
               )],
         },
      },
   ]
   ```

6. Lastly, be able to serve the component JS and CSS files as static files, modify `STATICFILES_FINDERS` section of settings.py as follows:

```py
STATICFILES_FINDERS = [
    # Default finders
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    # Django components
    "django_components.finders.ComponentsFileSystemFinder",
]
```

### Adding support for JS and CSS

If you want to use JS or CSS with components, you will need to:

1. Add [`ComponentDependencyMiddleware`](#setting-up-componentdependencymiddleware) to `MIDDLEWARE` setting.

The middleware searches the outgoing HTML for all components that were rendered
to generate the HTML, and adds the JS and CSS associated with those components.

```py
MIDDLEWARE = [
    ...
    "django_components.middleware.ComponentDependencyMiddleware",
]
```

Read more in [Rendering JS/CSS dependencies](#rendering-jscss-dependencies).

2. Add django-component's URL paths to your `urlpatterns`:

```py
from django.urls import include, path

urlpatterns = [
    ...
    path("", include("django_components.urls")),
]
```

### Optional

To avoid loading the app in each template using `{% load component_tags %}`, you can add the tag as a 'builtin' in settings.py

```python
TEMPLATES = [
    {
        ...,
        'OPTIONS': {
            'context_processors': [
                ...
            ],
            'builtins': [
                'django_components.templatetags.component_tags',
            ]
        },
    },
]
```

Read on to find out how to build your first component!

## Compatibility

Django-components supports all supported combinations versions of [Django](https://docs.djangoproject.com/en/dev/faq/install/#what-python-version-can-i-use-with-django) and [Python](https://devguide.python.org/versions/#versions).

| Python version | Django version |
| -------------- | -------------- |
| 3.8            | 4.2            |
| 3.9            | 4.2            |
| 3.10           | 4.2, 5.0       |
| 3.11           | 4.2, 5.0       |
| 3.12           | 4.2, 5.0       |

## Create your first component

A component in django-components is the combination of four things: CSS, Javascript, a Django template, and some Python code to put them all together.

```
    sampleproject/
    ├── calendarapp/
    ├── components/             🆕
    │   └── calendar/           🆕
    │       ├── calendar.py     🆕
    │       ├── script.js       🆕
    │       ├── style.css       🆕
    │       └── template.html   🆕
    ├── sampleproject/
    ├── manage.py
    └── requirements.txt
```

Start by creating empty files in the structure above.

First, you need a CSS file. Be sure to prefix all rules with a unique class so they don't clash with other rules.

```css title="[project root]/components/calendar/style.css"
/* In a file called [project root]/components/calendar/style.css */
.calendar-component {
  width: 200px;
  background: pink;
}
.calendar-component span {
  font-weight: bold;
}
```

Then you need a javascript file that specifies how you interact with this component. You are free to use any javascript framework you want. A good way to make sure this component doesn't clash with other components is to define all code inside an anonymous function that calls itself. This makes all variables defined only be defined inside this component and not affect other components.

```js title="[project root]/components/calendar/script.js"
/* In a file called [project root]/components/calendar/script.js */
(function () {
  if (document.querySelector(".calendar-component")) {
    document.querySelector(".calendar-component").onclick = function () {
      alert("Clicked calendar!");
    };
  }
})();
```

Now you need a Django template for your component. Feel free to define more variables like `date` in this example. When creating an instance of this component we will send in the values for these variables. The template will be rendered with whatever template backend you've specified in your Django settings file.

```htmldjango title="[project root]/components/calendar/calendar.html"
{# In a file called [project root]/components/calendar/template.html #}
<div class="calendar-component">Today's date is <span>{{ date }}</span></div>
```

Finally, we use django-components to tie this together. Start by creating a file called `calendar.py` in your component calendar directory. It will be auto-detected and loaded by the app.

Inside this file we create a Component by inheriting from the Component class and specifying the context method. We also register the global component registry so that we easily can render it anywhere in our templates.

```python  title="[project root]/components/calendar/calendar.py"
# In a file called [project root]/components/calendar/calendar.py
from django_components import Component, register

@register("calendar")
class Calendar(Component):
    # Templates inside `[your apps]/components` dir and `[project root]/components` dir
    # will be automatically found.
    #
    # `template_name` can be relative to dir where `calendar.py` is, or relative to COMPONENTS.dirs
    template_name = "template.html"
    # Or
    def get_template_name(context):
        return f"template-{context['name']}.html"

    # This component takes one parameter, a date string to show in the template
    def get_context_data(self, date):
        return {
            "date": date,
        }

    # Both `css` and `js` can be relative to dir where `calendar.py` is, or relative to COMPONENTS.dirs
    class Media:
        css = "style.css"
        js = "script.js"
```

And voilá!! We've created our first component.

## Using single-file components

Components can also be defined in a single file, which is useful for small components. To do this, you can use the `template`, `js`, and `css` class attributes instead of the `template_name` and `Media`. For example, here's the calendar component from above, defined in a single file:

```python title="[project root]/components/calendar.py"
# In a file called [project root]/components/calendar.py
from django_components import Component, register, types

@register("calendar")
class Calendar(Component):
    def get_context_data(self, date):
        return {
            "date": date,
        }

    template: types.django_html = """
        <div class="calendar-component">Today's date is <span>{{ date }}</span></div>
    """

    css: types.css = """
        .calendar-component { width: 200px; background: pink; }
        .calendar-component span { font-weight: bold; }
    """

    js: types.js = """
        (function(){
            if (document.querySelector(".calendar-component")) {
                document.querySelector(".calendar-component").onclick = function(){ alert("Clicked calendar!"); };
            }
        })()
    """
```

This makes it easy to create small components without having to create a separate template, CSS, and JS file.

### Syntax highlight and code assistance

#### VSCode

Note, in the above example, that the `t.django_html`, `t.css`, and `t.js` types are used to specify the type of the template, CSS, and JS files, respectively. This is not necessary, but if you're using VSCode with the [Python Inline Source Syntax Highlighting](https://marketplace.visualstudio.com/items?itemName=samwillis.python-inline-source) extension, it will give you syntax highlighting for the template, CSS, and JS.

#### Pycharm (or other Jetbrains IDEs)

If you're a Pycharm user (or any other editor from Jetbrains), you can have coding assistance as well:

```python
from django_components import Component, register

@register("calendar")
class Calendar(Component):
    def get_context_data(self, date):
        return {
            "date": date,
        }

    # language=HTML
    template= """
        <div class="calendar-component">Today's date is <span>{{ date }}</span></div>
    """

    # language=CSS
    css = """
        .calendar-component { width: 200px; background: pink; }
        .calendar-component span { font-weight: bold; }
    """

    # language=JS
    js = """
        (function(){
            if (document.querySelector(".calendar-component")) {
                document.querySelector(".calendar-component").onclick = function(){ alert("Clicked calendar!"); };
            }
        })()
    """
```

You don't need to use `types.django_html`, `types.css`, `types.js` since Pycharm uses [language injections](https://www.jetbrains.com/help/pycharm/using-language-injections.html).
You only need to write the comments `# language=<lang>` above the variables.

## Use components in templates

First load the `component_tags` tag library, then use the `component_[js/css]_dependencies` and `component` tags to render the component to the page.

```htmldjango
{% load component_tags %}
<!DOCTYPE html>
<html>
<head>
    <title>My example calendar</title>
    {% component_css_dependencies %}
</head>
<body>
    {% component "calendar" date="2015-06-19" %}{% endcomponent %}
    {% component_js_dependencies %}
</body>
<html>
```

> NOTE: Instead of writing `{% endcomponent %}` at the end, you can use a self-closing tag:
>
> `{% component "calendar" date="2015-06-19" / %}`

The output from the above template will be:

```html
<!DOCTYPE html>
<html>
  <head>
    <title>My example calendar</title>
    <link
      href="/static/calendar/style.css"
      type="text/css"
      media="all"
      rel="stylesheet"
    />
  </head>
  <body>
    <div class="calendar-component">
      Today's date is <span>2015-06-19</span>
    </div>
    <script src="/static/calendar/script.js"></script>
  </body>
  <html></html>
</html>
```

This makes it possible to organize your front-end around reusable components. Instead of relying on template tags and keeping your CSS and Javascript in the static directory.

## Use components outside of templates

_New in version 0.81_

Components can be rendered outside of Django templates, calling them as regular functions ("React-style").

The component class defines `render` and `render_to_response` class methods. These methods accept positional args, kwargs, and slots, offering the same flexibility as the `{% component %}` tag:

```py
class SimpleComponent(Component):
    template = """
        {% load component_tags %}
        hello: {{ hello }}
        foo: {{ foo }}
        kwargs: {{ kwargs|safe }}
        slot_first: {% slot "first" required / %}
    """

    def get_context_data(self, arg1, arg2, **kwargs):
        return {
            "hello": arg1,
            "foo": arg2,
            "kwargs": kwargs,
        }

rendered = SimpleComponent.render(
    args=["world", "bar"],
    kwargs={"kw1": "test", "kw2": "ooo"},
    slots={"first": "FIRST_SLOT"},
    context={"from_context": 98},
)
```

Renders:

```
hello: world
foo: bar
kwargs: {'kw1': 'test', 'kw2': 'ooo'}
slot_first: FIRST_SLOT
```

### Inputs of `render` and `render_to_response`

Both `render` and `render_to_response` accept the same input:

```py
Component.render(
    context: Mapping | django.template.Context | None = None,
    args: List[Any] | None = None,
    kwargs: Dict[str, Any] | None = None,
    slots: Dict[str, str | SafeString | SlotFunc] | None = None,
    escape_slots_content: bool = True
) -> str:
```

- _`args`_ - Positional args for the component. This is the same as calling the component
  as `{% component "my_comp" arg1 arg2 ... %}`

- _`kwargs`_ - Keyword args for the component. This is the same as calling the component
  as `{% component "my_comp" key1=val1 key2=val2 ... %}`

- _`slots`_ - Component slot fills. This is the same as pasing `{% fill %}` tags to the component.
  Accepts a dictionary of `{ slot_name: slot_content }` where `slot_content` can be a string
  or [`SlotFunc`](#slotfunc).

- _`escape_slots_content`_ - Whether the content from `slots` should be escaped. `True` by default to prevent XSS attacks. If you disable escaping, you should make sure that any content you pass to the slots is safe, especially if it comes from user input.

- _`context`_ - A context (dictionary or Django's Context) within which the component
  is rendered. The keys on the context can be accessed from within the template.
  - NOTE: In "isolated" mode, context is NOT accessible, and data MUST be passed via
    component's args and kwargs.

#### `SlotFunc`

When rendering components with slots in `render` or `render_to_response`, you can pass either a string or a function.

The function has following signature:

```py
def render_func(
   context: Context,
   data: Dict[str, Any],
   slot_ref: SlotRef,
) -> str | SafeString:
    return nodelist.render(ctx)
```

- _`context`_ - Django's Context available to the Slot Node.
- _`data`_ - Data passed to the `{% slot %}` tag. See [Scoped Slots](#scoped-slots).
- _`slot_ref`_ - The default slot content. See [Accessing original content of slots](#accessing-original-content-of-slots).
  - NOTE: The slot is lazily evaluated. To render the slot, convert it to string with `str(slot_ref)`.

Example:

```py
def footer_slot(ctx, data, slot_ref):
   return f"""
      SLOT_DATA: {data['abc']}
      ORIGINAL: {slot_ref}
   """

MyComponent.render_to_response(
    slots={
        "footer": footer_slot,
   },
)
```

### Response class of `render_to_response`

While `render` method returns a plain string, `render_to_response` wraps the rendered content in a "Response" class. By default, this is `django.http.HttpResponse`.

If you want to use a different Response class in `render_to_response`, set the `Component.response_class` attribute:

```py
class MyResponse(HttpResponse):
   def __init__(self, *args, **kwargs) -> None:
      super().__init__(*args, **kwargs)
      # Configure response
      self.headers = ...
      self.status = ...

class SimpleComponent(Component):
   response_class = MyResponse
   template: types.django_html = "HELLO"

response = SimpleComponent.render_to_response()
assert isinstance(response, MyResponse)
```

## Use components as views

_New in version 0.34_

_Note: Since 0.92, Component no longer subclasses View. To configure the View class, set the nested `Component.View` class_

Components can now be used as views:
- Components define the `Component.as_view()` class method that can be used the same as [`View.as_view()`](https://docs.djangoproject.com/en/5.1/ref/class-based-views/base/#django.views.generic.base.View.as_view).

- By default, you can define GET, POST or other HTTP handlers directly on the Component, same as you do with [View](https://docs.djangoproject.com/en/5.1/ref/class-based-views/base/#view). For example, you can override `get` and `post` to handle GET and POST requests, respectively.

- In addition, `Component` now has a [`render_to_response`](#inputs-of-render-and-render_to_response) method that renders the component template based on the provided context and slots' data and returns an `HttpResponse` object.

### Component as view example

Here's an example of a calendar component defined as a view:

```python
# In a file called [project root]/components/calendar.py
from django_components import Component, ComponentView, register

@register("calendar")
class Calendar(Component):

    template = """
        <div class="calendar-component">
            <div class="header">
                {% slot "header" / %}
            </div>
            <div class="body">
                Today's date is <span>{{ date }}</span>
            </div>
        </div>
    """

    # Handle GET requests
    def get(self, request, *args, **kwargs):
        context = {
            "date": request.GET.get("date", "2020-06-06"),
        }
        slots = {
            "header": "Calendar header",
        }
        # Return HttpResponse with the rendered content
        return self.render_to_response(
            context=context,
            slots=slots,
        )
```

Then, to use this component as a view, you should create a `urls.py` file in your components directory, and add a path to the component's view:

```python
# In a file called [project root]/components/urls.py
from django.urls import path
from components.calendar.calendar import Calendar

urlpatterns = [
    path("calendar/", Calendar.as_view()),
]
```

`Component.as_view()` is a shorthand for calling [`View.as_view()`](https://docs.djangoproject.com/en/5.1/ref/class-based-views/base/#django.views.generic.base.View.as_view) and passing the component
instance as one of the arguments.

Remember to add `__init__.py` to your components directory, so that Django can find the `urls.py` file.

Finally, include the component's urls in your project's `urls.py` file:

```python
# In a file called [project root]/urls.py
from django.urls import include, path

urlpatterns = [
    path("components/", include("components.urls")),
]
```

Note: Slots content are automatically escaped by default to prevent XSS attacks. To disable escaping, set `escape_slots_content=False` in the `render_to_response` method. If you do so, you should make sure that any content you pass to the slots is safe, especially if it comes from user input.

If you're planning on passing an HTML string, check Django's use of [`format_html`](https://docs.djangoproject.com/en/5.0/ref/utils/#django.utils.html.format_html) and [`mark_safe`](https://docs.djangoproject.com/en/5.0/ref/utils/#django.utils.safestring.mark_safe).

### Modifying the View class

The View class that handles the requests is defined on `Component.View`.

When you define a GET or POST handlers on the `Component` class, like so:

```py
class MyComponent(Component):
    def get(self, request, *args, **kwargs):
        return self.render_to_response(
            context={
                "date": request.GET.get("date", "2020-06-06"),
            },
        )

    def post(self, request, *args, **kwargs) -> HttpResponse:
        variable = request.POST.get("variable")
        return self.render_to_response(
            kwargs={"variable": variable}
        )
```

Then the request is still handled by `Component.View.get()` or `Component.View.post()`
methods. However, by default, `Component.View.get()` points to `Component.get()`, and so on.

```py
class ComponentView(View):
    component: Component = None
    ...

    def get(self, request, *args, **kwargs):
        return self.component.get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.component.post(request, *args, **kwargs)

    ...
```

If you want to define your own `View` class, you need to:
1. Set the class as `Component.View`
2. Subclass from `ComponentView`, so the View instance has access to the component instance.

In the example below, we added extra logic into `View.setup()`.

Note that the POST handler is still defined at the top. This is because `View` subclasses `ComponentView`, which defines the `post()` method that calls `Component.post()`.

If you were to overwrite the `View.post()` method, then `Component.post()` would be ignored.

```py
from django_components import Component, ComponentView

class MyComponent(Component):

    def post(self, request, *args, **kwargs) -> HttpResponse:
        variable = request.POST.get("variable")
        return self.component.render_to_response(
            kwargs={"variable": variable}
        )

    class View(ComponentView):
        def setup(self, request, *args, **kwargs):
            super(request, *args, **kwargs)

            do_something_extra(request, *args, **kwargs)
```

## Typing and validating components

### Adding type hints with Generics

_New in version 0.92_

The `Component` class optionally accepts type parameters
that allow you to specify the types of args, kwargs, slots, and
data:

```py
class Button(Component[Args, Kwargs, Slots, Data, JsData, CssData]):
    ...
```

- `Args` - Must be a `Tuple` or `Any`
- `Kwargs` - Must be a `TypedDict` or `Any`
- `Data` - Must be a `TypedDict` or `Any`
- `Slots` - Must be a `TypedDict` or `Any`

Here's a full example:

```py
from typing import NotRequired, Tuple, TypedDict, SlotContent, SlotFunc

# Positional inputs
Args = Tuple[int, str]

# Kwargs inputs
class Kwargs(TypedDict):
    variable: str
    another: int
    maybe_var: NotRequired[int] # May be ommited

# Data returned from `get_context_data`
class Data(TypedDict):
    variable: str

# The data available to the `my_slot` scoped slot
class MySlotData(TypedDict):
    value: int

# Slots
class Slots(TypedDict):
    # Use SlotFunc for slot functions.
    # The generic specifies the `data` dictionary
    my_slot: NotRequired[SlotFunc[MySlotData]]
    # SlotContent == Union[str, SafeString]
    another_slot: SlotContent

class Button(Component[Args, Kwargs, Slots, Data, JsData, CssData]):
    def get_context_data(self, variable, another):
        return {
            "variable": variable,
        }
```

When you then call `Component.render` or `Component.render_to_response`, you will get type hints:

```py
Button.render(
    # Error: First arg must be `int`, got `float`
    args=(1.25, "abc"),
    # Error: Key "another" is missing
    kwargs={
        "variable": "text",
    },
)
```

#### Usage for Python <3.11

On Python 3.8-3.10, use `typing_extensions`

```py
from typing_extensions import TypedDict, NotRequired
```

Additionally on Python 3.8-3.9, also import `annotations`:

```py
from __future__ import annotations
```

Moreover, on 3.10 and less, you may not be able to use `NotRequired`, and instead you will need to mark either all keys are required, or all keys as optional, using TypeDict's `total` kwarg.

[See PEP-655](https://peps.python.org/pep-0655) for more info.


### Passing additional args or kwargs

You may have a function that supports any number of args or kwargs:

```py
def get_context_data(self, *args, **kwargs):
    ...
```

This is not supported with the typed components.

As a workaround:
- For `*args`, set a positional argument that accepts a list of values:

    ```py
    # Tuple of one member of list of strings
    Args = Tuple[List[str]]
    ```

- For `*kwargs`, set a keyword argument that accepts a dictionary of values:

    ```py
    class Kwargs(TypedDict):
        variable: str
        another: int
        # Pass any extra keys under `extra`
        extra: Dict[str, any]
    ```

### Handling no args or no kwargs

To declare that a component accepts no Args, Kwargs, etc, you can use `EmptyTuple` and `EmptyDict` types:

```py
from django_components import Component, EmptyDict, EmptyTuple

Args = EmptyTuple
Kwargs = Data = Slots = EmptyDict

class Button(Component[Args, Kwargs, Slots, Data, JsData, CssData]):
    ...
```

### Runtime input validation with types

_New in version 0.96_

> NOTE: Kwargs, slots, and data validation is supported only for Python >=3.11

In Python 3.11 and later, when you specify the component types, you will get also runtime validation of the inputs you pass to `Component.render` or `Component.render_to_response`.

So, using the example from before, if you ignored the type errors and still ran the following code:

```py
Button.render(
    # Error: First arg must be `int`, got `float`
    args=(1.25, "abc"),
    # Error: Key "another" is missing
    kwargs={
        "variable": "text",
    },
)
```

This would raise a `TypeError`:

```txt
Component 'Button' expected positional argument at index 0 to be <class 'int'>, got 1.25 of type <class 'float'>
```

In case you need to skip these errors, you can either set the faulty member to `Any`, e.g.:

```py
# Changed `int` to `Any`
Args = Tuple[Any, str]
```

Or you can replace `Args` with `Any` altogether, to skip the validation of args:

```py
# Replaced `Args` with `Any`
class Button(Component[Any, Kwargs, Slots, Data, JsData, CssData]):
    ...
```

Same applies to kwargs, data, and slots.

## Pre-defined components

### Dynamic components

If you are writing something like a form component, you may design it such that users
give you the component names, and your component renders it.

While you can handle this with a series of if / else statements, this is not an extensible solution.

Instead, you can use **dynamic components**. Dynamic components are used in place of normal components.

```django
{% load component_tags %}
{% component "dynamic" is=component_name title="Cat Museum" %}
    {% fill "content" %}
        HELLO_FROM_SLOT_1
    {% endfill %}
    {% fill "sidebar" %}
        HELLO_FROM_SLOT_2
    {% endfill %}
{% endcomponent %}
```

or in case you use the `django_components.component_shorthand_formatter` tag formatter:

```django
{% dynamic is=component_name title="Cat Museu" %}
    {% fill "content" %}
        HELLO_FROM_SLOT_1
    {% endfill %}
    {% fill "sidebar" %}
        HELLO_FROM_SLOT_2
    {% endfill %}
{% enddynamic %}
```


These behave same way as regular components. You pass it the same args, kwargs, and slots as you would
to the component that you want to render.

The only exception is that also you supply 1-2 additional inputs:
- `is` - Required - The component name or a component class to render
- `registry` - Optional - The `ComponentRegistry` that will be searched if `is` is a component name. If omitted, ALL registries are searched.

By default, the dynamic component is registered under the name `"dynamic"`. In case of a conflict, you can change the name used for the dynamic components by defining the [`COMPONENTS.dynamic_component_name` setting](#dynamic_component_name).

If you need to use the dynamic components in Python, you can also import it from `django_components`:
```py
from django_components import DynamicComponent

comp = SimpleTableComp if is_readonly else TableComp

output = DynamicComponent.render(
    kwargs={
        "is": comp,
        # Other kwargs...
    },
    # args: [...],
    # slots: {...},
)
```

## Registering components

In previous examples you could repeatedly see us using `@register()` to "register"
the components. In this section we dive deeper into what it actually means and how you can
manage (add or remove) components.

As a reminder, we may have a component like this:

```python
from django_components import Component, register

@register("calendar")
class Calendar(Component):
    template_name = "template.html"

    # This component takes one parameter, a date string to show in the template
    def get_context_data(self, date):
        return {
            "date": date,
        }
```

which we then render in the template as:

```django
{% component "calendar" date="1970-01-01" %}
{% endcomponent %}
```

As you can see, `@register` links up the component class
with the `{% component %}` template tag. So when the template tag comes across
a component called `"calendar"`, it can look up it's class and instantiate it.

### What is ComponentRegistry

The `@register` decorator is a shortcut for working with the `ComponentRegistry`.

`ComponentRegistry` manages which components can be used in the template tags.

Each `ComponentRegistry` instance is associated with an instance
of Django's `Library`. And Libraries are inserted into Django template
using the `{% load %}` tags.

The `@register` decorator accepts an optional kwarg `registry`, which specifies, the `ComponentRegistry` to register components into.
If omitted, the default `ComponentRegistry` instance defined in django_components is used.

```py
my_registry = ComponentRegistry()

@register(registry=my_registry)
class MyComponent(Component):
    ...
```

The default `ComponentRegistry` is associated with the `Library` that
you load when you call `{% load component_tags %}` inside your template, or when you
add `django_components.templatetags.component_tags` to the template builtins.

So when you register or unregister a component to/from a component registry,
then behind the scenes the registry automatically adds/removes the component's
template tags to/from the Library, so you can call the component from within the templates
such as `{% component "my_comp" %}`.

### Working with ComponentRegistry

The default `ComponentRegistry` instance can be imported as:

```py
from django_components import registry
```

You can use the registry to manually add/remove/get components:

```py
from django_components import registry

# Register components
registry.register("button", ButtonComponent)
registry.register("card", CardComponent)

# Get all or single
registry.all()  # {"button": ButtonComponent, "card": CardComponent}
registry.get("card")  # CardComponent

# Unregister single component
registry.unregister("card")

# Unregister all components
registry.clear()
```

### Registering components to custom ComponentRegistry

If you are writing a component library to be shared with others, you may want to manage your own instance of `ComponentRegistry`
and register components onto a different `Library` instance than the default one.

The `Library` instance can be set at instantiation of `ComponentRegistry`. If omitted,
then the default Library instance from django_components is used.

```py
from django.template import Library
from django_components import ComponentRegistry

my_library = Library(...)
my_registry = ComponentRegistry(library=my_library)
```

When you have defined your own `ComponentRegistry`, you can either register the components
with `my_registry.register()`, or pass the registry to the `@component.register()` decorator
via the `registry` kwarg:

```py
from path.to.my.registry import my_registry

@register("my_component", registry=my_registry)
class MyComponent(Component):
    ...
```

NOTE: The Library instance can be accessed under `library` attribute of `ComponentRegistry`.

### ComponentRegistry settings

When you are creating an instance of `ComponentRegistry`, you can define the components' behavior within the template.

The registry accepts these settings:
- `context_behavior`
- `tag_formatter`

```py
from django.template import Library
from django_components import ComponentRegistry, RegistrySettings

register = library = django.template.Library()
comp_registry = ComponentRegistry(
    library=library,
    settings=RegistrySettings(
        context_behavior="isolated",
        tag_formatter="django_components.component_formatter",
    ),
)
```

These settings are [the same as the ones you can set for django_components](#available-settings).

In fact, when you set `COMPONENT.tag_formatter` or `COMPONENT.context_behavior`, these are forwarded to the default `ComponentRegistry`.

This makes it possible to have multiple registries with different settings in one projects, and makes sharing of component libraries possible.

## Autodiscovery

Every component that you want to use in the template with the `{% component %}` tag needs to be registered with the ComponentRegistry. Normally, we use the `@register` decorator for that:

```py
from django_components import Component, register

@register("calendar")
class Calendar(Component):
    ...
```

But for the component to be registered, the code needs to be executed - the file needs to be imported as a module.

One way to do that is by importing all your components in `apps.py`:

```py
from django.apps import AppConfig

class MyAppConfig(AppConfig):
    name = "my_app"

    def ready(self) -> None:
        from components.card.card import Card
        from components.list.list import List
        from components.menu.menu import Menu
        from components.button.button import Button
        ...
```

However, there's a simpler way!

By default, the Python files in the `COMPONENTS.dirs` directories (or app-level `[app]/components/`) are auto-imported in order to auto-register the components.

Autodiscovery occurs when Django is loaded, during the `ready` hook of the `apps.py` file.

If you are using autodiscovery, keep a few points in mind:

- Avoid defining any logic on the module-level inside the `components` dir, that you would not want to run anyway.
- Components inside the auto-imported files still need to be registered with `@register()`
- Auto-imported component files must be valid Python modules, they must use suffix `.py`, and module name should follow [PEP-8](https://peps.python.org/pep-0008/#package-and-module-names).

Autodiscovery can be disabled in the [settings](#autodiscover---toggle-autodiscovery).

### Manually trigger autodiscovery

Autodiscovery can be also triggered manually as a function call. This is useful if you want to run autodiscovery at a custom point of the lifecycle:

```py
from django_components import autodiscover

autodiscover()
```

## Using slots in templates

_New in version 0.26_:

- The `slot` tag now serves only to declare new slots inside the component template.
  - To override the content of a declared slot, use the newly introduced `fill` tag instead.
- Whereas unfilled slots used to raise a warning, filling a slot is now optional by default.
  - To indicate that a slot must be filled, the new `required` option should be added at the end of the `slot` tag.

---

Components support something called 'slots'.
When a component is used inside another template, slots allow the parent template to override specific parts of the child component by passing in different content.
This mechanism makes components more reusable and composable.
This behavior is similar to [slots in Vue](https://vuejs.org/guide/components/slots.html).

In the example below we introduce two block tags that work hand in hand to make this work. These are...

- `{% slot <name> %}`/`{% endslot %}`: Declares a new slot in the component template.
- `{% fill <name> %}`/`{% endfill %}`: (Used inside a `{% component %}` tag pair.) Fills a declared slot with the specified content.

Let's update our calendar component to support more customization. We'll add `slot` tag pairs to its template, _template.html_.

```htmldjango
<div class="calendar-component">
    <div class="header">
        {% slot "header" %}Calendar header{% endslot %}
    </div>
    <div class="body">
        {% slot "body" %}Today's date is <span>{{ date }}</span>{% endslot %}
    </div>
</div>
```

When using the component, you specify which slots you want to fill and where you want to use the defaults from the template. It looks like this:

```htmldjango
{% component "calendar" date="2020-06-06" %}
    {% fill "body" %}
        Can you believe it's already <span>{{ date }}</span>??
    {% endfill %}
{% endcomponent %}
```

Since the 'header' fill is unspecified, it's taken from the base template. If you put this in a template, and pass in `date=2020-06-06`, this is what gets rendered:

```htmldjango
<div class="calendar-component">
    <div class="header">
        Calendar header
    </div>
    <div class="body">
        Can you believe it's already <span>2020-06-06</span>??
    </div>
</div>
```

### Named slots

As seen in the previouse section, you can use `{% fill slot_name %}` to insert content into a specific
slot.

You can define fills for multiple slot simply by defining them all within the `{% component %} {% endcomponent %}`
tags:

```htmldjango
{% component "calendar" date="2020-06-06" %}
    {% fill "header" %}
        Hi this is header!
    {% endfill %}
    {% fill "body" %}
        Can you believe it's already <span>{{ date }}</span>??
    {% endfill %}
{% endcomponent %}
```

You can also use `{% for %}`, `{% with %}`, or other non-component tags (even `{% include %}`)
to construct the `{% fill %}` tags, **as long as these other tags do not leave any text behind!**

```django
{% component "table" %}
  {% for slot_name in slots %}
    {% fill name=slot_name %}
      {{ slot_name }}
    {% endfill %}
  {% endfor %}

  {% with slot_name="abc" %}
    {% fill name=slot_name %}
      {{ slot_name }}
    {% endfill %}
  {% endwith %}
{% endcomponent %}
```

### Default slot

_Added in version 0.28_

As you can see, component slots lets you write reusable containers that you fill in when you use a component. This makes for highly reusable components that can be used in different circumstances.

It can become tedious to use `fill` tags everywhere, especially when you're using a component that declares only one slot. To make things easier, `slot` tags can be marked with an optional keyword: `default`.

When added to the tag (as shown below), this option lets you pass filling content directly in the body of a `component` tag pair – without using a `fill` tag. Choose carefully, though: a component template may contain at most one slot that is marked as `default`. The `default` option can be combined with other slot options, e.g. `required`.

Here's the same example as before, except with default slots and implicit filling.

The template:

```htmldjango
<div class="calendar-component">
    <div class="header">
        {% slot "header" %}Calendar header{% endslot %}
    </div>
    <div class="body">
        {% slot "body" default %}Today's date is <span>{{ date }}</span>{% endslot %}
    </div>
</div>
```

Including the component (notice how the `fill` tag is omitted):

```htmldjango
{% component "calendar" date="2020-06-06" %}
    Can you believe it's already <span>{{ date }}</span>??
{% endcomponent %}
```

The rendered result (exactly the same as before):

```html
<div class="calendar-component">
  <div class="header">Calendar header</div>
  <div class="body">Can you believe it's already <span>2020-06-06</span>??</div>
</div>
```

You may be tempted to combine implicit fills with explicit `fill` tags. This will not work. The following component template will raise an error when rendered.

```htmldjango
{# DON'T DO THIS #}
{% component "calendar" date="2020-06-06" %}
    {% fill "header" %}Totally new header!{% endfill %}
    Can you believe it's already <span>{{ date }}</span>??
{% endcomponent %}
```

Instead, you can use a named fill with name `default` to target the default fill:

```htmldjango
{# THIS WORKS #}
{% component "calendar" date="2020-06-06" %}
    {% fill "header" %}Totally new header!{% endfill %}
    {% fill "default" %}
        Can you believe it's already <span>{{ date }}</span>??
    {% endfill %}
{% endcomponent %}
```

NOTE: If you doubly-fill a slot, that is, that both `{% fill "default" %}` and `{% fill "header" %}`
would point to the same slot, this will raise an error when rendered.

#### Accessing default slot in Python

Since the default slot is stored under the slot name `default`, you can access the default slot
like so:

```py
class MyTable(Component):
    def get_context_data(self, *args, **kwargs):
        default_slot = self.input.slots["default"]
        return {
            "default_slot": default_slot,
        }
```

### Render fill in multiple places

_Added in version 0.70_

You can render the same content in multiple places by defining multiple slots with
identical names:

```htmldjango
<div class="calendar-component">
    <div class="header">
        {% slot "image" %}Image here{% endslot %}
    </div>
    <div class="body">
        {% slot "image" %}Image here{% endslot %}
    </div>
</div>
```

So if used like:

```htmldjango
{% component "calendar" date="2020-06-06" %}
    {% fill "image" %}
        <img src="..." />
    {% endfill %}
{% endcomponent %}
```

This renders:

```htmldjango
<div class="calendar-component">
    <div class="header">
        <img src="..." />
    </div>
    <div class="body">
        <img src="..." />
    </div>
</div>
```

#### Default and required slots

If you use a slot multiple times, you can still mark the slot as `default` or `required`.
For that, you must mark each slot individually, e.g.:

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

Which you can then use as regular default slot:

```htmldjango
{% component "calendar" date="2020-06-06" %}
    <img src="..." />
{% endcomponent %}
```

Since each slot is tagged individually, you can have multiple slots
with the same name but different conditions.

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
        {% slot "image" default %}
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

### Accessing original content of slots

_Added in version 0.26_

> NOTE: In version 0.77, the syntax was changed from
>
> ```django
> {% fill "my_slot" as "alias" %} {{ alias.default }}
> ```
>
> to
>
> ```django
> {% fill "my_slot" default="slot_default" %} {{ slot_default }}
> ```

Sometimes you may want to keep the original slot, but only wrap or prepend/append content to it. To do so, you can access the default slot via the `default` kwarg.

Similarly to the `data` attribute, you specify the variable name through which the default slot will be made available.

For instance, let's say you're filling a slot called 'body'. To render the original slot, assign it to a variable using the `'default'` keyword. You then render this variable to insert the default content:

```htmldjango
{% component "calendar" date="2020-06-06" %}
    {% fill "body" default="body_default" %}
        {{ body_default }}. Have a great day!
    {% endfill %}
{% endcomponent %}
```

This produces:

```htmldjango
<div class="calendar-component">
    <div class="header">
        Calendar header
    </div>
    <div class="body">
        Today's date is <span>2020-06-06</span>. Have a great day!
    </div>
</div>
```

To access the original content of a default slot, set the name to `default`:

```htmldjango
{% component "calendar" date="2020-06-06" %}
    {% fill "default" default="slot_default" %}
        {{ slot_default }}. Have a great day!
    {% endfill %}
{% endcomponent %}
```

### Conditional slots

_Added in version 0.26._

> NOTE: In version 0.70, `{% if_filled %}` tags were replaced with `{{ component_vars.is_filled }}` variables. If your slot name contained special characters, see the section [Accessing `is_filled` of slot names with special characters](#accessing-is_filled-of-slot-names-with-special-characters).

In certain circumstances, you may want the behavior of slot filling to depend on
whether or not a particular slot is filled.

For example, suppose we have the following component template:

```htmldjango
<div class="frontmatter-component">
    <div class="title">
        {% slot "title" %}Title{% endslot %}
    </div>
    <div class="subtitle">
        {% slot "subtitle" %}{# Optional subtitle #}{% endslot %}
    </div>
</div>
```

By default the slot named 'subtitle' is empty. Yet when the component is used without
explicit fills, the div containing the slot is still rendered, as shown below:

```html
<div class="frontmatter-component">
  <div class="title">Title</div>
  <div class="subtitle"></div>
</div>
```

This may not be what you want. What if instead the outer 'subtitle' div should only
be included when the inner slot is in fact filled?

The answer is to use the `{{ component_vars.is_filled.<name> }}` variable. You can use this together with Django's `{% if/elif/else/endif %}` tags to define a block whose contents will be rendered only if the component slot with
the corresponding 'name' is filled.

This is what our example looks like with `component_vars.is_filled`.

```htmldjango
<div class="frontmatter-component">
    <div class="title">
        {% slot "title" %}Title{% endslot %}
    </div>
    {% if component_vars.is_filled.subtitle %}
    <div class="subtitle">
        {% slot "subtitle" %}{# Optional subtitle #}{% endslot %}
    </div>
    {% endif %}
</div>
```

Here's our example with more complex branching.

```htmldjango
<div class="frontmatter-component">
    <div class="title">
        {% slot "title" %}Title{% endslot %}
    </div>
    {% if component_vars.is_filled.subtitle %}
    <div class="subtitle">
        {% slot "subtitle" %}{# Optional subtitle #}{% endslot %}
    </div>
    {% elif component_vars.is_filled.title %}
        ...
    {% elif component_vars.is_filled.<name> %}
        ...
    {% endif %}
</div>
```

Sometimes you're not interested in whether a slot is filled, but rather that it _isn't_.
To negate the meaning of `component_vars.is_filled`, simply treat it as boolean and negate it with `not`:

```htmldjango
{% if not component_vars.is_filled.subtitle %}
<div class="subtitle">
    {% slot "subtitle" / %}
</div>
{% endif %}
```

#### Accessing `is_filled` of slot names with special characters

To be able to access a slot name via `component_vars.is_filled`, the slot name needs to be composed of only alphanumeric characters and underscores (e.g. `this__isvalid_123`).

However, you can still define slots with other special characters. In such case, the slot name in `component_vars.is_filled` is modified to replace all invalid characters into `_`.

So a slot named `"my super-slot :)"` will be available as `component_vars.is_filled.my_super_slot___`.

Same applies when you are accessing `is_filled` from within the Python, e.g.:

```py
class MyTable(Component):
    def on_render_before(self, context, template) -> None:
        # ✅ Works
        if self.is_filled["my_super_slot___"]:
            # Do something

        # ❌ Does not work
        if self.is_filled["my super-slot :)"]:
            # Do something
```

### Scoped slots

_Added in version 0.76_:

Consider a component with slot(s). This component may do some processing on the inputs, and then use the processed variable in the slot's default template:

```py
@register("my_comp")
class MyComp(Component):
    template = """
        <div>
            {% slot "content" default %}
                input: {{ input }}
            {% endslot %}
        </div>
    """

    def get_context_data(self, input):
        processed_input = do_something(input)
        return {"input": processed_input}
```

You may want to design a component so that users of your component can still access the `input` variable, so they don't have to recompute it.

This behavior is called "scoped slots". This is inspired by [Vue scoped slots](https://vuejs.org/guide/components/slots.html#scoped-slots) and [scoped slots of django-web-components](https://github.com/Xzya/django-web-components/tree/master?tab=readme-ov-file#scoped-slots).

Using scoped slots consists of two steps:

1. Passing data to `slot` tag
2. Accessing data in `fill` tag

#### Passing data to slots

To pass the data to the `slot` tag, simply pass them as keyword attributes (`key=value`):

```py
@register("my_comp")
class MyComp(Component):
    template = """
        <div>
            {% slot "content" default input=input %}
                input: {{ input }}
            {% endslot %}
        </div>
    """

    def get_context_data(self, input):
        processed_input = do_something(input)
        return {
            "input": processed_input,
        }
```

#### Accessing slot data in fill

Next, we head over to where we define a fill for this slot. Here, to access the slot data
we set the `data` attribute to the name of the variable through which we want to access
the slot data. In the example below, we set it to `data`:

```django
{% component "my_comp" %}
    {% fill "content" data="slot_data" %}
        {{ slot_data.input }}
    {% endfill %}
{% endcomponent %}
```

To access slot data on a default slot, you have to explictly define the `{% fill %}` tags.

So this works:

```django
{% component "my_comp" %}
    {% fill "default" data="slot_data" %}
        {{ slot_data.input }}
    {% endfill %}
{% endcomponent %}
```

While this does not:

```django
{% component "my_comp" data="data" %}
    {{ data.input }}
{% endcomponent %}
```

Note: You cannot set the `data` attribute and
[`default` attribute)](#accessing-original-content-of-slots)
to the same name. This raises an error:

```django
{% component "my_comp" %}
    {% fill "content" data="slot_var" default="slot_var" %}
        {{ slot_var.input }}
    {% endfill %}
{% endcomponent %}
```

### Dynamic slots and fills

Until now, we were declaring slot and fill names statically, as a string literal, e.g.

```django
{% slot "content" / %}
```

However, sometimes you may want to generate slots based on the given input. One example of this is [a table component like that of Vuetify](https://vuetifyjs.com/en/api/v-data-table/), which creates a header and an item slots for each user-defined column.

In django_components you can achieve the same, simply by using a variable (or a [template expression](#use-template-tags-inside-component-inputs)) instead of a string literal:

```django
<table>
  <tr>
    {% for header in headers %}
      <th>
        {% slot "header-{{ header.key }}" value=header.title %}
          {{ header.title }}
        {% endslot %}
      </th>
    {% endfor %}
  </tr>
</table>
```

When using the component, you can either set the fill explicitly:

```django
{% component "table" headers=headers items=items %}
  {% fill "header-name" data="data" %}
    <b>{{ data.value }}</b>
  {% endfill %}
{% endcomponent %}
```

Or also use a variable:

```django
{% component "table" headers=headers items=items %}
  {# Make only the active column bold #}
  {% fill "header-{{ active_header_name }}" data="data" %}
    <b>{{ data.value }}</b>
  {% endfill %}
{% endcomponent %}
```

> NOTE: It's better to use static slot names whenever possible for clarity. The dynamic slot names should be reserved for advanced use only.

Lastly, in rare cases, you can also pass the slot name via [the spread operator](#spread-operator). This is possible, because the slot name argument is actually a shortcut for a `name` keyword argument.

So this:

```django
{% slot "content" / %}
```

is the same as:

```django
{% slot name="content" / %}
```

So it's possible to define a `name` key on a dictionary, and then spread that onto the slot tag:

```django
{# slot_props = {"name": "content"} #}
{% slot ...slot_props / %}
```

### Pass through all the slots

You can dynamically pass all slots to a child component. This is similar to
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

## Accessing data passed to the component

When you call `Component.render` or `Component.render_to_response`, the inputs to these methods can be accessed from within the instance under `self.input`.

This means that you can use `self.input` inside:
- `get_context_data`
- `get_template_name`
- `get_template`
- `on_render_before`
- `on_render_after`

`self.input` is only defined during the execution of `Component.render`, and raises a `RuntimeError` when called outside of this context.

`self.input` has the same fields as the input to `Component.render`:

```py
class TestComponent(Component):
    def get_context_data(self, var1, var2, variable, another, **attrs):
        assert self.input.args == (123, "str")
        assert self.input.kwargs == {"variable": "test", "another": 1}
        assert self.input.slots == {"my_slot": ...}
        assert isinstance(self.input.context, Context)

        return {
            "variable": variable,
        }

rendered = TestComponent.render(
    kwargs={"variable": "test", "another": 1},
    args=(123, "str"),
    slots={"my_slot": "MY_SLOT"},
)
```

NOTE: The slots in `self.input.slots` are normalized to slot functions.

## Rendering HTML attributes

_New in version 0.74_:

You can use the `html_attrs` tag to render HTML attributes, given a dictionary
of values.

So if you have a template:

```django
<div class="{{ classes }}" data-id="{{ my_id }}">
</div>
```

You can simplify it with `html_attrs` tag:

```django
<div {% html_attrs attrs %}>
</div>
```

where `attrs` is:

```py
attrs = {
    "class": classes,
    "data-id": my_id,
}
```

This feature is inspired by [`merge_attrs` tag of django-web-components](https://github.com/Xzya/django-web-components/tree/master?tab=readme-ov-file#default--merged-attributes) and
["fallthrough attributes" feature of Vue](https://vuejs.org/guide/components/attrs).

### Removing atttributes

Attributes that are set to `None` or `False` are NOT rendered.

So given this input:

```py
attrs = {
    "class": "text-green",
    "required": False,
    "data-id": None,
}
```

And template:

```django
<div {% html_attrs attrs %}>
</div>
```

Then this renders:

```html
<div class="text-green"></div>
```

### Boolean attributes

In HTML, boolean attributes are usually rendered with no value. Consider the example below where the first button is disabled and the second is not:

```html
<button disabled>Click me!</button> <button>Click me!</button>
```

HTML rendering with `html_attrs` tag or `attributes_to_string` works the same way, where `key=True` is rendered simply as `key`, and `key=False` is not render at all.

So given this input:

```py
attrs = {
    "disabled": True,
    "autofocus": False,
}
```

And template:

```django
<div {% html_attrs attrs %}>
</div>
```

Then this renders:

```html
<div disabled></div>
```

### Default attributes

Sometimes you may want to specify default values for attributes. You can pass a second argument (or kwarg `defaults`) to set the defaults.

```django
<div {% html_attrs attrs defaults %}>
    ...
</div>
```

In the example above, if `attrs` contains e.g. the `class` key, `html_attrs` will render:

`class="{{ attrs.class }}"`

Otherwise, `html_attrs` will render:

`class="{{ defaults.class }}"`

### Appending attributes

For the `class` HTML attribute, it's common that we want to _join_ multiple values,
instead of overriding them. For example, if you're authoring a component, you may
want to ensure that the component will ALWAYS have a specific class. Yet, you may
want to allow users of your component to supply their own classes.

We can achieve this by adding extra kwargs. These values
will be appended, instead of overwriting the previous value.

So if we have a variable `attrs`:

```py
attrs = {
    "class": "my-class pa-4",
}
```

And on `html_attrs` tag, we set the key `class`:

```django
<div {% html_attrs attrs class="some-class" %}>
</div>
```

Then these will be merged and rendered as:

```html
<div data-value="my-class pa-4 some-class"></div>
```

To simplify merging of variables, you can supply the same key multiple times, and these will be all joined together:

```django
{# my_var = "class-from-var text-red" #}
<div {% html_attrs attrs class="some-class another-class" class=my_var %}>
</div>
```

Renders:

```html
<div
  data-value="my-class pa-4 some-class another-class class-from-var text-red"
></div>
```

### Rules for `html_attrs`

1. Both `attrs` and `defaults` can be passed as positional args

   `{% html_attrs attrs defaults key=val %}`

   or as kwargs

   `{% html_attrs key=val defaults=defaults attrs=attrs %}`

2. Both `attrs` and `defaults` are optional (can be omitted)

3. Both `attrs` and `defaults` are dictionaries, and we can define them the same way [we define dictionaries for the `component` tag](#pass-dictonary-by-its-key-value-pairs). So either as `attrs=attrs` or `attrs:key=value`.

4. All other kwargs are appended and can be repeated.

### Examples for `html_attrs`

Assuming that:

```py
class_from_var = "from-var"

attrs = {
    "class": "from-attrs",
    "type": "submit",
}

defaults = {
    "class": "from-defaults",
    "role": "button",
}
```

Then:

- Empty tag <br/>
  `{% html_attr %}`

  renders (empty string): <br/>
  ` `

- Only kwargs <br/>
  `{% html_attr class="some-class" class=class_from_var data-id="123" %}`

  renders: <br/>
  `class="some-class from-var" data-id="123"`

- Only attrs <br/>
  `{% html_attr attrs %}`

  renders: <br/>
  `class="from-attrs" type="submit"`

- Attrs as kwarg <br/>
  `{% html_attr attrs=attrs %}`

  renders: <br/>
  `class="from-attrs" type="submit"`

- Only defaults (as kwarg) <br/>
  `{% html_attr defaults=defaults %}`

  renders: <br/>
  `class="from-defaults" role="button"`

- Attrs using the `prefix:key=value` construct <br/>
  `{% html_attr attrs:class="from-attrs" attrs:type="submit" %}`

  renders: <br/>
  `class="from-attrs" type="submit"`

- Defaults using the `prefix:key=value` construct <br/>
  `{% html_attr defaults:class="from-defaults" %}`

  renders: <br/>
  `class="from-defaults" role="button"`

- All together (1) - attrs and defaults as positional args: <br/>
  `{% html_attrs attrs defaults class="added_class" class=class_from_var data-id=123 %}`

  renders: <br/>
  `class="from-attrs added_class from-var" type="submit" role="button" data-id=123`

- All together (2) - attrs and defaults as kwargs args: <br/>
  `{% html_attrs class="added_class" class=class_from_var data-id=123 attrs=attrs defaults=defaults %}`

  renders: <br/>
  `class="from-attrs added_class from-var" type="submit" role="button" data-id=123`

- All together (3) - mixed: <br/>
  `{% html_attrs attrs defaults:class="default-class" class="added_class" class=class_from_var data-id=123 %}`

  renders: <br/>
  `class="from-attrs added_class from-var" type="submit" data-id=123`

### Full example for `html_attrs`

```py
@register("my_comp")
class MyComp(Component):
    template: t.django_html = """
        <div
            {% html_attrs attrs
                defaults:class="pa-4 text-red"
                class="my-comp-date"
                class=class_from_var
                data-id="123"
            %}
        >
            Today's date is <span>{{ date }}</span>
        </div>
    """

    def get_context_data(self, date: Date, attrs: dict):
        return {
            "date": date,
            "attrs": attrs,
            "class_from_var": "extra-class"
        }

@register("parent")
class Parent(Component):
    template: t.django_html = """
        {% component "my_comp"
            date=date
            attrs:class="pa-0 border-solid border-red"
            attrs:data-json=json_data
            attrs:@click="(e) => onClick(e, 'from_parent')"
        / %}
    """

    def get_context_data(self, date: Date):
        return {
            "date": datetime.now(),
            "json_data": json.dumps({"value": 456})
        }
```

Note: For readability, we've split the tags across multiple lines.

Inside `MyComp`, we defined a default attribute

`defaults:class="pa-4 text-red"`

So if `attrs` includes key `class`, the default above will be ignored.

`MyComp` also defines `class` key twice. It means that whether the `class`
attribute is taken from `attrs` or `defaults`, the two `class` values
will be appended to it.

So by default, `MyComp` renders:

```html
<div class="pa-4 text-red my-comp-date extra-class" data-id="123">...</div>
```

Next, let's consider what will be rendered when we call `MyComp` from `Parent`
component.

`MyComp` accepts a `attrs` dictionary, that is passed to `html_attrs`, so the
contents of that dictionary are rendered as the HTML attributes.

In `Parent`, we make use of passing dictionary key-value pairs as kwargs to define
individual attributes as if they were regular kwargs.

So all kwargs that start with `attrs:` will be collected into an `attrs` dict.

```django
    attrs:class="pa-0 border-solid border-red"
    attrs:data-json=json_data
    attrs:@click="(e) => onClick(e, 'from_parent')"
```

And `get_context_data` of `MyComp` will receive `attrs` input with following keys:

```py
attrs = {
    "class": "pa-0 border-solid",
    "data-json": '{"value": 456}',
    "@click": "(e) => onClick(e, 'from_parent')",
}
```

`attrs["class"]` overrides the default value for `class`, whereas other keys
will be merged.

So in the end `MyComp` will render:

```html
<div
  class="pa-0 border-solid my-comp-date extra-class"
  data-id="123"
  data-json='{"value": 456}'
  @click="(e) => onClick(e, 'from_parent')"
>
  ...
</div>
```

### Rendering HTML attributes outside of templates

If you need to use serialize HTML attributes outside of Django template and the `html_attrs` tag, you can use `attributes_to_string`:

```py
from django_components.attributes import attributes_to_string

attrs = {
    "class": "my-class text-red pa-4",
    "data-id": 123,
    "required": True,
    "disabled": False,
    "ignored-attr": None,
}

attributes_to_string(attrs)
# 'class="my-class text-red pa-4" data-id="123" required'
```

## Template tag syntax

All template tags in django_component, like `{% component %}` or `{% slot %}`, and so on,
support extra syntax that makes it possible to write components like in Vue or React (JSX).

### Self-closing tags

When you have a tag like `{% component %}` or `{% slot %}`, but it has no content, you can simply append a forward slash `/` at the end, instead of writing out the closing tags like `{% endcomponent %}` or `{% endslot %}`:

So this:

```django
{% component "button" %}{% endcomponent %}
```

becomes

```django
{% component "button" / %}
```

### Special characters

_New in version 0.71_:

Keyword arguments can contain special characters `# @ . - _`, so keywords like
so are still valid:

```django
<body>
    {% component "calendar" my-date="2015-06-19" @click.native=do_something #some_id=True / %}
</body>
```

These can then be accessed inside `get_context_data` so:

```py
@register("calendar")
class Calendar(Component):
    # Since # . @ - are not valid identifiers, we have to
    # use `**kwargs` so the method can accept these args.
    def get_context_data(self, **kwargs):
        return {
            "date": kwargs["my-date"],
            "id": kwargs["#some_id"],
            "on_click": kwargs["@click.native"]
        }
```

### Spread operator

_New in version 0.93_:

Instead of passing keyword arguments one-by-one:

```django
{% component "calendar" title="How to abc" date="2015-06-19" author="John Wick" / %}
```

You can use a spread operator `...dict` to apply key-value pairs from a dictionary:

```py
post_data = {
    "title": "How to...",
    "date": "2015-06-19",
    "author": "John Wick",
}
```

```django
{% component "calendar" ...post_data / %}
```

This behaves similar to [JSX's spread operator](https://kevinyckim33.medium.com/jsx-spread-operator-component-props-meaning-3c9bcadd2493)
or [Vue's `v-bind`](https://vuejs.org/api/built-in-directives.html#v-bind).

Spread operators are treated as keyword arguments, which means that:
1. Spread operators must come after positional arguments.
2. You cannot use spread operators for [positional-only arguments](https://martinxpn.medium.com/positional-only-and-keyword-only-arguments-in-python-37-100-days-of-python-310c311657b0).

Other than that, you can use spread operators multiple times, and even put keyword arguments in-between or after them:

```django
{% component "calendar" ...post_data id=post.id ...extra / %}
```

In a case of conflicts, the values added later (right-most) overwrite previous values.

### Use template tags inside component inputs

_New in version 0.93_

When passing data around, sometimes you may need to do light transformations, like negating booleans or filtering lists.

Normally, what you would have to do is to define ALL the variables
inside `get_context_data()`. But this can get messy if your components contain a lot of logic.

```py
@register("calendar")
class Calendar(Component):
    def get_context_data(self, id: str, editable: bool):
        return {
            "editable": editable,
            "readonly": not editable,
            "input_id": f"input-{id}",
            "icon_id": f"icon-{id}",
            ...
        }
```

Instead, template tags in django_components (`{% component %}`, `{% slot %}`, `{% provide %}`, etc) allow you to treat literal string values as templates:

```django
{% component 'blog_post'
  "As positional arg {# yay #}"
  title="{{ person.first_name }} {{ person.last_name }}"
  id="{% random_int 10 20 %}"
  readonly="{{ editable|not }}"
  author="John Wick {# TODO: parametrize #}"
/ %}
```

In the example above:
- Component `test` receives a positional argument with value `"As positional arg "`. The comment is omitted.
- Kwarg `title` is passed as a string, e.g. `John Doe`
- Kwarg `id` is passed as `int`, e.g. `15`
- Kwarg `readonly` is passed as `bool`, e.g. `False`
- Kwarg `author` is passed as a string, e.g. `John Wick ` (Comment omitted)

This is inspired by [django-cotton](https://github.com/wrabit/django-cotton#template-expressions-in-attributes).

#### Passing data as string vs original values

Sometimes you may want to use the template tags to transform
or generate the data that is then passed to the component.

The data doesn't necessarily have to be strings. In the example above, the kwarg `id` was passed as an integer, NOT a string.

Although the string literals for components inputs are treated as regular Django templates, there is one special case:

When the string literal contains only a single template tag, with no extra text, then the value is passed as the original type instead of a string.

Here, `page` is an integer:

```django
{% component 'blog_post' page="{% random_int 10 20 %}" / %}
```

Here, `page` is a string:

```django
{% component 'blog_post' page=" {% random_int 10 20 %} " / %}
```

And same applies to the `{{ }}` variable tags:

Here, `items` is a list:

```django
{% component 'cat_list' items="{{ cats|slice:':2' }}" / %}
```

Here, `items` is a string:

```django
{% component 'cat_list' items="{{ cats|slice:':2' }} See more" / %}
```

#### Evaluating Python expressions in template

You can even go a step further and have a similar experience to Vue or React,
where you can evaluate arbitrary code expressions:

```jsx
<MyForm
  value={ isEnabled ? inputValue : null }
/>
```

Similar is possible with [`django-expr`](https://pypi.org/project/django-expr/), which adds an `expr` tag and filter that you can use to evaluate Python expressions from within the template:

```django
{% component "my_form"
  value="{% expr 'input_value if is_enabled else None' %}"
/ %}
```

> Note: Never use this feature to mix business logic and template logic. Business logic should still be in the view!

### Pass dictonary by its key-value pairs

_New in version 0.74_:

Sometimes, a component may expect a dictionary as one of its inputs.

Most commonly, this happens when a component accepts a dictionary
of HTML attributes (usually called `attrs`) to pass to the underlying template.

In such cases, we may want to define some HTML attributes statically, and other dynamically.
But for that, we need to define this dictionary on Python side:

```py
@register("my_comp")
class MyComp(Component):
    template = """
        {% component "other" attrs=attrs / %}
    """

    def get_context_data(self, some_id: str):
        attrs = {
            "class": "pa-4 flex",
            "data-some-id": some_id,
            "@click.stop": "onClickHandler",
        }
        return {"attrs": attrs}
```

But as you can see in the case above, the event handler `@click.stop` and styling `pa-4 flex`
are disconnected from the template. If the component grew in size and we moved the HTML
to a separate file, we would have hard time reasoning about the component's template.

Luckily, there's a better way.

When we want to pass a dictionary to a component, we can define individual key-value pairs
as component kwargs, so we can keep all the relevant information in the template. For that,
we prefix the key with the name of the dict and `:`. So key `class` of input `attrs` becomes
`attrs:class`. And our example becomes:

```py
@register("my_comp")
class MyComp(Component):
    template = """
        {% component "other"
            attrs:class="pa-4 flex"
            attrs:data-some-id=some_id
            attrs:@click.stop="onClickHandler"
        / %}
    """

    def get_context_data(self, some_id: str):
        return {"some_id": some_id}
```

Sweet! Now all the relevant HTML is inside the template, and we can move it to a separate file with confidence:

```django
{% component "other"
    attrs:class="pa-4 flex"
    attrs:data-some-id=some_id
    attrs:@click.stop="onClickHandler"
/ %}
```

> Note: It is NOT possible to define nested dictionaries, so
> `attrs:my_key:two=2` would be interpreted as:
>
> ```py
> {"attrs": {"my_key:two": 2}}
> ```

### Multi-line tags

By default, Django expects a template tag to be defined on a single line.

However, this can become unwieldy if you have a component with a lot of inputs:

```django
{% component "card" title="Joanne Arc" subtitle="Head of Kitty Relations" date_last_active="2024-09-03" ... %}
```

Instead, when you install django_components, it automatically configures Django
to suport multi-line tags.

So we can rewrite the above as:

```django
{% component "card"
    title="Joanne Arc"
    subtitle="Head of Kitty Relations"
    date_last_active="2024-09-03"
    ...
%}
```

Much better!

To disable this behavior, set [`COMPONENTS.multiline_tag`](#multiline_tags---enabledisable-multiline-support) to `False`

## Prop drilling and dependency injection (provide / inject)

_New in version 0.80_:

Django components supports dependency injection with the combination of:

1. `{% provide %}` tag
1. `inject()` method of the `Component` class

### What is "dependency injection" and "prop drilling"?

Prop drilling refers to a scenario in UI development where you need to pass data through many layers of a component tree to reach the nested components that actually need the data.

Normally, you'd use props to send data from a parent component to its children. However, this straightforward method becomes cumbersome and inefficient if the data has to travel through many levels or if several components scattered at different depths all need the same piece of information.

This results in a situation where the intermediate components, which don't need the data for their own functioning, end up having to manage and pass along these props. This clutters the component tree and makes the code verbose and harder to manage.

A neat solution to avoid prop drilling is using the "provide and inject" technique, AKA dependency injection.

With dependency injection, a parent component acts like a data hub for all its descendants. This setup allows any component, no matter how deeply nested it is, to access the required data directly from this centralized provider without having to messily pass props down the chain. This approach significantly cleans up the code and makes it easier to maintain.

This feature is inspired by Vue's [Provide / Inject](https://vuejs.org/guide/components/provide-inject) and React's [Context / useContext](https://react.dev/learn/passing-data-deeply-with-context).

### How to use provide / inject

As the name suggest, using provide / inject consists of 2 steps

1. Providing data
2. Injecting provided data

For examples of advanced uses of provide / inject, [see this discussion](https://github.com/EmilStenstrom/django-components/pull/506#issuecomment-2132102584).

### Using `{% provide %}` tag

First we use the `{% provide %}` tag to define the data we want to "provide" (make available).

```django
{% provide "my_data" key="hi" another=123 %}
    {% component "child" / %}  <--- Can access "my_data"
{% endprovide %}

{% component "child" / %}  <--- Cannot access "my_data"
```

Notice that the `provide` tag REQUIRES a name as a first argument. This is the _key_ by which we can then access the data passed to this tag.

`provide` tag name must resolve to a valid identifier (AKA a valid Python variable name).

Once you've set the name, you define the data you want to "provide" by passing it as keyword arguments. This is similar to how you pass data to the `{% with %}` tag.

> NOTE: Kwargs passed to `{% provide %}` are NOT added to the context.
> In the example below, the `{{ key }}` won't render anything:
>
> ```django
> {% provide "my_data" key="hi" another=123 %}
>     {{ key }}
> {% endprovide %}
> ```

Similarly to [slots and fills](#dynamic-slots-and-fills), also provide's name argument can be set dynamically via a variable, a template expression, or a spread operator:

```django
{% provide name=name ... %}
    ...
{% provide %}
</table>
```

### Using `inject()` method

To "inject" (access) the data defined on the `provide` tag, you can use the `inject()` method inside of `get_context_data()`.

For a component to be able to "inject" some data, the component (`{% component %}` tag) must be nested inside the `{% provide %}` tag.

In the example from previous section, we've defined two kwargs: `key="hi" another=123`. That means that if we now inject `"my_data"`, we get an object with 2 attributes - `key` and `another`.

```py
class ChildComponent(Component):
    def get_context_data(self):
        my_data = self.inject("my_data")
        print(my_data.key)     # hi
        print(my_data.another) # 123
        return {}
```

First argument to `inject` is the _key_ (or _name_) of the provided data. This
must match the string that you used in the `provide` tag. If no provider
with given key is found, `inject` raises a `KeyError`.

To avoid the error, you can pass a second argument to `inject` to which will act as a default value, similar to `dict.get(key, default)`:

```py
class ChildComponent(Component):
    def get_context_data(self):
        my_data = self.inject("invalid_key", DEFAULT_DATA)
        assert my_data == DEFAUKT_DATA
        return {}
```

The instance returned from `inject()` is a subclass of `NamedTuple`, so the instance is immutable. This ensures that the data returned from `inject` will always
have all the keys that were passed to the `provide` tag.

> NOTE: `inject()` works strictly only in `get_context_data`. If you try to call it from elsewhere, it will raise an error.

### Full example

```py
@register("child")
class ChildComponent(Component):
    template = """
        <div> {{ my_data.key }} </div>
        <div> {{ my_data.another }} </div>
    """

    def get_context_data(self):
        my_data = self.inject("my_data", "default")
        return {"my_data": my_data}

template_str = """
    {% load component_tags %}
    {% provide "my_data" key="hi" another=123 %}
        {% component "child" / %}
    {% endprovide %}
"""
```

renders:

```html
<div>hi</div>
<div>123</div>
```

## Component hooks

_New in version 0.96_

Component hooks are functions that allow you to intercept the rendering process at specific positions.

### Available hooks

- `on_render_before`

  ```py
  def on_render_before(
      self: Component,
      context: Context,
      template: Template
  ) -> None:
  ```

    Hook that runs just before the component's template is rendered.

    You can use this hook to access or modify the context or the template:

    ```py
    def on_render_before(self, context, template) -> None:
        # Insert value into the Context
        context["from_on_before"] = ":)"

        # Append text into the Template
        template.nodelist.append(TextNode("FROM_ON_BEFORE"))
    ```

- `on_render_after`

  ```py
  def on_render_after(
      self: Component,
      context: Context,
      template: Template,
      content: str
  ) -> None | str | SafeString:
  ```

    Hook that runs just after the component's template was rendered.
    It receives the rendered output as the last argument.

    You can use this hook to access the context or the template, but modifying
    them won't have any effect.

    To override the content that gets rendered, you can return a string or SafeString from this hook:

    ```py
    def on_render_after(self, context, template, content):
        # Prepend text to the rendered content
        return "Chocolate cookie recipe: " + content
    ```

### Component hooks example

You can use hooks together with [provide / inject](#how-to-use-provide--inject) to create components
that accept a list of items via a slot.

In the example below, each `tab_item` component will be rendered on a separate tab page, but they are all defined in the default slot of the `tabs` component.

[See here for how it was done](https://github.com/EmilStenstrom/django-components/discussions/540)

```django
{% component "tabs" %}
  {% component "tab_item" header="Tab 1" %}
    <p>
      hello from tab 1
    </p>
    {% component "button" %}
      Click me!
    {% endcomponent %}
  {% endcomponent %}

  {% component "tab_item" header="Tab 2" %}
    Hello this is tab 2
  {% endcomponent %}
{% endcomponent %}
```

## Component context and scope

By default, context variables are passed down the template as in regular Django - deeper scopes can access the variables from the outer scopes. So if you have several nested forloops, then inside the deep-most loop you can access variables defined by all previous loops.

With this in mind, the `{% component %}` tag behaves similarly to `{% include %}` tag - inside the component tag, you can access all variables that were defined outside of it.

And just like with `{% include %}`, if you don't want a specific component template to have access to the parent context, add `only` to the `{% component %}` tag:

```htmldjango
{% component "calendar" date="2015-06-19" only / %}
```

NOTE: `{% csrf_token %}` tags need access to the top-level context, and they will not function properly if they are rendered in a component that is called with the `only` modifier.

If you find yourself using the `only` modifier often, you can set the [context_behavior](#context-behavior) option to `"isolated"`, which automatically applies the `only` modifier. This is useful if you want to make sure that components don't accidentally access the outer context.

Components can also access the outer context in their context methods like `get_context_data` by accessing the property `self.outer_context`.

### Example of Accessing Outer Context

```django
<div>
  {% component "calender" / %}
</div>
```

Assuming that the rendering context has variables such as `date`, you can use `self.outer_context` to access them from within `get_context_data`. Here's how you might implement it:

```python
class Calender(Component):
    
    ...

    def get_context_data(self):
        outer_field = self.outer_context["date"]
        return {
            "date": outer_fields,
        }
```

However, as a best practice, it’s recommended not to rely on accessing the outer context directly through `self.outer_context`. Instead, explicitly pass the variables to the component. For instance, continue passing the variables in the component tag as shown in the previous examples.

## Pre-defined template variables

Here is a list of all variables that are automatically available from within the component's template and `on_render_before` / `on_render_after` hooks.

- `component_vars.is_filled`

    _New in version 0.70_

    Dictonary describing which slots are filled (`True`) or are not (`False`).

    Example:

    ```django
    {% if component_vars.is_filled.my_slot %}
        {% slot "my_slot" / %}
    {% endif %}
    ```

    This is equivalent to checking if a given key is among the slot fills:

    ```py
    class MyTable(Component):
        def get_context_data(self, *args, **kwargs):
            return {
                "my_slot_filled": "my_slot" in self.input.slots
            }
    ```

## Customizing component tags with TagFormatter

_New in version 0.89_

By default, components are rendered using the pair of `{% component %}` / `{% endcomponent %}` template tags:

```django
{% component "button" href="..." disabled %}
Click me!
{% endcomponent %}

{# or #}

{% component "button" href="..." disabled / %}
```

You can change this behaviour in the settings under the [`COMPONENTS.tag_formatter`](#tag-formatter-setting).

For example, if you set the tag formatter to `django_components.component_shorthand_formatter`, the components will use their name as the template tags:

```django
{% button href="..." disabled %}
  Click me!
{% endbutton %}

{# or #}

{% button href="..." disabled / %}
```

### Available TagFormatters

django_components provides following predefined TagFormatters:

- **`ComponentFormatter` (`django_components.component_formatter`)**

    Default

    Uses the `component` and `endcomponent` tags, and the component name is gives as the first positional argument.

    Example as block:
    ```django
    {% component "button" href="..." %}
        {% fill "content" %}
            ...
        {% endfill %}
    {% endcomponent %}
    ```

    Example as inlined tag:
    ```django
    {% component "button" href="..." / %}
    ```

- **`ShorthandComponentFormatter` (`django_components.component_shorthand_formatter`)**

    Uses the component name as start tag, and `end<component_name>`
    as an end tag.

    Example as block:
    ```django
    {% button href="..." %}
        Click me!
    {% endbutton %}
    ```

    Example as inlined tag:
    ```django
    {% button href="..." / %}
    ```

### Writing your own TagFormatter

#### Background

First, let's discuss how TagFormatters work, and how components are rendered in django_components.

When you render a component with `{% component %}` (or your own tag), the following happens:
1. `component` must be registered as a Django's template tag
2. Django triggers django_components's tag handler for tag `component`.
3. The tag handler passes the tag contents for pre-processing to `TagFormatter.parse()`.

    So if you render this:
    ```django
    {% component "button" href="..." disabled %}
    {% endcomponent %}
    ```

    Then `TagFormatter.parse()` will receive a following input:
    ```py
    ["component", '"button"', 'href="..."', 'disabled']
    ```
4. `TagFormatter` extracts the component name and the remaining input.

    So, given the above, `TagFormatter.parse()` returns the following:
    ```py
    TagResult(
        component_name="button",
        tokens=['href="..."', 'disabled']
    )
    ```
5. The tag handler resumes, using the tokens returned from `TagFormatter`.

    So, continuing the example, at this point the tag handler practically behaves as if you rendered:
    ```django
    {% component href="..." disabled %}
    ```
6. Tag handler looks up the component `button`, and passes the args, kwargs, and slots to it.

#### TagFormatter

`TagFormatter` handles following parts of the process above:
- Generates start/end tags, given a component. This is what you then call from within your template as `{% component %}`.

- When you `{% component %}`, tag formatter pre-processes the tag contents, so it can link back the custom template tag to the right component.

To do so, subclass from `TagFormatterABC` and implement following method:
- `start_tag`
- `end_tag`
- `parse`

For example, this is the implementation of [`ShorthandComponentFormatter`](#available-tagformatters)

```py
class ShorthandComponentFormatter(TagFormatterABC):
    # Given a component name, generate the start template tag
    def start_tag(self, name: str) -> str:
        return name  # e.g. 'button'

    # Given a component name, generate the start template tag
    def end_tag(self, name: str) -> str:
        return f"end{name}"  # e.g. 'endbutton'

    # Given a tag, e.g.
    # `{% button href="..." disabled %}`
    #
    # The parser receives:
    # `['button', 'href="..."', 'disabled']`
    def parse(self, tokens: List[str]) -> TagResult:
        tokens = [*tokens]
        name = tokens.pop(0)
        return TagResult(
            name,  # e.g. 'button'
            tokens  # e.g. ['href="..."', 'disabled']
        )
```

That's it! And once your `TagFormatter` is ready, don't forget to update the settings!

## Defining HTML/JS/CSS files

django_component's management of files builds on top of [Django's `Media` class](https://docs.djangoproject.com/en/5.0/topics/forms/media/).

To be familiar with how Django handles static files, we recommend reading also:

- [How to manage static files (e.g. images, JavaScript, CSS)](https://docs.djangoproject.com/en/5.0/howto/static-files/)

### Defining file paths relative to component or static dirs

As seen in the [getting started example](#create-your-first-component), to associate HTML/JS/CSS
files with a component, you set them as `template_name`, `Media.js` and `Media.css` respectively:

```py
# In a file [project root]/components/calendar/calendar.py
from django_components import Component, register

@register("calendar")
class Calendar(Component):
    template_name = "template.html"

    class Media:
        css = "style.css"
        js = "script.js"
```

In the example above, the files are defined relative to the directory where `component.py` is.

Alternatively, you can specify the file paths relative to the directories set in `COMPONENTS.dirs` or `COMPONENTS.app_dirs`.

Assuming that `COMPONENTS.dirs` contains path `[project root]/components`, we can rewrite the example as:

```py
# In a file [project root]/components/calendar/calendar.py
from django_components import Component, register

@register("calendar")
class Calendar(Component):
    template_name = "calendar/template.html"

    class Media:
        css = "calendar/style.css"
        js = "calendar/script.js"
```

NOTE: In case of conflict, the preference goes to resolving the files relative to the component's directory.

### Defining multiple paths

Each component can have only a single template. However, you can define as many JS or CSS files as you want using a list.

```py
class MyComponent(Component):
    class Media:
        js = ["path/to/script1.js", "path/to/script2.js"]
        css = ["path/to/style1.css", "path/to/style2.css"]
```

### Configuring CSS Media Types

You can define which stylesheets will be associated with which
[CSS Media types](https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_media_queries/Using_media_queries#targeting_media_types). You do so by defining CSS files as a dictionary.

See the corresponding [Django Documentation](https://docs.djangoproject.com/en/5.0/topics/forms/media/#css).

Again, you can set either a single file or a list of files per media type:

```py
class MyComponent(Component):
    class Media:
        css = {
            "all": "path/to/style1.css",
            "print": "path/to/style2.css",
        }
```

```py
class MyComponent(Component):
    class Media:
        css = {
            "all": ["path/to/style1.css", "path/to/style2.css"],
            "print": ["path/to/style3.css", "path/to/style4.css"],
        }
```

NOTE: When you define CSS as a string or a list, the `all` media type is implied.

### Supported types for file paths

File paths can be any of:

- `str`
- `bytes`
- `PathLike` (`__fspath__` method)
- `SafeData` (`__html__` method)
- `Callable` that returns any of the above, evaluated at class creation (`__new__`)

```py
from pathlib import Path

from django.utils.safestring import mark_safe

class SimpleComponent(Component):
    class Media:
        css = [
            mark_safe('<link href="/static/calendar/style.css" rel="stylesheet" />'),
            Path("calendar/style1.css"),
            "calendar/style2.css",
            b"calendar/style3.css",
            lambda: "calendar/style4.css",
        ]
        js = [
            mark_safe('<script src="/static/calendar/script.js"></script>'),
            Path("calendar/script1.js"),
            "calendar/script2.js",
            b"calendar/script3.js",
            lambda: "calendar/script4.js",
        ]
```

### Path as objects

In the example [above](#supported-types-for-file-paths), you could see that when we used `mark_safe` to mark a string as a `SafeString`, we had to define the full `<script>`/`<link>` tag.

This is an extension of Django's [Paths as objects](https://docs.djangoproject.com/en/5.0/topics/forms/media/#paths-as-objects) feature, where "safe" strings are taken as is, and accessed only at render time.

Because of that, the paths defined as "safe" strings are NEVER resolved, neither relative to component's directory, nor relative to `COMPONENTS.dirs`.

"Safe" strings can be used to lazily resolve a path, or to customize the `<script>` or `<link>` tag for individual paths:

```py
class LazyJsPath:
    def __init__(self, static_path: str) -> None:
        self.static_path = static_path

    def __html__(self):
        full_path = static(self.static_path)
        return format_html(
            f'<script type="module" src="{full_path}"></script>'
        )

@register("calendar")
class Calendar(Component):
    template_name = "calendar/template.html"

    def get_context_data(self, date):
        return {
            "date": date,
        }

    class Media:
        css = "calendar/style.css"
        js = [
            # <script> tag constructed by Media class
            "calendar/script1.js",
            # Custom <script> tag
            LazyJsPath("calendar/script2.js"),
        ]
```

### Customize how paths are rendered into HTML tags with `media_class`

Sometimes you may need to change how all CSS `<link>` or JS `<script>` tags are rendered for a given component. You can achieve this by providing your own subclass of [Django's `Media` class](https://docs.djangoproject.com/en/5.0/topics/forms/media) to component's `media_class` attribute.

Normally, the JS and CSS paths are passed to `Media` class, which decides how the paths are resolved and how the `<link>` and `<script>` tags are constructed.

To change how the tags are constructed, you can override the [`Media.render_js` and `Media.render_css` methods](https://github.com/django/django/blob/fa7848146738a9fe1d415ee4808664e54739eeb7/django/forms/widgets.py#L102):

```py
from django.forms.widgets import Media
from django_components import Component, register

class MyMedia(Media):
    # Same as original Media.render_js, except
    # the `<script>` tag has also `type="module"`
    def render_js(self):
        tags = []
        for path in self._js:
            if hasattr(path, "__html__"):
                tag = path.__html__()
            else:
                tag = format_html(
                    '<script type="module" src="{}"></script>',
                    self.absolute_path(path)
                )
        return tags

@register("calendar")
class Calendar(Component):
    template_name = "calendar/template.html"

    class Media:
        css = "calendar/style.css"
        js = "calendar/script.js"

    # Override the behavior of Media class
    media_class = MyMedia
```

NOTE: The instance of the `Media` class (or it's subclass) is available under `Component.media` after the class creation (`__new__`).

## Rendering JS/CSS dependencies

If:
1. Your components use JS and CSS, whether inlined via `Component.js/css` or via `Component.Media.js/css`,
2. And you use the `ComponentDependencyMiddleware` middleware

Then, by default, the components' JS and CSS will be automatically inserted into the HTML:
- CSS styles will be inserted at the end of the `<head>`
- JS scripts will be inserted at the end of the `<body>`

If you want to place the dependencies elsewhere, you can override that with following Django template tags:

- `{% component_js_dependencies %}` - Renders only JS
- `{% component_css_dependencies %}` - Renders only CSS

So if you have a component with JS and CSS:

```py
from django_components import Component, types

class MyButton(Component):
    template: types.django_html = """
        <button class="my-button">
            Click me!
        </button>
    """
    js: types.js = """
        for (const btnEl of document.querySelectorAll(".my-button")) {
            btnEl.addEventListener("click", () => {
                console.log("BUTTON CLICKED!");
            });
        }
    """
    css: types.css """
        .my-button {
            background: green;
        }
    """

    class Media:
        js = ["/extra/script.js"]
        css = ["/extra/style.css"]
```

Then the inlined JS and the scripts in `Media.js` will be rendered at the default place,
or in `{% component_js_dependencies %}`.

And the inlined CSS and the styles in `Media.css` will be rendered at the default place,
or in `{% component_css_dependencies %}`.

And if you don't specify `{% component_dependencies %}` tags, it is the equivalent of:

```django
<!doctype html>
<html>
  <head>
    <title>MyPage</title>
    ...
    {% component_css_dependencies %}
  </head>
  <body>
    <main>
      ...
    </main>
    {% component_js_dependencies %}
  </body>
</html>
```

### Setting Up `ComponentDependencyMiddleware`

`ComponentDependencyMiddleware` is a Django middleware designed to manage and inject CSS/JS dependencies for rendered components dynamically. It ensures that only the necessary stylesheets and scripts are loaded in your HTML responses, based on the components used in your Django templates.

To set it up, add the middleware to your `MIDDLEWARE` in settings.py:

```python
MIDDLEWARE = [
    # ... other middleware classes ...
    'django_components.middleware.ComponentDependencyMiddleware'
    # ... other middleware classes ...
]
```

### `render_dependencies` and deep-dive into rendering JS / CSS without the middleware

For most scenarios, using the `ComponentDependencyMiddleware` middleware will be just fine.

However, this section is for you if you want to:
- Render HTML that will NOT be sent as a server response
- Insert pre-rendered HTML into another component
- Render HTML fragments (partials)

Every time there is an HTML string that has parts which were rendered using components,
and any of those components has JS / CSS, then this HTML string MUST be processed with `render_dependencies`.

It is actually `render_dependencies` that finds all used components in the HTML string,
and inserts the component's JS and CSS into `{% component_dependencies %}` tags, or at the default locations.

#### Render JS / CSS without the middleware

The `ComponentDependencyMiddleware` middleware just calls `render_dependencies`, passing in the HTML
content. So if you rendered a template that contained `{% components %}` tags, instead of the middleware,
you MUST pass the result through `render_dependencies`:

```py
from django.template.base import Template
from django.template.context import Context
from django_component import render_dependencies

template = Template("""
    {% load component_tags %}
    <!doctype html>
    <html>
    <head>
        <title>MyPage</title>
    </head>
    <body>
        <main>
            {% component "my_button" %}
                Click me!
            {% endcomponent %}
        </main>
    </body>
    </html>
""")

rendered = template.render(Context({}))
rendered = render_dependencies(rendered)
```

Same applies if you render a template using Django's [`django.shortcuts.render`](https://docs.djangoproject.com/en/5.1/topics/http/shortcuts/#render):

```py
from django.shortcuts import render

def my_view(request):
    rendered = render(request, "pages/home.html")
    rendered = render_dependencies(rendered)
    return rendered
```

Alternatively, when you render HTML with `Component.render()` or `Component.render_to_response()`,
these automatically call `render_dependencies()` for you, so you don't have to:

```py
from django_components import Component

class MyButton(Component):
    ...

# No need to call `render_dependencies()`
rendered = MyButton.render()
```

#### Inserting pre-rendered HTML into another component

In previous section we've shown that `render_dependencies()` does NOT need to be called
when you render a component via `Component.render()`.

API of django-components makes it possible to compose components in a "React-like" way,
where we pre-render a piece of HTML and then insert it into a larger structure.

To do this, you must add `render_dependencies=False` to the nested components:

```py
card_actions = CardActions.render(
    kwargs={"editable": editable},
    render_dependencies=False,
)

card = Card.render(
    slots={"actions": card_actions},
    render_dependencies=False,
)

page = MyPage.render(
    slots={"card": card},
)
```

Why is `render_dependencies=False` required?

As mentioned earlier, each time we call `Component.render()`, we also call `render_dependencies()`.

However, there is a problem here - When we call `render_dependencies()` inside `CardActions.render()`,
we extract the info on components' JS and CSS from the HTML. But the template of `CardActions`
contains no `{% component_depedencies %}` tags, and nor `<head>` nor `<body>` HTML tags.
So the component's JS and CSS will NOT be inserted, and will be lost.

To work around this, you must set `render_dependencies=False` when rendering pieces of HTML with `Component.render()`
and inserting them into larger structures.

## Available settings

All library settings are handled from a global `COMPONENTS` variable that is read from `settings.py`. By default you don't need it set, there are resonable defaults.

Here's overview of all available settings and their defaults:

```py
COMPONENTS = {
    "autodiscover": True,
    "context_behavior": "django",  # "django" | "isolated"
    "dirs": [BASE_DIR / "components"],  # Root-level "components" dirs, e.g. `/path/to/proj/components/`
    "app_dirs": ["components"],  # App-level "components" dirs, e.g. `[app]/components/`
    "dynamic_component_name": "dynamic",
    "libraries": [],  # ["mysite.components.forms", ...]
    "multiline_tags": True,
    "reload_on_template_change": False,
    "static_files_allowed": [
        ".css",
        ".js",
        # Images
        ".apng", ".png", ".avif", ".gif", ".jpg",
        ".jpeg",  ".jfif", ".pjpeg", ".pjp", ".svg",
        ".webp", ".bmp", ".ico", ".cur", ".tif", ".tiff",
        # Fonts
        ".eot", ".ttf", ".woff", ".otf", ".svg",
    ],
    "static_files_forbidden": [
        ".html", ".django", ".dj", ".tpl",
        # Python files
        ".py", ".pyc",
    ],
    "tag_formatter": "django_components.component_formatter",
    "template_cache_size": 128,
}
```

### `libraries` - Load component modules

Configure the locations where components are loaded. To do this, add a `COMPONENTS` variable to you `settings.py` with a list of python paths to load. This allows you to build a structure of components that are independent from your apps.

```python
COMPONENTS = {
    "libraries": [
        "mysite.components.forms",
        "mysite.components.buttons",
        "mysite.components.cards",
    ],
}
```

Where `mysite/components/forms.py` may look like this:

```py
@register("form_simple")
class FormSimple(Component):
    template = """
        <form>
            ...
        </form>
    """

@register("form_other")
class FormOther(Component):
    template = """
        <form>
            ...
        </form>
    """
```

In the rare cases when you need to manually trigger the import of libraries, you can use the `import_libraries` function:

```py
from django_components import import_libraries

import_libraries()
```

### `autodiscover` - Toggle autodiscovery

If you specify all the component locations with the setting above and have a lot of apps, you can (very) slightly speed things up by disabling autodiscovery.

```python
COMPONENTS = {
    "autodiscover": False,
}
```

### `dirs`

Specify the directories that contain your components.

Directories must be full paths, same as with STATICFILES_DIRS.

These locations are searched during autodiscovery, or when you define HTML, JS, or CSS as
a separate file.

```py
COMPONENTS = {
    "dirs": [BASE_DIR / "components"],
}
```

### `app_dirs`

Specify the app-level directories that contain your components.

Directories must be relative to app, e.g.:

```py
COMPONENTS = {
    "app_dirs": ["my_comps"],  # To search for [app]/my_comps
}
```

These locations are searched during autodiscovery, or when you define HTML, JS, or CSS as
a separate file.

Each app will be searched for these directories.

Set to empty list to disable app-level components:

```py
COMPONENTS = {
    "app_dirs": [],
}
```

### `dynamic_component_name`

By default, the dynamic component is registered under the name `"dynamic"`. In case of a conflict, use this setting to change the name used for the dynamic components.

```python
COMPONENTS = {
    "dynamic_component_name": "new_dynamic",
}
```

### `multiline_tags` - Enable/Disable multiline support

If `True`, template tags can span multiple lines. Default: `True`

```python
COMPONENTS = {
    "multiline_tags": True,
}
```

### `static_files_allowed`

A list of regex patterns (as strings) that define which files within `COMPONENTS.dirs` and `COMPONENTS.app_dirs`
are treated as static files.

If a file is matched against any of the patterns, it's considered a static file. Such files are collected
when running `collectstatic`, and can be accessed under the static file endpoint.

You can also pass in compiled regexes (`re.Pattern`) for more advanced patterns.

By default, JS, CSS, and common image and font file formats are considered static files:

```python
COMPONENTS = {
    "static_files_allowed": [
            "css",
            "js",
            # Images
            ".apng", ".png",
            ".avif",
            ".gif",
            ".jpg", ".jpeg", ".jfif", ".pjpeg", ".pjp",  # JPEG
            ".svg",
            ".webp", ".bmp",
            ".ico", ".cur",  # ICO
            ".tif", ".tiff",
            # Fonts
            ".eot", ".ttf", ".woff", ".otf", ".svg",
    ],
}
```

### `static_files_forbidden`

A list of suffixes that define which files within `COMPONENTS.dirs` and `COMPONENTS.app_dirs`
will NEVER be treated as static files.

If a file is matched against any of the patterns, it will never be considered a static file, even if the file matches
a pattern in [`COMPONENTS.static_files_allowed`](#static_files_allowed).

Use this setting together with `COMPONENTS.static_files_allowed` for a fine control over what files will be exposed.

You can also pass in compiled regexes (`re.Pattern`) for more advanced patterns.

By default, any HTML and Python are considered NOT static files:

```python
COMPONENTS = {
    "static_files_forbidden": [
        ".html", ".django", ".dj", ".tpl", ".py", ".pyc",
    ],
}
```

### `template_cache_size` - Tune the template cache

Each time a template is rendered it is cached to a global in-memory cache (using Python's `lru_cache` decorator). This speeds up the next render of the component. As the same component is often used many times on the same page, these savings add up.

By default the cache holds 128 component templates in memory, which should be enough for most sites. But if you have a lot of components, or if you are using the `template` method of a component to render lots of dynamic templates, you can increase this number. To remove the cache limit altogether and cache everything, set template_cache_size to `None`.

```python
COMPONENTS = {
    "template_cache_size": 256,
}
```

If you want add templates to the cache yourself, you can use `cached_template()`:

```py
from django_components import cached_template

cached_template("Variable: {{ variable }}")

# You can optionally specify Template class, and other Template inputs:
class MyTemplate(Template):
    pass

cached_template(
    "Variable: {{ variable }}",
    template_cls=MyTemplate,
    name=...
    origin=...
    engine=...
)
```

### `context_behavior` - Make components isolated (or not)

> NOTE: `context_behavior` and `slot_context_behavior` options were merged in v0.70.
>
> If you are migrating from BEFORE v0.67, set `context_behavior` to `"django"`. From v0.67 to v0.78 (incl) the default value was `"isolated"`.
>
> For v0.79 and later, the default is again `"django"`. See the rationale for change [here](https://github.com/EmilStenstrom/django-components/issues/498).

You can configure what variables are available inside the `{% fill %}` tags. See [Component context and scope](#component-context-and-scope).

This has two modes:

- `"django"` - Default - The default Django template behavior.

  Inside the `{% fill %}` tag, the context variables you can access are a union of:

  - All the variables that were OUTSIDE the fill tag, including any loops or with tag
  - Data returned from `get_context_data()` of the component that wraps the fill tag.

- `"isolated"` - Similar behavior to [Vue](https://vuejs.org/guide/components/slots.html#render-scope) or React, this is useful if you want to make sure that components don't accidentally access variables defined outside of the component.

  Inside the `{% fill %}` tag, you can ONLY access variables from 2 places:

  - `get_context_data()` of the component which defined the template (AKA the "root" component)
  - Any loops (`{% for ... %}`) that the `{% fill %}` tag is part of.

```python
COMPONENTS = {
    "context_behavior": "isolated",
}
```

#### Example "django"

Given this template:

```py
class RootComp(Component):
    template = """
        {% with cheese="feta" %}
            {% component 'my_comp' %}
                {{ my_var }}  # my_var
                {{ cheese }}  # cheese
            {% endcomponent %}
        {% endwith %}
    """
    def get_context_data(self):
        return { "my_var": 123 }
```

Then if `get_context_data()` of the component `"my_comp"` returns following data:

```py
{ "my_var": 456 }
```

Then the template will be rendered as:

```django
456   # my_var
feta  # cheese
```

Because `"my_comp"` overshadows the variable `"my_var"`,
so `{{ my_var }}` equals `456`.

And variable `"cheese"` equals `feta`, because the fill CAN access
all the data defined in the outer layers, like the `{% with %}` tag.

#### Example "isolated"

Given this template:

```py
class RootComp(Component):
    template = """
        {% with cheese="feta" %}
            {% component 'my_comp' %}
                {{ my_var }}  # my_var
                {{ cheese }}  # cheese
            {% endcomponent %}
        {% endwith %}
    """
    def get_context_data(self):
        return { "my_var": 123 }
```

Then if `get_context_data()` of the component `"my_comp"` returns following data:

```py
{ "my_var": 456 }
```

Then the template will be rendered as:

```django
123   # my_var
      # cheese
```

Because variables `"my_var"` and `"cheese"` are searched only inside `RootComponent.get_context_data()`.
But since `"cheese"` is not defined there, it's empty.

Notice that the variables defined with the `{% with %}` tag are ignored inside the `{% fill %}` tag with the `"isolated"` mode.

### `reload_on_template_change` - Reload dev server on component file changes

If `True`, configures Django to reload on component files. See
[Reload dev server on component file changes](#reload-dev-server-on-component-file-changes).

NOTE: This setting should be enabled only for the dev environment!

### `tag_formatter` - Change how components are used in templates
Sets the [`TagFormatter`](#available-tagformatters) instance. See the section [Customizing component tags with TagFormatter](#customizing-component-tags-with-tagformatter).

Can be set either as direct reference, or as an import string;

```py
COMPONENTS = {
    "tag_formatter": "django_components.component_formatter"
}
```

Or

```py
from django_components import component_formatter

COMPONENTS = {
    "tag_formatter": component_formatter
}
```

## Running with development server

### Reload dev server on component file changes

This is relevant if you are using the project structure as shown in our examples, where
HTML, JS, CSS and Python are separate and nested in a directory.

In this case you may notice that when you are running a development server,
the server sometimes does not reload when you change comoponent files.

From relevant [StackOverflow thread](https://stackoverflow.com/a/76722393/9788634):

> TL;DR is that the server won't reload if it thinks the changed file is in a templates directory,
> or in a nested sub directory of a templates directory. This is by design.

To make the dev server reload on all component files, set [`reload_on_template_change`](#reload_on_template_change---reload-dev-server-on-component-file-changes) to `True`.
This configures Django to watch for component files too.

NOTE: This setting should be enabled only for the dev environment!

## Logging and debugging

Django components supports [logging with Django](https://docs.djangoproject.com/en/5.0/howto/logging/#logging-how-to). This can help with troubleshooting.

To configure logging for Django components, set the `django_components` logger in `LOGGING` in `settings.py` (below).

Also see the [`settings.py` file in sampleproject](https://github.com/EmilStenstrom/django-components/blob/master/sampleproject/sampleproject/settings.py) for a real-life example.

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

## Management Command

You can use the built-in management command `startcomponent` to create a django component. The command accepts the following arguments and options:

- `name`: The name of the component to create. This is a required argument.

- `--path`: The path to the components directory. This is an optional argument. If not provided, the command will use the `BASE_DIR` setting from your Django settings.

- `--js`: The name of the JavaScript file. This is an optional argument. The default value is `script.js`.

- `--css`: The name of the CSS file. This is an optional argument. The default value is `style.css`.

- `--template`: The name of the template file. This is an optional argument. The default value is `template.html`.

- `--force`: This option allows you to overwrite existing files if they exist. This is an optional argument.

- `--verbose`: This option allows the command to print additional information during component creation. This is an optional argument.

- `--dry-run`: This option allows you to simulate component creation without actually creating any files. This is an optional argument. The default value is `False`.

### Management Command Usage

To use the command, run the following command in your terminal:

```bash
python manage.py startcomponent <name> --path <path> --js <js_filename> --css <css_filename> --template <template_filename> --force --verbose --dry-run
```

Replace `<name>`, `<path>`, `<js_filename>`, `<css_filename>`, and `<template_filename>` with your desired values.

### Management Command Examples

Here are some examples of how you can use the command:

### Creating a Component with Default Settings

To create a component with the default settings, you only need to provide the name of the component:

```bash
python manage.py startcomponent my_component
```

This will create a new component named `my_component` in the `components` directory of your Django project. The JavaScript, CSS, and template files will be named `script.js`, `style.css`, and `template.html`, respectively.

### Creating a Component with Custom Settings

You can also create a component with custom settings by providing additional arguments:

```bash
python manage.py startcomponent new_component --path my_components --js my_script.js --css my_style.css --template my_template.html
```

This will create a new component named `new_component` in the `my_components` directory. The JavaScript, CSS, and template files will be named `my_script.js`, `my_style.css`, and `my_template.html`, respectively.

### Overwriting an Existing Component

If you want to overwrite an existing component, you can use the `--force` option:

```bash
python manage.py startcomponent my_component --force
```

This will overwrite the existing `my_component` if it exists.

### Simulating Component Creation

If you want to simulate the creation of a component without actually creating any files, you can use the `--dry-run` option:

```bash
python manage.py startcomponent my_component --dry-run
```

This will simulate the creation of `my_component` without creating any files.

## Writing and sharing component libraries

You can publish and share your components for others to use. Here are the steps to do so:

### Writing component libraries

1. Create a Django project with the following structure:

    ```txt
    project/
      |--  myapp/
        |--  __init__.py
        |--  apps.py
        |--  templates/
          |--  table/
            |--  table.py
            |--  table.js
            |--  table.css
            |--  table.html
        |--  menu.py   <--- single-file component
      |--  templatetags/
        |--  __init__.py
        |--  mytags.py
    ```

2. Create custom `Library` and `ComponentRegistry` instances in `mytags.py`

    This will be the entrypoint for using the components inside Django templates.

    Remember that Django requires the `Library` instance to be accessible under the `register` variable ([See Django docs](https://docs.djangoproject.com/en/dev/howto/custom-template-tags)):

    ```py
    from django.template import Library
    from django_components import ComponentRegistry, RegistrySettings

    register = library = django.template.Library()
    comp_registry = ComponentRegistry(
        library=library,
        settings=RegistrySettings(
            context_behavior="isolated",
            tag_formatter="django_components.component_formatter",
        ),
    )
    ```

    As you can see above, this is also the place where we configure how our components should behave, using the `settings` argument. If omitted, default settings are used.

    For library authors, we recommend setting `context_behavior` to `"isolated"`, so that the state cannot leak into the components, and so the components' behavior is configured solely through the inputs. This means that the components will be more predictable and easier to debug.

    Next, you can decide how will others use your components by settingt the `tag_formatter` options.

    If omitted or set to `"django_components.component_formatter"`,
    your components will be used like this:

    ```django
    {% component "table" items=items headers=headers %}
    {% endcomponent %}
    ```

    Or you can use `"django_components.component_shorthand_formatter"`
    to use components like so:

    ```django
    {% table items=items headers=headers %}
    {% endtable %}
    ```

    Or you can define a [custom TagFormatter](#tagformatter).

    Either way, these settings will be scoped only to your components. So, in the user code, there may be components side-by-side that use different formatters:

    ```django
    {% load mytags %}

    {# Component from your library "mytags", using the "shorthand" formatter #}
    {% table items=items headers=header %}
    {% endtable %}

    {# User-created components using the default settings #}
    {% component "my_comp" title="Abc..." %}
    {% endcomponent %}
    ```

3. Write your components and register them with your instance of `ComponentRegistry`

    There's one difference when you are writing components that are to be shared, and that's that the components must be explicitly registered with your instance of `ComponentRegistry` from the previous step.

    For better user experience, you can also define the types for the args, kwargs, slots and data.

    It's also a good idea to have a common prefix for your components, so they can be easily distinguished from users' components. In the example below, we use the prefix `my_` / `My`.

    ```py
    from typing import Dict, NotRequired, Optional, Tuple, TypedDict

    from django_components import Component, SlotFunc, register, types

    from myapp.templatetags.mytags import comp_registry

    # Define the types
    class EmptyDict(TypedDict):
        pass

    type MyMenuArgs = Tuple[int, str]

    class MyMenuSlots(TypedDict):
        default: NotRequired[Optional[SlotFunc[EmptyDict]]]

    class MyMenuProps(TypedDict):
        vertical: NotRequired[bool]
        klass: NotRequired[str]
        style: NotRequired[str]

    # Define the component
    # NOTE: Don't forget to set the `registry`!
    @register("my_menu", registry=comp_registry)
    class MyMenu(Component[MyMenuArgs, MyMenuProps, MyMenuSlots, Any, Any, Any]):
        def get_context_data(
            self,
            *args,
            attrs: Optional[Dict] = None,
        ):
            return {
                "attrs": attrs,
            }

        template: types.django_html = """
            {# Load django_components template tags #}
            {% load component_tags %}

            <div {% html_attrs attrs class="my-menu" %}>
                <div class="my-menu__content">
                    {% slot "default" default / %}
                </div>
            </div>
        """
    ```

4. Import the components in `apps.py`

    Normally, users rely on [autodiscovery](#autodiscovery) and `COMPONENTS.dirs` to load the component files.

    Since you, as the library author, are not in control of the file system, it is recommended to load the components manually.

    We recommend doing this in the `AppConfig.ready()` hook of your `apps.py`:

    ```py
    from django.apps import AppConfig

    class MyAppConfig(AppConfig):
        default_auto_field = "django.db.models.BigAutoField"
        name = "myapp"

        # This is the code that gets run when user adds myapp
        # to Django's INSTALLED_APPS
        def ready(self) -> None:
            # Import the components that you want to make available
            # inside the templates.
            from myapp.templates import (
                menu,
                table,
            )
    ```

    Note that you can also include any other startup logic within `AppConfig.ready()`.

And that's it! The next step is to publish it.

### Publishing component libraries

Once you are ready to share your library, you need to build
a distribution and then publish it to PyPI.

django_components uses the [`build`](https://build.pypa.io/en/stable/) utility to build a distribution:

```bash
python -m build --sdist --wheel --outdir dist/ .
```

And to publish to PyPI, you can use `twine` ([See Python user guide](https://packaging.python.org/en/latest/tutorials/packaging-projects/#uploading-the-distribution-archives))

```bash
twine upload --repository pypi dist/* -u __token__ -p <PyPI_TOKEN>
```

Notes on publishing:
- The user of the package NEEDS to have installed and configured `django_components`.
- If you use components where the HTML / CSS / JS files are separate, you may need to define `MANIFEST.in` to include those files with the distribution ([see user guide](https://setuptools.pypa.io/en/latest/userguide/miscellaneous.html)).

### Installing and using component libraries

After the package has been published, all that remains is to install it in other django projects:

1. Install the package:

    ```bash
    pip install myapp
    ```

2. Add the package to `INSTALLED_APPS`

    ```py
    INSTALLED_APPS = [
        ...
        "myapp",
    ]
    ```

3. Optionally add the template tags to the `builtins`, so you don't have to call `{% load mytags %}` in every template:

    ```py
    TEMPLATES = [
        {
            ...,
            'OPTIONS': {
                'context_processors': [
                    ...
                ],
                'builtins': [
                    'myapp.templatetags.mytags',
                ]
            },
        },
    ]
    ```

4. And, at last, you can use the components in your own project!

    ```django
    {% my_menu title="Abc..." %}
        Hello World!
    {% endmy_menu %}
    ```

## Community examples

One of our goals with `django-components` is to make it easy to share components between projects. If you have a set of components that you think would be useful to others, please open a pull request to add them to the list below.

- [django-htmx-components](https://github.com/iwanalabs/django-htmx-components): A set of components for use with [htmx](https://htmx.org/). Try out the [live demo](https://dhc.iwanalabs.com/).

## Contributing and development

### Install locally and run the tests

Start by forking the project by clicking the **Fork button** up in the right corner in the GitHub . This makes a copy of the repository in your own name. Now you can clone this repository locally and start adding features:

```sh
git clone https://github.com/<your GitHub username>/django-components.git
```

To quickly run the tests install the local dependencies by running:

```sh
pip install -r requirements-dev.txt
```

Now you can run the tests to make sure everything works as expected:

```sh
pytest
```

The library is also tested across many versions of Python and Django. To run tests that way:

```sh
pyenv install -s 3.8
pyenv install -s 3.9
pyenv install -s 3.10
pyenv install -s 3.11
pyenv install -s 3.12
pyenv local 3.8 3.9 3.10 3.11 3.12
tox -p
```

### Running Playwright tests

We use [Playwright](https://playwright.dev/python/docs/intro) for end-to-end tests. You will therefore need to install Playwright to be able to run these tests.

Luckily, Playwright makes it very easy:

```sh
pip install -r requirements-dev.txt
playwright install chromium --with-deps
```

After Playwright is ready, simply run the tests with `tox`:
```sh
tox
```

### Developing against live Django app

How do you check that your changes to django-components project will work in an actual Django project?

Use the [sampleproject](https://github.com/EmilStenstrom/django-components/tree/master/sampleproject/) demo project to validate the changes:

1. Navigate to [sampleproject](https://github.com/EmilStenstrom/django-components/tree/master/sampleproject/) directory:

   ```sh
   cd sampleproject
   ```

2. Install dependencies from the [requirements.txt](https://github.com/EmilStenstrom/django-components/blob/master/sampleproject/requirements.txt) file:

   ```sh
   pip install -r requirements.txt
   ```

3. Link to your local version of django-components:

   ```sh
   pip install -e ..
   ```

   NOTE: The path (in this case `..`) must point to the directory that has the `setup.py` file.

4. Start Django server
   ```sh
   python manage.py runserver
   ```

Once the server is up, it should be available at <http://127.0.0.1:8000>.

To display individual components, add them to the `urls.py`, like in the case of <http://127.0.0.1:8000/greeting>

### Building JS code

django_components uses a bit of JS code to:
- Manage the loading of JS and CSS files used by the components
- Allow to pass data from Python to JS

When you make changes to this JS code, you also need to compile it:

1. Make sure you are inside `src/django_components_js`:

```sh
cd src/django_components_js
```

2. Install the JS dependencies

```sh
npm install
```

3. Compile the JS/TS code:

```sh
python build.py
```

The script will combine all JS/TS code into a single `.js` file, minify it,
and copy it to `django_components/static/django_components/django_components.min.js`.

### Packaging and publishing

To package the library into a distribution that can be published to PyPI, run:

```sh
# Install pypa/build
python -m pip install build --user
# Build a binary wheel and a source tarball
python -m build --sdist --wheel --outdir dist/ .
```

To publish the package to PyPI, use `twine` ([See Python user guide](https://packaging.python.org/en/latest/tutorials/packaging-projects/#uploading-the-distribution-archives)):
```sh
twine upload --repository pypi dist/* -u __token__ -p <PyPI_TOKEN>
```

[See the full workflow here.](https://github.com/EmilStenstrom/django-components/discussions/557#discussioncomment-10179141)

### Development guides

Deep dive into how django_components' features are implemented.

- [Slot rendering](https://github.com/EmilStenstrom/django-components/blob/master/docs/devguides/slot_rendering.md)
- [Slots and blocks](https://github.com/EmilStenstrom/django-components/blob/master/docs/devguides/slots_and_blocks.md)
- [JS and CSS dependency management](https://github.com/EmilStenstrom/django-components/blob/master/docs/devguides/dependency_mgmt.md)
