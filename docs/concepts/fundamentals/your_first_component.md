---
title: Create your first component
weight: 1
---

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

```python title="[project root]/components/calendar/calendar.py"
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
