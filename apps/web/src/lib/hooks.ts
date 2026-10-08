"use client";

import { useSyncExternalStore } from "react";

const noopSubscribe = () => () => {};

/** True only on the client after hydration — without a setState-in-effect re-render. */
export function useMounted() {
  return useSyncExternalStore(noopSubscribe, () => true, () => false);
}

export function useIsMac() {
  return useSyncExternalStore(noopSubscribe, () => /Mac|iPhone|iPad/.test(navigator.platform), () => false);
}

let webglCache: boolean | null = null;
function detectWebGL() {
  if (webglCache === null) {
    try {
      const c = document.createElement("canvas");
      webglCache = !!(c.getContext("webgl2") || c.getContext("webgl"));
    } catch {
      webglCache = false;
    }
  }
  return webglCache;
}

export function useWebGL() {
  return useSyncExternalStore(noopSubscribe, detectWebGL, () => false);
}
