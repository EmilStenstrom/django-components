---
title: Welcome to Django Components
weight: 1
---

<img src="https://raw.githubusercontent.com/django-components/django-components/master/logo/logo-black-on-white.svg" alt="django-components" style="max-width: 100%; background: white; color: black;">

[![PyPI - Version](https://img.shields.io/pypi/v/django-components)](https://pypi.org/project/django-components/) [![PyPI - Python Version](https://img.shields.io/pypi/pyversions/django-components)](https://pypi.org/project/django-components/) [![PyPI - License](https://img.shields.io/pypi/l/django-components)](https://github.com/django-components/django-components/blob/master/LICENSE/) [![PyPI - Downloads](https://img.shields.io/pypi/dm/django-components)](https://pypistats.org/packages/django-components) [![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/django-components/django-components/tests.yml)](https://github.com/django-components/django-components/actions/workflows/tests.yml)

`django-components` combines Django's templating system with the modularity seen
in modern frontend frameworks like Vue or React.

With `django-components` you can support Django projects small and large without leaving the Django ecosystem.

## Features

### Modern and modular UI

- Create self-contained, reusable UI elements.
- Each component can include its own HTML, CSS, and JS, or additional third-party JS and CSS.
- HTML, CSS, and JS can be defined on the component class, or loaded from files.

```python
from django_components import Component

@register("calendar")
class Calendar(Component):
    template = """
        <div class="calendar">
            Today's date is
            <span>{{ date }}</span>
        </div>
    """

    css = """
        .calendar {
            width: 200px;
            background: pink;
        }
    """

    js = """
        document.querySelector(".calendar")
            .addEventListener("click", () => {
                alert("Clicked calendar!");
            });
    """

    # Additional JS and CSS
    class Media:
        js = ["https://cdn.jsdelivr.net/npm/htmx.org@2.1.1/dist/htmx.min.js"]
        css = ["bootstrap/dist/css/bootstrap.min.css"]

    # Variables available in the template
    def get_context_data(self, date):
        return {
            "date": date
        }
```

### Composition with slots

- Render components inside templates with `{% component %}` tag.
- Compose them with `{% slot %}` and `{% fill %}` tags.
- Vue-like slot system, including scoped slots.

```htmldjango
{% component "Layout"
    bookmarks=bookmarks
    breadcrumbs=breadcrumbs
%}
    {% fill "header" %}
        <div class="flex justify-between gap-x-12">
            <div class="prose">
                <h3>{{ project.name }}</h3>
            </div>
            <div class="font-semibold text-gray-500">
                {{ project.start_date }} - {{ project.end_date }}
            </div>
        </div>
    {% endfill %}

    {# Access data passed to `{% slot %}` with `data` #}
    {% fill "tabs" data="tabs_data" %}
        {% component "TabItem" header="Project Info" %}
            {% component "ProjectInfo"
                project=project
                project_tags=project_tags
                attrs:class="py-5"
                attrs:width=tabs_data.width
            / %}
        {% endcomponent %}
    {% endfill %}
{% endcomponent %}
```

### Extended template tags

`django-components` extends Django's template tags syntax with:

- Literal lists and dictionaries in template tags
- Self-closing tags `{% mytag / %}`
- Multi-line template tags
- Spread operator `...` to dynamically pass args or kwargs into the template tag
- Nested template tags like `"{{ first_name }} {{ last_name }}"`
- Flat definition of dictionary keys `attr:key=val`

```htmldjango
{% component "table"
    ...default_attrs
    title="Friend list for {{ user.name }}"
    headers=["Name", "Age", "Email"]
    data=[
        {
            "name": "John"|upper,
            "age": 30|add:1,
            "email": "john@example.com",
            "hobbies": ["reading"],
        },
        {
            "name": "Jane"|upper,
            "age": 25|add:1,
            "email": "jane@example.com",
            "hobbies": ["reading", "coding"],
        },
    ],
    attrs:class="py-4 ma-2 border-2 border-gray-300 rounded-md"
/ %}
```

### HTML fragment support

`django-components` makes intergration with HTMX, AlpineJS or jQuery easy by allowing components to be rendered as HTML fragments:

- Components's JS and CSS is loaded automatically when the fragment is inserted into the DOM

- Expose components as views with `get`, `post`, `put`, `patch`, `delete` methods

```py
# components/calendar/calendar.py
@register("calendar")
class Calendar(Component):
    template_file = "calendar.html"

    def get(self, request, *args, **kwargs):
        page = request.GET.get("page", 1)
        return self.render_to_response(
            kwargs={
                "page": page,
            }
        )

    def get_context_data(self, page):
        return {
            "page": page,
        }

# urls.py
path("calendar/", Calendar.as_view()),
```

### Type hints

Opt-in to type hints by defining types for component's args, kwargs, slots, and more:

```py
from typing import NotRequired, Tuple, TypedDict, SlotContent, SlotFunc

ButtonArgs = Tuple[int, str]

class ButtonKwargs(TypedDict):
    variable: str
    another: int
    maybe_var: NotRequired[int] # May be omitted

class ButtonData(TypedDict):
    variable: str

class ButtonSlots(TypedDict):
    my_slot: NotRequired[SlotFunc]
    another_slot: SlotContent

ButtonType = Component[ButtonArgs, ButtonKwargs, ButtonSlots, ButtonData, JsData, CssData]

class Button(ButtonType):
    def get_context_data(self, *args, **kwargs):
        self.input.args[0]  # int
        self.input.kwargs["variable"]  # str
        self.input.slots["my_slot"]  # SlotFunc[MySlotData]

        return {}  # Error: Key "variable" is missing
```

When you then call `Button.render()` or `Button.render_to_response()`, you will get type hints:

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

### Debugging features

- **Visual component inspection**: Highlight components and slots directly in your browser.
- **Detailed tracing logs to supply AI-agents with context**: The logs include component and slot names and IDs, and their position in the tree.

<div style="text-align: center;">
<img src="https://github.com/django-components/django-components/blob/master/docs/images/debug-highlight-slots.png?raw=true" alt="Component debugging visualization showing slot highlighting" width="500" style="margin: auto;">
</div>

### Sharing components

- Install and use third-party components from PyPI
- Or publish your own "component registry"
- Highly customizable - Choose how the components are called in the template (and more):

    ```htmldjango
    {% component "calendar" date="2024-11-06" %}
    {% endcomponent %}

    {% calendar date="2024-11-06" %}
    {% endcalendar %}
    ```

### Other features

- Vue-like provide / inject system
- Format HTML attributes with `{% html_attrs %}`

## Quickstart

A component in django-components can be as simple as a Django template and Python code to declare the component:

```htmldjango title="components/calendar/calendar.html"
<div class="calendar">
  Today's date is <span>{{ date }}</span>
</div>
```

```py title="components/calendar/calendar.py"
from django_components import Component

class Calendar(Component):
    template_file = "calendar.html"
```

Or a combination of Django template, Python, CSS, and Javascript:

```htmldjango title="components/calendar/calendar.html"
<div class="calendar">
  Today's date is <span>{{ date }}</span>
</div>
```

```css title="components/calendar/calendar.css"
.calendar {
  width: 200px;
  background: pink;
}
```

```js title="components/calendar/calendar.js"
document.querySelector(".calendar").onclick = function () {
  alert("Clicked calendar!");
};
```

```py title="components/calendar/calendar.py"
from django_components import Component

class Calendar(Component):
    template_file = "calendar.html"
    js_file = "calendar.js"
    css_file = "calendar.css"

    def get_context_data(self, date):
        return {"date": date}
```

Use the component like this:

```htmldjango
{% component "calendar" date="2024-11-06" %}{% endcomponent %}
```

And this is what gets rendered:

```html
<div class="calendar-component">
  Today's date is <span>2024-11-06</span>
</div>
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
