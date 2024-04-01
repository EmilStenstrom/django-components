# Installation

Install the app into your environment:

=== "pip"

    ```bash
    pip install django-components
    ```

=== "poetry"

    ```bash
    poetry add django-components
    ```

=== "pdm"

    ```bash
    pdm add django-components
    ```

Then add the app into [`INSTALLED_APPS`][INSTALLED_APPS] in your settings module (e.g. `settings.py`)

```python
INSTALLED_APPS = [
    ...,
    'django_components',
]
```

Modify [`TEMPLATES`][TEMPLATES] section of your settings module as follows:


- *Remove `'APP_DIRS': True,`*
- add `loaders` to [`OPTIONS`][TEMPLATES-OPTIONS] list and set it to following value:

```python
TEMPLATES = [
    {
        ...,
        'OPTIONS': {
            'context_processors': [
                ...
            ],
            'loaders':[(
                'django.template.loaders.cached.Loader', [
                    'django.template.loaders.filesystem.Loader',
                    'django.template.loaders.app_directories.Loader',
                    'django_components.template_loader.Loader',
                ]
            )],
        },
    },
]
```

Modify [`STATICFILES_DIRS`][STATICFILES_DIRS] (or add it if you don't have it) so django can find your static JS and CSS files:

```python
STATICFILES_DIRS = [
    ...,
    os.path.join(BASE_DIR, "components"),
]
```

## _Optional_: Load django-components in all templates

To avoid loading the app in each template using ``` {% load django_components %} ```, you can add the tag as a 'builtin' in settings.py

```python
TEMPLATES = [
    {
        ...,
        'OPTIONS': {
            'context_processors': [
                ...
            ],
            'builtins': [
                'django_components.templatetags.component_tags',
            ]
        },
    },
]
```

Read on to find out how to build your first component!
