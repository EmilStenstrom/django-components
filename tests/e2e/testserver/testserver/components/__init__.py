from django_components import Component, register, types


@register("inner")
class SimpleComponent(Component):
    template: types.django_html = """
        Variable: <strong class="inner">{{ variable }}</strong>
    """

    css: types.css = """
        .inner {
            font-size: 4px;
        }
    """

    js: types.js = """
        globalThis.testSimpleComponent = 'kapowww!'
    """

    def get_context_data(self, variable, variable2="default"):
        return {
            "variable": variable,
            "variable2": variable2,
        }

    class Media:
        css = "style.css"
        js = "script.js"


@register("outer")
class SimpleComponentNested(Component):
    template: types.django_html = """
        {% load component_tags %}
        <div class="outer">
            {% component "inner" variable=variable / %}
            {% slot "default" default / %}
        </div>
    """

    css: types.css = """
        .outer {
            font-size: 40px;
        }
    """

    js: types.js = """
        globalThis.testSimpleComponentNested = 'bongo!'
    """

    def get_context_data(self, variable):
        return {"variable": variable}

    class Media:
        css = ["style.css", "style2.css"]
        js = "script2.js"


@register("other")
class OtherComponent(Component):
    template: types.django_html = """
        XYZ: <strong class="other">{{ variable }}</strong>
    """

    css: types.css = """
        .other {
            display: flex;
        }
    """

    js: types.js = """
        globalThis.testOtherComponent = 'wowzee!'
    """

    def get_context_data(self, variable):
        return {"variable": variable}

    class Media:
        css = "style.css"
        js = "script.js"
