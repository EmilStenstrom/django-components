
# Use the component in a template

First load the [`component_tags`][django_components.templatetags.component_tags] tag library, then use the `component_[js/css]_dependencies` and [`component`][django_components.templatetags.component_tags.do_component] tags to render the component to the page.

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

The output from the above template will be:

```html
<!DOCTYPE html>
<html>
<head>
    <title>My example calendar</title>
    <link href="style.css" type="text/css" media="all" rel="stylesheet">
</head>
<body>
    <div class="calendar-component">Today's date is <span>2015-06-19</span></div>
    <script src="script.js"></script>
</body>
<html>
```

This makes it possible to organize your front-end around reusable components. Instead of relying on template tags and keeping your CSS and Javascript in the static directory.
