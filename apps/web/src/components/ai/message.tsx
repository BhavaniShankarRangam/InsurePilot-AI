"use client";

import { AnimatePresence, motion } from "framer-motion";
import { BookOpen, Check, ChevronDown, CircleAlert, Cpu, Database, Info, Lightbulb, LoaderCircle, Wrench } from "lucide-react";
import * as React from "react";
import { ConfidenceBadge } from "@/components/ui/primitives";
import type { ChatMessage, Citation } from "@/lib/types";
import { cn } from "@/lib/utils";
import { ApprovalCard } from "./approval-card";
import { AICardView } from "./cards";
import { Markdown } from "./markdown";

export function MessageView({ m, onSuggestion }: { m: ChatMessage; onSuggestion: (s: string) => void }) {
  const [activeCite, setActiveCite] = React.useState<number | null>(null);
  const [whyOpen, setWhyOpen] = React.useState(false);
  const citeRefs = React.useRef<Record<number, HTMLLIElement | null>>({});

  if (m.role === "user") {
    return (
      <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="flex justify-end">
        <p className="max-w-[85%] rounded-2xl rounded-br-md bg-accent-gradient px-4 py-2.5 text-[15px] text-white shadow-glow">{m.content}</p>
      </motion.div>
    );
  }

  const progress = (m.progress ?? []).filter((p) => p.label && p.type !== "route");
  return (
    <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="space-y-3">
      {(m.streaming || progress.length > 0) && <ProgressTrail items={progress} live={!!m.streaming && !m.content} />}

      {m.content && <Markdown text={m.content} onCite={(n) => { setActiveCite(n); citeRefs.current[n]?.scrollIntoView({ block: "nearest", behavior: "smooth" }); }} />}
      {m.streaming && m.content && <span className="inline-block h-4 w-1.5 animate-pulse rounded-sm bg-accent align-middle" aria-hidden />}
      {m.error && (
        <p role="alert" className="flex items-center gap-2 rounded-xl bg-danger-soft px-3 py-2 text-sm text-danger">
          <CircleAlert className="size-4" aria-hidden /> {m.error}
        </p>
      )}

      {!m.streaming && (
        <>
          {m.cards?.map((c, i) => <AICardView key={i} card={c} />)}
          {m.actions?.map((a) => <ApprovalCard key={a.id} action={a} />)}

          {m.citations && m.citations.length > 0 && <Citations items={m.citations} active={activeCite} refs={citeRefs} />}

          <div className="flex flex-wrap items-center gap-2">
            {m.confidence && <ConfidenceBadge confidence={m.confidence} />}
            {m.explain && (
              <button onClick={() => setWhyOpen((v) => !v)} className="inline-flex items-center gap-1 text-xs text-muted hover:text-fg" aria-expanded={whyOpen}>
                <Info className="size-3.5" aria-hidden /> Why am I seeing this?
                <ChevronDown className={cn("size-3 transition-transform", whyOpen && "rotate-180")} aria-hidden />
              </button>
            )}
          </div>
          <AnimatePresence>
            {whyOpen && m.explain && (
              <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
                <div className="space-y-2.5 rounded-2xl border border-border bg-surface p-3.5 text-sm">
                  <p className="flex gap-2"><Lightbulb className="mt-0.5 size-4 shrink-0 text-accent" aria-hidden /> {m.explain.reasoning_summary}</p>
                  {m.explain.data_used.length > 0 && <p className="flex gap-2 text-muted"><Database className="mt-0.5 size-4 shrink-0" aria-hidden /> Data used: {m.explain.data_used.join(" · ")}</p>}
                  {m.explain.tools_used.length > 0 && <p className="flex gap-2 text-muted"><Wrench className="mt-0.5 size-4 shrink-0" aria-hidden /> Tools: {m.explain.tools_used.join(", ")}</p>}
                  {m.explain.sources.length > 0 && <p className="flex gap-2 text-muted"><BookOpen className="mt-0.5 size-4 shrink-0" aria-hidden /> Sources: {m.explain.sources.join(" · ")}</p>}
                  {m.agent && <p className="flex gap-2 text-muted"><Cpu className="mt-0.5 size-4 shrink-0" aria-hidden /> Handled by: {m.agent}</p>}
                  {m.explain.limitations.length > 0 && <p className="flex gap-2 text-muted"><CircleAlert className="mt-0.5 size-4 shrink-0" aria-hidden /> Limitations: {m.explain.limitations.join(" ")}</p>}
                  <p className="text-xs text-subtle">This is a summary of how the answer was produced, not the model’s private reasoning.</p>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {m.suggestions && m.suggestions.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {m.suggestions.map((s) => (
                <button key={s} onClick={() => onSuggestion(s)} className="glass rounded-full px-3 py-1 text-xs text-muted transition hover:-translate-y-px hover:text-fg">
                  {s}
                </button>
              ))}
            </div>
          )}
        </>
      )}
    </motion.div>
  );
}

function ProgressTrail({ items, live }: { items: { label?: string; type: string; ok?: boolean }[]; live: boolean }) {
  const [open, setOpen] = React.useState(false);
  const shown = live ? items.slice(-4) : open ? items : [];
  return (
    <div className="text-xs">
      {!live && items.length > 0 && (
        <button onClick={() => setOpen((v) => !v)} className="mb-1 inline-flex items-center gap-1 text-subtle hover:text-fg" aria-expanded={open}>
          <Check className="size-3 text-ok" aria-hidden /> {items.length} steps completed
          <ChevronDown className={cn("size-3 transition-transform", open && "rotate-180")} aria-hidden />
        </button>
      )}
      <ul className="space-y-1" aria-live="polite">
        <AnimatePresence initial={false}>
          {shown.map((p, i) => {
            const isLast = live && i === shown.length - 1;
            return (
              <motion.li key={`${p.label}-${i}`} initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }} className="flex items-center gap-2 text-muted">
                {isLast ? <LoaderCircle className="size-3 animate-spin text-accent" aria-hidden /> : <Check className="size-3 text-ok" aria-hidden />}
                {p.label}
              </motion.li>
            );
          })}
        </AnimatePresence>
        {live && items.length === 0 && (
          <li className="flex items-center gap-2 text-muted">
            <LoaderCircle className="size-3 animate-spin text-accent" aria-hidden /> Understanding your request
          </li>
        )}
      </ul>
    </div>
  );
}

function Citations({ items, active, refs }: { items: Citation[]; active: number | null; refs: React.RefObject<Record<number, HTMLLIElement | null>> }) {
  return (
    <div>
      <p className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-subtle">Sources</p>
      <ol className="space-y-1.5">
        {items.map((c, i) => (
          <li
            key={c.chunk_id}
            ref={(el) => { refs.current[i + 1] = el; }}
            className={cn("rounded-xl border px-3 py-2 text-sm transition-colors", active === i + 1 ? "border-accent bg-accent-soft" : "border-border bg-surface")}
          >
            <p className="flex items-center gap-2 font-medium">
              <span className="grid size-4 place-items-center rounded bg-accent-soft text-[10px] font-semibold text-accent">{i + 1}</span>
              {c.label}
            </p>
            <p className="mt-0.5 line-clamp-2 text-xs text-muted">“{c.snippet}”</p>
          </li>
        ))}
      </ol>
    </div>
  );
}
