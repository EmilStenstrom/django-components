# Django componnets JS

## Usage

```js
// Register a function that is run at component initialization
Components.manager.registerComponent(
  "table",  // Component name
  async ({ $id, $name, $data, $els }) => {
    ...
  },
);

// Register data factory function that may be used by multiple
// components.
Components.registerComponentData(
  "table",  // Component name
  "3d09cf", // Input ID
  () => {
    return JSON.parse('{ "abc": 123 }');
  },
);

// Once the component and data factories are registered,
// we can run component's init function
Components.callComponent(
  "table",  // Component name
  12345,    // Component ID - An HTML element with corresponding
            //                attribute (`data-comp-id-12345`) MUST
            //                be present in the DOM.
  "3d09cf", // Input ID
);

// Load JS or CSS script if not laoded already
Components.loadScript("js", '<script src="/abc/def">');

// Or mark one as already-loaded, so it is ignored when
// we call `loadScript`
Components.markScriptLoaded("js", '/abc/def');
```
