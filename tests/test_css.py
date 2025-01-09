from django.utils.safestring import mark_safe

from django_components import Component, register, types

from .django_test_setup import setup_test_config
from .testutils import BaseTestCase, parametrize_context_behavior

setup_test_config({"autodiscover": False})

# TODO: DOCUMENT
# - Base case
# - Break out of the scope by using `:root`
# - Removes CSS comments
# - E2E test with two HTML snippets next to each other, where one would be CSS-scoped, while other not
# - Does NOT add `scope_id` to pseudo-classes
# - Does NOT add HTML attribute to Components without CSS or `css_scoped=False`
# - Applies `[data-djc-scope-abc123]` to every HTML element (even nested) until we hit nested components
# - Slot fill that was defined in the template is scoped too
# - Slot fill that was NOT defined in the template is NOT scoped by default
# - Slot fill that was NOT defined in the template CAN be scoped optionally
# - E2E test with two HTML snippets next to each other, where one would be CSS-scoped, while other not
# - MENTION THAT NO 2 COMPONENTS CAN SHARE THE SAME CLASS NAME __AND__ FILE NAME
#   - Maybe change logic for component class hash, so this is not a problem?
#     - See https://stackoverflow.com/questions/1252357
# - Add support for `>>>` or `/deep/` selectors, see https://vue-loader.vuejs.org/guide/scoped-css.html#deep-selectors


