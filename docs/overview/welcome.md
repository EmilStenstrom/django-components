---
title: Welcome to Django Components
weight: 1
---

<img src="https://raw.githubusercontent.com/django-components/django-components/master/logo/logo-black-on-white.svg" alt="django-components" style="max-width: 100%; background: white; color: black;">

[![PyPI - Version](https://img.shields.io/pypi/v/django-components)](https://pypi.org/project/django-components/) [![PyPI - Python Version](https://img.shields.io/pypi/pyversions/django-components)](https://pypi.org/project/django-components/) [![PyPI - License](https://img.shields.io/pypi/l/django-components)](https://github.com/django-components/django-components/blob/master/LICENSE/) [![PyPI - Downloads](https://img.shields.io/pypi/dm/django-components)](https://pypistats.org/packages/django-components) [![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/django-components/django-components/tests.yml)](https://github.com/django-components/django-components/actions/workflows/tests.yml)

django-components introduces component-based architecture to Django's server-side rendering.
It combines Django's templating system with the modularity seen in modern frontend frameworks like Vue or React.

A component in django-components can be as simple as a Django template and Python code to declare the component:

```htmldjango title="calendar.html"
<div class="calendar">
  Today's date is <span>{{ date }}</span>
</div>
```

```py title="calendar.py"
from django_components import Component

class Calendar(Component):
    template_file = "calendar.html"
```

Or a combination of Django template, Python, CSS, and Javascript:

```htmldjango title="calendar.html"
<div class="calendar">
  Today's date is <span>{{ date }}</span>
</div>
```

```css title="calendar.css"
.calendar {
  width: 200px;
  background: pink;
}
```

```js title="calendar.js"
document.querySelector(".calendar").onclick = function () {
  alert("Clicked calendar!");
};
```

```py title="calendar.py"
from django_components import Component

class Calendar(Component):
    template_file = "calendar.html"
    js_file = "calendar.js"
    css_file = "calendar.css"
```

Alternatively, you can "inline" HTML, JS, and CSS right into the component class:

```py
from django_components import Component

class Calendar(Component):
    template = """
      <div class="calendar">
        Today's date is <span>{{ date }}</span>
      </div>
    """

    css = """
      .calendar {
        width: 200px;
        background: pink;
      }
    """

    js = """
      document.querySelector(".calendar").onclick = function () {
        alert("Clicked calendar!");
      };
    """
```

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

### Debugging features

- **Visual component inspection**: Highlight components and slots directly in your browser.
- **Detailed tracing logs to supply AI-agents with context**: The logs include component and slot names and IDs, and their position in the tree.

<div style="text-align: center;">
<img src="https://github.com/django-components/django-components/blob/master/docs/images/debug-highlight-slots.png?raw=true" alt="Component debugging visualization showing slot highlighting" width="500" style="margin: auto;">
</div>

## Quickstart

django-components lets you create reusable blocks of code needed to generate the front end code you need for a modern app.

Define a component in `components/calendar/calendar.py` like this:

```python
@register("calendar")
class Calendar(Component):
    template_file = "template.html"

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

(If you instead prefer to jump right into the code, [check out the example project](https://github.com/django-components/django-components/tree/master/sampleproject))

## Release notes

Read the [Release Notes](../release_notes.md)
to see the latest features and fixes.

## Community examples

One of our goals with `django-components` is to make it easy to share components between projects. Head over to the [Community examples](./community.md#community-examples) to see some examples.

## Contributing and development

Get involved or sponsor this project - [See here](./contributing.md)

Running django-components locally for development - [See here](./development.md)
