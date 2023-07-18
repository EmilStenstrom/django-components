import os
from textwrap import dedent

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Creates a new component"

    def add_arguments(self, parser):
        parser.add_argument(
            "name", type=str, help="The name of the component to create"
        )

    def handle(self, *args, **kwargs):
        name = kwargs["name"]
        base_dir = settings.BASE_DIR

        components_path = os.path.join(base_dir, f"components/{name}")

        if os.path.exists(
            components_path
        ):  # If component directory already exists
            raise CommandError(
                f'The component "{name}" already exists at {components_path}.'
            )

        os.makedirs(components_path)

        with open(components_path + "/index.js", "w") as f:
            script_content = dedent(
                f"""
                window.addEventListener('load', (event) => {{
                    console.log("{name} component is fully loaded");
                }});
            """
            )
            f.write(script_content.strip())

        with open(components_path + "/style.css", "w") as f:
            style_content = dedent(
                f"""
                .component-{name} {{
                    background: red;
                }}
            """
            )
            f.write(style_content.strip())

        with open(components_path + "/template.html", "w") as f:
            template_content = dedent(
                f"""
                <div class="component-{name}">
                    Hello from {name} component!
                </div>
            """
            )
            f.write(template_content.strip())

        with open(components_path + f"/{name}.py", "w") as f:
            py_content = dedent(
                f"""
                from django_components import component

                @component.register("{name}")
                class {name.capitalize()}(component.Component):
                    template_name = "{name}/template.html"

                    # This component takes one parameter, a date string to show in the template
                    def get_context_data(self, date):
                        return {{
                            "date": date,
                        }}

                    class Media:
                        css = "{name}/style.css"
                        js = "{name}/script.js"
            """
            )
            f.write(py_content.strip())

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully created {name} component at {components_path}"
            )
        )
