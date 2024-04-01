
# Using slots in templates

_New in version 0.26_:

- The `slot` tag now serves only to declare new slots inside the component template.
  - To override the content of a declared slot, use the newly introduced `fill` tag instead.
- Whereas unfilled slots used to raise a warning, filling a slot is now optional by default.
  - To indicate that a slot must be filled, the new `required` option should be added at the end of the `slot` tag.

---

Components support something called 'slots'.
When a component is used inside another template, slots allow the parent template to override specific parts of the child component by passing in different content.
This mechanism makes components more reusable and composable.

In the example below we introduce two block tags that work hand in hand to make this work. These are...

- `{% slot <name> %}`/`{% endslot %}`: Declares a new slot in the component template.
- `{% fill <name> %}`/`{% endfill %}`: (Used inside a `component` tag pair.) Fills a declared slot with the specified content.

Let's update our calendar component to support more customization. We'll add `slot` tag pairs to its template, _calendar.html_.

```htmldjango
<div class="calendar-component">
    <div class="header">
        {% slot "header" %}Calendar header{% endslot %}
    </div>
    <div class="body">
        {% slot "body" %}Today's date is <span>{{ date }}</span>{% endslot %}
    </div>
</div>
```

When using the component, you specify which slots you want to fill and where you want to use the defaults from the template. It looks like this:

```htmldjango
{% component "calendar" date="2020-06-06" %}
    {% fill "body" %}Can you believe it's already <span>{{ date }}</span>??{% endfill %}
{% endcomponent %}
```

Since the header block is unspecified, it's taken from the base template. If you put this in a template, and pass in `date=2020-06-06`, this is what gets rendered:

```htmldjango
<div class="calendar-component">
    <div class="header">
        Calendar header
    </div>
    <div class="body">
        Can you believe it's already <span>2020-06-06</span>??
    </div>
</div>
```

As you can see, component slots lets you write reusable containers that you fill in when you use a component. This makes for highly reusable components that can be used in different circumstances.

It can become tedious to use `fill` tags everywhere, especially when you're using a component that declares only one slot. To make things easier, `slot` tags can be marked with an optional keyword: `default`. When added to the end of the tag (as shown below), this option lets you pass filling content directly in the body of a `component` tag pair – without using a `fill` tag. Choose carefully, though: a component template may contain at most one slot that is marked as `default`. The `default` option can be combined with other slot options, e.g. `required`.

Here's the same example as before, except with default slots and implicit filling.

The template:

```htmldjango
<div class="calendar-component">
    <div class="header">
        {% slot "header" %}Calendar header{% endslot %}
    </div>
    <div class="body">
        {% slot "body" default %}Today's date is <span>{{ date }}</span>{% endslot %}
    </div>
</div>
```

Including the component (notice how the `fill` tag is omitted):

```htmldjango
{% component "calendar" date="2020-06-06" %}
    Can you believe it's already <span>{{ date }}</span>??
{% endcomponent %}
```

The rendered result (exactly the same as before):

```html
<div class="calendar-component">
    <div class="header">
        Calendar header
    </div>
    <div class="body">
        Can you believe it's already <span>2020-06-06</span>??
    </div>
</div>
```

You may be tempted to combine implicit fills with explicit `fill` tags. This will not work. The following component template will raise an error when compiled.

```htmldjango
{# DON'T DO THIS #}
{% component "calendar" date="2020-06-06" %}
    {% fill "header" %}Totally new header!{% endfill %}
    Can you believe it's already <span>{{ date }}</span>??
{% endcomponent %}
```

By contrast, it is permitted to use `fill` tags in nested components, e.g.:

```htmldjango
{% component "calendar" date="2020-06-06" %}
    {% component "beautiful-box" %}
        {% fill "content" %} Can you believe it's already <span>{{ date }}</span>?? {% endfill %}
    {% endcomponent %}
{% endcomponent %}
```

This is fine too:

```htmldjango
{% component "calendar" date="2020-06-06" %}
    {% fill "header" %}
        {% component "calendar-header" %}
            Super Special Calendar Header
        {% endcomponent %}
    {% endfill %}
{% endcomponent %}
```

## Components as views

_New in version 0.34_

Components can now be used as views. To do this, [`Component`][django_components.component.Component] subclasses Django's [`View`][] class. This means that you can use all of the [methods](https://docs.djangoproject.com/en/5.0/ref/class-based-views/base/#view) of `View` in your component. For example, you can override `get` and `post` to handle GET and POST requests, respectively.

In addition, [`Component`][django_components.component.Component] now has a [`render_to_response`][django_components.component.Component.render_to_response] method that renders the component template based on the provided context and slots' data and returns an [`HttpResponse`][django.http.HttpResponse] object.

Here's an example of a calendar component defined as a view:

```python title="[project root]/components/calendar.py"
from django_components import component

@component.register("calendar")
class Calendar(component.Component):

    template = """
        <div class="calendar-component">
            <div class="header">
                {% slot "header" %}{% endslot %}
            </div>
            <div class="body">
                Today's date is <span>{{ date }}</span>
            </div>
        </div>
    """

    def get(self, request, *args, **kwargs):
        context = {
            "date": request.GET.get("date", "2020-06-06"),
        }
        slots = {
            "header": "Calendar header",
        }
        return self.render_to_response(context, slots)
```

Then, to use this component as a view, you should create a `urls.py` file in your components directory, and add a path to the component's view:

```python title="[project root]/components/urls.py"
from django.urls import path
from calendar import Calendar

urlpatterns = [
    path("calendar/", Calendar.as_view()),
]
```

Remember to add `__init__.py` to your components directory, so that Django can find the `urls.py` file.

Finally, include the component's urls in your project's `urls.py` file:

```python title="[project root]/urls.py"
from django.urls import include, path

urlpatterns = [
    path("components/", include("components.urls")),
]
```

Note: slots content are automatically escaped by default to prevent XSS attacks. To disable escaping, set `escape_slots_content=False` in the `render_to_response` method. If you do so, you should make sure that any content you pass to the slots is safe, especially if it comes from user input.

If you're planning on passing an HTML string, check Django's use of [`format_html`](https://docs.djangoproject.com/en/5.0/ref/utils/#django.utils.html.format_html) and [`mark_safe`](https://docs.djangoproject.com/en/5.0/ref/utils/#django.utils.safestring.mark_safe).
