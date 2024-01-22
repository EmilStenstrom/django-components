import inspect


class AlreadyRegistered(Exception):
    pass


class NotRegistered(Exception):
    pass


class ComponentRegistry(object):
    def __init__(self):
        self._registry = {}

    def register(self, name=None, component=None):
        if (
            name in self._registry
            and name
            and component
            and inspect.getsource(component)
            != inspect.getsource(self._registry[name])
        ):
            raise AlreadyRegistered(
                'The component "%s" has already been registered' % name
            )
        self._registry[name] = component

    def unregister(self, name):
        self.get(name)

        del self._registry[name]

    def get(self, name):
        if name not in self._registry:
            raise NotRegistered('The component "%s" is not registered' % name)

        return self._registry[name]

    def all(self):
        return self._registry

    def clear(self):
        self._registry = {}


# This variable represents the global component registry
registry = ComponentRegistry()


def register(name):
    """Class decorator to register a component.

    Usage:

    @register("my_component")
    class MyComponent(component.Component):
        ...
    """

    def decorator(component):
        registry.register(name=name, component=component)
        return component

    return decorator
