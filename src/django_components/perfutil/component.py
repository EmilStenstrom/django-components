import re
from collections import deque
from typing import Callable, Deque, Dict, List, Optional, Tuple

from django.utils.safestring import mark_safe

# Function that accepts a list of extra HTML attributes to be set on the component's root elements
# and returns the component's HTML content and a dictionary of child components' IDs
# and their root elements' HTML attributes.
#
# In other words, we use this to "delay" the actual rendering of the component's HTML content,
# until we know what HTML attributes to apply to the root elements.
ComponentRenderer = Callable[[Optional[List[str]]], Tuple[str, Dict[str, List[str]]]]

# Render-time cache for component rendering
# See Component._post_render()
component_renderer_cache: Dict[str, ComponentRenderer] = {}
child_component_attrs: Dict[str, List[str]] = {}

nested_comp_pattern = re.compile(r'<template [^>]*?djc-render-id="\w{6}"[^>]*?></template>')
render_id_pattern = re.compile(r'djc-render-id="(?P<render_id>\w{6})"')


# When a component is rendered, we want to apply HTML attributes like `data-djc-id-a1b3cf`
# to all root elements. However, we have to approach it smartly, to minimize the HTML parsing.
#
# If we naively first rendered the child components, and then the parent component, then we would
# have to parse the child's HTML twice (once for itself, and once as part of the parent).
# When we have a deeply nested component structure, this can add up to a lot of parsing.
# See https://github.com/django-components/django-components/issues/14#issuecomment-2596096632.
#
# Imagine we first render the child components. Once rendered, child's HTML gets embedded into
# the HTML of the parent. So by the time we get to the root, we will have to parse the full HTML
# document, even if the root component is only a small part of the document.
#
# So instead, when a nested component is rendered, we put there only a placeholder, and store the
# actual HTML content in `component_renderer_cache`.
#
# ```django
# <div>
#   <h2>...</h2>
#   <template djc-render-id="a1b3cf"></template>
#   <span>...</span>
#   <template djc-render-id="f3d3cf"></template>
# </div>
# ```
#
# The full flow is as follows:
# 1. When a component is nested in another, the child component is rendered, but it returns
#    only a placeholder like `<template djc-render-id="a1b3cf"></template>`.
#    The actual HTML output is stored in `component_renderer_cache`.
# 2. The parent of the child component is rendered normally.
# 3. If the placeholder for the child component is at root of the parent component,
#    then the placeholder may be tagged with extra attributes, e.g. `data-djc-id-a1b3cf`.
#    `<template djc-render-id="a1b3cf" data-djc-id-a1b3cf></template>`.
# 4. When the parent is done rendering, we go back to step 1., the parent component
#    either returns the actual HTML, or a placeholder.
# 5. Only once we get to the root component, that has no further parents, is when we finally
#    start putting it all together.
# 6. We start at the root component. We search the root component's output HTML for placeholders.
#    Each placeholder has ID `data-djc-render-id` that links to its actual content.
# 7. For each found placeholder, we replace it with the actual content.
#    But as part of step 7), we also:
#    - If any of the child placeholders had extra attributes, we cache these, so we can access them
#      once we get to rendering the child component.
#    - And if the parent component had any extra attributes set by its parent, we apply these
#      to the root elements.
# 8. Lastly, we merge all the parts together, and return the final HTML.
def component_post_render(
    renderer: ComponentRenderer,
    render_id: str,
    parent_id: Optional[str],
) -> str:
    # Instead of rendering the component's HTML content immediately, we store it,
    # so we can render the component only once we know if there are any HTML attributes
    # to be applied to the resulting HTML.
    component_renderer_cache[render_id] = renderer

    if parent_id is not None:
        # Case: Nested component
        # If component is nested, return a placeholder
        return mark_safe(f'<template djc-render-id="{render_id}"></template>')

    # Case: Root component - Construct the final HTML by recursively replacing placeholders
    #
    # We first generate the component's HTML content, by calling the renderer.
    #
    # Then we process the component's HTML from root-downwards, going depth-first.
    # So if we have a structure:
    # <div>
    #   <h2>...</h2>
    #   <template djc-render-id="a1b3cf"></template>
    #   <span>...</span>
    #   <template djc-render-id="f3d3cf"></template>
    # </div>
    #
    # Then we first split up the current HTML into parts, splitting at placeholders:
    # - <div><h2>...</h2>
    # - PLACEHOLDER djc-render-id="a1b3cf"
    # - <span>...</span>
    # - PLACEHOLDER djc-render-id="f3d3cf"
    # - </div>
    #
    # And put the pairs of (content, placeholder_id) into a queue:
    # - ("<div><h2>...</h2>", "a1b3cf")
    # - ("<span>...</span>", "f3d3cf")
    # - ("</div>", None)
    #
    # Then we process each part:
    # 1. Append the content to the output
    # 2. If the placeholder ID is not None, then we fetch the renderer by its placeholder ID (e.g. "a1b3cf")
    # 3. If there were any extra attributes set by the parent component, we apply these to the renderer.
    # 4. We split the content by placeholders, and put the pairs of (content, placeholder_id) into the queue,
    #    repeating this whole process until we've processed all nested components.
    content_parts: List[str] = []
    process_queue: Deque[Tuple[str, Optional[str]]] = deque()

    process_queue.append(("", render_id))

    while len(process_queue):
        curr_content_before_component, curr_comp_id = process_queue.popleft()

        # Process content before the component
        if curr_content_before_component:
            content_parts.append(curr_content_before_component)

        # The entry was only a remaining text, no more components to process, we're done
        if curr_comp_id is None:
            continue

        # Generate component's content, applying the extra HTML attributes set by the parent component
        curr_comp_renderer = component_renderer_cache.pop(curr_comp_id)
        # NOTE: This may be undefined, because this is set only for components that
        # are also root elements in their parent's HTML
        curr_comp_attrs = child_component_attrs.pop(curr_comp_id, None)
        curr_comp_content, curr_child_component_attrs = curr_comp_renderer(curr_comp_attrs)

        # Exclude the `data-djc-scope-...` attribute from being applied to the child component's HTML
        for key in list(curr_child_component_attrs.keys()):
            if key.startswith("data-djc-scope-"):
                curr_child_component_attrs.pop(key, None)

        child_component_attrs.update(curr_child_component_attrs)

        # Process the component's content
        last_index = 0
        parts_to_process: List[Tuple[str, Optional[str]]] = []

        # Split component's content by placeholders, and put the pairs of (content, placeholder_id) into the queue
        for match in nested_comp_pattern.finditer(curr_comp_content):
            part_before_component = curr_comp_content[last_index : match.start()]  # noqa: E203
            last_index = match.end()
            comp_part = match[0]

            # Extract the placeholder ID from `<template djc-render-id="a1b3cf"></template>`
            curr_child_id_match = render_id_pattern.search(comp_part)
            if curr_child_id_match is None:
                raise ValueError(f"No placeholder ID found in {comp_part}")
            curr_child_id = curr_child_id_match.group("render_id")
            parts_to_process.append((part_before_component, curr_child_id))

        # Append any remaining text
        if last_index < len(curr_comp_content):
            parts_to_process.append((curr_comp_content[last_index:], None))

        process_queue.extendleft(reversed(parts_to_process))

    output = "".join(content_parts)
    return mark_safe(output)
