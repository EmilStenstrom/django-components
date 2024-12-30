/** This file defines the API of the JS code. */
import { createComponentsManager } from './manager';
import { unescapeJs } from './utils';

export type * from './manager';

export const Components = {
  manager: createComponentsManager(),
  createComponentsManager,
  unescapeJs,
};

// In browser, this is accessed as `Components.manager`, etc
globalThis.Components = Components;
