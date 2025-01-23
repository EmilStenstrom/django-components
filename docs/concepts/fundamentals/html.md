---
title: HTML
weight: 7
---

Component HTML is the HTML template associated with the component.

Unlike regular Django templates, component HTML supports extra syntax that makes it possible to write components like in Vue or React (JSX).

## Self-closing tags

Inside the component HTML template, you can use self-closing tags for any tags.

Normally, HTML allows the syntax `<tag />` only for the [void elements](https://developer.mozilla.org/en-US/docs/Glossary/Void_element) like `<img />`, `<br />`, etc.

However, in django_components, you can use self-closing tags for other tags too. These will be
automatically expanded at render.

For example, this:

```html
<div style="background-image: url('...');" />
```

becomes

```html
<div style="background-image: url('...');">
</div>
```
