---
title: Single-file components
weight: 1
---

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
