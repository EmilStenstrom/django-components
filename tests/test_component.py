"""
Tests focusing on the Component class.
For tests focusing on the `component` tag, see `test_templatetags_component.py`
"""

import re
import sys
from typing import Any, Dict, List, Tuple, Union, no_type_check

# See https://peps.python.org/pep-0655/#usage-in-python-3-11
if sys.version_info >= (3, 11):
    from typing import NotRequired, TypedDict
else:
    from typing_extensions import NotRequired, TypedDict  # for Python <3.11 with (Not)Required

from unittest import skipIf

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpRequest, HttpResponse
from django.template import Context, RequestContext, Template, TemplateSyntaxError
from django.template.base import TextNode
from django.test import Client
from django.urls import path
from django.utils.safestring import SafeString

from django_components import Component, ComponentView, SlotFunc, register, registry, types
from django_components.slots import SlotRef

from .django_test_setup import setup_test_config
from .testutils import BaseTestCase, parametrize_context_behavior

setup_test_config({"autodiscover": False})


# Client for testing endpoints via requests
class CustomClient(Client):
    def __init__(self, urlpatterns=None, *args, **kwargs):
        import types

        if urlpatterns:
            urls_module = types.ModuleType("urls")
            urls_module.urlpatterns = urlpatterns  # type: ignore
            settings.ROOT_URLCONF = urls_module
        else:
            settings.ROOT_URLCONF = __name__
        settings.SECRET_KEY = "secret"  # noqa
        super().__init__(*args, **kwargs)


# Component typings
CompArgs = Tuple[int, str]


class CompData(TypedDict):
    variable: str


class CompSlots(TypedDict):
    my_slot: Union[str, int]
    my_slot2: SlotFunc


if sys.version_info >= (3, 11):

    class CompKwargs(TypedDict):
        variable: str
        another: int
        optional: NotRequired[int]

else:

    class CompKwargs(TypedDict, total=False):
        variable: str
        another: int
        optional: NotRequired[int]


# TODO_REMOVE_IN_V1 - Superseded by `self.get_template` in v1
class ComponentOldTemplateApiTest(BaseTestCase):
    @parametrize_context_behavior(["django", "isolated"])
    def test_get_template_string(self):
        class SimpleComponent(Component):
            def get_template_string(self, context):
                content: types.django_html = """
                    Variable: <strong>{{ variable }}</strong>
                """
                return content

            def get_context_data(self, variable=None):
                return {
                    "variable": variable,
                }

            class Media:
                css = "style.css"
                js = "script.js"

        rendered = SimpleComponent.render(kwargs={"variable": "test"})
        self.assertHTMLEqual(
            rendered,
            """
            Variable: <strong>test</strong>
            """,
        )


