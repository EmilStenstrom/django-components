/** Unescape JS that was escaped in Django side with `escape_js` */
export const unescapeJs = (escapedJs: string) => {
  const doc = new DOMParser().parseFromString(escapedJs, "text/html")
  return doc.documentElement.textContent as string;
};

// ////////////////////////////////////////////////////////
// Helper functions below were taken from @vue/shared
// See https://github.com/vuejs/core/blob/91112520427ff55941a1c759d7d60a0811ff4a61/packages/shared/src/general.ts#L105
// ////////////////////////////////////////////////////////

export const isArray = Array.isArray;
export const isFunction = (val: unknown): val is Function =>
  typeof val === "function";
export const isObject = (val: unknown): val is Record<any, any> => {
  return val !== null && typeof val === "object";
};
export const isPromise = <T = any>(val: unknown): val is Promise<T> => {
  return (
    (isObject(val) || isFunction(val)) &&
    isFunction((val as any).then) &&
    isFunction((val as any).catch)
  );
};
