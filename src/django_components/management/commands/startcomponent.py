import os
from textwrap import dedent
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, CommandParser


class Command(BaseCommand):
    """
    ### Management Command Usage

    To use the command, run the following command in your terminal:

    ```bash
    python manage.py startcomponent <name> --path <path> --js <js_filename> --css <css_filename> --template <template_filename> --force --verbose --dry-run
    ```

    Replace `<name>`, `<path>`, `<js_filename>`, `<css_filename>`, and `<template_filename>` with your desired values.

    ### Management Command Examples

    Here are some examples of how you can use the command:

    #### Creating a Component with Default Settings

    To create a component with the default settings, you only need to provide the name of the component:

    ```bash
    python manage.py startcomponent my_component
    ```

    This will create a new component named `my_component` in the `components` directory of your Django project. The JavaScript, CSS, and template files will be named `script.js`, `style.css`, and `template.html`, respectively.

    #### Creating a Component with Custom Settings

    You can also create a component with custom settings by providing additional arguments:

    ```bash
    python manage.py startcomponent new_component --path my_components --js my_script.js --css my_style.css --template my_template.html
    ```

    This will create a new component named `new_component` in the `my_components` directory. The JavaScript, CSS, and template files will be named `my_script.js`, `my_style.css`, and `my_template.html`, respectively.

    #### Overwriting an Existing Component

    If you want to overwrite an existing component, you can use the `--force` option:

    ```bash
    python manage.py startcomponent my_component --force
    ```

    This will overwrite the existing `my_component` if it exists.

    #### Simulating Component Creation

    If you want to simulate the creation of a component without actually creating any files, you can use the `--dry-run` option:

    ```bash
    python manage.py startcomponent my_component --dry-run
    ```

    This will simulate the creation of `my_component` without creating any files.
    """  # noqa: E501

    help = "Create a new django component."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "name",
            type=str,
            help="The name of the component to create. This is a required argument.",
        )
        parser.add_argument(
            "--path",
            type=str,
            help=(
                "The path to the component's directory. This is an optional argument. If not provided, "
                "the command will use the `COMPONENTS.dirs` setting from your Django settings."
            ),
            default=None,
        )
        parser.add_argument(
            "--js",
            type=str,
            help="The name of the JavaScript file. This is an optional argument. The default value is `script.js`.",
            default="script.js",
        )
        parser.add_argument(
            "--css",
            type=str,
            help="The name of the CSS file. This is an optional argument. The default value is `style.css`.",
            default="style.css",
        )
        parser.add_argument(
            "--template",
            type=str,
            help="The name of the template file. This is an optional argument. The default value is `template.html`.",
            default="template.html",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="This option allows you to overwrite existing files if they exist. This is an optional argument.",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help=(
                "This option allows the command to print additional information during component "
                "creation. This is an optional argument."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help=(
                "This option allows you to simulate component creation without actually creating any files. "
                "This is an optional argument. The default value is `False`."
            ),
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
                        from django_components import Component, register

                        @register("{name}")
                        class {name.capitalize()}(Component):
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
