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
