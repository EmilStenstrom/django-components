# django-components
<a href="https://travis-ci.org/EmilStenstrom/django-components"><img align="right" src="https://travis-ci.org/EmilStenstrom/django-components.svg?branch=master"></a>
A way to create simple reusable template components in Django.

# Installation

Install the app into your environment:

> ```pip install git+https://github.com/EmilStenstrom/django-components.git#egg=django_components```

Then add the app into INSTALLED APPS in settings.py

```
INSTALLED_APPS = [
    ...,
    "django_components",
    ...
]
```

## Optional

To avoid loading the app in each template using ``` {% load django_components %} ```, you can add the tag as a 'builtin' in settings.py

```
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

# Create your first component

A component in django-components is the combination of four things: CSS, Javascript, a Django template, and some Python code to put them all together.

First you need a CSS file. Be sure to prefix all rules with a unique class so they don't clash with other rules.

```css
/* In a file called style.css */
.calendar-component { width: 200px; background: pink; }
.calendar-component span { font-weight: bold; }
```

Then you need a javascript file that specifies how you interact with this component. You are free to use any javascript framework you want. A good way to make sure this component doesn't clash with other components is to define all code inside an anonymous function that calls itself. This makes all variables defined only be defined inside this component and not affect other components.

```js
/* In a file called script.js */
(function(){
    $(".calendar-component").click(function(){ alert("Clicked calendar!"); })
})()
```

Now you need a Django template for your component. Feel free to define more variables like `date` in this example. When creating an instance of this component we will send in the values for these variables. The template will be rendered with whatever template backend you've specified in your Django settings file.

```htmldjango
{# In a file called template.html #}
<div class="calendar-component">Today's date is <span>{{ date }}</span></div>
```

Finally, we use django-components to tie this together. We create a Component by inheriting from the Component class and specifying the context method. We also register the global component registry so that we easily can render it anywhere in our templates.

```python
from django_components import component

class Calendar(component.Component):
    def context(self, date):
        return {
            "date": date,
        }

    class Media:
        template = "[your app]/components/calendar/calendar.html"
        css = {'all': ('[your app]/components/calendar/calendar.css',)}
        js = ('[your app]/components/calendar/calendar.js',)

component.registry.register(name="calendar", component=Calendar)
```

And voilá! We've created our first component.

# Use the component in a template

First load the `django_components` tag library, then use the `component_dependencies` and `component` tags to render the component to the page.

```htmldjango
{% load django_components %}
<!DOCTYPE html>
<html>
<head>
    <title>My example calendar</title>
    {% component_dependencies %}
</head>
<body>
    {% component name="calendar" date="2015-06-19" %}
</body>
<html>
```

The output from the above template will be:

```html
<!DOCTYPE html>
<html>
<head>
    <title>My example calendar</title>
    <link href="style.css" type="text/css" media="all" rel="stylesheet" />
    <script type="text/javascript" src="script.js"></script>
</head>
<body>
    <div class="calendar-component">Today's date is <span>2015-06-19</span></div>
</body>
<html>
```

This makes it possible to organize your front-end around reusable components. Instead of relying on template tags and keeping your CSS and Javascript in the static directory.

# Running the tests

Install `tox`:

```sh
pip install tox
```

Then run all the tests over all Python versions:

```sh
tox
```

Or just the particular version you wish to test:

```sh
tox -e py34
```

You can also have it watch the directory for changes and re-run the tests:

```sh
tox -e py34 -- -f
```