class ScopedCssTests(BaseTestCase):
    @parametrize_context_behavior(["django", "isolated"])
    def test_no_action_when_no_css(self):
        class TestComponent(Component):
            def get_context_data(self, variable=None):
                return {
                    "variable": variable,
                }

            template: types.django_html = """
                {% load component_tags %}
                <div>
                    <h1>Parent content</h1>
                    Variable: <strong>{{ variable }}</strong>
                    <strong class="foo">Foo</strong>
                </div>
                {% component_css_dependencies %}
            """
            css = None
            css_scoped = True

        rendered = TestComponent.render(kwargs={"variable": "test"})
        self.assertInHTML(
            rendered,
            """
            <div data-djc-id-a1bc3e>
                <h1>Parent content</h1>
                Variable: <strong>test</strong>
                <strong class="foo">Foo</strong>
            </div>
            """,
            count=1,
        )
        self.assertNotIn("<style", rendered)

    @parametrize_context_behavior(["django", "isolated"])
    def test_no_action_when_not_scoped(self):
        class TestComponent(Component):
            def get_context_data(self, variable=None):
                return {
                    "variable": variable,
                }

            template: types.django_html = """
                {% load component_tags %}
                <div>
                    <h1>Parent content</h1>
                    Variable: <strong>{{ variable }}</strong>
                    <strong class="foo">Foo</strong>
                </div>
                {% component_css_dependencies %}
            """
            css = """
                /* Example CSS */
                div {
                    color: red;
                }
                div > .foo, .foo:hover {
                    color: red;
                }
            """
            css_scoped = False

        rendered = TestComponent.render(kwargs={"variable": "test"})
        self.assertInHTML(
            """
            <div data-djc-id-a1bc3e>
                <h1>Parent content</h1>
                Variable: <strong>test</strong>
                <strong class="foo">Foo</strong>
            </div>
            """,
            rendered,
            count=1,
        )
        self.assertInHTML(
            """
            <style>
                /* Example CSS */
                div { color: red; }
                div > .foo, .foo:hover { color: red; }
            </style>
            """,
            rendered,
            count=1,
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_scopes_css(self):
        class TestComponent(Component):
            def get_context_data(self, variable=None):
                return {
                    "variable": variable,
                }

            template: types.django_html = """
                {% load component_tags %}
                <div>
                    <h1>Parent content</h1>
                    Variable: <strong>{{ variable }}</strong>
                    <strong class="foo">Foo</strong>
                </div>
                {% component_css_dependencies %}
            """
            css = """
                /* Example CSS */
                div {
                    color: red;
                }
                div > .foo, .foo:hover {
                    color: red;
                }
            """
            css_scoped = True

        rendered = TestComponent.render(kwargs={"variable": "test"})
        self.assertInHTML(
            """
            <div data-djc-id-a1bc3e data-djc-scope-a6b94c>
                <h1 data-djc-scope-a6b94c>Parent content</h1>
                Variable: <strong data-djc-scope-a6b94c>test</strong>
                <strong class="foo" data-djc-scope-a6b94c>Foo</strong>
            </div>
            """,
            rendered,
            count=1,
        )
        self.assertInHTML(
            """
            <style>
            div[data-djc-scope-a6b94c] { color: red; }
            div[data-djc-scope-a6b94c] > .foo[data-djc-scope-a6b94c], .foo:hover[data-djc-scope-a6b94c] {
                color: red;
            }
            </style>
            """,
            rendered,
            count=1,
        )

    # Check that we can "break out" of the scope by using `:root`
    @parametrize_context_behavior(["django", "isolated"])
    def test_ignores_selectors_starting_with_root(self):
        class TestComponent(Component):
            def get_context_data(self, variable=None):
                return {
                    "variable": variable,
                }

            template: types.django_html = """
                {% load component_tags %}
                <div>
                    <h1>Parent content</h1>
                    Variable: <strong>{{ variable }}</strong>
                    <strong class="foo">Foo</strong>
                </div>
                {% component_css_dependencies %}
            """
            css = """
                /* Example CSS */
                div {
                    color: red;
                }
                :root div > .foo, .foo:hover, :root > .foo:hover {
                    color: red;
                }
            """
            css_scoped = True

        rendered = TestComponent.render(kwargs={"variable": "test"})
        self.assertInHTML(
            """
            <div data-djc-id-a1bc3e data-djc-scope-d0c57f>
                <h1 data-djc-scope-d0c57f>Parent content</h1>
                Variable: <strong data-djc-scope-d0c57f>test</strong>
                <strong class="foo" data-djc-scope-d0c57f>Foo</strong>
            </div>
            """,
            rendered,
            count=1,
        )
        self.assertInHTML(
            """
            <style>
            div[data-djc-scope-d0c57f] { color: red; }
            :root div > .foo, .foo:hover[data-djc-scope-d0c57f], :root > .foo:hover {
                color: red;
            }
            </style>
            """,
            rendered,
            count=1,
        )

    # Check that, while `:root` allows us to  "break out" of the scope, other selectors, like `:visited`
    # are still scoped.
    @parametrize_context_behavior(["django", "isolated"])
    def test_non_root_selectors_not_ignored(self):
        class TestComponent(Component):
            def get_context_data(self, variable=None):
                return {
                    "variable": variable,
                }

            template: types.django_html = """
                {% load component_tags %}
                <div>
                    <h1>Parent content</h1>
                    Variable: <strong>{{ variable }}</strong>
                    <strong class="foo">Foo</strong>
                </div>
                {% component_css_dependencies %}
            """
            css = """
                /* Example CSS */
                div {
                    color: red;
                }
                :visited div > .foo, .foo:visited, :visited > .foo:visited {
                    color: red;
                }
            """
            css_scoped = True

        rendered = TestComponent.render(kwargs={"variable": "test"})
        self.assertInHTML(
            """
            <div data-djc-id-a1bc3e data-djc-scope-a17556>
                <h1 data-djc-scope-a17556>Parent content</h1>
                Variable: <strong data-djc-scope-a17556>test</strong>
                <strong class="foo" data-djc-scope-a17556>Foo</strong>
            </div>
            """,
            rendered,
            count=1,
        )
        self.assertInHTML(
            """
            <style>
            div[data-djc-scope-a17556] { color: red; }
            :visited[data-djc-scope-a17556] div[data-djc-scope-a17556] > .foo[data-djc-scope-a17556], .foo:visited[data-djc-scope-a17556], :visited[data-djc-scope-a17556] > .foo:visited[data-djc-scope-a17556] {
                color: red;
            }
            </style>
            """,  # noqa: E501
            rendered,
            count=1,
        )

    # Check that the CSS scope is applied to every HTML element that's part of this component's
    # template, but it does NOT modify HTML elements belonging to nested components
    @parametrize_context_behavior(["django", "isolated"])
    def test_css_scope_not_applied_to_nested_components(self):
        @register("nested")
        class NestedComponent(Component):
            template: types.django_html = """
                <div>
                    <h2>Nested content</h1>
                    <strong class="foo">Foo</strong>
                </div>
            """
            css_scoped = False

        class TestComponent(Component):
            def get_context_data(self, variable=None):
                return {
                    "variable": variable,
                }

            template: types.django_html = """
                {% load component_tags %}
                <div>
                    <h1>Parent content</h1>
                    Variable: <strong>{{ variable }}</strong>
                    <strong class="foo">
                        Foo
                        <span>Bar</span>
                        {% component 'nested' / %}
                        <span>Baz</span>
                    </strong>
                </div>
                {% component_css_dependencies %}
            """
            css = """
                /* Example CSS */
                div {
                    color: red;
                }
                :visited div > .foo, .foo:visited, :visited > .foo:visited {
                    color: red;
                }
            """
            css_scoped = True

        rendered = TestComponent.render(kwargs={"variable": "test"})

        self.assertInHTML(
            """
            <div data-djc-id-a1bc3e data-djc-scope-ffc2f4>
                <h1 data-djc-scope-ffc2f4>Parent content</h1>
                Variable: <strong data-djc-scope-ffc2f4>test</strong>
                <strong class="foo" data-djc-scope-ffc2f4>
                    Foo
                    <span data-djc-scope-ffc2f4>Bar</span>

                    <div data-djc-id-a1bc41="">
                        <h2>Nested content
                            <strong class="foo">Foo</strong>
                        </h2>
                    </div>

                    <span data-djc-scope-ffc2f4>Baz</span>
                </strong>
            </div>
            """,
            rendered,
            count=1,
        )
        self.assertInHTML(
            """
            <style>
            div[data-djc-scope-ffc2f4] { color: red; }
            :visited[data-djc-scope-ffc2f4] div[data-djc-scope-ffc2f4] > .foo[data-djc-scope-ffc2f4], .foo:visited[data-djc-scope-ffc2f4], :visited[data-djc-scope-ffc2f4] > .foo:visited[data-djc-scope-ffc2f4] {
                color: red;
            }
            </style>
            """,  # noqa: E501
            rendered,
            count=1,
        )

    # Check that the CSS scope is applied inside the template imported with `{% include %}`
    @parametrize_context_behavior(["django", "isolated"])
    def test_css_scope_is_applied_to_included_template(self):
        class TestComponent(Component):
            def get_context_data(self, variable=None):
                return {
                    "variable": variable,
                }

            template: types.django_html = """
                {% load component_tags %}
                <div>
                    <h1>Parent content</h1>
                    Variable: <strong>{{ variable }}</strong>
                    <strong class="foo">
                        Foo
                        <span>Bar</span>
                        {% include 'slotted_template.html' %}
                        <span>Baz</span>
                    </strong>
                </div>
                {% component_css_dependencies %}
            """
            css = """
                /* Example CSS */
                div {
                    color: red;
                }
                :visited div > .foo, .foo:visited, :visited > .foo:visited {
                    color: red;
                }
            """
            css_scoped = True

        rendered = TestComponent.render(kwargs={"variable": "test"})

        self.assertInHTML(
            """
            <div data-djc-id-a1bc3e data-djc-scope-1127dd>
                <h1 data-djc-scope-1127dd>Parent content</h1>
                Variable: <strong data-djc-scope-1127dd>test</strong>
                <strong class="foo" data-djc-scope-1127dd>
                    Foo
                    <span data-djc-scope-1127dd>Bar</span>

                    <custom-template data-djc-scope-1127dd>
                        <header data-djc-scope-1127dd>Default header</header>
                        <main data-djc-scope-1127dd>Default main</main>
                        <footer data-djc-scope-1127dd>Default footer</footer>
                    </custom-template>

                    <span data-djc-scope-1127dd>Baz</span>
                </strong>
            </div>
            """,
            rendered,
            count=1,
        )
        self.assertInHTML(
            """
            <style>
            div[data-djc-scope-1127dd] { color: red; }
            :visited[data-djc-scope-1127dd] div[data-djc-scope-1127dd] > .foo[data-djc-scope-1127dd], .foo:visited[data-djc-scope-1127dd], :visited[data-djc-scope-1127dd] > .foo:visited[data-djc-scope-1127dd] {
                color: red;
            }
            </style>
            """,  # noqa: E501
            rendered,
            count=1,
        )

    # If the component is set to apply CSS scoping, we want to apply it to the slot fills
    # that were defined as part of the original template file - AKA the content inside
    # the `{% fill %}` tags that you can see in the template file - This is consistent with
    # Vue's scoped CSS behavior.
    #
    # As for the other slot fills, e.g. those that were passed in as functions, those are NOT scoped
    # by default. And instead, users can opt-in by passing in a Slot instance with `apply_css=True`.
    @parametrize_context_behavior(["django", "isolated"])
    def test_css_scope_is_applied_to_intemplate_slot_fills(self):
        @register("nested")
        class NestedComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div>
                    <h2>Nested content</h1>
                    <strong class="foo">Foo</strong>
                    <span>{% slot "content" default / %}</span>
                    <footer>{% slot "footer" / %}</footer>
                </div>
            """
            css_scoped = False

        class TestComponent(Component):
            def get_context_data(self, variable=None):
                return {
                    "variable": variable,
                }

            template: types.django_html = """
                {% load component_tags %}
                <div>
                    <h1>Parent content</h1>
                    Variable: <strong>{{ variable }}</strong>
                    <strong class="foo">
                        Foo
                        <span>Bar</span>
                        {% component "nested" %}
                            {% fill "content" %}
                                <span>
                                    Main content
                                    <strong>Main foo</strong>
                                </span>
                            {% endfill %}
                            {% fill "footer" %}
                                <span>
                                    Footer content
                                    <strong>Footer foo</strong>
                                </span>
                            {% endfill %}
                        {% endcomponent %}
                        <span>Baz</span>
                    </strong>
                </div>
                {% component_css_dependencies %}
            """
            css = """
                /* Example CSS */
                div {
                    color: red;
                }
                :visited div > .foo, .foo:visited, :visited > .foo:visited {
                    color: red;
                }
            """
            css_scoped = True

        rendered = TestComponent.render(kwargs={"variable": "test"})

        self.assertInHTML(
            """
            <div data-djc-id-a1bc3e data-djc-scope-60c583>
                <h1 data-djc-scope-60c583>Parent content</h1>
                Variable: <strong data-djc-scope-60c583>test</strong>
                <strong class="foo" data-djc-scope-60c583>
                    Foo
                    <span data-djc-scope-60c583>Bar</span>

                    <div data-djc-id-a1bc43>
                        <h2>
                            Nested content
                            <strong class="foo">Foo</strong>
                            <span>
                                <span data-djc-scope-60c583>
                                    Main content
                                    <strong data-djc-scope-60c583>Main foo</strong>
                                </span>
                            </span>
                            <footer>
                                <span data-djc-scope-60c583>
                                    Footer content
                                    <strong data-djc-scope-60c583>Footer foo</strong>
                                </span>
                            </footer>
                        </h2>
                    </div>

                    <span data-djc-scope-60c583>Baz</span>
                </strong>
            </div>
            """,
            rendered,
            count=1,
        )
        self.assertInHTML(
            """
            <style>
            div[data-djc-scope-60c583] { color: red; }
            :visited[data-djc-scope-60c583] div[data-djc-scope-60c583] > .foo[data-djc-scope-60c583], .foo:visited[data-djc-scope-60c583], :visited[data-djc-scope-60c583] > .foo:visited[data-djc-scope-60c583] {
                color: red;
            }
            </style>
            """,  # noqa: E501
            rendered,
            count=1,
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_css_scope_is_not_applied_by_default_to_non_template_slot_fills(self):
        @register("nested")
        class NestedComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div>
                    <h2>Nested content</h1>
                    <strong class="foo">Foo</strong>
                    <span>{% slot "content" default / %}</span>
                    <footer>{% slot "footer" / %}</footer>
                </div>
            """
            css_scoped = False

        class TestComponent(Component):
            def get_context_data(self):
                nested_content = NestedComponent.render(
                    context=self.input.context,
                    slots={
                        "content": self.input.slots["content"],
                        "footer": self.input.slots["footer"],
                    }
                )
                return {
                    "nested_content": nested_content,
                }

            template: types.django_html = """
                {% load component_tags %}
                <div>
                    <h1>Parent content</h1>
                    <strong class="foo">
                        Foo
                        <span>Bar</span>
                        {{ nested_content|safe }}
                        <span>Baz</span>
                    </strong>
                </div>
                {% component_css_dependencies %}
            """
            css = """
                /* Example CSS */
                div {
                    color: red;
                }
                :visited div > .foo, .foo:visited, :visited > .foo:visited {
                    color: red;
                }
            """
            css_scoped = True

        rendered = TestComponent.render(
            slots={
                "content": mark_safe("<span> Main content <strong>Main foo</strong></span>"),
                "footer": mark_safe("<span> Footer content <strong>Footer foo</strong></span>"),
            },
        )

        self.assertInHTML(
            """
            <div data-djc-id-a1bc3e data-djc-scope-d14013>
                <h1 data-djc-scope-d14013>Parent content</h1>
                <strong class="foo" data-djc-scope-d14013>
                    Foo
                    <span data-djc-scope-d14013>Bar</span>

                    <div data-djc-id-a1bc3f>
                        <h2>
                            Nested content
                            <strong class="foo">Foo</strong>
                            <span>
                                <span>
                                    Main content
                                    <strong>Main foo</strong>
                                </span>
                            </span>
                            <footer>
                                <span>
                                    Footer content
                                    <strong>Footer foo</strong>
                                </span>
                            </footer>
                        </h2>
                    </div>

                    <span data-djc-scope-d14013>Baz</span>
                </strong>
            </div>
            """,
            rendered,
            count=1,
        )
        self.assertInHTML(
            """
            <style>
            div[data-djc-scope-d14013] { color: red; }
            :visited[data-djc-scope-d14013] div[data-djc-scope-d14013] > .foo[data-djc-scope-d14013], .foo:visited[data-djc-scope-d14013], :visited[data-djc-scope-d14013] > .foo:visited[data-djc-scope-d14013] {
                color: red;
            }
            </style>
            """,  # noqa: E501
            rendered,
            count=1,
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_css_scope_is_applied_if_non_template_slot_fills_opt_in(self):
        @register("nested")
        class NestedComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div>
                    <h2>Nested content</h1>
                    <strong class="foo">Foo</strong>
                    <span>{% slot "content" default / %}</span>
                    <footer>{% slot "footer" / %}</footer>
                </div>
            """
            css_scoped = False

        class TestComponent(Component):
            # We render `NestedComponent` here and not in `get_context_data()`
            # so that `NestedComponent` has access to the parent component `TestComponent`.
            def on_render_before(self, context, template):
                # Opt-in to CSS scoping
                self.input.slots["content"].apply_css = True
                self.input.slots["footer"].apply_css = True

                nested_content = NestedComponent.render(
                    context=self.input.context,
                    slots={
                        "content": self.input.slots["content"],
                        "footer": self.input.slots["footer"],
                    }
                )
                context["nested_content"] = nested_content

            template: types.django_html = """
                {% load component_tags %}
                <div>
                    <h1>Parent content</h1>
                    <strong class="foo">
                        Foo
                        <span>Bar</span>
                        {{ nested_content|safe }}
                        <span>Baz</span>
                    </strong>
                </div>
                {% component_css_dependencies %}
            """
            css = """
                /* Example CSS */
                div {
                    color: red;
                }
                :visited div > .foo, .foo:visited, :visited > .foo:visited {
                    color: red;
                }
            """
            css_scoped = True

        rendered = TestComponent.render(
            slots={
                "content": mark_safe("<span> Main content <strong>Main foo</strong></span>"),
                "footer": mark_safe("<span> Footer content <strong>Footer foo</strong></span>"),
            },
        )

        self.assertInHTML(
            """
            <div data-djc-id-a1bc3e data-djc-scope-eb8ef9>
                <h1 data-djc-scope-eb8ef9>Parent content</h1>
                <strong class="foo" data-djc-scope-eb8ef9>
                    Foo
                    <span data-djc-scope-eb8ef9>Bar</span>

                    <div data-djc-id-a1bc40>
                        <h2>
                            Nested content
                            <strong class="foo">Foo</strong>
                            <span>
                                <span data-djc-scope-eb8ef9>
                                    Main content
                                    <strong data-djc-scope-eb8ef9>Main foo</strong>
                                </span>
                            </span>
                            <footer>
                                <span data-djc-scope-eb8ef9>
                                    Footer content
                                    <strong data-djc-scope-eb8ef9>Footer foo</strong>
                                </span>
                            </footer>
                        </h2>
                    </div>

                    <span data-djc-scope-eb8ef9>Baz</span>
                </strong>
            </div>
            """,
            rendered,
            count=1,
        )
        self.assertInHTML(
            """
            <style>
            div[data-djc-scope-eb8ef9] { color: red; }
            :visited[data-djc-scope-eb8ef9] div[data-djc-scope-eb8ef9] > .foo[data-djc-scope-eb8ef9], .foo:visited[data-djc-scope-eb8ef9], :visited[data-djc-scope-eb8ef9] > .foo:visited[data-djc-scope-eb8ef9] {
                color: red;
            }
            </style>
            """,  # noqa: E501
            rendered,
            count=1,
        )
