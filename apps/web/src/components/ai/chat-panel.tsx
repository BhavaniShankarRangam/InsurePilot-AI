"use client";

import { ArrowUp, Mic, MicOff, RotateCcw, Square, Volume2, VolumeX } from "lucide-react";
import * as React from "react";
import { Button } from "@/components/ui/button";
import { useAssistant } from "@/lib/store";
import { cn } from "@/lib/utils";
import { MessageView } from "./message";
import { Orb, orbLabel } from "./orb";
import { useChat } from "./use-chat";
import { speak, useVoice } from "./voice";
import { VoiceWave } from "./voice-wave";

export const STARTERS = [
  "Handle my insurance",
  "Why did my premium increase?",
  "My car repair is $1,200. Should I file a claim?",
  "Why was my home claim denied?",
  "Can I get an MRI at Lakeside Imaging?",
  "Explain my hospital bill",
  "Find coverage gaps",
  "Someone hit my car",
];

/** The conversational surface shared by the Command Center sheet and the full Assistant page. */
export function ChatPanel({ variant = "sheet" }: { variant?: "sheet" | "page" }) {
  const { messages, orb, orbLabel: liveLabel, page, reset, consumePrompt, pendingPrompt } = useAssistant();
  const [input, setInput] = React.useState("");
  const [voiceReplies, setVoiceReplies] = React.useState(false);
  const chat = useChat({ speak: voiceReplies ? speak : undefined });
  const scrollRef = React.useRef<HTMLDivElement>(null);
  const inputRef = React.useRef<HTMLTextAreaElement>(null);

  const voice = useVoice(
    React.useCallback(
      (text: string) => {
        setVoiceReplies(true);
        chat.send(text);
      },
      [chat],
    ),
  );

  React.useEffect(() => {
    const p = consumePrompt();
    if (p) chat.send(p);
  }, [pendingPrompt, consumePrompt, chat]);

  React.useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  React.useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const submit = () => {
    if (!input.trim()) return;
    chat.send(input);
    setInput("");
  };

  const state = voice.listening ? "listening" : orb;

  return (
    <div className="flex h-full min-h-0 flex-col">
      <header className="flex items-center gap-3 border-b border-border px-5 py-3.5">
        <Orb state={state} size={38} level={voice.level} />
        <div className="min-w-0 flex-1">
          <p className="font-display font-semibold leading-tight">AI Command Center</p>
          <p className="truncate text-xs text-muted" aria-live="polite">
            {voice.listening ? "Listening…" : liveLabel || orbLabel(orb)}
            {page.title ? ` · Viewing ${page.title}` : ""}
          </p>
        </div>
        <Button size="icon-sm" variant="ghost" onClick={() => setVoiceReplies((v) => !v)} aria-label={voiceReplies ? "Turn off spoken replies" : "Turn on spoken replies"} aria-pressed={voiceReplies}>
          {voiceReplies ? <Volume2 /> : <VolumeX />}
        </Button>
        {messages.length > 0 && (
          <Button size="icon-sm" variant="ghost" onClick={reset} aria-label="New conversation">
            <RotateCcw />
          </Button>
        )}
      </header>

      <div ref={scrollRef} className={cn("flex-1 space-y-6 overflow-y-auto px-5 py-5", variant === "page" && "px-2 md:px-6")} aria-live="polite">
        {messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <Orb state={state} size={88} level={voice.level} />
            <h2 className="mt-6 font-display text-2xl font-semibold tracking-tight">How can I help with your insurance?</h2>
            <p className="mt-1.5 max-w-sm text-sm text-muted">Ask anything in plain English. I’ll check your policies and documents, and I’ll never act without your approval.</p>
            <div className="mt-6 grid w-full max-w-md gap-2 sm:grid-cols-2">
              {STARTERS.map((s) => (
                <button key={s} onClick={() => chat.send(s)} className="glass rounded-xl px-3.5 py-2.5 text-left text-sm text-muted transition hover:-translate-y-0.5 hover:text-fg">
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((m) => <MessageView key={m.id} m={m} onSuggestion={(s) => chat.send(s)} />)
        )}
      </div>

      <div className="border-t border-border p-3">
        {(voice.listening || voice.interim) && (
          <div className="mb-2 flex items-center gap-3 rounded-xl bg-accent-soft px-3 py-2">
            <VoiceWave level={voice.level} active={voice.listening} />
            <p className="truncate text-sm text-muted">{voice.interim || "Listening — speak naturally"}</p>
          </div>
        )}
        {voice.error && <p role="alert" className="mb-2 text-xs text-danger">{voice.error}</p>}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            submit();
          }}
          className="glass flex items-end gap-2 rounded-2xl p-1.5 focus-within:ring-4 focus-within:ring-accent-soft"
        >
          <label htmlFor="ai-input" className="sr-only">Message InsurePilot</label>
          <textarea
            id="ai-input"
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit();
              }
            }}
            rows={1}
            placeholder="Ask about your coverage, claims, bills…"
            className="max-h-32 min-h-10 flex-1 resize-none bg-transparent px-2.5 py-2 text-[15px] placeholder:text-subtle focus:outline-none"
          />
          <Button
            type="button"
            size="icon"
            variant={voice.listening ? "danger" : "ghost"}
            onClick={() => (voice.listening ? voice.stop() : voice.start())}
            aria-label={voice.listening ? "Stop listening" : "Speak"}
            aria-pressed={voice.listening}
          >
            {voice.listening ? <MicOff /> : <Mic />}
          </Button>
          {chat.busy ? (
            <Button type="button" size="icon" variant="secondary" onClick={chat.stop} aria-label="Stop generating">
              <Square />
            </Button>
          ) : (
            <Button type="submit" size="icon" disabled={!input.trim()} aria-label="Send">
              <ArrowUp />
            </Button>
          )}
        </form>
        <p className="mt-1.5 px-1 text-center text-[11px] text-subtle">InsurePilot explains your coverage; it doesn’t replace your insurer’s decisions. High-impact actions always need your approval.</p>
      </div>
    </div>
  );
}
