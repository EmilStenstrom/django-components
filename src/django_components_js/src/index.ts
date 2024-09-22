/** This file defines the API of the JS code. */
import { createComponentsManager } from './manager';

export type * from './manager';

export const Components = (() => {
  const manager = createComponentsManager();

  /** Unescape JS that was escaped in Django side with `escape_js` */
  const unescapeJs = (escapedJs: string) => {
    return new DOMParser().parseFromString(escapedJs, 'text/html').documentElement.textContent;
  };

  return {
    manager,
    createComponentsManager,
    unescapeJs,
  };
})();

// In browser, this is accessed as `Components.manager`, etc
globalThis.Components = Components;
