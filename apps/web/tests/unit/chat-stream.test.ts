import { afterEach, describe, expect, it, vi } from "vitest";
import { streamChat } from "@/lib/chat-stream";

function sseResponse(chunks: string[]) {
  const enc = new TextEncoder();
  const body = new ReadableStream({
    start(c) {
      chunks.forEach((ch) => c.enqueue(enc.encode(ch)));
      c.close();
    },
  });
  return new Response(body, { status: 200, headers: { "Content-Type": "text/event-stream" } });
}

describe("streamChat", () => {
  afterEach(() => vi.restoreAllMocks());

  it("parses SSE frames split across network chunks", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(sseResponse([
      'data: {"type":"conversation","id":"c1"}\n\ndata: {"type":"tok',
      'en","text":"Hello"}\n\n',
      'data: {"type":"token","text":" there"}\n\n',
    ])));
    const events = [];
    for await (const e of streamChat({ message: "hi", conversation_id: null, page: {} })) events.push(e);
    expect(events.map((e) => e.type)).toEqual(["conversation", "token", "token"]);
  });

  it("yields a friendly error on rate limiting", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("", { status: 429 })));
    const events = [];
    for await (const e of streamChat({ message: "hi", conversation_id: null, page: {} })) events.push(e);
    expect(events[0]).toMatchObject({ type: "error" });
  });
});
