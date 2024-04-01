# Using single-file components

Components can also be defined in a single file, which is useful for small components. To do this, you can use the `template`, `js`, and `css` class attributes instead of the `template_name` and `Media`. For example, here's the calendar component from above, defined in a single file:

```python title="[project root]/components/calendar.py"
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
