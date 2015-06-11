from .component_registry import ComponentRegistry, AlreadyRegistered, NotRegistered  # NOQA

class Component(object):
    def __init__(self):
        self._media = self.Media()

    def context(self):
        return {}

    class Media:
        template = None
        css = {}
        js = ()

# This variable represents the global component registry
registry = ComponentRegistry()
