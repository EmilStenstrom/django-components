import { createComponentsManager } from './manager';

export type * from './manager';
export { createComponentsManager } from './manager';

// If using CDN, this is accessed as `Components.manager`
// If using as a package, import as `import { manager } from "components"`
export const manager = createComponentsManager();

/** Unescape JS that was escaped in Django side with `escape_js` */
export const unescapeJs = (escapedJs: string) => {
  return new DOMParser().parseFromString(escapedJs, 'text/html').documentElement.textContent;
};
