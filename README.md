# <img src="logo/logo-black-on-white.svg" alt="django-components" style="max-width: 100%; background: white; color: black;">
<a href="https://github.com/EmilStenstrom/django-components/actions?query=workflow%3A%22Run+tests%22"><img align="right" src="https://github.com/EmilStenstrom/django-components/workflows/Run%20tests/badge.svg" alt="Show test status"></a>
<a href="https://pepy.tech/project/django-components"><img align="right" src="https://pepy.tech/badge/django-components" alt="Show download stats"></a>

A way to create simple reusable template components in Django.

It lets you create "template components", that contains both the template, the Javascript and the CSS needed to generate the front end code you need for a modern app. Components look like this:

```htmldjango
{% component "calendar" date="2015-06-19" %}{% endcomponent %}
```

And this is what gets rendered (plus the CSS and Javascript you've specified):

```html
<div class="calendar-component">Today's date is <span>2015-06-19</span></div>
```

[See the example project](./sampleproject) or read on to learn about the details!

## Table of Contents

- [Release notes](#release-notes)
- [Security notes 🚨](#security-notes-)
- [Installation](#installation)
- [Compatiblity](#compatiblity)
- [Create your first component](#create-your-first-component)
- [Using single-file components](#using-single-file-components)
- [Use components in templates](#use-components-in-templates)
- [Use components outside of templates](#use-components-outside-of-templates)
- [Use components as views](#use-components-as-views)
- [Autodiscovery](#autodiscovery)
- [Using slots in templates](#using-slots-in-templates)
- [Passing data to components](#passing-data-to-components)
- [Rendering HTML attributes](#rendering-html-attributes)
- [Prop drilling and dependency injection (provide / inject)](#prop-drilling-and-dependency-injection-provide--inject)
- [Component context and scope](#component-context-and-scope)
- [Defining HTML/JS/CSS files](#defining-htmljscss-files)
- [Rendering JS/CSS dependencies](#rendering-jscss-dependencies)
- [Available settings](#available-settings)
- [Logging and debugging](#logging-and-debugging)
- [Management Command](#management-command)
- [Community examples](#community-examples)
- [Running django-components project locally](#running-django-components-project-locally)
- [Development guides](#development-guides)

## Release notes

🚨📢 **Version 0.81** Aligned the `render_to_response` method with the (now public) `render` method of `Component` class. Moreover, slots passed to these can now be rendered also as functions.

- BREAKING CHANGE: The order of arguments to `render_to_response` has changed.

**Version 0.80** introduces dependency injection with the `{% provide %}` tag and `inject()` method.

🚨📢 **Version 0.79**

- BREAKING CHANGE: Default value for the `COMPONENTS.context_behavior` setting was changes from `"isolated"` to `"django"`. If you did not set this value explicitly before, this may be a breaking change. See the rationale for change [here](https://github.com/EmilStenstrom/django-components/issues/498).


🚨📢 **Version 0.77** CHANGED the syntax for accessing default slot content.
- Previously, the syntax was
`{% fill "my_slot" as "alias" %}` and `{{ alias.default }}`.
- Now, the syntax is
`{% fill "my_slot" default="alias" %}` and `{{ alias }}`.

**Version 0.74** introduces `html_attrs` tag and `prefix:key=val` construct for passing dicts to components.

🚨📢 **Version 0.70**

- `{% if_filled "my_slot" %}` tags were replaced with `{{ component_vars.is_filled.my_slot }}` variables.
- Simplified settings - `slot_context_behavior` and `context_behavior` were merged. See the [documentation](#context-behavior) for more details.

**Version 0.67** CHANGED the default way how context variables are resolved in slots. See the [documentation](https://github.com/EmilStenstrom/django-components/tree/0.67#isolate-components-slots) for more details.

🚨📢 **Version 0.5** CHANGES THE SYNTAX for components. `component_block` is now `component`, and `component` blocks need an ending `endcomponent` tag. The new `python manage.py upgradecomponent` command can be used to upgrade a directory (use --path argument to point to each dir) of components to the new syntax automatically.

This change is done to simplify the API in anticipation of a 1.0 release of django_components. After 1.0 we intend to be stricter with big changes like this in point releases.

**Version 0.34** adds components as views, which allows you to handle requests and render responses from within a component. See the [documentation](#use-components-as-views) for more details.

**Version 0.28** introduces 'implicit' slot filling and the `default` option for `slot` tags.

**Version 0.27** adds a second installable app: *django_components.safer_staticfiles*. It provides the same behavior as *django.contrib.staticfiles* but with extra security guarantees (more info below in Security Notes).

**Version 0.26** changes the syntax for `{% slot %}` tags. From now on, we separate defining a slot (`{% slot %}`) from filling a slot with content (`{% fill %}`). This means you will likely need to change a lot of slot tags to fill. We understand this is annoying, but it's the only way we can get support for nested slots that fill in other slots, which is a very nice featuPpre to have access to. Hoping that this will feel worth it!

**Version 0.22** starts autoimporting all files inside components subdirectores, to simplify setup. An existing project might start to get AlreadyRegistered-errors because of this. To solve this, either remove your custom loading of components, or set "autodiscover": False in settings.COMPONENTS.

**Version 0.17** renames `Component.context` and `Component.template` to `get_context_data` and `get_template_name`. The old methods still work, but emit a deprecation warning. This change was done to sync naming with Django's class based views, and make using django-components more familiar to Django users. `Component.context` and `Component.template` will be removed when version 1.0 is released.

## Security notes 🚨

*You are advised to read this section before using django-components in production.*

### Static files

Components can be organized however you prefer.
That said, our prefered way is to keep the files of a component close together by bundling them in the same directory.
This means that files containing backend logic, such as Python modules and HTML templates, live in the same directory as static files, e.g. JS and CSS.

If your are using _django.contrib.staticfiles_ to collect static files, no distinction is made between the different kinds of files.
As a result, your Python code and templates may inadvertently become available on your static file server.
You probably don't want this, as parts of your backend logic will be exposed, posing a __potential security vulnerability__.

As of *v0.27*, django-components ships with an additional installable app *django_components.__safer_staticfiles__*.
It is a drop-in replacement for *django.contrib.staticfiles*.
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
[see the demo project](./sampleproject/README.md).

## Installation

Install the app into your environment:

> `pip install django_components`

Then add the app into INSTALLED_APPS in settings.py

```python
INSTALLED_APPS = [
    ...,
    'django_components',
]
```

Modify `TEMPLATES` section of settings.py as follows:
- *Remove `'APP_DIRS': True,`*
- add `loaders` to `OPTIONS` list and set it to following value:

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
                    'django.template.loaders.filesystem.Loader',
                    'django.template.loaders.app_directories.Loader',
                    'django_components.template_loader.Loader',
                ]
            )],
        },
    },
]
```

Modify STATICFILES_DIRS (or add it if you don't have it) so django can find your static JS and CSS files:

```python
STATICFILES_DIRS = [
    ...,
    os.path.join(BASE_DIR, "components"),
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

## Compatiblity

Django-components supports all supported combinations versions of [Django](https://docs.djangoproject.com/en/dev/faq/install/#what-python-version-can-i-use-with-django) and [Python](https://devguide.python.org/versions/#versions).

| Python version | Django version           |
|----------------|--------------------------|
| 3.8            | 4.2                      |
| 3.9            | 4.2                      |
| 3.10           | 4.2, 5.0                 |
| 3.11           | 4.2, 5.0                 |
| 3.12           | 4.2, 5.0                 |

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

First you need a CSS file. Be sure to prefix all rules with a unique class so they don't clash with other rules.

```css
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

```js
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

```htmldjango
{# In a file called [project root]/components/calendar/template.html #}
<div class="calendar-component">Today's date is <span>{{ date }}</span></div>
```

Finally, we use django-components to tie this together. Start by creating a file called `calendar.py` in your component calendar directory. It will be auto-detected and loaded by the app.

Inside this file we create a Component by inheriting from the Component class and specifying the context method. We also register the global component registry so that we easily can render it anywhere in our templates.

```python
# In a file called [project root]/components/calendar/calendar.py
from django_components import component

@component.register("calendar")
class Calendar(component.Component):
    # Templates inside `[your apps]/components` dir and `[project root]/components` dir
    # will be automatically found. To customize which template to use based on context
    # you can override method `get_template_name` instead of specifying `template_name`.
    #
    # `template_name` can be relative to dir where `calendar.py` is, or relative to STATICFILES_DIRS
    template_name = "template.html"

    # This component takes one parameter, a date string to show in the template
    def get_context_data(self, date):
        return {
            "date": date,
        }

    # Both `css` and `js` can be relative to dir where `calendar.py` is, or relative to STATICFILES_DIRS
    class Media:
        css = "style.css"
        js = "script.js"
```

And voilá!! We've created our first component.

## Using single-file components

Components can also be defined in a single file, which is useful for small components. To do this, you can use the `template`, `js`, and `css` class attributes instead of the `template_name` and `Media`. For example, here's the calendar component from above, defined in a single file:

```python
# In a file called [project root]/components/calendar.py
from django_components import component
from django_components import types as t

@component.register("calendar")
class Calendar(component.Component):
    def get_context_data(self, date):
        return {
            "date": date,
        }

    template: t.django_html = """
        <div class="calendar-component">Today's date is <span>{{ date }}</span></div>
    """

    css: t.css = """
        .calendar-component { width: 200px; background: pink; }
        .calendar-component span { font-weight: bold; }
    """

    js: t.js = """
        (function(){
            if (document.querySelector(".calendar-component")) {
                document.querySelector(".calendar-component").onclick = function(){ alert("Clicked calendar!"); };
            }
        })()
    """
```

This makes it easy to create small components without having to create a separate template, CSS, and JS file.

Note that the `t.django_html`, `t.css`, and `t.js` types are used to specify the type of the template, CSS, and JS files, respectively. This is not necessary, but if you're using VSCode with the [Python Inline Source Syntax Highlighting](https://marketplace.visualstudio.com/items?itemName=samwillis.python-inline-source) extension, it will give you syntax highlighting for the template, CSS, and JS.

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
class SimpleComponent(component.Component):
    template = """
        {% load component_tags %}
        hello: {{ hello }}
        foo: {{ foo }}
        kwargs: {{ kwargs|safe }}
        slot_first: {% slot "first" required %}{% endslot %}
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
    slots: Dict[str, str | SafeString | SlotRenderFunc] | None = None,
    escape_slots_content: bool = True
) -> str:
```

- _`args`_ - Positional args for the component. This is the same as calling the component
   as `{% component "my_comp" arg1 arg2 ... %}`

- _`kwargs`_ - Keyword args for the component. This is the same as calling the component
   as `{% component "my_comp" key1=val1 key2=val2 ... %}`

- _`slots`_ - Component slot fills. This is the same as pasing `{% fill %}` tags to the component.
   Accepts a dictionary of `{ slot_name: slot_content }` where `slot_content` can be a string
   or [`SlotRenderFunc`](#slotrenderfunc).

- _`escape_slots_content`_ - Whether the content from `slots` should be escaped. `True` by default to prevent XSS attacks. If you disable escaping, you should make sure that any content you pass to the slots is safe, especially if it comes from user input.

- _`context`_ - A context (dictionary or Django's Context) within which the component
   is rendered. The keys on the context can be accessed from within the template.
   - NOTE: In "isolated" mode, context is NOT accessible, and data MUST be passed via
      component's args and kwargs.

#### `SlotRenderFunc`

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

class SimpleComponent(component.Component):
   response_class = MyResponse
   template: types.django_html = "HELLO"

response = SimpleComponent.render_to_response()
assert isinstance(response, MyResponse)
```

## Use components as views

_New in version 0.34_

Components can now be used as views. To do this, `Component` subclasses Django's `View` class. This means that you can use all of the [methods](https://docs.djangoproject.com/en/5.0/ref/class-based-views/base/#view) of `View` in your component. For example, you can override `get` and `post` to handle GET and POST requests, respectively.

In addition, `Component` now has a [`render_to_response`](#inputs-of-render-and-render_to_response) method that renders the component template based on the provided context and slots' data and returns an `HttpResponse` object.

Here's an example of a calendar component defined as a view:

```python
# In a file called [project root]/components/calendar.py
from django_components import component

@component.register("calendar")
class Calendar(component.Component):

    template = """
        <div class="calendar-component">
            <div class="header">
                {% slot "header" %}{% endslot %}
            </div>
            <div class="body">
                Today's date is <span>{{ date }}</span>
            </div>
        </div>
    """

    def get(self, request, *args, **kwargs):
        context = {
            "date": request.GET.get("date", "2020-06-06"),
        }
        slots = {
            "header": "Calendar header",
        }
        return self.render_to_response(context=context, slots=slots)
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

Remember to add `__init__.py` to your components directory, so that Django can find the `urls.py` file.

Finally, include the component's urls in your project's `urls.py` file:

```python
# In a file called [project root]/urls.py
from django.urls import include, path

urlpatterns = [
    path("components/", include("components.urls")),
]
```

Note: slots content are automatically escaped by default to prevent XSS attacks. To disable escaping, set `escape_slots_content=False` in the `render_to_response` method. If you do so, you should make sure that any content you pass to the slots is safe, especially if it comes from user input.

If you're planning on passing an HTML string, check Django's use of [`format_html`](https://docs.djangoproject.com/en/5.0/ref/utils/#django.utils.html.format_html) and [`mark_safe`](https://docs.djangoproject.com/en/5.0/ref/utils/#django.utils.safestring.mark_safe).

## Autodiscovery

By default, the Python files in the `components` app are auto-imported in order to auto-register the components (e.g. `components/button/button.py`).

Autodiscovery occurs when Django is loaded, during the `ready` hook of the `apps.py` file.

If you are using autodiscovery, keep a few points in mind:

- Avoid defining any logic on the module-level inside the `components` dir, that you would not want to run anyway.
- Components inside the auto-imported files still need to be registered with `@component.register()`
- Auto-imported component files must be valid Python modules, they must use suffix `.py`, and module name should follow [PEP-8](https://peps.python.org/pep-0008/#package-and-module-names).

Autodiscovery can be disabled via in the [settings](#disable-autodiscovery).

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
- `{% fill <name> %}`/`{% endfill %}`: (Used inside a `component` tag pair.) Fills a declared slot with the specified content.

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
    {% fill "body" %}Can you believe it's already <span>{{ date }}</span>??{% endfill %}
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

### Default slot

_Added in version 0.28_

As you can see, component slots lets you write reusable containers that you fill in when you use a component. This makes for highly reusable components that can be used in different circumstances.

It can become tedious to use `fill` tags everywhere, especially when you're using a component that declares only one slot. To make things easier, `slot` tags can be marked with an optional keyword: `default`. When added to the end of the tag (as shown below), this option lets you pass filling content directly in the body of a `component` tag pair – without using a `fill` tag. Choose carefully, though: a component template may contain at most one slot that is marked as `default`. The `default` option can be combined with other slot options, e.g. `required`.

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
    <div class="header">
        Calendar header
    </div>
    <div class="body">
        Can you believe it's already <span>2020-06-06</span>??
    </div>
</div>
```

You may be tempted to combine implicit fills with explicit `fill` tags. This will not work. The following component template will raise an error when compiled.

```htmldjango
{# DON'T DO THIS #}
{% component "calendar" date="2020-06-06" %}
    {% fill "header" %}Totally new header!{% endfill %}
    Can you believe it's already <span>{{ date }}</span>??
{% endcomponent %}
```

By contrast, it is permitted to use `fill` tags in nested components, e.g.:

```htmldjango
{% component "calendar" date="2020-06-06" %}
    {% component "beautiful-box" %}
        {% fill "content" %} Can you believe it's already <span>{{ date }}</span>?? {% endfill %}
    {% endcomponent %}
{% endcomponent %}
```

This is fine too:

```htmldjango
{% component "calendar" date="2020-06-06" %}
    {% fill "header" %}
        {% component "calendar-header" %}
            Super Special Calendar Header
        {% endcomponent %}
    {% endfill %}
{% endcomponent %}
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
For that, you must mark ONLY ONE of the identical slots.

We recommend to mark the first occurence for consistency, e.g.:

```htmldjango
<div class="calendar-component">
    <div class="header">
        {% slot "image" default required %}Image here{% endslot %}
    </div>
    <div class="body">
        {% slot "image" %}Image here{% endslot %}
    </div>
</div>
```

Which you can then use are regular default slot:

```htmldjango
{% component "calendar" date="2020-06-06" %}
    <img src="..." />
{% endcomponent %}
```

### Accessing original content of slots

_Added in version 0.26_

> NOTE: In version 0.77, the syntax was changed from
> ```django
> {% fill "my_slot" as "alias" %} {{ alias.default }}
> ```
> to
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

### Conditional slots

_Added in version 0.26._

> NOTE: In version 0.70, `{% if_filled %}` tags were replaced with `{{ component_vars.is_filled }}` variables. If your slot name contained special characters, see the section "Accessing slot names with special characters".

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
    <div class="title">
        Title
    </div>
    <div class="subtitle">
    </div>
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
    {% slot "subtitle" %}{% endslot %}
</div>
{% endif %}
```

#### Accessing `is_filled` of slot names with special characters

To be able to access a slot name via `component_vars.is_filled`, the slot name needs to be composed of only alphanumeric characters and underscores (e.g. `this__isvalid_123`).

However, you can still define slots with other special characters. In such case, the slot name in `component_vars.is_filled` is modified to replace all invalid characters into `_`.

So a slot named `"my super-slot :)"` will be available as `component_vars.is_filled.my_super_slot___`.

### Scoped slots

_Added in version 0.76_:

Consider a component with slot(s). This component may do some processing on the inputs, and then use the processed variable in the slot's default template:

```py
@component.register("my_comp")
class MyComp(component.Component):
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
@component.register("my_comp")
class MyComp(component.Component):
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
    {% fill "content" data="data" %}
        {{ data.input }}
    {% endfill %}
{% endcomponent %}
```

To access slot data on a default slot, you have to explictly define the `{% fill %}` tags.

So this works:

```django
{% component "my_comp" %}
    {% fill "content" data="data" %}
        {{ data.input }}
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

## Passing data to components

As seen above, you can pass arguments to components like so:

```django
<body>
    {% component "calendar" date="2015-06-19" %}
    {% endcomponent %}
</body>
```

### Special characters

_New in version 0.71_:

Keyword arguments can contain special characters `# @ . - _`, so keywords like
so are still valid:

```django
<body>
    {% component "calendar" my-date="2015-06-19" @click.native=do_something #some_id=True %}
    {% endcomponent %}
</body>
```

These can then be accessed inside `get_context_data` so:

```py
@component.register("calendar")
class Calendar(component.Component):
    # Since # . @ - are not valid identifiers, we have to
    # use `**kwargs` so the method can accept these args.
    def get_context_data(self, **kwargs):
        return {
            "date": kwargs["my-date"],
            "id": kwargs["#some_id"],
            "on_click": kwargs["@click.native"]
        }
```

### Pass dictonary by its key-value pairs

_New in version 0.74_:

Sometimes, a component may expect a dictionary as one of its inputs.

Most commonly, this happens when a component accepts a dictionary
of HTML attributes (usually called `attrs`) to pass to the underlying template.

In such cases, we may want to define some HTML attributes statically, and other dynamically.
But for that, we need to define this dictionary on Python side:

```py
@component.register("my_comp")
class MyComp(component.Component):
    template = """
        {% component "other" attrs=attrs %}
        {% endcomponent %}
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
@component.register("my_comp")
class MyComp(component.Component):
    template = """
        {% component "other"
            attrs:class="pa-4 flex"
            attrs:data-some-id=some_id
            attrs:@click.stop="onClickHandler"
        %}
        {% endcomponent %}
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
%}
{% endcomponent %}
```

> Note: It is NOT possible to define nested dictionaries, so
> `attrs:my_key:two=2` would be interpreted as:
>
> ```py
> {"attrs": {"my_key:two": 2}}
> ```

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
<div class="text-green">
</div>
```

### Boolean attributes

In HTML, boolean attributes are usually rendered with no value. Consider the example below where the first button is disabled and the second is not:

```html
<button disabled> Click me! </button>
<button> Click me! </button>
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
<div disabled>
</div>
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
<div data-value="my-class pa-4 some-class">
</div>
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
@component.register("my_comp")
class MyComp(component.Component):
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

@component.register("parent")
class Parent(component.Component):
    template: t.django_html = """
        {% component "my_comp"
            date=date
            attrs:class="pa-0 border-solid border-red"
            attrs:data-json=json_data
            attrs:@click="(e) => onClick(e, 'from_parent')"
        %}
        {% endcomponent %}
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
<div class="pa-4 text-red my-comp-date extra-class" data-id="123">
    ...
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
    {% component "child" %}  <--- Can access "my_data"
    {% endcomponent %}
{% endprovide %}

{% component "child" %}  <--- Cannot access "my_data"
{% endcomponent %}
```

Notice that the `provide` tag REQUIRES a name as a first argument. This is the _key_ by which we can then access the data passed to this tag.

`provide` tag _key_, similarly to the _name_ argument in `component` or `slot` tags, has these requirements:
- The _key_ must be a string literal
- It must be a valid identifier (AKA a valid Python variable name)

Once you've set the name, you define the data you want to "provide" by passing it as keyword arguments. This is similar to how you pass data to the `{% with %}` tag.

> NOTE: Kwargs passed to `{% provide %}` are NOT added to the context.
> In the example below, the `{{ key }}` won't render anything:
> ```django
> {% provide "my_data" key="hi" another=123 %}
>     {{ key }} 
> {% endprovide %}
> ```

### Using `inject()` method

To "inject" (access) the data defined on the `provide` tag, you can use the `inject()` method inside of `get_context_data()`.

For a component to be able to "inject" some data, the component (`{% component %}` tag) must be nested inside the `{% provide %}` tag.

In the example from previous section, we've defined two kwargs: `key="hi" another=123`. That means that if we now inject `"my_data"`, we get an object with 2 attributes - `key` and `another`.

```py
class ChildComponent(component.Component):
    def get_context_data(self):
        my_data = self.inject("my_data")
        print(my_data.key)     # hi
        print(my_data.another) # 123
        return {}
```

First argument to `inject` is the _key_ of the provided data. This
must match the string that you used in the `provide` tag. If no provider
with given key is found, `inject` raises a `KeyError`.

To avoid the error, you can pass a second argument to `inject` to which will act as a default value, similar to `dict.get(key, default)`:

```py
class ChildComponent(component.Component):
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
@component.register("child")
class ChildComponent(component.Component):
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
        {% component "child" %}
        {% endcomponent %}
    {% endprovide %}
"""
```

renders:

```html
<div> hi </div>
<div> 123 </div>
```

## Component context and scope

By default, context variables are passed down the template as in regular Django - deeper scopes can access the variables from the outer scopes. So if you have several nested forloops, then inside the deep-most loop you can access variables defined by all previous loops.

With this in mind, the `{% component %}` tag behaves similarly to `{% include %}` tag - inside the component tag, you can access all variables that were defined outside of it. 

And just like with `{% include %}`, if you don't want a specific component template to have access to the parent context, add `only` to the end of the `{% component %}` tag:

```htmldjango
{% component "calendar" date="2015-06-19" only %}{% endcomponent %}
```

NOTE: `{% csrf_token %}` tags need access to the top-level context, and they will not function properly if they are rendered in a component that is called with the `only` modifier.

If you find yourself using the `only` modifier often, you can set the [context_behavior](#context-behavior) option to `"isolated"`, which automatically applies the `only` modifier. This is useful if you want to make sure that components don't accidentally access the outer context.

Components can also access the outer context in their context methods like `get_context_data` by accessing the property `self.outer_context`.

## Defining HTML/JS/CSS files

django_component's management of files builds on top of [Django's `Media` class](https://docs.djangoproject.com/en/5.0/topics/forms/media/).

To be familiar with how Django handles static files, we recommend reading also:
- [How to manage static files (e.g. images, JavaScript, CSS)](https://docs.djangoproject.com/en/5.0/howto/static-files/)

### Defining file paths relative to component or static dirs

As seen in the [getting started example](#create-your-first-component), to associate HTML/JS/CSS
files with a component, you set them as `template_name`, `Media.js` and `Media.css` respectively:

```py
# In a file [project root]/components/calendar/calendar.py
from django_components import component

@component.register("calendar")
class Calendar(component.Component):
    template_name = "template.html"

    class Media:
        css = "style.css"
        js = "script.js"
```

In the example above, the files are defined relative to the directory where `component.py` is.

Alternatively, you can specify the file paths relative to the directories set in `STATICFILES_DIRS`.

Assuming that `STATICFILES_DIRS` contains path `[project root]/components`, we can rewrite the example as:

```py
# In a file [project root]/components/calendar/calendar.py
from django_components import component

@component.register("calendar")
class Calendar(component.Component):
    template_name = "calendar/template.html"

    class Media:
        css = "calendar/style.css"
        js = "calendar/script.js"
```

NOTE: In case of conflict, the preference goes to resolving the files relative to the component's directory.

### Defining multiple paths

Each component can have only a single template. However, you can define as many JS or CSS files as you want using a list.

```py
class MyComponent(component.Component):
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
class MyComponent(component.Component):
    class Media:
        css = {
            "all": "path/to/style1.css",
            "print": "path/to/style2.css",
        }
```

```py
class MyComponent(component.Component):
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

class SimpleComponent(component.Component):
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

Because of that, the paths defined as "safe" strings are NEVER resolved, neither relative to component's directory, nor relative to `STATICFILES_DIRS`.

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

@component.register("calendar")
class Calendar(component.Component):
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
from django_components import component

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

@component.register("calendar")
class Calendar(component.Component):
    template_name = "calendar/template.html"

    class Media:
        css = "calendar/style.css"
        js = "calendar/script.js"
    
    # Override the behavior of Media class
    media_class = MyMedia
```

NOTE: The instance of the `Media` class (or it's subclass) is available under `Component.media` after the class creation (`__new__`).

## Rendering JS/CSS dependencies

The JS and CSS files included in components are not automatically rendered.
Instead, use the following tags to specify where to render the dependencies:
- `component_dependencies` - Renders both JS and CSS
- `component_js_dependencies` - Renders only JS
- `component_css_dependencies` - Reneders only CSS

JS files are rendered as `<script>` tags.<br/>
CSS files are rendered as `<style>` tags.

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

Then, enable `RENDER_DEPENDENCIES` in setting.py:

```python
COMPONENTS = {
    "RENDER_DEPENDENCIES": True,
    # ... other component settings ...
}
```

## Available settings

All library settings are handled from a global `COMPONENTS` variable that is read from `settings.py`. By default you don't need it set, there are resonable defaults.

### Configure the module where components are loaded from

Configure the location where components are loaded. To do this, add a `COMPONENTS` variable to you `settings.py` with a list of python paths to load. This allows you to build a structure of components that are independent from your apps.

```python
COMPONENTS = {
    "libraries": [
        "mysite.components.forms",
        "mysite.components.buttons",
        "mysite.components.cards",
    ],
}
```

### Disable autodiscovery

If you specify all the component locations with the setting above and have a lot of apps, you can (very) slightly speed things up by disabling autodiscovery.

```python
COMPONENTS = {
    "autodiscover": False,
}
```

### Tune the template cache

Each time a template is rendered it is cached to a global in-memory cache (using Python's lru_cache decorator). This speeds up the next render of the component. As the same component is often used many times on the same page, these savings add up. By default the cache holds 128 component templates in memory, which should be enough for most sites. But if you have a lot of components, or if you are using the `template` method of a component to render lots of dynamic templates, you can increase this number. To remove the cache limit altogether and cache everything, set template_cache_size to `None`.

```python
COMPONENTS = {
    "template_cache_size": 256,
}
```

### Context behavior

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
class RootComp(component.Component):
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
class RootComp(component.Component):
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

## Community examples

One of our goals with `django-components` is to make it easy to share components between projects. If you have a set of components that you think would be useful to others, please open a pull request to add them to the list below.

- [django-htmx-components](https://github.com/iwanalabs/django-htmx-components): A set of components for use with [htmx](https://htmx.org/). Try out the [live demo](https://dhc.iwanalabs.com/).

## Running django-components project locally

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

## Development guides

- [Slot rendering flot](https://github.com/EmilStenstrom/django-components/blob/master/docs/slot_rendering.md)
