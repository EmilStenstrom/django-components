# Component context and scope

By default, components can access context variables from the parent template, just like templates that are included with the `{% include %}` tag. Just like with `{% include %}`, if you don't want the component template to have access to the parent context, add `only` to the end of the `{% component %}` tag):

```htmldjango
   {% component "calendar" date="2015-06-19" only %}{% endcomponent %}
```

NOTE: `{% csrf_token %}` tags need access to the top-level context, and they will not function properly if they are rendered in a component that is called with the `only` modifier.

Components can also access the outer context in their context methods by accessing the property `outer_context`.

You can also set `context_behavior` to `isolated` to make all components isolated by default. This is useful if you want to make sure that components don't accidentally access the outer context.
