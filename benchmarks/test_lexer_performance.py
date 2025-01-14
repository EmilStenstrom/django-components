# NOTE: This file is more of a playground than a proper test

import timeit
from typing import List, Tuple

from django.template.base import DebugLexer, Lexer, Token

from django_components.util.template_parser import parse_template


def django_lexer(template: str) -> List[Token]:
    """Use Django's built-in lexer to tokenize a template."""
    lexer = Lexer(template)
    return list(lexer.tokenize())


def django_debug_lexer(template: str) -> List[Token]:
    """Use Django's built-in lexer to tokenize a template."""
    lexer = DebugLexer(template)
    return list(lexer.tokenize())


def run_benchmark(template: str, num_iterations: int = 5000) -> Tuple[float, float]:
    """Run performance comparison between Django and custom lexer."""
    # django_time = timeit.timeit(lambda: django_lexer(template), number=num_iterations)
    django_debug_time = timeit.timeit(lambda: django_debug_lexer(template), number=num_iterations)
    custom_time = timeit.timeit(lambda: parse_template(template), number=num_iterations)
    # return django_time, django_debug_time
    return django_debug_time, custom_time


def print_benchmark_results(template: str, django_time: float, custom_time: float, num_iterations: int) -> None:
    """Print formatted benchmark results."""
    print(f"\nTemplate: {template}")
    print(f"Iterations: {num_iterations}")
    print(f"Django Lexer: {django_time:.6f} seconds")
    print(f"Custom Lexer: {custom_time:.6f} seconds")
    print(f"Difference: {abs(django_time - custom_time):.6f} seconds")
    print(f"Custom lexer is {(django_time / custom_time):.2f}x {'faster' if custom_time < django_time else 'slower'}")


if __name__ == "__main__":
    test_cases = [
        # Simple text
        "Hello World",
        # Simple variable
        "Hello {{ name }}",
        # Simple block
        "{% if condition %}Hello{% endif %}",
        # Complex nested template
        """
        {% extends "base.html" %}
        {% block content %}
            <h1>{{ title }}</h1>
            {% for item in items %}
                <div class="{{ item.class }}">
                    {{ item.name }}
                    {% if item.description %}
                        <p>{{ item.description }}</p>
                    {% endif %}
                </div>
            {% endfor %}
        {% endblock %}
        """,
        # Component with nested tags
        """
        {% component 'table'
            headers=headers
            rows=rows
            footer="{% slot 'footer' %}Total: {{ total }}{% endslot %}"
            title="{% trans 'Data Table' %}"
        %}
        """,
        # Real world example
        """
        <div class="prose flex flex-col gap-8">
        {# Info section #}
        <div class="border-b border-neutral-300">
            <div class="flex justify-between items-start">
            <h3 class="mt-0">Project Info</h3>

                {% if editable %}
                {% component "Button"
                    href=project_edit_url
                    attrs:class="not-prose"
                    footer="{% slot 'footer' %}Total: {{ total }}{% endslot %}"
                    title="{% trans 'Data Table' %}"
                %}
                    Edit Project
                {% endcomponent %}
                {% endif %}
            </div>

            <table>
            {% for key, value in project_info %}
                <tr>
                <td class="font-bold pr-4">
                    {{ key }}:
                </td>
                <td>
                {{ value }}
                </td>
                </tr>
            {% endfor %}
            </table>
        </div>

        {# Status Updates section #}
        {% component "ProjectStatusUpdates"
            project_id=project.pk
            status_updates=status_updates
            editable=editable
            footer="{% slot 'footer' %}Total: {{ total }}{% endslot %}"
            title="{% trans 'Data Table' %}"
        / %}
        <div class="xl:grid xl:grid-cols-2 gap-10">
            {# Team section #}
            <div class="border-b border-neutral-300">
            <div class="flex justify-between items-start">
                <h3 class="mt-0">Dcode Team</h3>

                {% if editable %}
                    {% component "Button"
                        href=edit_project_roles_url
                        attrs:class="not-prose"
                        footer="{% slot 'footer' %}Total: {{ total }}{% endslot %}"
                        title="{% trans 'Data Table' %}"
                    %}
                    Edit Team
                    {% endcomponent %}
                {% endif %}
            </div>

            {% component "ProjectUsers"
                project_id=project.pk
                roles_with_users=roles_with_users
                editable=False
                footer="{% slot 'footer' %}Total: {{ total }}{% endslot %}"
                title="{% trans 'Data Table' %}"
            / %}
            </div>

            {# POCs section #}
            <div>
            <div class="flex justify-between items-start max-xl:mt-6">
                <h3 class="mt-0">Client POCs</h3>

                {% if editable %}
                {% component "Button"
                    href=edit_pocs_url
                    attrs:class="not-prose"
                    footer="{% slot 'footer' %}Total: {{ total }}{% endslot %}"
                    title="{% trans 'Data Table' %}"
                %}
                    Edit POCs
                {% endcomponent %}
                {% endif %}
            </div>

            {% if poc_data %}
                <table>
                <tr>
                    <th>Name</th>
                    <th>Job Title</th>
                    <th>Hubspot Profile</th>
                </tr>
                {% for data in poc_data %}
                    <tr>
                    <td>{{ data.poc.contact.first_name }} {{ data.poc.contact.last_name }}</td>
                    <td>{{ data.poc.contact.job_title }}</td>
                    <td>
                        {% component "Icon"
                            href=data.hubspot_url
                            name="arrow-top-right-on-square"
                            variant="outline"
                            color="text-gray-400 hover:text-gray-500"
                            footer="{% slot 'footer' %}Total: {{ total }}{% endslot %}"
                            title="{% trans 'Data Table' %}"
                        / %}
                    </td>
                    </tr>
                {% endfor %}
                </table>
            {% else %}
                <p class="text-sm italic">No entries</p>
            {% endif %}
            </div>
        </div>
        </div>
        """,
    ]

    for template in test_cases:
        django_time, custom_time = run_benchmark(template)
        print_benchmark_results(template, django_time, custom_time, 200)
