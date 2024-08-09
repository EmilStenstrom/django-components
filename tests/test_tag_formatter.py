from typing import List
from django.template import Context, Template

from django_components import Component, register, types
from django_components.tag_formatter import ShorthandComponentFormatter, TagResult

from .django_test_setup import setup_test_config
from .testutils import BaseTestCase, parametrize_context_behavior


setup_test_config({"autodiscover": False})


class MultiwordBlockStartTagFormatter(ShorthandComponentFormatter):
    def start_block_tag(self, name):
        return f"{name} comp"


class MultiwordBlockEndTagFormatter(ShorthandComponentFormatter):
    def end_tag(self, name):
        return f"end {name}"


class MultiwordInlineTagFormatter(ShorthandComponentFormatter):
    def start_inline_tag(self, name):
        return f"#{name} comp"


class SeparateInlineAndBlockTagFormatter(ShorthandComponentFormatter):
    def start_block_tag(self, name: str) -> str:
        return super().start_block_tag(name) + "_block"

    def start_inline_tag(self, name: str) -> str:
        return super().start_inline_tag(name) + "_inline"
    
    def parse(self, tokens: List[str]) -> TagResult:
        result = super().parse(tokens)

        # Drop the suffix
        component_name = result.component_name.split("_")[0]

        new_result = TagResult(component_name, [*result.tokens])

        if tokens[0].endswith("_inline"):
            # Append slash so the tag is parsed as inlined
            new_result.tokens.append("/")

        return new_result


# Create a TagFormatter class to validate the public interface
def create_validator_tag_formatter(tag_name: str):
    class ValidatorTagFormatter(ShorthandComponentFormatter):
        def start_block_tag(self, name):
            assert name == tag_name
            return super().start_block_tag(name)

        def end_tag(self, name):
            assert name == tag_name
            return super().end_tag(name)

        def start_inline_tag(self, name):
            assert name == tag_name
            return super().start_inline_tag(name)

        def parse(self, tokens):
            assert isinstance(tokens, list)
            assert tokens[0] == tag_name
            return super().parse(tokens)

    return ValidatorTagFormatter()