class ComponentTest(BaseTestCase):
    class ParentComponent(Component):
        template: types.django_html = """
            {% load component_tags %}
            <div>
                <h1>Parent content</h1>
                {% component name="variable_display" shadowing_variable='override' new_variable='unique_val' %}
                {% endcomponent %}
            </div>
            <div>
                {% slot 'content' %}
                    <h2>Slot content</h2>
                    {% component name="variable_display" shadowing_variable='slot_default_override' new_variable='slot_default_unique' %}
                    {% endcomponent %}
                {% endslot %}
            </div>
        """  # noqa

        def get_context_data(self):
            return {"shadowing_variable": "NOT SHADOWED"}

    class VariableDisplay(Component):
        template: types.django_html = """
            {% load component_tags %}
            <h1>Shadowing variable = {{ shadowing_variable }}</h1>
            <h1>Uniquely named variable = {{ unique_variable }}</h1>
        """

        def get_context_data(self, shadowing_variable=None, new_variable=None):
            context = {}
            if shadowing_variable is not None:
                context["shadowing_variable"] = shadowing_variable
            if new_variable is not None:
                context["unique_variable"] = new_variable
            return context

    def setUp(self):
        super().setUp()
        registry.register(name="parent_component", component=self.ParentComponent)
        registry.register(name="variable_display", component=self.VariableDisplay)

    @parametrize_context_behavior(["django", "isolated"])
    def test_empty_component(self):
        class EmptyComponent(Component):
            pass

        with self.assertRaises(ImproperlyConfigured):
            EmptyComponent("empty_component")._get_template(Context({}))

    @parametrize_context_behavior(["django", "isolated"])
    def test_template_string_static_inlined(self):
        class SimpleComponent(Component):
            template: types.django_html = """
                Variable: <strong>{{ variable }}</strong>
            """

            def get_context_data(self, variable=None):
                return {
                    "variable": variable,
                }

            class Media:
                css = "style.css"
                js = "script.js"

        rendered = SimpleComponent.render(kwargs={"variable": "test"})
        self.assertHTMLEqual(
            rendered,
            """
            Variable: <strong>test</strong>
            """,
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_template_string_dynamic(self):
        class SimpleComponent(Component):
            def get_template(self, context):
                content: types.django_html = """
                    Variable: <strong>{{ variable }}</strong>
                """
                return content

            def get_context_data(self, variable=None):
                return {
                    "variable": variable,
                }

            class Media:
                css = "style.css"
                js = "script.js"

        rendered = SimpleComponent.render(kwargs={"variable": "test"})
        self.assertHTMLEqual(
            rendered,
            """
            Variable: <strong>test</strong>
            """,
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_template_name_static(self):
        class SimpleComponent(Component):
            template_name = "simple_template.html"

            def get_context_data(self, variable=None):
                return {
                    "variable": variable,
                }

            class Media:
                css = "style.css"
                js = "script.js"

        rendered = SimpleComponent.render(kwargs={"variable": "test"})
        self.assertHTMLEqual(
            rendered,
            """
            Variable: <strong>test</strong>
            """,
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_template_name_dynamic(self):
        class SvgComponent(Component):
            def get_context_data(self, name, css_class="", title="", **attrs):
                return {
                    "name": name,
                    "css_class": css_class,
                    "title": title,
                    **attrs,
                }

            def get_template_name(self, context):
                return f"dynamic_{context['name']}.svg"

        self.assertHTMLEqual(
            SvgComponent.render(kwargs={"name": "svg1"}),
            """
            <svg>Dynamic1</svg>
            """,
        )
        self.assertHTMLEqual(
            SvgComponent.render(kwargs={"name": "svg2"}),
            """
            <svg>Dynamic2</svg>
            """,
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_allows_to_return_template(self):
        class TestComponent(Component):
            def get_context_data(self, variable, **attrs):
                return {
                    "variable": variable,
                }

            def get_template(self, context):
                template_str = "Variable: <strong>{{ variable }}</strong>"
                return Template(template_str)

        rendered = TestComponent.render(kwargs={"variable": "test"})
        self.assertHTMLEqual(
            rendered,
            """
            Variable: <strong>test</strong>
            """,
        )

    def test_input(self):
        tester = self

        class TestComponent(Component):
            @no_type_check
            def get_context_data(self, var1, var2, variable, another, **attrs):
                tester.assertEqual(self.input.args, (123, "str"))
                tester.assertEqual(self.input.kwargs, {"variable": "test", "another": 1})
                tester.assertIsInstance(self.input.context, Context)
                tester.assertEqual(self.input.slots, {"my_slot": "MY_SLOT"})

                return {
                    "variable": variable,
                }

            @no_type_check
            def get_template(self, context):
                tester.assertEqual(self.input.args, (123, "str"))
                tester.assertEqual(self.input.kwargs, {"variable": "test", "another": 1})
                tester.assertIsInstance(self.input.context, Context)
                tester.assertEqual(self.input.slots, {"my_slot": "MY_SLOT"})

                template_str: types.django_html = """
                    {% load component_tags %}
                    Variable: <strong>{{ variable }}</strong>
                    {% slot 'my_slot' / %}
                """
                return Template(template_str)

        rendered = TestComponent.render(
            kwargs={"variable": "test", "another": 1},
            args=(123, "str"),
            slots={"my_slot": "MY_SLOT"},
        )

        self.assertHTMLEqual(
            rendered,
            """
            Variable: <strong>test</strong> MY_SLOT
            """,
        )


class ComponentValidationTest(BaseTestCase):
    def test_validate_input_passes(self):
        class TestComponent(Component[CompArgs, CompKwargs, CompData, CompSlots]):
            def get_context_data(self, var1, var2, variable, another, **attrs):
                return {
                    "variable": variable,
                }

            template: types.django_html = """
                {% load component_tags %}
                Variable: <strong>{{ variable }}</strong>
                Slot 1: {% slot "my_slot" / %}
                Slot 2: {% slot "my_slot2" / %}
            """

        rendered = TestComponent.render(
            kwargs={"variable": "test", "another": 1},
            args=(123, "str"),
            slots={
                "my_slot": SafeString("MY_SLOT"),
                "my_slot2": lambda ctx, data, ref: "abc",
            },
        )

        self.assertHTMLEqual(
            rendered,
            """
            Variable: <strong>test</strong>
            Slot 1: MY_SLOT
            Slot 2: abc
            """,
        )

    @skipIf(sys.version_info < (3, 11), "Requires >= 3.11")
    def test_validate_input_fails(self):
        class TestComponent(Component[CompArgs, CompKwargs, CompData, CompSlots]):
            def get_context_data(self, var1, var2, variable, another, **attrs):
                return {
                    "variable": variable,
                }

            template: types.django_html = """
                {% load component_tags %}
                Variable: <strong>{{ variable }}</strong>
                Slot 1: {% slot "my_slot" / %}
                Slot 2: {% slot "my_slot2" / %}
            """

        with self.assertRaisesMessage(TypeError, "Component 'TestComponent' expected 2 positional arguments, got 1"):
            TestComponent.render(
                kwargs={"variable": 1, "another": "test"},  # type: ignore
                args=(123,),  # type: ignore
                slots={
                    "my_slot": "MY_SLOT",
                    "my_slot2": lambda ctx, data, ref: "abc",
                },
            )

        with self.assertRaisesMessage(TypeError, "Component 'TestComponent' expected 2 positional arguments, got 0"):
            TestComponent.render(
                kwargs={"variable": 1, "another": "test"},  # type: ignore
                slots={
                    "my_slot": "MY_SLOT",
                    "my_slot2": lambda ctx, data, ref: "abc",
                },
            )

        with self.assertRaisesMessage(
            TypeError,
            "Component 'TestComponent' expected keyword argument 'variable' to be <class 'str'>, got 1 of type <class 'int'>",  # noqa: E501
        ):
            TestComponent.render(
                kwargs={"variable": 1, "another": "test"},  # type: ignore
                args=(123, "abc", 456),  # type: ignore
                slots={
                    "my_slot": "MY_SLOT",
                    "my_slot2": lambda ctx, data, ref: "abc",
                },
            )

        with self.assertRaisesMessage(TypeError, "Component 'TestComponent' expected 2 positional arguments, got 0"):
            TestComponent.render()

        with self.assertRaisesMessage(
            TypeError,
            "Component 'TestComponent' expected keyword argument 'variable' to be <class 'str'>, got 1 of type <class 'int'>",  # noqa: E501
        ):
            TestComponent.render(
                kwargs={"variable": 1, "another": "test"},  # type: ignore
                args=(123, "str"),
                slots={
                    "my_slot": "MY_SLOT",
                    "my_slot2": lambda ctx, data, ref: "abc",
                },
            )

        with self.assertRaisesMessage(
            TypeError, "Component 'TestComponent' is missing a required keyword argument 'another'"
        ):
            TestComponent.render(
                kwargs={"variable": "abc"},  # type: ignore
                args=(123, "str"),
                slots={
                    "my_slot": "MY_SLOT",
                    "my_slot2": lambda ctx, data, ref: "abc",
                },
            )

        with self.assertRaisesMessage(
            TypeError,
            "Component 'TestComponent' expected slot 'my_slot' to be typing.Union[str, int], got 123.5 of type <class 'float'>",  # noqa: E501
        ):
            TestComponent.render(
                kwargs={"variable": "abc", "another": 1},
                args=(123, "str"),
                slots={
                    "my_slot": 123.5,  # type: ignore
                    "my_slot2": lambda ctx, data, ref: "abc",
                },
            )

        with self.assertRaisesMessage(TypeError, "Component 'TestComponent' is missing a required slot 'my_slot2'"):
            TestComponent.render(
                kwargs={"variable": "abc", "another": 1},
                args=(123, "str"),
                slots={
                    "my_slot": "MY_SLOT",
                },  # type: ignore
            )

    def test_validate_input_skipped(self):
        class TestComponent(Component[Any, CompKwargs, CompData, Any]):
            def get_context_data(self, var1, var2, variable, another, **attrs):
                return {
                    "variable": variable,
                }

            template: types.django_html = """
                {% load component_tags %}
                Variable: <strong>{{ variable }}</strong>
                Slot 1: {% slot "my_slot" / %}
                Slot 2: {% slot "my_slot2" / %}
            """

        rendered = TestComponent.render(
            kwargs={"variable": "test", "another": 1},
            args=("123", "str"),  # NOTE: Normally should raise
            slots={
                "my_slot": 123.5,  # NOTE: Normally should raise
                "my_slot2": lambda ctx, data, ref: "abc",
            },
        )

        self.assertHTMLEqual(
            rendered,
            """
            Variable: <strong>test</strong>
            Slot 1: 123.5
            Slot 2: abc
            """,
        )

    def test_validate_output_passes(self):
        class TestComponent(Component[CompArgs, CompKwargs, CompData, CompSlots]):
            def get_context_data(self, var1, var2, variable, another, **attrs):
                return {
                    "variable": variable,
                }

            template: types.django_html = """
                {% load component_tags %}
                Variable: <strong>{{ variable }}</strong>
                Slot 1: {% slot "my_slot" / %}
                Slot 2: {% slot "my_slot2" / %}
            """

        rendered = TestComponent.render(
            kwargs={"variable": "test", "another": 1},
            args=(123, "str"),
            slots={
                "my_slot": SafeString("MY_SLOT"),
                "my_slot2": lambda ctx, data, ref: "abc",
            },
        )

        self.assertHTMLEqual(
            rendered,
            """
            Variable: <strong>test</strong>
            Slot 1: MY_SLOT
            Slot 2: abc
            """,
        )

    def test_validate_output_fails(self):
        class TestComponent(Component[CompArgs, CompKwargs, CompData, CompSlots]):
            def get_context_data(self, var1, var2, variable, another, **attrs):
                return {
                    "variable": variable,
                    "invalid_key": var1,
                }

            template: types.django_html = """
                {% load component_tags %}
                Variable: <strong>{{ variable }}</strong>
                Slot 1: {% slot "my_slot" / %}
                Slot 2: {% slot "my_slot2" / %}
            """

        with self.assertRaisesMessage(TypeError, "Component 'TestComponent' got unexpected data keys 'invalid_key'"):
            TestComponent.render(
                kwargs={"variable": "test", "another": 1},
                args=(123, "str"),
                slots={
                    "my_slot": SafeString("MY_SLOT"),
                    "my_slot2": lambda ctx, data, ref: "abc",
                },
            )

    def test_handles_components_in_typing(self):
        class InnerKwargs(TypedDict):
            one: str

        class InnerData(TypedDict):
            one: Union[str, int]
            self: "InnerComp"  # type: ignore[misc]

        InnerComp = Component[Any, InnerKwargs, InnerData, Any]  # type: ignore[misc]

        class Inner(InnerComp):
            def get_context_data(self, one):
                return {
                    "self": self,
                    "one": one,
                }

            template = ""

        TodoArgs = Tuple[Inner]  # type: ignore[misc]

        class TodoKwargs(TypedDict):
            inner: Inner

        class TodoData(TypedDict):
            one: Union[str, int]
            self: "TodoComp"  # type: ignore[misc]
            inner: str

        TodoComp = Component[TodoArgs, TodoKwargs, TodoData, Any]  # type: ignore[misc]

        # NOTE: Since we're using ForwardRef for "TodoComp" and "InnerComp", we need
        # to ensure that the actual types are set as globals, so the ForwardRef class
        # can resolve them.
        globals()["TodoComp"] = TodoComp
        globals()["InnerComp"] = InnerComp

        class TestComponent(TodoComp):
            def get_context_data(self, var1, inner):
                return {
                    "self": self,
                    "one": "2123",
                    # NOTE: All of this is typed
                    "inner": self.input.kwargs["inner"].render(kwargs={"one": "abc"}),
                }

            template: types.django_html = """
                {% load component_tags %}
                Name: <strong>{{ self.name }}</strong>
            """

        rendered = TestComponent.render(args=(Inner(),), kwargs={"inner": Inner()})

        self.assertHTMLEqual(
            rendered,
            """
            Name: <strong>TestComponent</strong>
            """,
        )

    def test_handles_typing_module(self):
        TodoArgs = Tuple[
            Union[str, int],
            Dict[str, int],
            List[str],
            Tuple[int, Union[str, int]],
        ]

        class TodoKwargs(TypedDict):
            one: Union[str, int]
            two: Dict[str, int]
            three: List[str]
            four: Tuple[int, Union[str, int]]

        class TodoData(TypedDict):
            one: Union[str, int]
            two: Dict[str, int]
            three: List[str]
            four: Tuple[int, Union[str, int]]

        TodoComp = Component[TodoArgs, TodoKwargs, TodoData, Any]

        # NOTE: Since we're using ForwardRef for "TodoComp", we need
        # to ensure that the actual types are set as globals, so the ForwardRef class
        # can resolve them.
        globals()["TodoComp"] = TodoComp

        class TestComponent(TodoComp):
            def get_context_data(self, *args, **kwargs):
                return {
                    **kwargs,
                }

            template = ""

        TestComponent.render(
            args=("str", {"str": 123}, ["a", "b", "c"], (123, "123")),
            kwargs={
                "one": "str",
                "two": {"str": 123},
                "three": ["a", "b", "c"],
                "four": (123, "123"),
            },
        )


class ComponentRenderTest(BaseTestCase):
    @parametrize_context_behavior(["django", "isolated"])
    def test_render_minimal(self):
        class SimpleComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                the_arg2: {{ the_arg2 }}
                args: {{ args|safe }}
                the_kwarg: {{ the_kwarg }}
                kwargs: {{ kwargs|safe }}
                ---
                from_context: {{ from_context }}
                ---
                slot_second: {% slot "second" default %}
                    SLOT_SECOND_DEFAULT
                {% endslot %}
            """

            def get_context_data(self, the_arg2=None, *args, the_kwarg=None, **kwargs):
                return {
                    "the_arg2": the_arg2,
                    "the_kwarg": the_kwarg,
                    "args": args,
                    "kwargs": kwargs,
                }

        rendered = SimpleComponent.render()
        self.assertHTMLEqual(
            rendered,
            """
            the_arg2: None
            args: ()
            the_kwarg: None
            kwargs: {}
            ---
            from_context:
            ---
            slot_second: SLOT_SECOND_DEFAULT
            """,
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_render_full(self):
        class SimpleComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                the_arg: {{ the_arg }}
                the_arg2: {{ the_arg2 }}
                args: {{ args|safe }}
                the_kwarg: {{ the_kwarg }}
                kwargs: {{ kwargs|safe }}
                ---
                from_context: {{ from_context }}
                ---
                slot_first: {% slot "first" required %}
                {% endslot %}
                ---
                slot_second: {% slot "second" default %}
                    SLOT_SECOND_DEFAULT
                {% endslot %}
            """

            def get_context_data(self, the_arg, the_arg2=None, *args, the_kwarg, **kwargs):
                return {
                    "the_arg": the_arg,
                    "the_arg2": the_arg2,
                    "the_kwarg": the_kwarg,
                    "args": args,
                    "kwargs": kwargs,
                }

        rendered = SimpleComponent.render(
            context={"from_context": 98},
            args=["one", "two", "three"],
            kwargs={"the_kwarg": "test", "kw2": "ooo"},
            slots={"first": "FIRST_SLOT"},
        )
        self.assertHTMLEqual(
            rendered,
            """
            the_arg: one
            the_arg2: two
            args: ('three',)
            the_kwarg: test
            kwargs: {'kw2': 'ooo'}
            ---
            from_context: 98
            ---
            slot_first: FIRST_SLOT
            ---
            slot_second: SLOT_SECOND_DEFAULT
            """,
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_render_to_response_full(self):
        class SimpleComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                the_arg: {{ the_arg }}
                the_arg2: {{ the_arg2 }}
                args: {{ args|safe }}
                the_kwarg: {{ the_kwarg }}
                kwargs: {{ kwargs|safe }}
                ---
                from_context: {{ from_context }}
                ---
                slot_first: {% slot "first" required %}
                {% endslot %}
                ---
                slot_second: {% slot "second" default %}
                    SLOT_SECOND_DEFAULT
                {% endslot %}
            """

            def get_context_data(self, the_arg, the_arg2=None, *args, the_kwarg, **kwargs):
                return {
                    "the_arg": the_arg,
                    "the_arg2": the_arg2,
                    "the_kwarg": the_kwarg,
                    "args": args,
                    "kwargs": kwargs,
                }

        rendered = SimpleComponent.render_to_response(
            context={"from_context": 98},
            args=["one", "two", "three"],
            kwargs={"the_kwarg": "test", "kw2": "ooo"},
            slots={"first": "FIRST_SLOT"},
        )
        self.assertIsInstance(rendered, HttpResponse)

        self.assertHTMLEqual(
            rendered.content.decode(),
            """
            the_arg: one
            the_arg2: two
            args: ('three',)
            the_kwarg: test
            kwargs: {'kw2': 'ooo'}
            ---
            from_context: 98
            ---
            slot_first: FIRST_SLOT
            ---
            slot_second: SLOT_SECOND_DEFAULT
            """,
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_render_to_response_change_response_class(self):
        class MyResponse:
            def __init__(self, content: str) -> None:
                self.content = bytes(content, "utf-8")

        class SimpleComponent(Component):
            response_class = MyResponse
            template: types.django_html = "HELLO"

        rendered = SimpleComponent.render_to_response()
        self.assertIsInstance(rendered, MyResponse)

        self.assertHTMLEqual(
            rendered.content.decode(),
            "HELLO",
        )

    @parametrize_context_behavior([("django", False), ("isolated", True)])
    def test_render_slot_as_func(self, context_behavior_data):
        is_isolated = context_behavior_data

        class SimpleComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                {% slot "first" required data1="abc" data2:hello="world" data2:one=123 %}
                    SLOT_DEFAULT
                {% endslot %}
            """

            def get_context_data(self, the_arg, the_kwarg=None, **kwargs):
                return {
                    "the_arg": the_arg,
                    "the_kwarg": the_kwarg,
                    "kwargs": kwargs,
                }

        def first_slot(ctx: Context, slot_data: Dict, slot_ref: SlotRef):
            self.assertIsInstance(ctx, Context)
            # NOTE: Since the slot has access to the Context object, it should behave
            # the same way as it does in templates - when in "isolated" mode, then the
            # slot fill has access only to the "root" context, but not to the data of
            # get_context_data() of SimpleComponent.
            if is_isolated:
                self.assertEqual(ctx.get("the_arg"), None)
                self.assertEqual(ctx.get("the_kwarg"), None)
                self.assertEqual(ctx.get("kwargs"), None)
                self.assertEqual(ctx.get("abc"), None)
            else:
                self.assertEqual(ctx["the_arg"], "1")
                self.assertEqual(ctx["the_kwarg"], 3)
                self.assertEqual(ctx["kwargs"], {})
                self.assertEqual(ctx["abc"], "def")

            slot_data_expected = {
                "data1": "abc",
                "data2": {"hello": "world", "one": 123},
            }
            self.assertDictEqual(slot_data_expected, slot_data)

            self.assertIsInstance(slot_ref, SlotRef)
            self.assertEqual("SLOT_DEFAULT", str(slot_ref).strip())

            return f"FROM_INSIDE_FIRST_SLOT | {slot_ref}"

        rendered = SimpleComponent.render(
            context={"abc": "def"},
            args=["1"],
            kwargs={"the_kwarg": 3},
            slots={"first": first_slot},
        )
        self.assertHTMLEqual(
            rendered,
            "FROM_INSIDE_FIRST_SLOT | SLOT_DEFAULT",
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_render_raises_on_missing_slot(self):
        class SimpleComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                {% slot "first" required %}
                {% endslot %}
            """

        with self.assertRaises(TemplateSyntaxError):
            SimpleComponent.render()

        SimpleComponent.render(
            slots={"first": "FIRST_SLOT"},
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_render_with_include(self):
        class SimpleComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                {% include 'slotted_template.html' %}
            """

        rendered = SimpleComponent.render()
        self.assertHTMLEqual(
            rendered,
            """
            <custom-template>
                <header>Default header</header>
                <main>Default main</main>
                <footer>Default footer</footer>
            </custom-template>
            """,
        )

    # See https://github.com/EmilStenstrom/django-components/issues/580
    # And https://github.com/EmilStenstrom/django-components/commit/fee26ec1d8b46b5ee065ca1ce6143889b0f96764
    @parametrize_context_behavior(["django", "isolated"])
    def test_render_with_include_and_context(self):
        class SimpleComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                {% include 'slotted_template.html' %}
            """

        rendered = SimpleComponent.render(context=Context())
        self.assertHTMLEqual(
            rendered,
            """
            <custom-template>
                <header>Default header</header>
                <main>Default main</main>
                <footer>Default footer</footer>
            </custom-template>
            """,
        )

    # See https://github.com/EmilStenstrom/django-components/issues/580
    # And https://github.com/EmilStenstrom/django-components/issues/634
    # And https://github.com/EmilStenstrom/django-components/commit/fee26ec1d8b46b5ee065ca1ce6143889b0f96764
    @parametrize_context_behavior(["django", "isolated"])
    def test_render_with_include_and_request_context(self):
        class SimpleComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                {% include 'slotted_template.html' %}
            """

        rendered = SimpleComponent.render(context=RequestContext(HttpRequest()))
        self.assertHTMLEqual(
            rendered,
            """
            <custom-template>
                <header>Default header</header>
                <main>Default main</main>
                <footer>Default footer</footer>
            </custom-template>
            """,
        )

    # See https://github.com/EmilStenstrom/django-components/issues/580
    # And https://github.com/EmilStenstrom/django-components/issues/634
    @parametrize_context_behavior(["django", "isolated"])
    def test_request_context_is_populated_from_context_processors(self):
        @register("thing")
        class Thing(Component):
            template: types.django_html = """
                <kbd>Rendered {{ how }}</kbd>
                <div>
                    CSRF token: {{ csrf_token|default:"<em>No CSRF token</em>" }}
                </div>
            """

            def get_context_data(self, *args, how: str, **kwargs):
                return {"how": how}

            class View(ComponentView):
                def get(self, request):
                    how = "via GET request"

                    return self.component.render_to_response(
                        context=RequestContext(self.request),
                        kwargs=self.component.get_context_data(how=how),
                    )

        client = CustomClient(urlpatterns=[path("test_thing/", Thing.as_view())])
        response = client.get("/test_thing/")

        self.assertEqual(response.status_code, 200)

        # Full response:
        # """
        # <kbd>
        #     Rendered via GET request
        # </kbd>
        # <div>
        #     CSRF token:
        #     <div>
        #         test_csrf_token
        #     </div>
        # </div>
        # """
        self.assertInHTML(
            """
            <kbd>
                Rendered via GET request
            </kbd>
            """,
            response.content.decode(),
        )

        token_re = re.compile(rb"CSRF token:\s+(?P<token>[0-9a-zA-Z]{64})")
        token = token_re.findall(response.content)[0]

        self.assertTrue(token)
        self.assertEqual(len(token), 64)

    @parametrize_context_behavior(["django", "isolated"])
    def test_render_with_extends(self):
        class SimpleComponent(Component):
            template: types.django_html = """
                {% extends 'block.html' %}
                {% block body %}
                    OVERRIDEN
                {% endblock %}
            """

        rendered = SimpleComponent.render()
        self.assertHTMLEqual(
            rendered,
            """
            <!DOCTYPE html>
            <html lang="en">
            <body>
                <main role="main">
                <div class='container main-container'>
                    OVERRIDEN
                </div>
                </main>
            </body>
            </html>

            """,
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_render_can_access_instance(self):
        class TestComponent(Component):
            template = "Variable: <strong>{{ id }}</strong>"

            def get_context_data(self, **attrs):
                return {
                    "id": self.component_id,
                }

        rendered = TestComponent(component_id="123").render()
        self.assertHTMLEqual(
            rendered,
            "Variable: <strong>123</strong>",
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_render_to_response_can_access_instance(self):
        class TestComponent(Component):
            template = "Variable: <strong>{{ id }}</strong>"

            def get_context_data(self, **attrs):
                return {
                    "id": self.component_id,
                }

        rendered_resp = TestComponent(component_id="123").render_to_response()
        self.assertHTMLEqual(
            rendered_resp.content.decode("utf-8"),
            "Variable: <strong>123</strong>",
        )


class ComponentHookTest(BaseTestCase):
    def test_on_render_before(self):
        class SimpleComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                args: {{ args|safe }}
                kwargs: {{ kwargs|safe }}
                ---
                from_on_before: {{ from_on_before }}
            """

            def get_context_data(self, *args, **kwargs):
                return {
                    "args": args,
                    "kwargs": kwargs,
                }

            def on_render_before(self, context: Context, template: Template) -> None:
                # Insert value into the Context
                context["from_on_before"] = ":)"

                # Insert text into the Template
                template.nodelist.append(TextNode("\n---\nFROM_ON_BEFORE"))

        rendered = SimpleComponent.render()
        self.assertHTMLEqual(
            rendered,
            """
            args: ()
            kwargs: {}
            ---
            from_on_before: :)
            ---
            FROM_ON_BEFORE
            """,
        )

    # Check that modifying the context or template does nothing
    def test_on_render_after(self):
        captured_content = None

        class SimpleComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                args: {{ args|safe }}
                kwargs: {{ kwargs|safe }}
                ---
                from_on_before: {{ from_on_before }}
            """

            def get_context_data(self, *args, **kwargs):
                return {
                    "args": args,
                    "kwargs": kwargs,
                }

            # Check that modifying the context or template does nothing
            def on_render_after(self, context: Context, template: Template, content: str) -> None:
                # Insert value into the Context
                context["from_on_before"] = ":)"

                # Insert text into the Template
                template.nodelist.append(TextNode("\n---\nFROM_ON_BEFORE"))

                nonlocal captured_content
                captured_content = content

        rendered = SimpleComponent.render()

        self.assertHTMLEqual(
            captured_content,
            """
            args: ()
            kwargs: {}
            ---
            from_on_before:
            """,
        )
        self.assertHTMLEqual(
            rendered,
            """
            args: ()
            kwargs: {}
            ---
            from_on_before:
            """,
        )

    # Check that modifying the context or template does nothing
    @parametrize_context_behavior(["django", "isolated"])
    def test_on_render_after_override_output(self):
        captured_content = None

        class SimpleComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                args: {{ args|safe }}
                kwargs: {{ kwargs|safe }}
                ---
                from_on_before: {{ from_on_before }}
            """

            def get_context_data(self, *args, **kwargs):
                return {
                    "args": args,
                    "kwargs": kwargs,
                }

            def on_render_after(self, context: Context, template: Template, content: str) -> str:
                nonlocal captured_content
                captured_content = content

                return "Chocolate cookie recipe: " + content

        rendered = SimpleComponent.render()

        self.assertHTMLEqual(
            captured_content,
            """
            args: ()
            kwargs: {}
            ---
            from_on_before:
            """,
        )
        self.assertHTMLEqual(
            rendered,
            """
            Chocolate cookie recipe:
            args: ()
            kwargs: {}
            ---
            from_on_before:
            """,
        )
