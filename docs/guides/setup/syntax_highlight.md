---
title: Syntax highlighting
---

## VSCode

1. First install [Python Inline Source Syntax Highlighting](https://marketplace.visualstudio.com/items?itemName=samwillis.python-inline-source) extension, it will give you syntax highlighting for the template, CSS, and JS.

2. Next, in your component, set typings of `Component.template/css/js` to `types.django_html`, `types.css`, and `types.js` respectively. The extension will recognize these and will activate syntax highlighting.

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

## Pycharm (or other Jetbrains IDEs)

With PyCharm (or any other editor from Jetbrains), you don't need to use `types.django_html`, `types.css`, `types.js` since Pycharm uses [language injections](https://www.jetbrains.com/help/pycharm/using-language-injections.html).
You only need to write the comments `# language=<lang>` above the variables.

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
