import re

from django.forms import Media

RENDERED_COMPONENTS_CONTEXT_KEY = "_COMPONENT_DEPENDENCIES"
CSS_DEPENDENCY_PLACEHOLDER = '<link name="CSS_PLACEHOLDER" href="#">'
JS_DEPENDENCY_PLACEHOLDER = '<src name="JS_PLACEHOLDER" href="#">'


def component_dependency_middleware_factory(get_response):
    dependency_regex_value_as_bytes = bytes('{}|{}'.format(CSS_DEPENDENCY_PLACEHOLDER, JS_DEPENDENCY_PLACEHOLDER),
                                            encoding='utf-8')
    dependency_regex = re.compile(dependency_regex_value_as_bytes)

    def component_dependency_middleware(request):
        response = get_response(request)
        assert response.is_rendered, "Component dependency middleware received unrendered response"

        if not hasattr(response, 'add_post_render_callback'):
            raise TypeError('Component dependency middleware expected response to have add_post_render_callback')

        def component_dependency_callback(rendered_response):
            rendered_components = rendered_response.context_data.get(RENDERED_COMPONENTS_CONTEXT_KEY, [])
            required_media = join_media(rendered_components)

            replacer = DependencyReplacer(required_media.render_css(), required_media.render_js(),
                                          response_encoding=rendered_response.charset)
            response.content = re.sub(dependency_regex, replacer, response.content)

        response.add_post_render_callback(component_dependency_callback)
        return response

    return component_dependency_middleware


class DependencyReplacer:
    """Replacer for use in re.sub that replaces the first placeholder CSS and JS
    tags it encounters and removes any subsequent ones."""

    CSS_PLACEHOLDER = bytes(CSS_DEPENDENCY_PLACEHOLDER, encoding='utf-8')
    JS_PLACEHOLDER = bytes(JS_DEPENDENCY_PLACEHOLDER, encoding='utf-8')

    def __init__(self, css_string, js_string, response_encoding='utf-8'):
        self.response_encoding = response_encoding
        self.js_string = js_string
        self.css_string = css_string

    def __call__(self, match):
        if match[0] == self.CSS_PLACEHOLDER:
            replacement = self.css_string
            self.css_string = b""
            return self.encode(replacement)
        elif match[0] == self.JS_PLACEHOLDER:
            replacement = self.js_string
            self.js_string = b""
            return self.encode(replacement)
        raise AssertionError('Invalid match for DependencyReplacer' + match)

    def encode(self, s):
        return bytes(s, encoding=self.response_encoding)


def join_media(components):
    """Return combined media object for iterable of components."""

    return sum([component.media for component in components], Media())
