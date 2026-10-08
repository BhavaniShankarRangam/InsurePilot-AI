"use client";

import { useQueryClient } from "@tanstack/react-query";
import * as React from "react";
import { streamChat } from "@/lib/chat-stream";
import { keys } from "@/lib/queries";
import { useAssistant } from "@/lib/store";
import type { OrbState } from "@/lib/types";

let counter = 0;
const uid = () => `m-${Date.now()}-${counter++}`;

export function useChat(opts: { speak?: (text: string) => void } = {}) {
  const { addMessage, updateMessage, setOrb, setConversation } = useAssistant.getState();
  const qc = useQueryClient();
  const abortRef = React.useRef<AbortController | null>(null);
  const [busy, setBusy] = React.useState(false);

  const send = React.useCallback(
    async (text: string) => {
      const message = text.trim();
      if (!message || busy) return;
      abortRef.current?.abort();
      const ctrl = new AbortController();
      abortRef.current = ctrl;
      setBusy(true);

      addMessage({ id: uid(), role: "user", content: message });
      const id = uid();
      addMessage({ id, role: "assistant", content: "", streaming: true, progress: [] });
      setOrb("understanding", "Understanding your request");

      const { conversationId, page } = useAssistant.getState();
      try {
        for await (const ev of streamChat({ message, conversation_id: conversationId, page: page as Record<string, unknown> }, ctrl.signal)) {
          switch (ev.type) {
            case "conversation":
              setConversation(ev.id);
              break;
            case "status":
            case "tool":
            case "route":
              if (ev.type === "status" && ev.state) setOrb(ev.state as OrbState, ev.label);
              if (ev.type === "tool") setOrb("tool", ev.label);
              updateMessage(id, (m) => ({ progress: [...(m.progress ?? []), ev] }));
              break;
            case "token":
              updateMessage(id, (m) => ({ content: m.content + ev.text }));
              break;
            case "error":
              setOrb("error", ev.message);
              updateMessage(id, { streaming: false, error: ev.message });
              break;
            case "done": {
              const m = ev.message;
              updateMessage(id, {
                id: m.id,
                content: m.content,
                agent: m.agent,
                confidence: m.confidence,
                citations: m.citations,
                cards: m.cards,
                actions: m.actions,
                suggestions: m.suggestions,
                explain: m.explain,
                streaming: false,
              });
              const final: OrbState = m.actions?.some((a) => a.status === "pending")
                ? "awaiting_confirmation"
                : m.confidence === "human_review"
                  ? "human_review"
                  : "completed";
              setOrb(final);
              opts.speak?.(m.content);
              qc.invalidateQueries({ queryKey: keys.actions });
              qc.invalidateQueries({ queryKey: keys.activity });
              if (m.cards?.some((c) => ["fnol_summary", "claim_packet"].includes(c.type))) qc.invalidateQueries({ queryKey: keys.claims });
              if (final === "completed") setTimeout(() => useAssistant.getState().orb === "completed" && setOrb("idle"), 2400);
              break;
            }
          }
        }
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          setOrb("error", "Connection lost");
          updateMessage(id, { streaming: false, error: "Connection lost. Please try again." });
        }
      } finally {
        setBusy(false);
      }
    },
    [busy, addMessage, updateMessage, setOrb, setConversation, qc, opts],
  );

  const stop = React.useCallback(() => {
    abortRef.current?.abort();
    setBusy(false);
    setOrb("idle");
  }, [setOrb]);

  return { send, stop, busy };
}
