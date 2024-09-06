from django_components import Component, register


@register("todo")
class Todo(Component):
    # Templates inside `[your apps]/components` dir and `[project root]/components` dir
    # will be automatically found.
    template_name = "todo/todo.html"
