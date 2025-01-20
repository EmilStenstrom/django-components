from typing import Any

from django.template import Context
from django.utils.safestring import SafeString

from django_components.context import set_provided_context_var
from django_components.node import BaseNode


class ProvideNode(BaseNode):
    """
    The "provider" part of the [provide / inject feature](../../concepts/advanced/provide_inject).
    Pass kwargs to this tag to define the provider's data.
    Any components defined within the `{% provide %}..{% endprovide %}` tags will be able to access this data
    with [`Component.inject()`](../api#django_components.Component.inject).

    This is similar to React's [`ContextProvider`](https://react.dev/learn/passing-data-deeply-with-context),
    or Vue's [`provide()`](https://vuejs.org/guide/components/provide-inject).

    **Args:**

    - `name` (str, required): Provider name. This is the name you will then use in
        [`Component.inject()`](../api#django_components.Component.inject).
    - `**kwargs`: Any extra kwargs will be passed as the provided data.

    **Example:**

    Provide the "user_data" in parent component:

    ```python
    @register("parent")
    class Parent(Component):
        template = \"\"\"
          <div>
            {% provide "user_data" user=user %}
              {% component "child" / %}
            {% endprovide %}
          </div>
        \"\"\"

        def get_context_data(self, user: User):
            return {
                "user": user,
            }
    ```

    Since the "child" component is used within the `{% provide %} / {% endprovide %}` tags,
    we can request the "user_data" using `Component.inject("user_data")`:

    ```python
    @register("child")
    class Child(Component):
        template = \"\"\"
          <div>
            User is: {{ user }}
          </div>
        \"\"\"

        def get_context_data(self):
            user = self.inject("user_data").user
            return {
                "user": user,
            }
    ```

    Notice that the keys defined on the `{% provide %}` tag are then accessed as attributes
    when accessing them with [`Component.inject()`](../api#django_components.Component.inject).

    ✅ Do this
    ```python
    user = self.inject("user_data").user
    ```

    ❌ Don't do this
    ```python
    user = self.inject("user_data")["user"]
    ```
    """

    tag = "provide"
    end_tag = "endprovide"
    allowed_flags = []

    def render(self, context: Context, name: str, **kwargs: Any) -> SafeString:
        # NOTE: The "provided" kwargs are meant to be shared privately, meaning that components
        # have to explicitly opt in by using the `Component.inject()` method. That's why we don't
        # add the provided kwargs into the Context.
        with context.update({}):
            # "Provide" the data to child nodes
            set_provided_context_var(context, name, kwargs)

            output = self.nodelist.render(context)

        return output
