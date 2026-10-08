"use client";

import { motion } from "framer-motion";
import { CircleHelp, Hospital, TriangleAlert } from "lucide-react";
import { Steps, type Step } from "@/components/ai/steps";
import { Badge, CertaintyTag, SafetyNote } from "@/components/ui/primitives";
import type { Certainty } from "@/lib/types";
import { cn, money, shortDate } from "@/lib/utils";

export interface Reconciliation {
  rows: { key: string; label: string; amount: number; explain: string }[];
  issues: { title: string; detail: string; certainty: Certainty; amount?: number }[];
  status: string;
  summary: string;
  suggested_questions: string[];
}

const ROW_STYLE: Record<string, string> = {
  hospital_charge: "bg-subtle/30",
  allowed: "bg-info",
  plan_paid: "bg-ok",
  deductible: "bg-warn",
  coinsurance: "bg-accent",
  copay: "bg-accent-2",
  patient_responsibility: "bg-danger",
};

/** Medical bill vs EOB, as a proportional bar breakdown with discrepancies highlighted. */
export function ReconciliationView({ r }: { r: Reconciliation }) {
  const max = Math.max(...r.rows.map((x) => x.amount), 1);
  return (
    <div className="space-y-4">
      <ul className="space-y-2.5">
        {r.rows.map((row, i) => (
          <li key={row.key}>
            <div className="mb-1 flex items-baseline justify-between text-sm">
              <span className={cn(row.key === "patient_responsibility" && "font-semibold")} title={row.explain}>
                {row.label}
              </span>
              <span className={cn("tabular", row.key === "patient_responsibility" ? "font-display text-lg font-semibold" : "font-medium")}>{money(row.amount)}</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-surface-hover" aria-hidden>
              <motion.div className={cn("h-full rounded-full", ROW_STYLE[row.key])} initial={{ width: 0 }} animate={{ width: `${(row.amount / max) * 100}%` }} transition={{ delay: i * 0.07, duration: 0.7 }} />
            </div>
            <p className="mt-0.5 text-xs text-subtle">{row.explain}</p>
          </li>
        ))}
      </ul>
      <p className="text-sm font-medium">{r.summary}</p>
      {r.issues.map((i) => (
        <div key={i.title} className="rounded-2xl border border-warn/40 bg-warn-soft/40 p-3.5">
          <div className="flex flex-wrap items-center gap-2">
            {i.certainty === "possible" ? <CircleHelp className="size-4 text-warn" aria-hidden /> : <TriangleAlert className="size-4 text-warn" aria-hidden />}
            <p className="text-sm font-medium">{i.title}</p>
            {i.amount ? <Badge tone="warn">{money(Math.abs(i.amount))}</Badge> : null}
            <CertaintyTag certainty={i.certainty} />
          </div>
          <p className="mt-1 text-sm text-muted">{i.detail}</p>
        </div>
      ))}
      {r.suggested_questions.length > 0 && (
        <div>
          <p className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-subtle">Questions to ask your insurer</p>
          <ul className="list-disc space-y-1 pl-5 text-sm text-muted">
            {r.suggested_questions.map((q) => (
              <li key={q}>{q}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export interface ProcedureCheck {
  available: boolean;
  procedure: string;
  cpt: string;
  provider?: string;
  in_network?: boolean;
  steps: Step[];
  estimate: { negotiated_price: number; deductible_portion: number; coinsurance_portion: number; you_pay: number; plan_pays: number; basis: string } | null;
  alternatives?: { name: string; price: number | null; in_network: boolean }[];
  summary: string;
  uncertainty?: string[];
}

export function ProcedureView({ r }: { r: ProcedureCheck }) {
  return (
    <div className="space-y-5">
      {r.provider && (
        <div className="flex flex-wrap items-center gap-2">
          <Hospital className="size-4 text-accent" aria-hidden />
          <p className="font-medium">{r.provider}</p>
          <Badge tone={r.in_network ? "ok" : "warn"}>{r.in_network ? "In-network" : "Not in network directory"}</Badge>
          {r.cpt && <Badge>CPT {r.cpt}</Badge>}
        </div>
      )}
      {r.estimate && (
        <div className="grid grid-cols-3 gap-2 text-center">
          {[
            ["Typical price", r.estimate.negotiated_price],
            ["You may pay", r.estimate.you_pay],
            ["Plan may pay", r.estimate.plan_pays],
          ].map(([l, v], i) => (
            <div key={l as string} className={cn("rounded-2xl border border-border p-3", i === 1 && "border-accent/40 bg-accent-soft")}>
              <p className="text-xs text-subtle">{l}</p>
              <p className="font-display text-lg font-semibold tabular">{money(v as number)}</p>
            </div>
          ))}
        </div>
      )}
      <Steps steps={r.steps} compact />
      {r.alternatives && r.alternatives.length > 0 && (
        <div>
          <p className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-subtle">Other options</p>
          <ul className="space-y-1.5 text-sm">
            {r.alternatives.map((a) => (
              <li key={a.name} className="flex items-center justify-between gap-2 rounded-xl bg-surface px-3 py-2">
                <span>{a.name}</span>
                <span className="flex items-center gap-2">
                  <Badge tone={a.in_network ? "ok" : "warn"}>{a.in_network ? "In-network" : "Out-of-network"}</Badge>
                  <span className="tabular text-muted">{money(a.price)}</span>
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
      {r.estimate && <SafetyNote>{r.estimate.basis}</SafetyNote>}
      {r.uncertainty?.map((u) => <SafetyNote key={u}>{u}</SafetyNote>)}
    </div>
  );
}

export interface PriorAuth {
  procedure: string;
  cpt: string | null;
  status: string;
  decision_due: string | null;
  provider: string | null;
  steps: Step[];
  requirements: { item: string; status: string }[];
  missing: string[];
  administrative_risk: string;
  packet: string[];
  disclaimer: string;
}

export function PriorAuthView({ a }: { a: PriorAuth }) {
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={a.status === "approved" ? "ok" : a.status === "denied" ? "danger" : "info"}>{a.status}</Badge>
        {a.decision_due && <span className="text-sm text-muted">Decision expected by {shortDate(a.decision_due)}</span>}
        <Badge tone={a.administrative_risk === "elevated" ? "warn" : "ok"}>Paperwork risk: {a.administrative_risk}</Badge>
      </div>
      <Steps steps={a.steps} compact />
      <div>
        <p className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-subtle">Authorization packet</p>
        <ul className="grid gap-1.5 text-sm sm:grid-cols-2">
          {a.packet.map((p) => (
            <li key={p} className="rounded-xl bg-surface px-3 py-2 text-muted">{p}</li>
          ))}
        </ul>
      </div>
      <SafetyNote>{a.disclaimer}</SafetyNote>
    </div>
  );
}
