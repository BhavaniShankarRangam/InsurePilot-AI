"use client";

import type { LucideIcon } from "lucide-react";
import { motion } from "framer-motion";
import { Check, CircleDashed, CircleHelp, Hourglass, TriangleAlert, X } from "lucide-react";
import { cn } from "@/lib/utils";

export interface Step {
  step: string;
  status: string; // done | warning | blocked | waiting | ready | skipped | current | upcoming
  detail?: string;
  source?: string | null;
  certainty?: string;
}

const ICON: Record<string, { icon: LucideIcon; cls: string; label: string }> = {
  done: { icon: Check, cls: "bg-ok-soft text-ok", label: "Done" },
  ready: { icon: Check, cls: "bg-accent-soft text-accent", label: "Ready" },
  warning: { icon: TriangleAlert, cls: "bg-warn-soft text-warn", label: "Needs attention" },
  blocked: { icon: X, cls: "bg-danger-soft text-danger", label: "Blocked" },
  waiting: { icon: Hourglass, cls: "bg-info-soft text-info", label: "Waiting on you" },
  skipped: { icon: CircleDashed, cls: "bg-surface-hover text-subtle", label: "Skipped" },
};

/** Animated vertical stepper used for workflows (renewal autopilot, procedure checks, prior auth). */
export function Steps({ steps, compact }: { steps: Step[]; compact?: boolean }) {
  return (
    <ol className="relative space-y-3">
      {steps.map((s, i) => {
        const meta = ICON[s.status] ?? ICON.done;
        return (
          <motion.li
            key={s.step}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.06 }}
            className="relative flex gap-3"
          >
            {i < steps.length - 1 && <span aria-hidden className="absolute left-[13px] top-7 h-[calc(100%-12px)] w-px bg-border-strong" />}
            <span className={cn("relative z-10 grid size-7 shrink-0 place-items-center rounded-full", meta.cls)}>
              <meta.icon className="size-3.5" aria-hidden />
              <span className="sr-only">{meta.label}</span>
            </span>
            <div className="min-w-0 pb-1">
              <p className={cn("font-medium", compact ? "text-sm" : "text-[15px]")}>{s.step}</p>
              {s.detail && <p className="text-sm text-muted">{s.detail}</p>}
              <div className="mt-0.5 flex flex-wrap gap-2 text-xs text-subtle">
                {s.certainty === "possible" && (
                  <span className="inline-flex items-center gap-1">
                    <CircleHelp className="size-3" aria-hidden /> Possible — needs verification
                  </span>
                )}
                {s.source && <span>Source: {s.source}</span>}
              </div>
            </div>
          </motion.li>
        );
      })}
    </ol>
  );
}
