"use client";

import { Scale } from "lucide-react";
import { CertaintyTag, SafetyNote } from "@/components/ui/primitives";
import type { Certainty } from "@/lib/types";
import { money } from "@/lib/utils";

export interface DecisionData {
  available: boolean;
  repair_estimate: number;
  deductible: number;
  estimated_insurer_payment: number;
  prior_claims: number;
  options: { title: string; pros: string[]; cons: string[] }[];
  considerations: { label: string; value: string; certainty: Certainty; note?: string }[];
  source: string | null;
  note: string;
}

/** Claim Decision Assistant — transparent math, two options, never a verdict. */
export function DecisionView({ d }: { d: DecisionData }) {
  const youPay = Math.min(d.repair_estimate, d.deductible);
  const pctYou = d.repair_estimate ? (youPay / d.repair_estimate) * 100 : 0;
  return (
    <div className="space-y-4">
      <div>
        <div className="mb-2 flex items-baseline justify-between text-sm">
          <span className="text-muted">Repair estimate</span>
          <span className="font-display text-xl font-semibold tabular">{money(d.repair_estimate)}</span>
        </div>
        <div className="flex h-9 overflow-hidden rounded-xl text-xs font-medium" role="img" aria-label={`You pay ${money(youPay)}, insurer may pay ${money(d.estimated_insurer_payment)}`}>
          <div className="flex items-center justify-center bg-warn-soft text-warn" style={{ width: `${pctYou}%` }}>
            You · {money(youPay)}
          </div>
          <div className="flex flex-1 items-center justify-center bg-ok-soft text-ok">Insurer · ~{money(d.estimated_insurer_payment)}</div>
        </div>
        <p className="mt-1.5 text-xs text-subtle">Your collision deductible is {money(d.deductible)}.</p>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        {d.options.map((o) => (
          <div key={o.title} className="rounded-2xl border border-border bg-surface p-4">
            <p className="mb-2 flex items-center gap-2 font-medium">
              <Scale className="size-4 text-accent" aria-hidden /> {o.title}
            </p>
            <ul className="space-y-1 text-sm">
              {o.pros.map((p) => (
                <li key={p} className="flex gap-2 text-muted">
                  <span className="text-ok" aria-label="Pro">＋</span> {p}
                </li>
              ))}
              {o.cons.map((c) => (
                <li key={c} className="flex gap-2 text-muted">
                  <span className="text-danger" aria-label="Con">－</span> {c}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <ul className="divide-y divide-border rounded-2xl border border-border">
        {d.considerations.map((c) => (
          <li key={c.label} className="flex items-start justify-between gap-3 px-4 py-2.5 text-sm">
            <div>
              <p>{c.label}</p>
              {c.note && <p className="text-xs text-subtle">{c.note}</p>}
            </div>
            <div className="flex shrink-0 items-center gap-2">
              <span className="font-medium tabular">{c.value}</span>
              <CertaintyTag certainty={c.certainty} />
            </div>
          </li>
        ))}
      </ul>
      <SafetyNote>{d.note}</SafetyNote>
    </div>
  );
}
