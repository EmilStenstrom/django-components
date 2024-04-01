
# Security notes 🚨

*You are advised to read this section before using django-components in production.*

### Static files

Components can be organized however you prefer.
That said, our prefered way is to keep the files of a component close together by bundling them in the same directory.
This means that files containing backend logic, such as Python modules and HTML templates, live in the same directory as static files, e.g. JS and CSS.

If your are using [`django.contrib.staticfiles`][] to collect static files, no distinction is made between the different kinds of files.
As a result, your Python code and templates may inadvertently become available on your static file server.
You probably don't want this, as parts of your backend logic will be exposed, posing a __potential security vulnerability__.

As of *v0.27*, django-components ships with an additional installable app *[`django_components.safer_staticfiles`][]*.
It is a drop-in replacement for *[`django.contrib.staticfiles`][]*.
Its behavior is 100% identical except it ignores .py and .html files, meaning these will not end up on your static files server.
To use it, add it to [`INSTALLED_APPS`][] and remove [`django.contrib.staticfiles`].

```python
INSTALLED_APPS = [
    # 'django.contrib.staticfiles',   # <-- REMOVE
    'django_components',
    'django_components.safer_staticfiles'  # <-- ADD
]
```

If you are on an older version of django-components, your alternatives are a) passing `--ignore <pattern>` options to the _collecstatic_ CLI command, or b) defining a subclass of `StaticFilesConfig`.
Both routes are described in the official [docs of the _staticfiles_ app](https://docs.djangoproject.com/en/4.2/ref/contrib/staticfiles/#customizing-the-ignored-pattern-list).
