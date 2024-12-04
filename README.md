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

## Release notes

Read the [Release Notes](https://github.com/EmilStenstrom/django-components/tree/master/CHANGELOG.md)
to see the latest features and fixes.

## Community examples

One of our goals with `django-components` is to make it easy to share components between projects. If you have a set of components that you think would be useful to others, please open a pull request to add them to the list below.

- [django-htmx-components](https://github.com/iwanalabs/django-htmx-components): A set of components for use with [htmx](https://htmx.org/). Try out the [live demo](https://dhc.iwanalabs.com/).

## Contributing and development

Get involved or sponsor this project - [See here](https://emilstenstrom.github.io/django-components/dev/overview/contributing/)

Running django-components locally for development - [See here](https://emilstenstrom.github.io/django-components/dev/overview/development/)
