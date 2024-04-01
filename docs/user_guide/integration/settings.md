
# Available settings

All library settings are handled from a global `COMPONENTS` variable that is read from settings.py. By default you don't need it set, there are reasonable defaults.

## Configure the module where components are loaded from

Configure the location where components are loaded. To do this, add a `COMPONENTS` variable to you settings.py with a list of python paths to load. This allows you to build a structure of components that are independent from your apps.

```python
COMPONENTS = {
    "libraries": [
        "mysite.components.forms",
        "mysite.components.buttons",
        "mysite.components.cards",
    ],
}
```

## Disable autodiscovery

If you specify all the component locations with the setting above and have a lot of apps, you can (very) slightly speed things up by disabling autodiscovery.

```python
COMPONENTS = {
    "autodiscover": False,
}
```

## Tune the template cache

Each time a template is rendered it is cached to a global in-memory cache (using Python's lru_cache decorator). This speeds up the next render of the component. As the same component is often used many times on the same page, these savings add up. By default the cache holds 128 component templates in memory, which should be enough for most sites. But if you have a lot of components, or if you are using the `template` method of a component to render lots of dynamic templates, you can increase this number. To remove the cache limit altogether and cache everything, set template_cache_size to `None`.

```python
COMPONENTS = {
    "template_cache_size": 256,
}
```

## Isolate components' context by default

If you'd like to prevent components from accessing the outer context by default, you can set the `context_behavior` setting to `isolated`. This is useful if you want to make sure that components don't accidentally access the outer context.

```python
COMPONENTS = {
    "context_behavior": "isolated",
}
```

## Middleware

RENDER_DEPENDENCIES: If you are using the `ComponentDependencyMiddleware` middleware, you can enable or disable it here.

```python
COMPONENTS = {
    "RENDER_DEPENDENCIES": True,
}
```