class ComponentTagTests(BaseTestCase):
    @parametrize_context_behavior(["django", "isolated"])
    def test_formatter_default_inline(self):
        @register("simple")
        class SimpleComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                hello1
                <div>
                    {% slot "content" default %} SLOT_DEFAULT {% endslot %}
                </div>
                hello2
            """

        template = Template(
            """
            {% load component_tags %}
            {% component "simple" / %}
        """
        )
        rendered = template.render(Context())
        self.assertHTMLEqual(
            rendered,
            """
            hello1
            <div>
                SLOT_DEFAULT
            </div>
            hello2
            """,
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_formatter_default_block(self):
        @register("simple")
        class SimpleComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                hello1
                <div>
                    {% slot "content" default %} SLOT_DEFAULT {% endslot %}
                </div>
                hello2
            """

        template = Template(
            """
            {% load component_tags %}
            {% component "simple" %}
                OVERRIDEN!
            {% endcomponent %}
        """
        )
        rendered = template.render(Context())
        self.assertHTMLEqual(
            rendered,
            """
            hello1
            <div>
                OVERRIDEN!
            </div>
            hello2
            """,
        )

    @parametrize_context_behavior(
        cases=["django", "isolated"],
        settings={
            "COMPONENTS": {
                "tag_formatter": "django_components.component_formatter",
            },
        },
    )
    def test_formatter_component_inline(self):
        @register("simple")
        class SimpleComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                hello1
                <div>
                    {% slot "content" default %} SLOT_DEFAULT {% endslot %}
                </div>
                hello2
            """

        template = Template(
            """
            {% load component_tags %}
            {% component "simple" / %}
        """
        )
        rendered = template.render(Context())
        self.assertHTMLEqual(
            rendered,
            """
            hello1
            <div>
                SLOT_DEFAULT
            </div>
            hello2
            """,
        )

    @parametrize_context_behavior(
        cases=["django", "isolated"],
        settings={
            "COMPONENTS": {
                "tag_formatter": "django_components.component_formatter",
            },
        },
    )
    def test_formatter_component_block(self):
        @register("simple")
        class SimpleComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                hello1
                <div>
                    {% slot "content" default %} SLOT_DEFAULT {% endslot %}
                </div>
                hello2
            """

        template = Template(
            """
            {% load component_tags %}
            {% component "simple" %}
                OVERRIDEN!
            {% endcomponent %}
        """
        )
        rendered = template.render(Context())
        self.assertHTMLEqual(
            rendered,
            """
            hello1
            <div>
                OVERRIDEN!
            </div>
            hello2
            """,
        )

    @parametrize_context_behavior(
        cases=["django", "isolated"],
        settings={
            "COMPONENTS": {
                "tag_formatter": "django_components.component_shorthand_formatter",
            },
        },
    )
    def test_formatter_shorthand_inline(self):
        @register("simple")
        class SimpleComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                hello1
                <div>
                    {% slot "content" default %} SLOT_DEFAULT {% endslot %}
                </div>
                hello2
            """

        template = Template(
            """
            {% load component_tags %}
            {% simple / %}
        """
        )
        rendered = template.render(Context())
        self.assertHTMLEqual(
            rendered,
            """
            hello1
            <div>
                SLOT_DEFAULT
            </div>
            hello2
            """,
        )

    @parametrize_context_behavior(
        cases=["django", "isolated"],
        settings={
            "COMPONENTS": {
                "tag_formatter": "django_components.component_shorthand_formatter",
            },
        },
    )
    def test_formatter_shorthand_block(self):
        @register("simple")
        class SimpleComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                hello1
                <div>
                    {% slot "content" default %} SLOT_DEFAULT {% endslot %}
                </div>
                hello2
            """

        template = Template(
            """
            {% load component_tags %}
            {% simple %}
                OVERRIDEN!
            {% endsimple %}
        """
        )
        rendered = template.render(Context())
        self.assertHTMLEqual(
            rendered,
            """
            hello1
            <div>
                OVERRIDEN!
            </div>
            hello2
            """,
        )

    @parametrize_context_behavior(
        cases=["django", "isolated"],
        settings={
            "COMPONENTS": {
                "tag_formatter": ShorthandComponentFormatter(),
            },
        },
    )
    def test_import_formatter_by_value(self):
        @register("simple")
        class SimpleComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div>
                    {% slot "content" default %} SLOT_DEFAULT {% endslot %}
                </div>
            """

        template = Template(
            """
            {% load component_tags %}
            {% simple %}
                OVERRIDEN!
            {% endsimple %}
        """
        )
        rendered = template.render(Context())
        self.assertHTMLEqual(
            rendered,
            """
            <div>
                OVERRIDEN!
            </div>
            """,
        )

    @parametrize_context_behavior(
        cases=["django", "isolated"],
        settings={
            "COMPONENTS": {
                "tag_formatter": MultiwordBlockStartTagFormatter(),
            },
        },
    )
    def test_raises_on_invalid_block_start_tag(self):
        with self.assertRaisesMessage(
            ValueError, "MultiwordBlockStartTagFormatter returned an invalid tag for start_block_tag: 'simple comp'"
        ):

            @register("simple")
            class SimpleComponent(Component):
                template = """{% load component_tags %}"""

    @parametrize_context_behavior(
        cases=["django", "isolated"],
        settings={
            "COMPONENTS": {
                "tag_formatter": MultiwordBlockEndTagFormatter(),
            },
        },
    )
    def test_raises_on_invalid_block_end_tag(self):
        with self.assertRaisesMessage(
            ValueError, "MultiwordBlockEndTagFormatter returned an invalid tag for end_tag: 'end simple'"
        ):

            @register("simple")
            class SimpleComponent(Component):
                template: types.django_html = """
                    {% load component_tags %}
                    <div>
                        {% slot "content" default %} SLOT_DEFAULT {% endslot %}
                    </div>
                """

            Template(
                """
                {% load component_tags %}
                {% simple %}
                    OVERRIDEN!
                {% bar %}
            """
            )

    @parametrize_context_behavior(
        cases=["django", "isolated"],
        settings={
            "COMPONENTS": {
                "tag_formatter": MultiwordInlineTagFormatter(),
            },
        },
    )
    def test_raises_on_invalid_inline_tag(self):
        with self.assertRaisesMessage(
            ValueError, "MultiwordInlineTagFormatter returned an invalid tag for start_inline_tag: '#simple comp'"
        ):

            @register("simple")
            class SimpleComponent(Component):
                template: types.django_html = """
                    {% load component_tags %}
                    <div>
                        {% slot "content" default %} SLOT_DEFAULT {% endslot %}
                    </div>
                """

    @parametrize_context_behavior(
        cases=["django", "isolated"],
        settings={
            "COMPONENTS": {
                "tag_formatter": create_validator_tag_formatter("simple"),
            },
        },
    )
    def test_method_args(self):
        @register("simple")
        class SimpleComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                hello1
                <div>
                    {% slot "content" default %} SLOT_DEFAULT {% endslot %}
                </div>
                hello2
            """

        template = Template(
            """
            {% load component_tags %}
            {% simple / %}
        """
        )
        rendered = template.render(Context())
        self.assertHTMLEqual(
            rendered,
            """
            hello1
            <div>
                SLOT_DEFAULT
            </div>
            hello2
            """,
        )

        template = Template(
            """
            {% load component_tags %}
            {% simple %}
                OVERRIDEN!
            {% endsimple %}
        """
        )
        rendered = template.render(Context())
        self.assertHTMLEqual(
            rendered,
            """
            hello1
            <div>
                OVERRIDEN!
            </div>
            hello2
            """,
        )

    @parametrize_context_behavior(
        cases=["django", "isolated"],
        settings={
            "COMPONENTS": {
                "tag_formatter": SeparateInlineAndBlockTagFormatter(),
            },
        },
    )
    def test_formatter_different_inline_and_block_tags(self):
        @register("simple")
        class SimpleComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div>
                    {% slot "content" default %} SLOT_DEFAULT {% endslot %}
                </div>
            """

        template = Template(
            """
            {% load component_tags %}
            {% simple_inline %}

            {% simple_block %}
                OVERRIDEN!
            {% endsimple %}
        """
        )
        rendered = template.render(Context())
        self.assertHTMLEqual(
            rendered,
            """
            <div>
                SLOT_DEFAULT
            </div>
            <div>
                OVERRIDEN!
            </div>
            """,
        )
