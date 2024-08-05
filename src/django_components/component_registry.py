from typing import TYPE_CHECKING, Callable, Dict, List, NamedTuple, Optional, Set, Type, TypeVar

from django.template import Library

if TYPE_CHECKING:
    from django_components.component import Component

_TComp = TypeVar("_TComp", bound=Type["Component"])


PROTECTED_TAGS = [
    "component",
    "component_dependencies",
    "component_css_dependencies",
    "component_js_dependencies",
    "fill",
    "html_attrs",
    "provide",
    "slot",
]


class AlreadyRegistered(Exception):
    pass


class NotRegistered(Exception):
    pass


# Why do we store the tags with the component?
#
# Each component may be associated with two template tags - One for "block"
# and one for "inline" usage. E.g. in the following snippets, the template
# tags are `component` and `#component`:
#
# `{% component "abc" %}{% endcomponent %}`
# `{% #component "abc" %}`
#
# (NOTE: While `endcomponent` also looks like a template tag, we don't have to register
# it, because it simply marks the end of body.)
#
# With the component tag formatter (configurable tags per component class),
# each component may have a unique set of template tags.
#
# For user's convenience, we automatically add/remove the tags from Django's tag Library,
# when a component is (un)registered.
#
# Thus we need to remember which component used which template tags.
class ComponentRegistryEntry(NamedTuple):
    cls: Type["Component"]
    block_tag: str
    inline_tag: str

    @property
    def tags(self) -> List[str]:
        return [self.block_tag, self.inline_tag]


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

    def __init__(self, library: Optional[Library] = None) -> None:
        self._registry: Dict[str, ComponentRegistryEntry] = {}  # component name -> component_entry mapping
        self._tags: Dict[str, Set[str]] = {}  # tag -> list[component names]
        self._library = library

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
            mark_protected_tags(tag_library, PROTECTED_TAGS)
            lib = self._library = tag_library
        return lib

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

        block_tag = "component"
        inline_tag = "#component"

        entry = ComponentRegistryEntry(
            cls=component,
            block_tag=block_tag,
            inline_tag=inline_tag,
        )

        # Keep track of which components use which tags, because multiple components may
        # use the same tag.
        for tag in entry.tags:
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

        # Unregister the tag from library if this was the last component using this tag
        for tag in entry.tags:
            # Unlink component from tag
            self._tags[tag].remove(name)

            # Cleanup
            is_tag_empty = not len(self._tags[tag])
            if is_tag_empty:
                del self._tags[tag]

            # Do NOT unregister tag if it's protected
            is_protected = is_tag_protected(self.library, tag)
            if is_protected:
                continue

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


def mark_protected_tags(lib: Library, tags: List[str]) -> None:
    # By marking the library as default,
    lib._protected_tags = [*tags]


def is_tag_protected(lib: Library, tag: str) -> bool:
    protected_tags = getattr(lib, "_protected_tags", [])
    return tag in protected_tags
