from typing import TYPE_CHECKING, Callable, Dict, List, NamedTuple, Optional, Set, Type, TypeVar, Union

from django.template import Library

from django_components.app_settings import ContextBehavior, app_settings
from django_components.library import is_tag_protected, mark_protected_tags, register_tag_from_formatter
from django_components.tag_formatter import TagFormatterABC, get_tag_formatter

if TYPE_CHECKING:
    from django_components.component import Component

_TComp = TypeVar("_TComp", bound=Type["Component"])


class AlreadyRegistered(Exception):
    pass


class NotRegistered(Exception):
    pass


# Why do we store the tags with the components?
#
# With the addition of TagFormatter, each component class may have a unique
# set of template tags.
#
# For user's convenience, we automatically add/remove the tags from Django's tag Library,
# when a component is (un)registered.
#
# Thus we need to remember which component used which template tags.
class ComponentRegistryEntry(NamedTuple):
    cls: Type["Component"]
    tag: str


class RegistrySettings(NamedTuple):
    CONTEXT_BEHAVIOR: Optional[ContextBehavior] = None
    TAG_FORMATTER: Optional[Union["TagFormatterABC", str]] = None


class InternalRegistrySettings(NamedTuple):
    CONTEXT_BEHAVIOR: ContextBehavior
    TAG_FORMATTER: Union["TagFormatterABC", str]


# We keep track of all registries that exist so that, when users want to
# dynamically resolve component name to component class, they would be able
# to search across all registries.
all_registries: List["ComponentRegistry"] = []


