from typing import Literal, NamedTuple

from django_components.util.misc import gen_id


class HighlightColor(NamedTuple):
    text_color: str
    border_color: str


COLORS = {
    "component": HighlightColor(text_color="#2f14bb", border_color="blue"),
    "slot": HighlightColor(text_color="#bb1414", border_color="#e40c0c"),
}


def apply_component_highlight(type: Literal["component", "slot"], output: str, name: str) -> str:
    """
    Wrap HTML (string) in a div with a border and a highlight color.

    This is part of the component / slot highlighting feature. User can toggle on
    to see the component / slot boundaries.
    """
    color = COLORS[type]

    # Because the component / slot name is set via styling as a `::before` pseudo-element,
    # we need to generate a unique ID for each component / slot to avoid conflicts.
    highlight_id = gen_id()

    output = f"""
        <style>
        .{type}-highlight-{highlight_id}::before {{
            content: "{name}: ";
            font-weight: bold;
            color: {color.text_color};
        }}
        </style>
        <div class="{type}-highlight-{highlight_id}" style="border: 1px solid {color.border_color}">
            {output}
        </div>
    """

    return output
