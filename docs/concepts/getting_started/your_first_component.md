---
title: Create your first component
weight: 1
---

A component in django-components can be as simple as a Django template and Python code to declare the component:

```py
from django_components import Component

class Calendar(Component):
    template = """
      <div class="calendar">
        Today's date is <span>{{ date }}</span>
      </div>
    """
```

Or a combination of Django template, Python, CSS, and Javascript:

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

!!! note

    With django-components, you can "inline" the HTML, JS and CSS code into the Python class,
    as seen above.

    You can set up [syntax highlighting](../../guides/setup/syntax_highlight.md),
    but autocompletion / intellisense does not yet work.

    So, in the example below we define the Django template in a separate file, `calendar.html`,
    to allow our IDEs to interpret the file as HTML / Django file.


We'll start by creating a component that defines only a Django template:

### 1. Create project structure

Start by creating empty `calendar.py` and `calendar.html` files:

```
sampleproject/
├── calendarapp/
├── components/             🆕
│   └── calendar/           🆕
│       ├── calendar.py     🆕
│       └── calendar.html   🆕
├── sampleproject/
├── manage.py
└── requirements.txt
```

### 2. Write Django template

Inside `calendar.html`, write:

```htmldjango title="[project root]/components/calendar/calendar.html"
<div class="calendar">
  Today's date is <span>{{ date }}</span>
</div>
```

In this example we've defined one template variable `date`. You can use any and as many variables as you like. These variables will be
defined in the Python file in [`get_context_data()`](../../../reference/api#django_components.Component.get_context_data)
when creating an instance of this component.

!!! note

    The template will be rendered with whatever template backend you've specified in your Django settings file.

    Currently django-components supports only the default `"django.template.backends.django.DjangoTemplates"` template backend!

### 3. Create new Component in Python

In `calendar.py`, create a subclass of [Component](../../../reference/api#django_components.Component)
to create a new component.

To link the HTML template with our component, set [`template_name`](../../../reference/api#django_components.Component.template_name)
to the name of the HTML file.

```python title="[project root]/components/calendar/calendar.py"
from django_components import Component

class Calendar(Component):
    template_name = "calendar.html"
```

!!! note

    The path to the template file can be either:

    1. Relative to the component's python file (as seen above),
    2. Relative to any of the component directories as defined by
    [`COMPONENTS.dirs`](../../reference/settings.md#django_components.app_settings.ComponentsSettings.dirs)
    and/or [`COMPONENTS.app_dirs`](../../reference/settings.md#django_components.app_settings.ComponentsSettings.app_dirs)
    (e.g. `[your apps]/components` dir and `[project root]/components`)

### 4. Define the template variables

In `calendar.html`, we've used the variable `date`. So we need to define it for the template to work.

This is done using [`Component.get_context_data()`](../../../reference/api#django_components.Component.get_context_data).
It's a function that returns a dictionary. The entries in this dictionary
will become available within the template as variables, e.g. as `{{ date }}`.

```python title="[project root]/components/calendar/calendar.py"
from django_components import Component

class Calendar(Component):
    template_name = "calendar.html"

    def get_context_data(self):
        return {
            "date": "1970-01-01",
        }
```

Now, when we render the component with [`Component.render()`](../../../reference/api#django_components.Component.render)
method:

```py
Calendar.render()
```

It will output

```html
<div class="calendar">
  Today's date is <span>1970-01-01</span>
</div>
```

And voilá!! We've created our first component.

Next, [let's add JS and CSS to this component ➡️](./adding_js_and_css.md).
