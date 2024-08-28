import inspect
from typing import Any, Dict, Optional, Type, Union, cast

from django_components import Component, ComponentRegistry, NotRegistered, types
from django_components.component_registry import all_registries


class DynamicComponent(Component):
    """
    Dynamic component - This component takes inputs and renders the outputs depending on the
    `is` and `registry` arguments.

    - `is` - required - The component class or registered name of the component that will be
    rendered in this place.

    - `registry` - optional - Specify the registry to search for the registered name. If omitted,
    all registries are searched.
    """

    _is_dynamic_component = True

    def get_context_data(
        self,
        *args: Any,
        registry: Optional[ComponentRegistry] = None,
        **kwargs: Any,
    ) -> Dict:
        # NOTE: We have to access `is` via kwargs, because it's a special keyword in Python
        comp_name_or_class: Union[str, Type[Component]] = kwargs.pop("is", None)
        if not comp_name_or_class:
            raise TypeError(f"Component '{self.name}' is missing a required argument 'is'")

        comp_class = self._resolve_component(comp_name_or_class, registry)

        comp = comp_class(
            registered_name=self.registered_name,
            component_id=self.component_id,
            outer_context=self.outer_context,
            fill_content=self.fill_content,
            registry=self.registry,
        )
        output = comp.render(
            context=self.input.context,
            args=args,
            kwargs=kwargs,
            escape_slots_content=self.input.escape_slots_content,
        )

        return {
            "output": output,
        }

    template: types.django_html = """
        {{ output }}
    """

    def _resolve_component(
        self,
        comp_name_or_class: Union[str, Type[Component], Any],
        registry: Optional[ComponentRegistry] = None,
    ) -> Type[Component]:
        component_cls: Optional[Type[Component]] = None

        if not isinstance(comp_name_or_class, str):
            # NOTE: When Django template is resolving the variable that refers to the
            # component class, it may see that it's callable and evaluate it. Hence, we need
            # get check if we've got class or instance.
            if inspect.isclass(comp_name_or_class):
                component_cls = comp_name_or_class
            else:
                component_cls = cast(Type[Component], comp_name_or_class.__class__)

        else:
            if registry:
                component_cls = registry.get(comp_name_or_class)
            else:
                # Search all registries for the first match
                for reg in all_registries:
                    try:
                        component_cls = reg.get(comp_name_or_class)
                        break
                    except NotRegistered:
                        continue

        # Raise if none found
        if not component_cls:
            raise NotRegistered(f"The component '{comp_name_or_class}' was not found")

        return component_cls
