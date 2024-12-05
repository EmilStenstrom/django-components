from django.http import HttpResponse
from django.template import Context, Template

from django_components import render_dependencies, types


def single_component_view(request):
    template_str: types.django_html = """
        {% load component_tags %}
        <!DOCTYPE html>
        <html>
            <head>
                {% component_css_dependencies %}
            </head>
            <body>
                {% component 'inner' variable='foo' / %}
                <div class="my-style">123</div>
                <div class="my-style2">xyz</div>
                {% component_js_dependencies %}
            </body>
        </html>
    """
    template = Template(template_str)

    rendered_raw = template.render(Context({}))
    rendered = render_dependencies(rendered_raw)
    return HttpResponse(rendered)


def multiple_components_view(request):
    template_str: types.django_html = """
        {% load component_tags %}
        <!DOCTYPE html>
        <html>
            <head>
                {% component_css_dependencies %}
            </head>
            <body>
                {% component 'outer' variable='variable' %}
                    {% component 'other' variable='variable_inner' / %}
                {% endcomponent %}
                <div class="my-style">123</div>
                <div class="my-style2">xyz</div>
                {% component_js_dependencies %}
            </body>
        </html>
    """
    template = Template(template_str)
    rendered_raw = template.render(Context({}))
    rendered = render_dependencies(rendered_raw)
    return HttpResponse(rendered)


def check_js_order_in_js_view(request):
    template_str: types.django_html = """
        {% load component_tags %}
        <!DOCTYPE html>
        <html>
            <head>
                {% component_css_dependencies %}
            </head>
            <body>
                {% component 'outer' variable='variable' %}
                    {% component 'other' variable='variable_inner' / %}
                {% endcomponent %}
                {# check_script_order_in_media is AFTER the other components #}
                {% component 'check_script_order_in_js' / %}
                abc
                {% component_js_dependencies %}
            </body>
        </html>
    """
    template = Template(template_str)
    rendered_raw = template.render(Context({}))
    rendered = render_dependencies(rendered_raw)
    return HttpResponse(rendered)


def check_js_order_in_media_view(request):
    template_str: types.django_html = """
        {% load component_tags %}
        <!DOCTYPE html>
        <html>
            <head>
                {% component_css_dependencies %}
            </head>
            <body>
                {% component 'outer' variable='variable' %}
                    {% component 'other' variable='variable_inner' / %}
                {% endcomponent %}
                {# check_script_order_in_media is AFTER the other components #}
                {% component 'check_script_order_in_media' / %}
                abc
                {% component_js_dependencies %}
            </body>
        </html>
    """
    template = Template(template_str)
    rendered_raw = template.render(Context({}))
    rendered = render_dependencies(rendered_raw)
    return HttpResponse(rendered)


def check_js_order_vars_not_available_before_view(request):
    template_str: types.django_html = """
        {% load component_tags %}
        <!DOCTYPE html>
        <html>
            <head>
                {% component_css_dependencies %}
            </head>
            <body>
                {# check_script_order_in_media is BEFORE the other components #}
                {% component 'check_script_order_in_media' / %}
                {% component 'outer' variable='variable' %}
                    {% component 'other' variable='variable_inner' / %}
                {% endcomponent %}
                abc
                {% component_js_dependencies %}
            </body>
        </html>
    """
    template = Template(template_str)
    rendered_raw = template.render(Context({}))
    rendered = render_dependencies(rendered_raw)
    return HttpResponse(rendered)


def alpine_in_head_view(request):
    template_str: types.django_html = """
        {% load component_tags %}
        <!DOCTYPE html>
        <html>
            <head>
                {% component_css_dependencies %}
                <script defer src="https://unpkg.com/alpinejs"></script>
            </head>
            <body>
                {% component 'alpine_test_in_media' / %}
                {% component_js_dependencies %}
            </body>
        </html>
    """
    template = Template(template_str)
    rendered_raw = template.render(Context({}))
    rendered = render_dependencies(rendered_raw)
    return HttpResponse(rendered)


def alpine_in_body_view(request):
    template_str: types.django_html = """
        {% load component_tags %}
        <!DOCTYPE html>
        <html>
            <head>
                {% component_css_dependencies %}
            </head>
            <body>
                {% component 'alpine_test_in_media' / %}
                {% component_js_dependencies %}
                <script src="https://unpkg.com/alpinejs"></script>
            </body>
        </html>
    """
    template = Template(template_str)
    rendered_raw = template.render(Context({}))
    rendered = render_dependencies(rendered_raw)
    return HttpResponse(rendered)


# Same as before, but Alpine component defined in Component.js
def alpine_in_body_view_2(request):
    template_str: types.django_html = """
        {% load component_tags %}
        <!DOCTYPE html>
        <html>
            <head>
                {% component_css_dependencies %}
            </head>
            <body>
                {% component 'alpine_test_in_js' / %}
                {% component_js_dependencies %}
                <script src="https://unpkg.com/alpinejs"></script>
            </body>
        </html>
    """
    template = Template(template_str)
    rendered_raw = template.render(Context({}))
    rendered = render_dependencies(rendered_raw)
    return HttpResponse(rendered)


def alpine_in_body_vars_not_available_before_view(request):
    template_str: types.django_html = """
        {% load component_tags %}
        <!DOCTYPE html>
        <html>
            <head>
                {% component_css_dependencies %}
            </head>
            <body>
                {% component 'alpine_test_in_js' / %}
                {# Alpine loaded BEFORE components JS #}
                <script src="https://unpkg.com/alpinejs"></script>
                {% component_js_dependencies %}
            </body>
        </html>
    """
    template = Template(template_str)
    rendered_raw = template.render(Context({}))
    rendered = render_dependencies(rendered_raw)
    return HttpResponse(rendered)
