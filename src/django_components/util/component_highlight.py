from typing import Literal, NamedTuple


class HighlightColor(NamedTuple):
    text_color: str
    border_color: str


COLORS = {
    "component": HighlightColor(text_color="#2f14bb", border_color="blue"),
    "slot": HighlightColor(text_color="#bb1414", border_color="red"),
}


def apply_component_highlight(type: Literal["component", "slot"], output: str, name: str) -> str:
    """
    Wrap HTML (string) in a div with a border and a highlight color.

    This is part of the component / slot highlighting feature. User can toggle on
    to see the component / slot boundaries.
    """
    color = COLORS[type]

    output = f"""
        <div style="
            border-radius: 12px;
            padding: 4px;
            margin: 4px;
            border: 1px solid {color.border_color};
            transition: all 0.2s ease;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3), 0 2px 6px rgba(0, 0, 0, 0.2);
        ">
            <p style="
                background: white;
                color: {color.text_color};
                font-weight: 600;
                border-radius: 6px;
                padding: 2px;
            ">{name}</p>
            {output}
        </div>
    """

    return output
