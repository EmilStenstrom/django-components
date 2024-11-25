---
title: Syntax highlighting
---

## VSCode

Note, in the above example, that the `t.django_html`, `t.css`, and `t.js` types are used to specify the type of the template, CSS, and JS files, respectively. This is not necessary, but if you're using VSCode with the [Python Inline Source Syntax Highlighting](https://marketplace.visualstudio.com/items?itemName=samwillis.python-inline-source) extension, it will give you syntax highlighting for the template, CSS, and JS.

## Pycharm (or other Jetbrains IDEs)

If you're a Pycharm user (or any other editor from Jetbrains), you can have coding assistance as well:

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

You don't need to use `types.django_html`, `types.css`, `types.js` since Pycharm uses [language injections](https://www.jetbrains.com/help/pycharm/using-language-injections.html).
You only need to write the comments `# language=<lang>` above the variables.
