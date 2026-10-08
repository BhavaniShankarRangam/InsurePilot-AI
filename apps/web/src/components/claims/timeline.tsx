"use client";

import { motion } from "framer-motion";
import { Check, Circle, Clock, X } from "lucide-react";
import { ExplainThis } from "@/components/ai/explain-this";
import type { ClaimEvent } from "@/lib/types";
import { cn, shortDate } from "@/lib/utils";

const STATUS = {
  done: { icon: Check, ring: "bg-ok text-white", label: "Completed" },
  current: { icon: Circle, ring: "bg-accent-gradient text-white shadow-glow", label: "In progress" },
  upcoming: { icon: Clock, ring: "bg-surface-hover text-subtle", label: "Upcoming" },
  blocked: { icon: X, ring: "bg-danger text-white", label: "Blocked" },
} as const;

/** Animated claim progression: Accident → Submitted → Adjuster → Review → Estimate → Payment. */
export function ClaimTimeline({ events, explain = true }: { events: (ClaimEvent | { title: string; status: string; at?: string; occurred_at?: string; id?: string; description?: string | null })[]; explain?: boolean }) {
  const doneCount = events.filter((e) => e.status === "done").length;
  const pct = events.length > 1 ? Math.min(1, (doneCount + (events.some((e) => e.status === "current") ? 0.5 : 0)) / (events.length - 1)) : 1;
  return (
    <div className="relative">
      <div aria-hidden className="absolute left-[15px] top-4 bottom-4 w-0.5 rounded-full bg-border-strong" />
      <motion.div
        aria-hidden
        className="absolute left-[15px] top-4 w-0.5 rounded-full bg-accent-gradient"
        initial={{ height: 0 }}
        animate={{ height: `calc(${pct * 100}% - ${pct * 32}px)` }}
        transition={{ duration: 1.2, ease: [0.22, 1, 0.36, 1] }}
      />
      <ol className="space-y-5">
        {events.map((e, i) => {
          const s = STATUS[(e.status as keyof typeof STATUS) ?? "done"] ?? STATUS.done;
          const when = "occurred_at" in e ? e.occurred_at : (e as { at?: string }).at;
          return (
            <motion.li key={(e as { id?: string }).id ?? i} className="relative flex gap-4" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 + i * 0.08 }}>
              <span className={cn("relative z-10 grid size-8 shrink-0 place-items-center rounded-full", s.ring)}>
                {e.status === "current" && <span className="absolute inset-0 animate-ping rounded-full bg-accent opacity-30" aria-hidden />}
                <s.icon className="size-4" aria-hidden />
              </span>
              <div className="min-w-0 flex-1 pt-0.5">
                <div className="flex flex-wrap items-center gap-2">
                  <p className={cn("font-medium", e.status === "upcoming" && "text-muted")}>{e.title}</p>
                  <span className="text-xs text-subtle">
                    {s.label}
                    {when ? ` · ${shortDate(when)}` : ""}
                  </span>
                  {explain && "id" in e && e.id && <ExplainThis kind="claim_event" refId={e.id} label={e.title} small />}
                </div>
                {"description" in e && e.description && <p className="mt-0.5 text-sm text-muted">{e.description}</p>}
              </div>
            </motion.li>
          );
        })}
      </ol>
    </div>
  );
}
