class ComponentRegistry(object):
    def __init__(self):
        self._registry = {}  # component name -> component_class mapping

    def register(self, name=None, component=None):
        self._registry[name] = component

# This variable represents the global component registry
registry = ComponentRegistry()
