from django.template import Context, Template
from django.template.exceptions import TemplateSyntaxError

from django_components import types
from django_components.node import BaseNode, template_tag
from django_components.templatetags import component_tags

from .django_test_setup import setup_test_config
from .testutils import BaseTestCase

setup_test_config({"autodiscover": False})


class NodeTests(BaseTestCase):
    def test_node_class_requires_tag(self):
        with self.assertRaises(ValueError):

            class CaptureNode(BaseNode):
                pass

    # Test that the template tag can be used within the template under the registered tag
    def test_node_class_tags(self):
        class TestNode(BaseNode):
            tag = "mytag"
            end_tag = "endmytag"

            def render(self, context: Context, name: str, **kwargs) -> str:
                return f"Hello, {name}!"

        TestNode.register(component_tags.register)

        # Works with end tag and self-closing
        template_str: types.django_html = """
            {% load component_tags %}
            {% mytag 'John' %}
            {% endmytag %}
            Shorthand: {% mytag 'Mary' / %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        self.assertEqual(rendered.strip(), "Hello, John!\n            Shorthand: Hello, Mary!")

        # But raises if missing end tag
        template_str2: types.django_html = """
            {% load component_tags %}
            {% mytag 'John' %}
        """
        with self.assertRaisesMessage(TemplateSyntaxError, "Unclosed tag on line 3: 'mytag'"):
            Template(template_str2)

        TestNode.unregister(component_tags.register)

    def test_node_class_no_end_tag(self):
        class TestNode(BaseNode):
            tag = "mytag"

            def render(self, context: Context, name: str, **kwargs) -> str:
                return f"Hello, {name}!"

        TestNode.register(component_tags.register)

        # Raises with end tag or self-closing
        template_str: types.django_html = """
            {% load component_tags %}
            {% mytag 'John' %}
            {% endmytag %}
            Shorthand: {% mytag 'Mary' / %}
        """
        with self.assertRaisesMessage(TemplateSyntaxError, "Invalid block tag on line 4: 'endmytag'"):
            Template(template_str)

        # Works when missing end tag
        template_str2: types.django_html = """
            {% load component_tags %}
            {% mytag 'John' %}
        """
        template2 = Template(template_str2)
        rendered2 = template2.render(Context({}))
        self.assertEqual(rendered2.strip(), "Hello, John!")

        TestNode.unregister(component_tags.register)

    def test_node_class_flags(self):
        captured = None

        class TestNode(BaseNode):
            tag = "mytag"
            end_tag = "endmytag"
            allowed_flags = ["required", "default"]

            def render(self, context: Context, name: str, **kwargs) -> str:
                nonlocal captured
                captured = self.allowed_flags, self.flags, self.active_flags

                return f"Hello, {name}!"

        TestNode.register(component_tags.register)

        template_str = """
            {% load component_tags %}
            {% mytag 'John' required / %}
        """
        template = Template(template_str)
        template.render(Context({}))

        allowed_flags, flags, active_flags = captured  # type: ignore
        self.assertEqual(allowed_flags, ["required", "default"])
        self.assertEqual(flags, {"required": True, "default": False})
        self.assertEqual(active_flags, ["required"])

        TestNode.unregister(component_tags.register)

    def test_node_render(self):
        # Check that the render function is called with the context
        captured = None

        class TestNode(BaseNode):
            tag = "mytag"

            def render(self, context: Context) -> str:
                nonlocal captured
                captured = context.flatten()

                return f"Hello, {context['name']}!"

        TestNode.register(component_tags.register)

        template_str = """
            {% load component_tags %}
            {% mytag / %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"name": "John"}))

        self.assertEqual(captured, {"False": False, "None": None, "True": True, "name": "John"})
        self.assertEqual(rendered.strip(), "Hello, John!")

        TestNode.unregister(component_tags.register)

    def test_node_render_raises_if_no_context_arg(self):
        with self.assertRaisesMessage(TypeError, "`render()` method of TestNode must have at least two parameters"):

            class TestNode(BaseNode):
                tag = "mytag"

                def render(self) -> str:  # type: ignore
                    return ""

    def test_node_render_accepted_params_set_by_render_signature(self):
        captured = None

        class TestNode1(BaseNode):
            tag = "mytag"
            allowed_flags = ["required", "default"]

            def render(self, context: Context, name: str, count: int = 1, *, msg: str, mode: str = "default") -> str:
                nonlocal captured
                captured = name, count, msg, mode
                return ""

        TestNode1.register(component_tags.register)

        # Set only required params
        template1 = Template(
            """
            {% load component_tags %}
            {% mytag 'John' msg='Hello' required %}
        """
        )
        template1.render(Context({}))
        self.assertEqual(captured, ("John", 1, "Hello", "default"))

        # Set all params
        template2 = Template(
            """
            {% load component_tags %}
            {% mytag 'John2' count=2 msg='Hello' mode='custom' required %}
        """
        )
        template2.render(Context({}))
        self.assertEqual(captured, ("John2", 2, "Hello", "custom"))

        # Set no params
        template3 = Template(
            """
            {% load component_tags %}
            {% mytag %}
        """
        )
        with self.assertRaisesMessage(
            TypeError, "Invalid parameters for tag 'mytag': missing a required argument: 'name'"
        ):
            template3.render(Context({}))

        # Omit required arg
        template4 = Template(
            """
            {% load component_tags %}
            {% mytag msg='Hello' %}
        """
        )
        with self.assertRaisesMessage(
            TypeError, "Invalid parameters for tag 'mytag': missing a required argument: 'name'"
        ):
            template4.render(Context({}))

        # Omit required kwarg
        template5 = Template(
            """
            {% load component_tags %}
            {% mytag name='John' %}
        """
        )
        with self.assertRaisesMessage(
            TypeError, "Invalid parameters for tag 'mytag': missing a required argument: 'msg'"
        ):
            template5.render(Context({}))

        # Extra args
        template6 = Template(
            """
            {% load component_tags %}
            {% mytag 123 count=1 name='John' %}
        """
        )
        with self.assertRaisesMessage(
            TypeError, "Invalid parameters for tag 'mytag': multiple values for argument 'name'"
        ):
            template6.render(Context({}))

        # Extra args after kwargs
        template6 = Template(
            """
            {% load component_tags %}
            {% mytag count=1 name='John' 123 %}
        """
        )
        with self.assertRaisesMessage(SyntaxError, "positional argument follows keyword argument"):
            template6.render(Context({}))

        # Extra kwargs
        template7 = Template(
            """
            {% load component_tags %}
            {% mytag 'John' msg='Hello' mode='custom' var=123 %}
        """
        )
        with self.assertRaisesMessage(
            TypeError, "Invalid parameters for tag 'mytag': got an unexpected keyword argument 'var'"
        ):
            template7.render(Context({}))

        # Extra kwargs - non-identifier or kwargs
        template7 = Template(
            """
            {% load component_tags %}
            {% mytag 'John' msg='Hello' mode='custom' data-id=123 class="pa-4" @click.once="myVar" %}
        """
        )
        with self.assertRaisesMessage(
            TypeError, "Invalid parameters for tag 'mytag': got an unexpected keyword argument 'data-id'"
        ):
            template7.render(Context({}))

        TestNode1.unregister(component_tags.register)

    def test_node_render_extra_args_and_kwargs(self):
        captured = None

        class TestNode1(BaseNode):
            tag = "mytag"
            allowed_flags = ["required", "default"]

            def render(self, context: Context, name: str, *args, msg: str, **kwargs) -> str:
                nonlocal captured
                captured = name, args, msg, kwargs
                return ""

        TestNode1.register(component_tags.register)

        template1 = Template(
            """
            {% load component_tags %}
            {% mytag 'John'
                123 456 789 msg='Hello' a=1 b=2 c=3 required
                data-id=123 class="pa-4" @click.once="myVar"
            %}
        """
        )
        template1.render(Context({}))
        self.assertEqual(
            captured,
            (
                "John",
                (123, 456, 789),
                "Hello",
                {"a": 1, "b": 2, "c": 3, "data-id": 123, "class": "pa-4", "@click.once": "myVar"},
            ),
        )

        TestNode1.unregister(component_tags.register)


