# django-components
<a href="https://travis-ci.org/EmilStenstrom/django-components"><img align="right" src="https://travis-ci.org/EmilStenstrom/django-components.svg?branch=master"></a>
A way to create simple reusable template components in Django.

# Installation
```pip install django-components``` (NOTE: Does not work yet)

# Usage

Start by creating a Component by inheriting from the Component class. Don't forget to register the component so that it's available in the templates.

```python
from django_components import component

class Calendar(component.Component):
    def context(self, date):
        return {
            "date": date,
        }

    class Media:
        template = "[your app]/components/calendar/calendar.html"
        css = {'all': ('[your app]/components/calendar/calendar.css',)}
        js = ('[your app]/components/calendar/calendar.js',) 

component.register(name="calendar", component=Calendar) 
```

In your templates, use your component by first importing the django_components tag library, and then using the component_dependencies and component tags to render the component to the page.

```htmldjango
{% load components %}
{% block extra_media %}{% component_dependencies %}{% endblock %}
{% block main %}
    {% component name="calendar" date=custom_date %}
{% endblock %} 
```

# Running the tests

Install and run `tox`:

```sh
pip install tox
tox
```
