# Setting Up `ComponentDependencyMiddleware`

[`ComponentDependencyMiddleware`][django_components.middleware.ComponentDependencyMiddleware] is a Django middleware designed to manage and inject CSS/JS dependencies for rendered components dynamically. It ensures that only the necessary stylesheets and scripts are loaded in your HTML responses, based on the components used in your Django templates.

To set it up, add the middleware to your [`MIDDLEWARE`][] in settings.py:

```python
MIDDLEWARE = [
    # ... other middleware classes ...
    'django_components.middleware.ComponentDependencyMiddleware'
    # ... other middleware classes ...
]
```

Then, enable `RENDER_DEPENDENCIES` in setting.py:

```python
COMPONENTS = {
    "RENDER_DEPENDENCIES": True,
    # ... other component settings ...
}
```
