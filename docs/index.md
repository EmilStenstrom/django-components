# django-components

[![PyPI - Version](https://img.shields.io/pypi/v/django-components)](https://pypi.org/project/django-components/) [![PyPI - Python Version](https://img.shields.io/pypi/pyversions/django-components)](https://pypi.org/project/django-components/) [![PyPI - License](https://img.shields.io/pypi/l/django-components)](https://EmilStenstrom.github.io/django-components/latest/license/) [![PyPI - Downloads](https://img.shields.io/pypi/dm/django-components)](https://pypistats.org/packages/django-components) [![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/EmilStenstrom/django-components/tests.yml)](https://github.com/EmilStenstrom/django-components/actions/workflows/tests.yml)

Create simple reusable template components in Django

## Features

- ✨ **Reusable components**: [Create components](user_guide/creating_using_components/create_first_component.md) that can be reused in different parts of your project, or even in different projects.
- 📁 **Single file components**: [Keep your Python, CSS, Javascript and HTML in one place](user_guide/creating_using_components/single_file_component.md) (if you wish)
- 🎰 **Slots**: Define [slots](user_guide/creating_using_components/using_slots.md) in your components to make them more flexible.
- 💻 **CLI**: A [command line interface](user_guide/integration/commands.md) to help you create new components.
- 🚀 **Wide compatibility**: Works with [modern and LTS versions of Django](user_guide/installation/requirements_compatibility.md).
- **Load assets**: Automatically load the right CSS and Javascript files for your components, with [our middleware](user_guide/integration/middleware.md).


## Summary

It lets you create "template components", that contains both the template, the Javascript and the CSS needed to generate the front end code you need for a modern app. Use components like this:

```htmldjango
{% component "calendar" date="2015-06-19" %}{% endcomponent %}
```

And this is what gets rendered (plus the CSS and Javascript you've specified):

```html
<div class="calendar-component">Today's date is <span>2015-06-19</span></div>
```

Read our [user guide](user_guide/index.md) to set it up and learn about the details!

## Compatibility

`django-components` is compatible with modern and LTS versions of Django.

Check out the [compatibility guide](user_guide/installation/requirements_compatibility.md) to see which versions are supported.

## Community examples

One of our goals with `django-components` is to make it easy to share components between projects. If you have a set of components that you think would be useful to others, please open a pull request to add them to the list below.

- [django-htmx-components](https://github.com/iwanalabs/django-htmx-components): A set of components for use with [htmx](https://htmx.org/). Try out the [live demo](https://dhc.iwanalabs.com/).

## License

`django-components` is licensed under the MIT license. See the [LICENSE](license.md) file for more details.
