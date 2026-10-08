"use client";

import { useMutation } from "@tanstack/react-query";
import { BookOpen, Sparkles } from "lucide-react";
import * as React from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTrigger } from "@/components/ui/overlay";
import { ConfidenceBadge, Skeleton } from "@/components/ui/primitives";
import { api } from "@/lib/api";
import { useAssistant } from "@/lib/store";
import type { Confidence } from "@/lib/types";
import { cn } from "@/lib/utils";

interface Explanation {
  simple: string;
  why_it_matters: string;
  what_happens_next: string;
  actions: string[];
  source: string | null;
  confidence: Confidence;
}

/** "Explain This" — available on every complicated insurance item. */
export function ExplainThis({ kind, refId, label, small, className }: { kind: string; refId: string; label: string; small?: boolean; className?: string }) {
  const [open, setOpen] = React.useState(false);
  const ask = useAssistant((s) => s.ask);
  const m = useMutation({ mutationFn: () => api.post<Explanation>("/ai/explain", { kind, ref: refId }) });

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        setOpen(o);
        if (o && !m.data) m.mutate();
      }}
    >
      <DialogTrigger asChild>
        <button
          type="button"
          className={cn(
            "inline-flex items-center gap-1 rounded-full border border-border px-2 py-0.5 text-[11px] font-medium text-accent transition-colors hover:bg-accent-soft",
            small && "px-1.5",
            className,
          )}
          aria-label={`Explain ${label}`}
        >
          <Sparkles className="size-3" aria-hidden /> Explain this
        </button>
      </DialogTrigger>
      <DialogContent title={label} description="In plain English">
        {m.isPending || !m.data ? (
          <div className="space-y-3">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-5/6" />
            <Skeleton className="h-4 w-2/3" />
          </div>
        ) : (
          <div className="space-y-5">
            <p className="text-[15px] leading-relaxed">{m.data.simple}</p>
            {m.data.why_it_matters && (
              <section>
                <h4 className="text-xs font-semibold uppercase tracking-wider text-subtle">Why it matters</h4>
                <p className="mt-1 text-sm text-muted">{m.data.why_it_matters}</p>
              </section>
            )}
            {m.data.what_happens_next && (
              <section>
                <h4 className="text-xs font-semibold uppercase tracking-wider text-subtle">What happens next</h4>
                <p className="mt-1 text-sm text-muted">{m.data.what_happens_next}</p>
              </section>
            )}
            <div className="flex flex-wrap items-center gap-2 border-t border-border pt-4">
              <ConfidenceBadge confidence={m.data.confidence} />
              {m.data.source && (
                <span className="inline-flex items-center gap-1 text-xs text-subtle">
                  <BookOpen className="size-3" aria-hidden /> {m.data.source}
                </span>
              )}
            </div>
            <Button
              variant="secondary"
              className="w-full"
              onClick={() => {
                setOpen(false);
                ask(`Explain "${label}" for my situation`);
              }}
            >
              <Sparkles /> Ask a follow-up
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
