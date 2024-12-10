---
title: Defining HTML / JS / CSS files
weight: 8
---

django_component's management of files builds on top of [Django's `Media` class](https://docs.djangoproject.com/en/5.0/topics/forms/media/).

To be familiar with how Django handles static files, we recommend reading also:

- [How to manage static files (e.g. images, JavaScript, CSS)](https://docs.djangoproject.com/en/5.0/howto/static-files/)

## Defining file paths relative to component or static dirs

As seen in the [getting started example](#create-your-first-component), to associate HTML/JS/CSS
files with a component, you set them as `template_name`, `Media.js` and `Media.css` respectively:

```py
# In a file [project root]/components/calendar/calendar.py
from django_components import Component, register

@register("calendar")
class Calendar(Component):
    template_name = "template.html"

    class Media:
        css = "style.css"
        js = "script.js"
```

In the example above, the files are defined relative to the directory where `component.py` is.

Alternatively, you can specify the file paths relative to the directories set in `COMPONENTS.dirs` or `COMPONENTS.app_dirs`.

Assuming that `COMPONENTS.dirs` contains path `[project root]/components`, we can rewrite the example as:

```py
# In a file [project root]/components/calendar/calendar.py
from django_components import Component, register

@register("calendar")
class Calendar(Component):
    template_name = "calendar/template.html"

    class Media:
        css = "calendar/style.css"
        js = "calendar/script.js"
```

NOTE: In case of conflict, the preference goes to resolving the files relative to the component's directory.

## Defining multiple paths

Each component can have only a single template. However, you can define as many JS or CSS files as you want using a list.

```py
class MyComponent(Component):
    class Media:
        js = ["path/to/script1.js", "path/to/script2.js"]
        css = ["path/to/style1.css", "path/to/style2.css"]
```

## Configuring CSS Media Types

You can define which stylesheets will be associated with which
[CSS Media types](https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_media_queries/Using_media_queries#targeting_media_types). You do so by defining CSS files as a dictionary.

See the corresponding [Django Documentation](https://docs.djangoproject.com/en/5.0/topics/forms/media/#css).

Again, you can set either a single file or a list of files per media type:

```py
class MyComponent(Component):
    class Media:
        css = {
            "all": "path/to/style1.css",
            "print": "path/to/style2.css",
        }
```

```py
class MyComponent(Component):
    class Media:
        css = {
            "all": ["path/to/style1.css", "path/to/style2.css"],
            "print": ["path/to/style3.css", "path/to/style4.css"],
        }
```

NOTE: When you define CSS as a string or a list, the `all` media type is implied.

## Supported types for file paths

File paths can be any of:

- `str`
- `bytes`
- `PathLike` (`__fspath__` method)
- `SafeData` (`__html__` method)
- `Callable` that returns any of the above, evaluated at class creation (`__new__`)

```py
from pathlib import Path

from django.utils.safestring import mark_safe

class SimpleComponent(Component):
    class Media:
        css = [
            mark_safe('<link href="/static/calendar/style.css" rel="stylesheet" />'),
            Path("calendar/style1.css"),
            "calendar/style2.css",
            b"calendar/style3.css",
            lambda: "calendar/style4.css",
        ]
        js = [
            mark_safe('<script src="/static/calendar/script.js"></script>'),
            Path("calendar/script1.js"),
            "calendar/script2.js",
            b"calendar/script3.js",
            lambda: "calendar/script4.js",
        ]
```

## Path as objects

In the example [above](#supported-types-for-file-paths), you could see that when we used `mark_safe` to mark a string as a `SafeString`, we had to define the full `<script>`/`<link>` tag.

This is an extension of Django's [Paths as objects](https://docs.djangoproject.com/en/5.0/topics/forms/media/#paths-as-objects) feature, where "safe" strings are taken as is, and accessed only at render time.

Because of that, the paths defined as "safe" strings are NEVER resolved, neither relative to component's directory, nor relative to `COMPONENTS.dirs`.

"Safe" strings can be used to lazily resolve a path, or to customize the `<script>` or `<link>` tag for individual paths:

```py
class LazyJsPath:
    def __init__(self, static_path: str) -> None:
        self.static_path = static_path

    def __html__(self):
        full_path = static(self.static_path)
        return format_html(
            f'<script type="module" src="{full_path}"></script>'
        )

@register("calendar")
class Calendar(Component):
    template_name = "calendar/template.html"

    def get_context_data(self, date):
        return {
            "date": date,
        }

    class Media:
        css = "calendar/style.css"
        js = [
            # <script> tag constructed by Media class
            "calendar/script1.js",
            # Custom <script> tag
            LazyJsPath("calendar/script2.js"),
        ]
```

## Customize how paths are rendered into HTML tags with `media_class`

Sometimes you may need to change how all CSS `<link>` or JS `<script>` tags are rendered for a given component. You can achieve this by providing your own subclass of [Django's `Media` class](https://docs.djangoproject.com/en/5.0/topics/forms/media) to component's `media_class` attribute.

Normally, the JS and CSS paths are passed to `Media` class, which decides how the paths are resolved and how the `<link>` and `<script>` tags are constructed.

To change how the tags are constructed, you can override the [`Media.render_js` and `Media.render_css` methods](https://github.com/django/django/blob/fa7848146738a9fe1d415ee4808664e54739eeb7/django/forms/widgets.py#L102):

```py
from django.forms.widgets import Media
from django_components import Component, register

class MyMedia(Media):
    # Same as original Media.render_js, except
    # the `<script>` tag has also `type="module"`
    def render_js(self):
        tags = []
        for path in self._js:
            if hasattr(path, "__html__"):
                tag = path.__html__()
            else:
                tag = format_html(
                    '<script type="module" src="{}"></script>',
                    self.absolute_path(path)
                )
        return tags

@register("calendar")
class Calendar(Component):
    template_name = "calendar/template.html"

    class Media:
        css = "calendar/style.css"
        js = "calendar/script.js"

    # Override the behavior of Media class
    media_class = MyMedia
```

NOTE: The instance of the `Media` class (or it's subclass) is available under `Component.media` after the class creation (`__new__`).
