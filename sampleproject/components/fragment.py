from django_components import Component, types


# Common logic for all FragmentBase components
class _FragmentBase(Component):
    def get(self, request):
        return self.render_to_response()


# HTML into which a fragment will be loaded using vanilla JS
class FragmentBaseJs(_FragmentBase):
    template: types.django_html = """
        {% load component_tags %}
        <!DOCTYPE html>
        <html>
            <head>
                {% component_css_dependencies %}
            </head>
            <body>
                <div id="target">OLD</div>

                <button id="loader">
                  Click me!
                </button>
                <script>
                    const url = `/fragment/frag/js`;
                    document.querySelector('#loader').addEventListener('click', function () {
                        fetch(url)
                            .then(response => response.text())
                            .then(html => {
                                console.log({ fragment: html })
                                document.querySelector('#target').outerHTML = html;
                            });
                    });
                </script>

                {% component_js_dependencies %}
            </body>
        </html>
    """


# HTML into which a fragment will be loaded using AlpineJs
class FragmentBaseAlpine(_FragmentBase):
    template: types.django_html = """
        {% load component_tags %}
        <!DOCTYPE html>
        <html>
            <head>
                {% component_css_dependencies %}
                <script defer src="https://unpkg.com/alpinejs"></script>
            </head>
            <body x-data="{
                htmlVar: 'OLD',
                loadFragment: function () {
                    const url = '/fragment/frag/alpine';
                    fetch(url)
                        .then(response => response.text())
                        .then(html => {
                            console.log({ fragment: html });
                            this.htmlVar = html;
                        });
                }
            }">
                <div id="target" x-html="htmlVar">OLD</div>

                <button id="loader" @click="loadFragment">
                  Click me!
                </button>

                {% component_js_dependencies %}
            </body>
        </html>
    """


# HTML into which a fragment will be loaded using HTMX
class FragmentBaseHtmx(_FragmentBase):
    template: types.django_html = """
        {% load component_tags %}
        <!DOCTYPE html>
        <html>
            <head>
                {% component_css_dependencies %}
                <script src="https://unpkg.com/htmx.org@1.9.12"></script>
            </head>
            <body>
                <div id="target">OLD</div>

                <button id="loader" hx-get="/fragment/frag/js" hx-swap="outerHTML" hx-target="#target">
                  Click me!
                </button>

                {% component_js_dependencies %}
            </body>
        </html>
    """


# Common logic for all Frag components
class _Frag(Component):
    def get(self, request):
        return self.render_to_response(type="fragment")


# Fragment where the JS and CSS are defined on the Component
class FragJs(_Frag):
    template: types.django_html = """
        <div class="frag">
            123
            <span id="frag-text"></span>
        </div>
    """

    js: types.js = """
        document.querySelector('#frag-text').textContent = 'xxx';
    """

    css: types.css = """
        .frag {
            background: blue;
        }
    """


# Fragment that defines an AlpineJS component
class FragAlpine(_Frag):
    # NOTE: We wrap the actual fragment in a template tag with x-if="false" to prevent it
    #       from being rendered until we have registered the component with AlpineJS.
    template: types.django_html = """
    <template x-if="false" data-name="frag">
        <div class="frag">
            123
            <span x-data="frag" x-text="fragVal">
            </span>
        </div>
    </template>
    """

    js: types.js = """
        Alpine.data('frag', () => ({
            fragVal: 'xxx',
        }));

        // Now that the component has been defined in AlpineJS, we can "activate" all instances
        // where we use the `x-data="frag"` directive.
        document.querySelectorAll('[data-name="frag"]').forEach((el) => {
            el.setAttribute('x-if', 'true');
        });
    """

    css: types.css = """
        .frag {
            background: blue;
        }
    """
