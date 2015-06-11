class AlreadyRegistered(Exception):
    pass

class NotRegistered(Exception):
    pass

class ComponentRegistry(object):
    def __init__(self):
        self._registry = {}  # component name -> component_class mapping

    def register(self, name=None, component=None):
        if name in self._registry:
            raise AlreadyRegistered('The component "%s" is already registered' % name)

        self._registry[name] = component

    def unregister(self, name):
        if name not in self._registry:
            raise NotRegistered('The component "%s" is not registered' % name)

        del self._registry[name]

# This variable represents the global component registry
registry = ComponentRegistry()
