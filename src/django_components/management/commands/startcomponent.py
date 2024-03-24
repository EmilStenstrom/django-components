import os
from textwrap import dedent
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, CommandParser


class Command(BaseCommand):
    help = "Creates a new component"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("name", type=str, help="The name of the component to create")
        parser.add_argument(
            "--path",
            type=str,
            help="The path to the components directory",
            default=None,
        )
        parser.add_argument(
            "--js",
            type=str,
            help="The name of the javascript file",
            default="script.js",
        )
        parser.add_argument(
            "--css",
            type=str,
            help="The name of the style file",
            default="style.css",
        )
        parser.add_argument(
            "--template",
            type=str,
            help="The name of the template file",
            default="template.html",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite existing files if they exist",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Print additional information during component creation",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulate component creation without actually creating any files",
            default=False,
        )

    def handle(self, *args: Any, **kwargs: Any) -> None:
        name = kwargs["name"]

        if name:
            path = kwargs["path"]
            js_filename = kwargs["js"]
            css_filename = kwargs["css"]
            template_filename = kwargs["template"]
            base_dir = getattr(settings, "BASE_DIR", None)
            force = kwargs["force"]
            verbose = kwargs["verbose"]
            dry_run = kwargs["dry_run"]

            if path:
                component_path = os.path.join(path, name)
            elif base_dir:
                component_path = os.path.join(base_dir, "components", name)
            else:
                raise CommandError("You must specify a path or set BASE_DIR in your django settings")

            if os.path.exists(component_path):
                if force:
                    if verbose:
                        self.stdout.write(
                            self.style.WARNING(
                                f'The component "{name}" already exists at {component_path}. Overwriting...'
                            )
                        )
                    else:
                        self.stdout.write(self.style.WARNING(f'The component "{name}" already exists. Overwriting...'))
                else:
                    raise CommandError(
                        f'The component "{name}" already exists at {component_path}. Use --force to overwrite.'
                    )

            if not dry_run:
                os.makedirs(component_path, exist_ok=force)

                with open(os.path.join(component_path, js_filename), "w") as f:
                    script_content = dedent(
                        f"""
                        window.addEventListener('load', (event) => {{
                            console.log("{name} component is fully loaded");
                        }});
                    """
                    )
                    f.write(script_content.strip())

                with open(os.path.join(component_path, css_filename), "w") as f:
                    style_content = dedent(
                        f"""
                        .component-{name} {{
                            background: red;
                        }}
                    """
                    )
                    f.write(style_content.strip())

                with open(os.path.join(component_path, template_filename), "w") as f:
                    template_content = dedent(
                        f"""
                        <div class="component-{name}">
                            Hello from {name} component!
                            <br>
                            This is {{ param }} context value.
                        </div>
                    """
                    )
                    f.write(template_content.strip())

                with open(os.path.join(component_path, f"{name}.py"), "w") as f:
                    py_content = dedent(
                        f"""
                        from django_components import component

                        @component.register("{name}")
                        class {name.capitalize()}(component.Component):
                            template_name = "{name}/{template_filename}"

                            def get_context_data(self, value):
                                return {{
                                    "param": "sample value",
                                }}

                            class Media:
                                css = "{name}/{css_filename}"
                                js = "{name}/{js_filename}"
                    """
                    )
                    f.write(py_content.strip())

            if verbose:
                self.stdout.write(self.style.SUCCESS(f"Successfully created {name} component at {component_path}"))
            else:
                self.stdout.write(self.style.SUCCESS(f"Successfully created {name} component"))
        else:
            raise CommandError("You must specify a component name")
