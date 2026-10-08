"use client";

import type { LucideIcon } from "lucide-react";
import { ArrowRight, BookOpen, CircleCheck, CircleHelp, CircleMinus, Search, ShieldPlus, TrendingDown, TrendingUp } from "lucide-react";
import { Steps, type Step } from "@/components/ai/steps";
import { Badge, CertaintyTag, SafetyNote } from "@/components/ui/primitives";
import type { PolicyExplainer } from "@/lib/types";
import { cn, money, shortDate } from "@/lib/utils";

export interface PremiumChange {
  prior_premium: number;
  current_premium: number;
  change: number;
  change_percent: number;
  confirmed: { label: string; impact: number | null; source: string }[];
  possible: { label: string; impact: number | null; source: string }[];
  unexplained_amount: number;
  discount_opportunities: string[];
  note: string;
}

export function PremiumChangeView({ pc }: { pc: PremiumChange }) {
  const up = pc.change > 0;
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <div>
          <p className="text-xs text-subtle">Prior premium</p>
          <p className="font-display text-xl font-semibold tabular text-muted">{money(pc.prior_premium)}</p>
        </div>
        <ArrowRight className="size-5 text-subtle" aria-hidden />
        <div>
          <p className="text-xs text-subtle">New premium</p>
          <p className="font-display text-2xl font-semibold tabular">{money(pc.current_premium)}</p>
        </div>
        <Badge tone={up ? "danger" : "ok"} className="ml-auto text-sm">
          {up ? <TrendingUp aria-hidden /> : <TrendingDown aria-hidden />}
          {pc.change_percent > 0 ? "+" : ""}
          {pc.change_percent}% · {money(Math.abs(pc.change))}/yr
        </Badge>
      </div>
      {pc.confirmed.length > 0 && (
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-subtle">Confirmed reasons</p>
          <ul className="space-y-1.5">
            {pc.confirmed.map((f) => (
              <li key={f.label} className="flex items-start justify-between gap-3 rounded-xl bg-surface px-3 py-2 text-sm">
                <span className="flex gap-2">
                  <CircleCheck className="mt-0.5 size-4 shrink-0 text-ok" aria-hidden /> {f.label}
                </span>
                <span className="shrink-0 tabular text-muted">{f.impact ? `+${money(f.impact)}` : "amount not stated"}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      {pc.possible.length > 0 && (
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-subtle">Possible factors (not stated by your carrier)</p>
          <ul className="space-y-1.5">
            {pc.possible.map((f) => (
              <li key={f.label} className="flex gap-2 rounded-xl border border-dashed border-border-strong px-3 py-2 text-sm text-muted">
                <CircleHelp className="mt-0.5 size-4 shrink-0" aria-hidden /> {f.label}
              </li>
            ))}
          </ul>
        </div>
      )}
      {pc.discount_opportunities.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          <span className="text-xs text-subtle">Discounts to ask about:</span>
          {pc.discount_opportunities.map((d) => (
            <Badge key={d} tone="accent">{d}</Badge>
          ))}
        </div>
      )}
      <SafetyNote>{pc.note}</SafetyNote>
    </div>
  );
}

export function RenewalSteps({ r }: { r: { steps: Step[]; renewal_date: string; days_until_renewal: number } }) {
  return (
    <div className="space-y-3">
      <p className="text-sm text-muted">
        Renews <strong className="text-fg">{shortDate(r.renewal_date)}</strong> · {r.days_until_renewal} days away
      </p>
      <Steps steps={r.steps} compact />
    </div>
  );
}

export interface Comparison {
  available: boolean;
  rows: { key: string; label: string }[];
  columns: ({ id: string; name: string; current: boolean } & Record<string, unknown>)[];
  tradeoffs: { name: string; notes: string[] }[];
  note: string;
}

function fmt(v: unknown, key: string): string {
  if (v === null || v === undefined || v === "") return "—";
  if (Array.isArray(v)) return v.length ? v.join(", ") : "None";
  if (typeof v === "number") return key.includes("premium") || key.includes("deductible") || key.includes("payments") ? money(v) : String(v);
  return String(v);
}

/** Normalized side-by-side comparison. Highlights differences from the current policy; never ranks. */
export function ComparisonTable({ c }: { c: Comparison }) {
  const base = c.columns[0];
  return (
    <div className="space-y-4">
      <div className="overflow-x-auto rounded-2xl border border-border">
        <table className="w-full min-w-[560px] text-sm">
          <caption className="sr-only">Policy comparison</caption>
          <thead>
            <tr className="border-b border-border bg-surface">
              <th scope="col" className="px-3 py-2.5 text-left font-medium text-subtle">Coverage</th>
              {c.columns.map((col) => (
                <th key={col.id} scope="col" className="px-3 py-2.5 text-left font-semibold">
                  {col.name}
                  {col.current && <Badge tone="accent" className="ml-1.5">Yours</Badge>}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {c.rows.map((row) => (
              <tr key={row.key} className="border-b border-border last:border-0">
                <th scope="row" className="px-3 py-2.5 text-left font-normal text-muted">{row.label}</th>
                {c.columns.map((col) => {
                  const differs = !col.current && fmt(col[row.key], row.key) !== fmt(base[row.key], row.key);
                  return (
                    <td key={col.id} className={cn("px-3 py-2.5 tabular", differs && "bg-accent-soft/60 font-medium")}>
                      {fmt(col[row.key], row.key)}
                      {differs && <span className="sr-only"> (differs from your current policy)</span>}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="grid gap-3 md:grid-cols-3">
        {c.tradeoffs.map((t) => (
          <div key={t.name} className="rounded-2xl border border-border bg-surface p-4">
            <p className="mb-1.5 font-medium">{t.name}</p>
            <ul className="space-y-1 text-sm text-muted">
              {t.notes.map((n) => (
                <li key={n}>• {n}</li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <SafetyNote>{c.note}</SafetyNote>
    </div>
  );
}

export function PolicyExplainerView({ p, compact }: { p: PolicyExplainer; compact?: boolean }) {
  const Item = ({ icon: Icon, tone, name, detail, extra, source }: { icon: LucideIcon; tone: string; name: string; detail: string; extra?: string; source?: string | null }) => (
    <li className="flex gap-3 rounded-xl px-1 py-1.5">
      <Icon className={cn("mt-0.5 size-4 shrink-0", tone)} aria-hidden />
      <div className="min-w-0">
        <p className="text-sm font-medium">
          {name} {extra && <span className="font-normal text-subtle">· {extra}</span>}
        </p>
        <p className="text-sm text-muted">{detail}</p>
        {source && !compact && (
          <p className="mt-0.5 inline-flex items-center gap-1 text-xs text-subtle">
            <BookOpen className="size-3" aria-hidden /> {source}
          </p>
        )}
      </div>
    </li>
  );
  return (
    <div className={cn("grid gap-5", !compact && "md:grid-cols-2")}>
      <section>
        <h4 className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-ok">What you’re covered for</h4>
        <ul>{p.covered.slice(0, compact ? 4 : 20).map((c) => <Item key={c.name} icon={CircleCheck} tone="text-ok" name={c.name} detail={c.detail} extra={c.limit} source={c.source} />)}</ul>
      </section>
      <section>
        <h4 className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-danger">What you’re not covered for</h4>
        <ul>{p.not_covered.slice(0, compact ? 3 : 20).map((c) => <Item key={c.name} icon={CircleMinus} tone="text-danger" name={c.name} detail={c.detail} source={c.source} />)}</ul>
        {p.endorsements.length > 0 && (
          <>
            <h4 className="mb-1.5 mt-4 text-xs font-semibold uppercase tracking-wider text-accent">Optional add-ons you have</h4>
            <ul>{p.endorsements.map((e) => <Item key={e.name} icon={ShieldPlus} tone="text-accent" name={e.name} detail={e.detail} extra={e.limit} source={e.source} />)}</ul>
          </>
        )}
        {p.potential_gaps.length > 0 && (
          <>
            <h4 className="mb-1.5 mt-4 text-xs font-semibold uppercase tracking-wider text-warn">Potential gaps</h4>
            <ul>{p.potential_gaps.map((g) => <Item key={g.name} icon={Search} tone="text-warn" name={g.name} detail={g.detail} />)}</ul>
          </>
        )}
      </section>
    </div>
  );
}

export function RiskList({ items }: { items: { id: string; title: string; explanation: string; severity: string; certainty: "confirmed" | "possible" }[] }) {
  return (
    <ul className="space-y-2">
      {items.slice(0, 6).map((r) => (
        <li key={r.id} className="rounded-xl bg-surface px-3 py-2.5">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={r.severity === "attention" ? "danger" : r.severity === "review" ? "warn" : "info"}>{r.severity === "attention" ? "Needs attention" : r.severity === "review" ? "Review" : "Info"}</Badge>
            <CertaintyTag certainty={r.certainty} />
          </div>
          <p className="mt-1 text-sm font-medium">{r.title}</p>
          <p className="text-sm text-muted">{r.explanation}</p>
        </li>
      ))}
    </ul>
  );
}
