import type { AIActionItem, AICard, Citation, Confidence, ExplainPayload, ProgressEvent } from "./types";

export type StreamEvent =
  | { type: "conversation"; id: string }
  | ProgressEvent
  | { type: "token"; text: string }
  | { type: "error"; message: string }
  | {
      type: "done";
      message: {
        id: string;
        content: string;
        agent: string;
        confidence: Confidence;
        citations: Citation[];
        cards: AICard[];
        actions: AIActionItem[];
        suggestions: string[];
        explain: ExplainPayload;
      };
    };

/** POSTs to the SSE chat endpoint and yields parsed events as they arrive. */
export async function* streamChat(
  body: { message: string; conversation_id: string | null; page: Record<string, unknown> },
  signal?: AbortSignal,
): AsyncGenerator<StreamEvent> {
  const res = await fetch("/api/ai/chat", {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", "X-InsurePilot-Client": "web", Accept: "text/event-stream" },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok || !res.body) {
    const detail = res.status === 429 ? "You're sending messages quickly — give it a moment." : "The assistant is unavailable right now.";
    yield { type: "error", message: detail };
    return;
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let idx: number;
    while ((idx = buffer.indexOf("\n\n")) !== -1) {
      const raw = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);
      const line = raw.split("\n").find((l) => l.startsWith("data: "));
      if (line) {
        try {
          yield JSON.parse(line.slice(6)) as StreamEvent;
        } catch {
          /* ignore malformed frame */
        }
      }
    }
  }
}
