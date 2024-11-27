---
title: Components in templates
weight: 3
---

First load the `component_tags` tag library, then use the `component_[js/css]_dependencies` and `component` tags to render the component to the page.

```htmldjango
{% load component_tags %}
<!DOCTYPE html>
<html>
<head>
    <title>My example calendar</title>
    {% component_css_dependencies %}
</head>
<body>
    {% component "calendar" date="2015-06-19" %}{% endcomponent %}
    {% component_js_dependencies %}
</body>
<html>
```

> NOTE: Instead of writing `{% endcomponent %}` at the end, you can use a self-closing tag:
>
> `{% component "calendar" date="2015-06-19" / %}`

The output from the above template will be:

```html
<!DOCTYPE html>
<html>
  <head>
    <title>My example calendar</title>
    <link
      href="/static/calendar/style.css"
      type="text/css"
      media="all"
      rel="stylesheet"
    />
  </head>
  <body>
    <div class="calendar-component">
      Today's date is <span>2015-06-19</span>
    </div>
    <script src="/static/calendar/script.js"></script>
  </body>
  <html></html>
</html>
```

This makes it possible to organize your front-end around reusable components. Instead of relying on template tags and keeping your CSS and Javascript in the static directory.
