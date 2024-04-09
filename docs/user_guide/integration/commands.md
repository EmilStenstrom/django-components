# Management Command

You can use the built-in management command `startcomponent` to create a django component. The command accepts the following arguments and options:

- `name`: The name of the component to create. This is a required argument.

- `--path`: The path to the components directory. This is an optional argument. If not provided, the command will use the `BASE_DIR` setting from your Django settings.

- `--js`: The name of the JavaScript file. This is an optional argument. The default value is `script.js`.

- `--css`: The name of the CSS file. This is an optional argument. The default value is `style.css`.

- `--template`: The name of the template file. This is an optional argument. The default value is `template.html`.

- `--force`: This option allows you to overwrite existing files if they exist. This is an optional argument.

- `--verbose`: This option allows the command to print additional information during component creation. This is an optional argument.

- `--dry-run`: This option allows you to simulate component creation without actually creating any files. This is an optional argument. The default value is `False`.

### Management Command Usage

To use the command, run the following command in your terminal:

```bash
python manage.py startcomponent <name> --path <path> --js <js_filename> --css <css_filename> --template <template_filename> --force --verbose --dry-run
```

Replace `<name>`, `<path>`, `<js_filename>`, `<css_filename>`, and `<template_filename>` with your desired values.

### Management Command Examples

Here are some examples of how you can use the command:

### Creating a Component with Default Settings

To create a component with the default settings, you only need to provide the name of the component:

```bash
python manage.py startcomponent my_component
```

This will create a new component named `my_component` in the `components` directory of your Django project. The JavaScript, CSS, and template files will be named `script.js`, `style.css`, and `template.html`, respectively.

### Creating a Component with Custom Settings

You can also create a component with custom settings by providing additional arguments:

```bash
python manage.py startcomponent new_component --path my_components --js my_script.js --css my_style.css --template my_template.html
```

This will create a new component named `new_component` in the `my_components` directory. The JavaScript, CSS, and template files will be named `my_script.js`, `my_style.css`, and `my_template.html`, respectively.

### Overwriting an Existing Component

If you want to overwrite an existing component, you can use the `--force` option:

```bash
python manage.py startcomponent my_component --force
```

This will overwrite the existing `my_component` if it exists.

### Simulating Component Creation

If you want to simulate the creation of a component without actually creating any files, you can use the `--dry-run` option:

```bash
python manage.py startcomponent my_component --dry-run
```

This will simulate the creation of `my_component` without creating any files.
