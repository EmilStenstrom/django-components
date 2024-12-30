/** Set up MutationObserver that watches for `<script>` tags with `data-djc` attribute */
export const observeScriptTag = (onScriptTag: (node: HTMLScriptElement) => void) => {
  const observer = new MutationObserver((mutationsList) => {
    for (const mutation of mutationsList) {
      if (mutation.type === "childList") {
        // Check added nodes
        mutation.addedNodes.forEach((node) => {
          if (
            node.nodeName === "SCRIPT" &&
            (node as HTMLElement).hasAttribute("data-djc")
          ) {
            onScriptTag(node as HTMLScriptElement);
          }
        });
        2;
      }
    }
  });

  // Observe the entire document
  observer.observe(document, {
    childList: true,
    subtree: true, // To detect nodes added anywhere in the DOM
  });

  return observer;
};
