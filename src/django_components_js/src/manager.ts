import { callWithAsyncErrorHandling } from './errorHandling';

type MaybePromise<T> = Promise<T> | T;

export interface ComponentContext<
  TData extends object = object,
  TEl extends HTMLElement = HTMLElement,
> {
  $name: string;
  $id: string;
  $data: TData;
  $els: TEl[];
}

export type ComponentFn<TData extends object = object, TEl extends HTMLElement = HTMLElement> = (
  ctx: ComponentContext<TData, TEl>
) => MaybePromise<any>;

export type DataFn = () => object;

export type ScriptType = 'js' | 'css';

/**
 * Usage:
 *
 * ```js
 * Components.registerComponent("table", async ({ $id, $name, $data, $els }) => {
 *   ...
 * });
 * ```
 *
 * ```js
 * Components.registerComponentData("table", "3d09cf", () => {
 *   return JSON.parse('{ "abc": 123 }');
 * });
 * ```
 *
 * ```js
 * Components.callComponent("table", 12345, "3d09cf");
 * ```
 *
 * ```js
 * Components.loadScript("js", '<script src="/abc/def"></script>');
 * ```
 *
 * ```js
 * Components.markScriptLoaded("js", '/abc/def');
 * ```
 */
export const createComponentsManager = () => {
  const loadedJs = new Set<string>();
  const loadedCss = new Set<string>();
  const components: Record<string, ComponentFn> = {};
  const componentInputs: Record<string, DataFn> = {};

  const parseScriptTag = (tag: string) => {
    const scriptNode = new DOMParser().parseFromString(tag, 'text/html').querySelector('script');
    if (!scriptNode) {
      throw Error(
        '[Components] Failed to extract <script> tag. Make sure that the string contains' +
          ' <script></script> and is a valid HTML'
      );
    }
    return scriptNode;
  };

  const parseLinkTag = (tag: string) => {
    const linkNode = new DOMParser().parseFromString(tag, 'text/html').querySelector('link');
    if (!linkNode) {
      throw Error(
        '[Components] Failed to extract <link> tag. Make sure that the string contains' +
          ' <link></link> and is a valid HTML'
      );
    }
    return linkNode;
  };

  // NOTE: The way we turn the string into an HTMLElement, if we then try to
  // insert the node into the Document, it will NOT load. So instead we create
  // a <script> that that WILL load once inserted, and copy all attributes from
  // one to the other.
  // Might be related to https://security.stackexchange.com/a/240362/302733
  // See https://stackoverflow.com/questions/13121948
  const cloneNode = (srcNode: HTMLElement) => {
    const targetNode = document.createElement(srcNode.tagName);
    for (const attr of srcNode.attributes) {
      targetNode.setAttributeNode(attr.cloneNode() as Attr);
    }
    return targetNode;
  };

  const loadScript = (type: ScriptType, tag: string) => {
    if (type === 'js') {
      const srcScriptNode = parseScriptTag(tag);

      // Use `.getAttribute()` instead of `.src` so we get the value as is,
      // without the host name prepended if URL is just a path.
      const src = srcScriptNode.getAttribute('src');
      if (!src || loadedJs.has(src)) return;

      loadedJs.add(src);

      const targetScriptNode = cloneNode(srcScriptNode);

      // In case of JS scripts, we return a Promise that resolves when the script is loaded
      // See https://stackoverflow.com/a/57267538/9788634
      return new Promise<void>((resolve, reject) => {
        targetScriptNode.onload = () => {
          resolve();
        };

        // Insert the script at the end of <body> to follow convention
        globalThis.document.body.append(targetScriptNode);
      });
    } else if (type === 'css') {
      const linkNode = parseLinkTag(tag);
      // NOTE: Use `.getAttribute()` instead of `.href` so we get the value as is,
      // without the host name prepended if URL is just a path.
      const href = linkNode.getAttribute('href');
      if (!href || loadedCss.has(href)) return;

      // Insert at the end of <head> to follow convention
      const targetLinkNode = cloneNode(linkNode);
      globalThis.document.head.append(targetLinkNode);
      loadedCss.add(href);

      // For CSS, we return a dummy Promise, since we don't need to wait for anything
      return Promise.resolve();
    } else {
      throw Error(
        `[Components] loadScript received invalid script type '${type}'. Must be one of 'js', 'css'`
      );
    }
  };

  const markScriptLoaded = (type: ScriptType, url: string) => {
    if (type === 'js') {
      loadedJs.add(url);
    } else if (type === 'css') {
      loadedCss.add(url);
    } else {
      throw Error(
        `[Components] markScriptLoaded received invalid script type '${type}'. Must be one of 'js', 'css'`
      );
    }
  };

  const registerComponent = (name: string, compFn: ComponentFn) => {
    components[name] = compFn;
  };

  /**
   * @example
   * Components.registerComponentData("table", "a1b2c3", () => {{
   *   return JSON.parse('{ "a": 2 }');
   * }});
   */
  const registerComponentData = (name: string, inputHash: string, dataFactory: DataFn) => {
    const key = `${name}:${inputHash}`;
    componentInputs[key] = dataFactory;
  };

  const callComponent = (name: string, compId: string, inputHash: string): MaybePromise<any> => {
    const initFn = components[name];
    if (!initFn) throw Error(`[Components] No component registered for name '${name}'`);

    const elems = Array.from(document.querySelectorAll<HTMLElement>(`[data-comp-id-${compId}]`));
    if (!elems.length) throw Error(`[Components] No elements with component ID '${compId}' found`);

    const dataKey = `${name}:${inputHash}`;
    const dataFactory = componentInputs[dataKey];
    if (!dataFactory) throw Error(`[Components] Cannot find input for hash '${inputHash}'`);

    const data = dataFactory();

    const ctx = {
      $name: name,
      $id: compId,
      $data: data,
      $els: elems,
    } satisfies ComponentContext;

    return callWithAsyncErrorHandling(initFn, [ctx]);
  };

  return {
    callComponent,
    registerComponent,
    registerComponentData,
    loadScript,
    markScriptLoaded,
  };
};
