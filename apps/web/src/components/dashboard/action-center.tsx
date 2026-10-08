"use client";

import { AnimatePresence, motion } from "framer-motion";
import { BellRing, CircleCheckBig, Eye, EyeOff, Sparkles, Wrench } from "lucide-react";
import Link from "next/link";
import * as React from "react";
import { toast } from "sonner";
import { ExplainThis } from "@/components/ai/explain-this";
import { Button } from "@/components/ui/button";
import { CertaintyTag, EmptyState, FilterChips, SeverityBadge } from "@/components/ui/primitives";
import { CATEGORY_META } from "@/lib/categories";
import { useFindingDecision } from "@/lib/queries";
import { useAssistant } from "@/lib/store";
import type { Finding } from "@/lib/types";
import { money } from "@/lib/utils";

const FIX_PROMPT: Record<string, string> = {
  renewal: "Why did my premium increase?",
  underinsurance: "How can I fix my home coverage gap?",
  missing_claim_document: "Prepare my claim",
  denial_review: "Why was my home claim denied?",
  prior_auth: "Check my MRI prior authorization",
  network_mismatch: "Explain my hospital bill",
  billing_discrepancy: "Explain my hospital bill",
  missing_beneficiary: "How do I add a backup beneficiary to my life policy?",
  coverage_expired: "Do I need travel insurance?",
};

/** "What needs your attention?" — the Smart Action Center. */
export function ActionCenter({ items }: { items: Finding[] }) {
  const [filter, setFilter] = React.useState<"all" | "attention" | "review">("all");
  const ask = useAssistant((s) => s.ask);
  const decide = useFindingDecision();
  const shown = items.filter((i) => filter === "all" || i.severity === filter);

  if (!items.length)
    return <EmptyState icon={CircleCheckBig} title="Nothing needs your attention" body="Everything looks good today. InsurePilot keeps watching your policies for you." />;

  return (
    <div className="space-y-4">
      <FilterChips
        label="Filter actions"
        value={filter}
        onChange={setFilter}
        options={[
          { value: "all", label: "All", count: items.length },
          { value: "attention", label: "Needs attention", count: items.filter((i) => i.severity === "attention").length },
          { value: "review", label: "Worth reviewing", count: items.filter((i) => i.severity === "review").length },
        ]}
      />
      <ul className="space-y-3">
        <AnimatePresence initial={false}>
          {shown.map((f, i) => {
            const meta = CATEGORY_META[f.category];
            return (
              <motion.li
                key={f.id}
                layout
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0, transition: { delay: i * 0.04 } }}
                exit={{ opacity: 0, x: 40, transition: { duration: 0.25 } }}
                className="glass rounded-2xl p-4"
              >
                <div className="flex gap-3.5">
                  <div className="grid size-10 shrink-0 place-items-center rounded-xl ring-1 ring-border" style={{ background: `color-mix(in oklab, ${meta.hue} 14%, transparent)` }}>
                    <meta.icon className="size-[18px]" style={{ color: meta.hue }} aria-hidden />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-medium">{f.title}</p>
                      {f.amount ? <span className="text-xs tabular text-subtle">{money(f.amount)}</span> : null}
                    </div>
                    <div className="mt-1 flex flex-wrap gap-1.5">
                      <SeverityBadge severity={f.severity} />
                      <CertaintyTag certainty={f.certainty} />
                    </div>
                    <p className="mt-2 text-sm text-muted">{f.explanation}</p>
                    {f.source && <p className="mt-1 text-xs text-subtle">Source: {f.source}</p>}
                    <div className="mt-3 flex flex-wrap items-center gap-1.5">
                      <ExplainThis kind="risk" refId={f.id} label={f.title} />
                      {f.actions.includes("fix") && (
                        <Button size="sm" variant="secondary" onClick={() => ask(FIX_PROMPT[f.kind] ?? `Help me with: ${f.title}`)}>
                          <Wrench /> Fix
                        </Button>
                      )}
                      <Button size="sm" variant="ghost" asChild>
                        <Link href={f.link}>
                          <Eye /> Review
                        </Link>
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => ask(FIX_PROMPT[f.kind] ?? `Tell me more about: ${f.title}`)}>
                        <Sparkles /> Ask AI
                      </Button>
                      {f.actions.includes("remind") && (
                        <Button size="sm" variant="ghost" onClick={() => decide.mutate({ id: f.id, decision: "remind", days: 3 }, { onSuccess: () => toast("We'll remind you in 3 days.") })}>
                          <BellRing /> Remind me later
                        </Button>
                      )}
                      {f.actions.includes("ignore") && (
                        <Button size="sm" variant="ghost" onClick={() => decide.mutate({ id: f.id, decision: "ignore" }, { onSuccess: () => toast("Hidden. You can find it again in Insights.") })}>
                          <EyeOff /> Ignore
                        </Button>
                      )}
                    </div>
                  </div>
                </div>
              </motion.li>
            );
          })}
        </AnimatePresence>
      </ul>
    </div>
  );
}