class ComponentRegistry:
    """
    Manages which components can be used in the template tags.

    Each ComponentRegistry instance is associated with an instance
    of Django's Library. So when you register or unregister a component
    to/from a component registry, behind the scenes the registry
    automatically adds/removes the component's template tag to/from
    the Library.

    The Library instance can be set at instantiation. If omitted, then
    the default Library instance from django_components is used. The
    Library instance can be accessed under `library` attribute.

    Example:

    ```py
    # Use with default Library
    registry = ComponentRegistry()

    # Or a custom one
    my_lib = Library()
    registry = ComponentRegistry(library=my_lib)

    # Usage
    registry.register("button", ButtonComponent)
    registry.register("card", CardComponent)
    registry.all()
    registry.clear()
    registry.get()
    ```
    """

    def __init__(
        self,
        library: Optional[Library] = None,
        settings: Optional[Union[RegistrySettings, Callable[["ComponentRegistry"], RegistrySettings]]] = None,
    ) -> None:
        self._registry: Dict[str, ComponentRegistryEntry] = {}  # component name -> component_entry mapping
        self._tags: Dict[str, Set[str]] = {}  # tag -> list[component names]
        self._library = library
        self._settings_input = settings
        self._settings: Optional[Callable[[], InternalRegistrySettings]] = None

        all_registries.append(self)

    @property
    def library(self) -> Library:
        """
        The template tag library with which the component registry is associated.
        """
        # Lazily use the default library if none was passed
        if self._library is not None:
            lib = self._library
        else:
            from django_components.templatetags.component_tags import register as tag_library

            # For the default library, we want to protect our template tags from
            # being overriden.
            # On the other hand, if user provided their own Library instance,
            # it is up to the user to use `mark_protected_tags` if they want
            # to protect any tags.
            mark_protected_tags(tag_library)
            lib = self._library = tag_library
        return lib

    @property
    def settings(self) -> InternalRegistrySettings:
        # This is run on subsequent calls
        if self._settings is not None:
            # NOTE: Registry's settings can be a function, so we always take
            # the latest value from Django's settings.
            settings = self._settings()

        # First-time initialization
        # NOTE: We allow the settings to be given as a getter function
        # so the settings can respond to changes.
        # So we wrapp that in our getter, which assigns default values from the settings.
        else:

            def get_settings() -> InternalRegistrySettings:
                if callable(self._settings_input):
                    settings_input: Optional[RegistrySettings] = self._settings_input(self)
                else:
                    settings_input = self._settings_input

                return InternalRegistrySettings(
                    CONTEXT_BEHAVIOR=(settings_input and settings_input.CONTEXT_BEHAVIOR)
                    or app_settings.CONTEXT_BEHAVIOR,
                    TAG_FORMATTER=(settings_input and settings_input.TAG_FORMATTER) or app_settings.TAG_FORMATTER,
                )

            self._settings = get_settings
            settings = self._settings()

        return settings

    def register(self, name: str, component: Type["Component"]) -> None:
        """
        Register a component with this registry under the given name.

        A component MUST be registered before it can be used in a template such as:
        ```django
        {% component "my_comp" %}{% endcomponent %}
        ```

        Raises `AlreadyRegistered` if a different component was already registered
        under the same name.

        Example:

        ```py
        registry.register("button", ButtonComponent)
        ```
        """
        existing_component = self._registry.get(name)
        if existing_component and existing_component.cls._class_hash != component._class_hash:
            raise AlreadyRegistered('The component "%s" has already been registered' % name)

        entry = self._register_to_library(name, component)

        # Keep track of which components use which tags, because multiple components may
        # use the same tag.
        tag = entry.tag
        if tag not in self._tags:
            self._tags[tag] = set()
        self._tags[tag].add(name)

        self._registry[name] = entry

    def unregister(self, name: str) -> None:
        """
        Unlinks a previously-registered component from the registry under the given name.

        Once a component is unregistered, it CANNOT be used in a template anymore.
        Following would raise an error:
        ```django
        {% component "my_comp" %}{% endcomponent %}
        ```

        Raises `NotRegistered` if the given name is not registered.

        Example:

        ```py
        # First register component
        registry.register("button", ButtonComponent)
        # Then unregister
        registry.unregister("button")
        ```
        """
        # Validate
        self.get(name)

        entry = self._registry[name]
        tag = entry.tag

        # Unregister the tag from library if this was the last component using this tag
        # Unlink component from tag
        self._tags[tag].remove(name)

        # Cleanup
        is_tag_empty = not len(self._tags[tag])
        if is_tag_empty:
            del self._tags[tag]

        # Only unregister a tag if it's NOT protected
        is_protected = is_tag_protected(self.library, tag)
        if not is_protected:
            # Unregister the tag from library if this was the last component using this tag
            if is_tag_empty and tag in self.library.tags:
                del self.library.tags[tag]

        del self._registry[name]

    def get(self, name: str) -> Type["Component"]:
        """
        Retrieve a component class registered under the given name.

        Raises `NotRegistered` if the given name is not registered.

        Example:

        ```py
        # First register component
        registry.register("button", ButtonComponent)
        # Then get
        registry.get("button")
        # > ButtonComponent
        ```
        """
        if name not in self._registry:
            raise NotRegistered('The component "%s" is not registered' % name)

        return self._registry[name].cls

    def all(self) -> Dict[str, Type["Component"]]:
        """
        Retrieve all registered component classes.

        Example:

        ```py
        # First register components
        registry.register("button", ButtonComponent)
        registry.register("card", CardComponent)
        # Then get all
        registry.all()
        # > {
        # >   "button": ButtonComponent,
        # >   "card": CardComponent,
        # > }
        ```
        """
        comps = {key: entry.cls for key, entry in self._registry.items()}
        return comps

    def clear(self) -> None:
        """
        Clears the registry, unregistering all components.

        Example:

        ```py
        # First register components
        registry.register("button", ButtonComponent)
        registry.register("card", CardComponent)
        # Then clear
        registry.clear()
        # Then get all
        registry.all()
        # > {}
        ```
        """
        all_comp_names = list(self._registry.keys())
        for comp_name in all_comp_names:
            self.unregister(comp_name)

        self._registry = {}
        self._tags = {}

    def _register_to_library(
        self,
        comp_name: str,
        component: Type["Component"],
    ) -> ComponentRegistryEntry:
        # Lazily import to avoid circular dependencies
        from django_components.templatetags.component_tags import component as do_component

        formatter = get_tag_formatter(self)
        tag = register_tag_from_formatter(self, do_component, formatter, comp_name)

        return ComponentRegistryEntry(cls=component, tag=tag)


# This variable represents the global component registry
registry: ComponentRegistry = ComponentRegistry()
"""
The default and global component registry. Use this instance to directly
register or remove components:

```py
# Register components
registry.register("button", ButtonComponent)
registry.register("card", CardComponent)
# Get single
registry.get("button")
# Get all
registry.all()
# Unregister single
registry.unregister("button")
# Unregister all
registry.clear()
```
"""

# NOTE: Aliased so that the arg to `@register` can also be called `registry`
_the_registry = registry


def register(name: str, registry: Optional[ComponentRegistry] = None) -> Callable[[_TComp], _TComp]:
    """
    Class decorator to register a component.

    Usage:

    ```py
    @register("my_component")
    class MyComponent(Component):
        ...
    ```

    Optionally specify which `ComponentRegistry` the component should be registered to by
    setting the `registry` kwarg:

    ```py
    my_lib = django.template.Library()
    my_reg = ComponentRegistry(library=my_lib)

    @register("my_component", registry=my_reg)
    class MyComponent(Component):
        ...
    ```
    """
    if registry is None:
        registry = _the_registry

    def decorator(component: _TComp) -> _TComp:
        registry.register(name=name, component=component)
        return component

    return decorator
