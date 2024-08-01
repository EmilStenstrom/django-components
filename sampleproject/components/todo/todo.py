from django_components import Component, register


@register("todo")
class Calendar(Component):
    # Note that Django will look for templates inside `[your apps]/components` dir and
    # `[project root]/components` dir. To customize which template to use based on context
    # you can override def get_template_name() instead of specifying the below variable.
    template_name = "todo/todo.html"
