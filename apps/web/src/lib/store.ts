"use client";

import { create } from "zustand";
import type { ChatMessage, OrbState } from "./types";

export interface PageContext {
  section?: string;
  category?: string;
  policy_id?: string;
  claim_id?: string;
  document_id?: string;
  title?: string;
}

interface AssistantState {
  open: boolean;
  orb: OrbState;
  orbLabel: string;
  messages: ChatMessage[];
  conversationId: string | null;
  page: PageContext;
  pendingPrompt: string | null;
  setOpen: (open: boolean) => void;
  setOrb: (orb: OrbState, label?: string) => void;
  setPage: (page: PageContext) => void;
  ask: (prompt: string) => void;
  consumePrompt: () => string | null;
  setConversation: (id: string | null) => void;
  addMessage: (m: ChatMessage) => void;
  updateMessage: (id: string, patch: Partial<ChatMessage> | ((m: ChatMessage) => Partial<ChatMessage>)) => void;
  reset: () => void;
}

export const useAssistant = create<AssistantState>((set, get) => ({
  open: false,
  orb: "idle",
  orbLabel: "",
  messages: [],
  conversationId: null,
  page: {},
  pendingPrompt: null,
  setOpen: (open) => set({ open }),
  setOrb: (orb, label = "") => set({ orb, orbLabel: label }),
  setPage: (page) => set({ page }),
  ask: (prompt) => set({ open: true, pendingPrompt: prompt }),
  consumePrompt: () => {
    const p = get().pendingPrompt;
    if (p) set({ pendingPrompt: null });
    return p;
  },
  setConversation: (conversationId) => set({ conversationId }),
  addMessage: (m) => set((s) => ({ messages: [...s.messages, m] })),
  updateMessage: (id, patch) =>
    set((s) => ({
      messages: s.messages.map((m) => (m.id === id ? { ...m, ...(typeof patch === "function" ? patch(m) : patch) } : m)),
    })),
  reset: () => set({ messages: [], conversationId: null, orb: "idle", orbLabel: "" }),
}));

interface UIState {
  sidebarCollapsed: boolean;
  paletteOpen: boolean;
  lowPower: boolean;
  reducedMotion: boolean;
  toggleSidebar: () => void;
  setPalette: (open: boolean) => void;
  setLowPower: (v: boolean) => void;
  setReducedMotion: (v: boolean) => void;
}

function readPref(key: string, fallback: boolean) {
  if (typeof window === "undefined") return fallback;
  try {
    const v = window.localStorage.getItem(key);
    return v === null ? fallback : v === "true";
  } catch {
    return fallback;
  }
}

function writePref(key: string, v: boolean) {
  try {
    window.localStorage.setItem(key, String(v));
  } catch {
    /* storage unavailable (private mode) — preference stays in memory */
  }
}

export const useUI = create<UIState>((set) => ({
  sidebarCollapsed: false,
  paletteOpen: false,
  lowPower: false,
  reducedMotion: false,
  toggleSidebar: () =>
    set((s) => {
      writePref("ip.sidebar", !s.sidebarCollapsed);
      return { sidebarCollapsed: !s.sidebarCollapsed };
    }),
  setPalette: (paletteOpen) => set({ paletteOpen }),
  setLowPower: (lowPower) => {
    writePref("ip.lowpower", lowPower);
    set({ lowPower });
  },
  setReducedMotion: (reducedMotion) => {
    writePref("ip.reducedmotion", reducedMotion);
    if (typeof document !== "undefined") document.documentElement.dataset.reducedMotion = String(reducedMotion);
    set({ reducedMotion });
  },
}));

/** Loads persisted UI preferences after mount (keeps server and client renders identical). */
export function hydrateUI() {
  const reducedMotion = readPref("ip.reducedmotion", false);
  document.documentElement.dataset.reducedMotion = String(reducedMotion);
  useUI.setState({
    sidebarCollapsed: readPref("ip.sidebar", false),
    lowPower: readPref("ip.lowpower", false),
    reducedMotion,
  });
}
