from django.template import Context, Template, TemplateSyntaxError

# isort: off
from .django_test_setup import *  # NOQA
from .testutils import BaseTestCase, parametrize_context_behavior

# isort: on

from django_components import component, types


class ProvideTemplateTagTest(BaseTestCase):
    @parametrize_context_behavior(["django", "isolated"])
    def test_provide_basic(self):
        @component.register("injectee")
        class InjectComponent(component.Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_context_data(self):
                var = self.inject("my_provide", "default")
                return {"var": var}

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide "my_provide" key="hi" another=123 %}
                {% component "injectee" %}
                {% endcomponent %}
            {% endprovide %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        self.assertHTMLEqual(
            rendered,
            """
            <div> injected: DepInject(key='hi', another=123) </div>
            """,
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_provide_access_keys_in_python(self):
        @component.register("injectee")
        class InjectComponent(component.Component):
            template: types.django_html = """
                <div> key: {{ key }} </div>
                <div> another: {{ another }} </div>
            """

            def get_context_data(self):
                my_provide = self.inject("my_provide")
                return {
                    "key": my_provide.key,
                    "another": my_provide.another,
                }

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide "my_provide" key="hi" another=123 %}
                {% component "injectee" %}
                {% endcomponent %}
            {% endprovide %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        self.assertHTMLEqual(
            rendered,
            """
            <div> key: hi </div>
            <div> another: 123 </div>
            """,
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_provide_access_keys_in_django(self):
        @component.register("injectee")
        class InjectComponent(component.Component):
            template: types.django_html = """
                <div> key: {{ my_provide.key }} </div>
                <div> another: {{ my_provide.another }} </div>
            """

            def get_context_data(self):
                my_provide = self.inject("my_provide")
                return {
                    "my_provide": my_provide,
                }

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide "my_provide" key="hi" another=123 %}
                {% component "injectee" %}
                {% endcomponent %}
            {% endprovide %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        self.assertHTMLEqual(
            rendered,
            """
            <div> key: hi </div>
            <div> another: 123 </div>
            """,
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_provide_does_not_leak(self):
        @component.register("injectee")
        class InjectComponent(component.Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_context_data(self):
                var = self.inject("my_provide", "default")
                return {"var": var}

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide "my_provide" key="hi" another=123 %}
            {% endprovide %}
            {% component "injectee" %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        self.assertHTMLEqual(
            rendered,
            """
            <div> injected: default </div>
            """,
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_provide_empty(self):
        """Check provide tag with no kwargs"""

        @component.register("injectee")
        class InjectComponent(component.Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_context_data(self):
                var = self.inject("my_provide", "default")
                return {"var": var}

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide "my_provide" %}
                {% component "injectee" %}
                {% endcomponent %}
            {% endprovide %}
            {% component "injectee" %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        self.assertHTMLEqual(
            rendered,
            """
            <div> injected: DepInject() </div>
            <div> injected: default </div>
        """,
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_provide_no_inject(self):
        """Check that nothing breaks if we do NOT inject even if some data is provided"""

        @component.register("injectee")
        class InjectComponent(component.Component):
            template: types.django_html = """
                <div></div>
            """

            def get_context_data(self):
                return {}

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide "my_provide" key="hi" another=123 %}
                {% component "injectee" %}
                {% endcomponent %}
            {% endprovide %}
            {% component "injectee" %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        self.assertHTMLEqual(
            rendered,
            """
            <div></div>
            <div></div>
        """,
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_provide_key_single_quotes(self):
        @component.register("injectee")
        class InjectComponent(component.Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_context_data(self):
                var = self.inject("my_provide", "default")
                return {"var": var}

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide 'my_provide' key="hi" another=123 %}
                {% component "injectee" %}
                {% endcomponent %}
            {% endprovide %}
            {% component "injectee" %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        self.assertHTMLEqual(
            rendered,
            """
            <div> injected: DepInject(key='hi', another=123) </div>
            <div> injected: default </div>
        """,
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_provide_no_key_raises(self):
        @component.register("injectee")
        class InjectComponent(component.Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_context_data(self):
                var = self.inject("my_provide", "default")
                return {"var": var}

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide key="hi" another=123 %}
                {% component "injectee" %}
                {% endcomponent %}
            {% endprovide %}
            {% component "injectee" %}
            {% endcomponent %}
        """
        with self.assertRaises(TemplateSyntaxError):
            Template(template_str)

    @parametrize_context_behavior(["django", "isolated"])
    def test_provide_key_must_be_string_literal(self):
        @component.register("injectee")
        class InjectComponent(component.Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_context_data(self):
                var = self.inject("my_provide", "default")
                return {"var": var}

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide my_var key="hi" another=123 %}
                {% component "injectee" %}
                {% endcomponent %}
            {% endprovide %}
            {% component "injectee" %}
            {% endcomponent %}
        """
        with self.assertRaises(TemplateSyntaxError):
            Template(template_str)

    @parametrize_context_behavior(["django", "isolated"])
    def test_provide_key_must_be_identifier(self):
        @component.register("injectee")
        class InjectComponent(component.Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_context_data(self):
                var = self.inject("my_provide", "default")
                return {"var": var}

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide "%heya%" key="hi" another=123 %}
                {% component "injectee" %}
                {% endcomponent %}
            {% endprovide %}
            {% component "injectee" %}
            {% endcomponent %}
        """
        template = Template(template_str)
        with self.assertRaises(TemplateSyntaxError):
            template.render(Context({}))

    @parametrize_context_behavior(["django", "isolated"])
    def test_provide_aggregate_dics(self):
        @component.register("injectee")
        class InjectComponent(component.Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_context_data(self):
                var = self.inject("my_provide", "default")
                return {"var": var}

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide "my_provide" var1:key="hi" var1:another=123 var2:x="y" %}
                {% component "injectee" %}
                {% endcomponent %}
            {% endprovide %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        self.assertHTMLEqual(
            rendered,
            """
            <div> injected: DepInject(var1={'key': 'hi', 'another': 123}, var2={'x': 'y'}) </div>
            """,
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_provide_does_not_expose_kwargs_to_context(self):
        """Check that `provide` tag doesn't assign the keys to the context like `with` tag does"""

        @component.register("injectee")
        class InjectComponent(component.Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_context_data(self):
                var = self.inject("my_provide", "default")
                return {"var": var}

        template_str: types.django_html = """
            {% load component_tags %}
            var_out: {{ var }}
            key_out: {{ key }}
            {% provide "my_provide" key="hi" another=123 %}
                var_in: {{ var }}
                key_in: {{ key }}
            {% endprovide %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"var": "123"}))

        self.assertHTMLEqual(
            rendered,
            """
            var_out: 123
            key_out:
            var_in: 123
            key_in:
            """,
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_provide_nested_in_provide_same_key(self):
        """Check that inner `provide` with same key overshadows outer `provide`"""

        @component.register("injectee")
        class InjectComponent(component.Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_context_data(self):
                var = self.inject("my_provide", "default")
                return {"var": var}

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide "my_provide" key="hi" another=123 lost=0 %}
                {% provide "my_provide" key="hi1" another=1231 new=3 %}
                    {% component "injectee" %}
                    {% endcomponent %}
                {% endprovide %}

                {% component "injectee" %}
                {% endcomponent %}
            {% endprovide %}
            {% component "injectee" %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        self.assertHTMLEqual(
            rendered,
            """
            <div> injected: DepInject(key='hi1', another=1231, new=3) </div>
            <div> injected: DepInject(key='hi', another=123, lost=0) </div>
            <div> injected: default </div>
            """,
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_provide_nested_in_provide_different_key(self):
        """Check that `provide` tag with different keys don't affect each other"""

        @component.register("injectee")
        class InjectComponent(component.Component):
            template: types.django_html = """
                <div> first_provide: {{ first_provide|safe }} </div>
                <div> second_provide: {{ second_provide|safe }} </div>
            """

            def get_context_data(self):
                first_provide = self.inject("first_provide", "default")
                second_provide = self.inject("second_provide", "default")
                return {
                    "first_provide": first_provide,
                    "second_provide": second_provide,
                }

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide "first_provide" key="hi" another=123 lost=0 %}
                {% provide "second_provide" key="hi1" another=1231 new=3 %}
                    {% component "injectee" %}
                    {% endcomponent %}
                {% endprovide %}
            {% endprovide %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        self.assertHTMLEqual(
            rendered,
            """
            <div> first_provide: DepInject(key='hi', another=123, lost=0) </div>
            <div> second_provide: DepInject(key='hi1', another=1231, new=3) </div>
            """,
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_provide_in_include(self):
        @component.register("injectee")
        class InjectComponent(component.Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_context_data(self):
                var = self.inject("my_provide", "default")
                return {"var": var}

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide "my_provide" key="hi" another=123 %}
                {% include "inject.html" %}
            {% endprovide %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        self.assertHTMLEqual(
            rendered,
            """
            <div>
                <div> injected: DepInject(key='hi', another=123) </div>
            </div>
            """,
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_slot_in_provide(self):
        @component.register("injectee")
        class InjectComponent(component.Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_context_data(self):
                var = self.inject("my_provide", "default")
                return {"var": var}

        @component.register("parent")
        class ParentComponent(component.Component):
            template: types.django_html = """
                {% load component_tags %}
                {% provide "my_provide" key="hi" another=123 %}
                    {% slot "content" default %}{% endslot %}
                {% endprovide %}
            """

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "parent" %}
                {% component "injectee" %}{% endcomponent %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        self.assertHTMLEqual(
            rendered,
            """
            <div>
                injected: DepInject(key='hi', another=123)
            </div>
            """,
        )


class InjectTest(BaseTestCase):
    @parametrize_context_behavior(["django", "isolated"])
    def test_inject_basic(self):
        @component.register("injectee")
        class InjectComponent(component.Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_context_data(self):
                var = self.inject("my_provide")
                return {"var": var}

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide "my_provide" key="hi" another=123 %}
                {% component "injectee" %}
                {% endcomponent %}
            {% endprovide %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        self.assertHTMLEqual(
            rendered,
            """
            <div> injected: DepInject(key='hi', another=123) </div>
            """,
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_inject_missing_key_raises_without_default(self):
        @component.register("injectee")
        class InjectComponent(component.Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_context_data(self):
                var = self.inject("abc")
                return {"var": var}

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "injectee" %}
            {% endcomponent %}
        """
        template = Template(template_str)

        with self.assertRaises(KeyError):
            template.render(Context({}))

    @parametrize_context_behavior(["django", "isolated"])
    def test_inject_missing_key_ok_with_default(self):
        @component.register("injectee")
        class InjectComponent(component.Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_context_data(self):
                var = self.inject("abc", "default")
                return {"var": var}

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "injectee" %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))
        self.assertHTMLEqual(
            rendered,
            """
            <div> injected: default </div>
            """,
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_inject_empty_string(self):
        @component.register("injectee")
        class InjectComponent(component.Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_context_data(self):
                var = self.inject("")
                return {"var": var}

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide "my_provide" key="hi" another=123 %}
                {% component "injectee" %}
                {% endcomponent %}
            {% endprovide %}
            {% component "injectee" %}
            {% endcomponent %}
        """
        template = Template(template_str)

        with self.assertRaises(KeyError):
            template.render(Context({}))

    @parametrize_context_behavior(["django", "isolated"])
    def test_inject_raises_on_called_outside_get_context_data(self):
        @component.register("injectee")
        class InjectComponent(component.Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_context_data(self):
                var = self.inject("abc", "default")
                return {"var": var}

        comp = InjectComponent("")
        with self.assertRaises(RuntimeError):
            comp.inject("abc", "def")
