---
hide:
  - navigation
---

# Development guide

## Running django-components project locally

### Install locally and run the tests

Start by forking the project by clicking the **Fork button** up in the right corner in the GitHub . This makes a copy of the repository in your own name. Now you can clone this repository locally and start adding features:

```sh
git clone https://github.com/<your GitHub username>/django-components.git
```

To quickly run the tests install the local dependencies by running:

```sh
pip install -r requirements-dev.txt
```

Now you can run the tests to make sure everything works as expected:

```sh
pytest
```

The library is also tested across many versions of Python and Django. To run tests that way:

```bash
pyenv install -s 3.8
pyenv install -s 3.9
pyenv install -s 3.10
pyenv install -s 3.11
pyenv install -s 3.12
pyenv local 3.8 3.9 3.10 3.11 3.12
tox -p
```

### Developing against live Django app

How do you check that your changes to django-components project will work in an actual Django project?

Use the [sampleproject](https://github.com/EmilStenstrom/django-components/tree/master/sampleproject/) demo project to validate the changes:

1. Navigate to [sampleproject](https://github.com/EmilStenstrom/django-components/tree/master/sampleproject/) directory:
    ```sh
    cd sampleproject
    ```

2. Install dependencies from the [requirements.txt](https://github.com/EmilStenstrom/django-components/tree/master/sampleproject/requirements.txt) file:
    ```sh
    pip install -r requirements.txt
    ```

3. Link to your local version of django-components:
    ```sh
    pip install -e ..
    ```
    NOTE: The path (in this case `..`) must point to the directory that has the `setup.py` file.

4. Start Django server
    ```sh
    python manage.py runserver
    ```

Once the server is up, it should be available at <http://127.0.0.1:8000>.

To display individual components, add them to the `urls.py`, like in the case of <http://127.0.0.1:8000/greeting>

## Slot rendering flow

1. Flow starts when a template string is being parsed into Django Template instance.

2. When a `{% component %}` template tag is encountered, its body is searched for all `{% fill %}` nodes (explicit or implicit). and this is attached to the created [`ComponentNode`][django_components.component.ComponentNode].

    See the implementation of [`component`][django_components.templatetags.component_tags.do_component] template tag for details.

3. Template rendering is a separate action from template parsing. When the template is being rendered, the [`ComponentNode`][django_components.component.ComponentNode] creates an instance of the [`Component`][django_components.component.Component] class and passes it the slot fills.

    It's at this point when [`Component.render`][django_components.component.Component.render] is called, and the slots are
    rendered.