class DecoratorTests(BaseTestCase):
    def test_decorator_requires_tag(self):
        with self.assertRaisesMessage(TypeError, "template_tag() missing 1 required positional argument: 'tag'"):

            @template_tag(component_tags.register)  # type: ignore
            def mytag(node: BaseNode, context: Context) -> str:
                return ""

    # Test that the template tag can be used within the template under the registered tag
    def test_decorator_tags(self):
        @template_tag(component_tags.register, tag="mytag", end_tag="endmytag")
        def render(node: BaseNode, context: Context, name: str, **kwargs) -> str:
            return f"Hello, {name}!"

        # Works with end tag and self-closing
        template_str: types.django_html = """
            {% load component_tags %}
            {% mytag 'John' %}
            {% endmytag %}
            Shorthand: {% mytag 'Mary' / %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        self.assertEqual(rendered.strip(), "Hello, John!\n            Shorthand: Hello, Mary!")

        # But raises if missing end tag
        template_str2: types.django_html = """
            {% load component_tags %}
            {% mytag 'John' %}
        """
        with self.assertRaisesMessage(TemplateSyntaxError, "Unclosed tag on line 3: 'mytag'"):
            Template(template_str2)

        render._node.unregister(component_tags.register)  # type: ignore[attr-defined]

    def test_decorator_no_end_tag(self):
        @template_tag(component_tags.register, tag="mytag")  # type: ignore
        def render(node: BaseNode, context: Context, name: str, **kwargs) -> str:
            return f"Hello, {name}!"

        # Raises with end tag or self-closing
        template_str: types.django_html = """
            {% load component_tags %}
            {% mytag 'John' %}
            {% endmytag %}
            Shorthand: {% mytag 'Mary' / %}
        """
        with self.assertRaisesMessage(TemplateSyntaxError, "Invalid block tag on line 4: 'endmytag'"):
            Template(template_str)

        # Works when missing end tag
        template_str2: types.django_html = """
            {% load component_tags %}
            {% mytag 'John' %}
        """
        template2 = Template(template_str2)
        rendered2 = template2.render(Context({}))
        self.assertEqual(rendered2.strip(), "Hello, John!")

        render._node.unregister(component_tags.register)  # type: ignore[attr-defined]

    def test_decorator_flags(self):
        @template_tag(component_tags.register, tag="mytag", end_tag="endmytag", allowed_flags=["required", "default"])
        def render(node: BaseNode, context: Context, name: str, **kwargs) -> str:
            return ""

        render._node.unregister(component_tags.register)  # type: ignore[attr-defined]

    def test_decorator_render(self):
        # Check that the render function is called with the context
        captured = None

        @template_tag(component_tags.register, tag="mytag")  # type: ignore
        def render(node: BaseNode, context: Context) -> str:
            nonlocal captured
            captured = context.flatten()
            return f"Hello, {context['name']}!"

        template_str = """
            {% load component_tags %}
            {% mytag / %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"name": "John"}))

        self.assertEqual(captured, {"False": False, "None": None, "True": True, "name": "John"})
        self.assertEqual(rendered.strip(), "Hello, John!")

        render._node.unregister(component_tags.register)  # type: ignore[attr-defined]

    def test_decorator_render_raises_if_no_context_arg(self):
        with self.assertRaisesMessage(
            TypeError,
            "Failed to create node class in 'template_tag()' for 'render'",
        ):

            @template_tag(component_tags.register, tag="mytag")  # type: ignore
            def render(node: BaseNode) -> str:  # type: ignore
                return ""

    def test_decorator_render_accepted_params_set_by_render_signature(self):
        captured = None

        @template_tag(component_tags.register, tag="mytag", allowed_flags=["required", "default"])  # type: ignore
        def render(
            node: BaseNode, context: Context, name: str, count: int = 1, *, msg: str, mode: str = "default"
        ) -> str:
            nonlocal captured
            captured = name, count, msg, mode
            return ""

        # Set only required params
        template1 = Template(
            """
            {% load component_tags %}
            {% mytag 'John' msg='Hello' required %}
        """
        )
        template1.render(Context({}))
        self.assertEqual(captured, ("John", 1, "Hello", "default"))

        # Set all params
        template2 = Template(
            """
            {% load component_tags %}
            {% mytag 'John2' count=2 msg='Hello' mode='custom' required %}
        """
        )
        template2.render(Context({}))
        self.assertEqual(captured, ("John2", 2, "Hello", "custom"))

        # Set no params
        template3 = Template(
            """
            {% load component_tags %}
            {% mytag %}
        """
        )
        with self.assertRaisesMessage(
            TypeError, "Invalid parameters for tag 'mytag': missing a required argument: 'name'"
        ):
            template3.render(Context({}))

        # Omit required arg
        template4 = Template(
            """
            {% load component_tags %}
            {% mytag msg='Hello' %}
        """
        )
        with self.assertRaisesMessage(
            TypeError, "Invalid parameters for tag 'mytag': missing a required argument: 'name'"
        ):
            template4.render(Context({}))

        # Omit required kwarg
        template5 = Template(
            """
            {% load component_tags %}
            {% mytag name='John' %}
        """
        )
        with self.assertRaisesMessage(
            TypeError, "Invalid parameters for tag 'mytag': missing a required argument: 'msg'"
        ):
            template5.render(Context({}))

        # Extra args
        template6 = Template(
            """
            {% load component_tags %}
            {% mytag 123 count=1 name='John' %}
        """
        )
        with self.assertRaisesMessage(
            TypeError, "Invalid parameters for tag 'mytag': multiple values for argument 'name'"
        ):
            template6.render(Context({}))

        # Extra args after kwargs
        template6 = Template(
            """
            {% load component_tags %}
            {% mytag count=1 name='John' 123 %}
        """
        )
        with self.assertRaisesMessage(SyntaxError, "positional argument follows keyword argument"):
            template6.render(Context({}))

        # Extra kwargs
        template7 = Template(
            """
            {% load component_tags %}
            {% mytag 'John' msg='Hello' mode='custom' var=123 %}
        """
        )
        with self.assertRaisesMessage(
            TypeError, "Invalid parameters for tag 'mytag': got an unexpected keyword argument 'var'"
        ):
            template7.render(Context({}))

        # Extra kwargs - non-identifier or kwargs
        template7 = Template(
            """
            {% load component_tags %}
            {% mytag 'John' msg='Hello' mode='custom' data-id=123 class="pa-4" @click.once="myVar" %}
        """
        )
        with self.assertRaisesMessage(
            TypeError, "Invalid parameters for tag 'mytag': got an unexpected keyword argument 'data-id'"
        ):
            template7.render(Context({}))

        render._node.unregister(component_tags.register)  # type: ignore[attr-defined]

    def test_decorator_render_extra_args_and_kwargs(self):
        captured = None

        @template_tag(component_tags.register, tag="mytag", allowed_flags=["required", "default"])  # type: ignore
        def render(node: BaseNode, context: Context, name: str, *args, msg: str, **kwargs) -> str:
            nonlocal captured
            captured = name, args, msg, kwargs
            return ""

        template1 = Template(
            """
            {% load component_tags %}
            {% mytag 'John'
                123 456 789 msg='Hello' a=1 b=2 c=3 required
                data-id=123 class="pa-4" @click.once="myVar"
            %}
        """
        )
        template1.render(Context({}))
        self.assertEqual(
            captured,
            (
                "John",
                (123, 456, 789),
                "Hello",
                {"a": 1, "b": 2, "c": 3, "data-id": 123, "class": "pa-4", "@click.once": "myVar"},
            ),
        )

        render._node.unregister(component_tags.register)  # type: ignore[attr-defined]
