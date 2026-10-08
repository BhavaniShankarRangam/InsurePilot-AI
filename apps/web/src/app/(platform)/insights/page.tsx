"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { ArrowRight, CalendarClock, FlaskConical, TrendingUp } from "lucide-react";
import Link from "next/link";
import * as React from "react";
import { Button } from "@/components/ui/button";
import { AnimatedNumber, Badge, Card, CertaintyTag, FilterChips, PageHeader, SafetyNote, SectionHeader, Skeleton } from "@/components/ui/primitives";
import { api } from "@/lib/api";
import { CATEGORY_META } from "@/lib/categories";
import type { Category, Certainty } from "@/lib/types";
import { usePageContext } from "@/lib/use-page-context";
import { cn, money, shortDate, titleCase } from "@/lib/utils";

interface Insights {
  annual_premium: number;
  monthly_equivalent: number;
  premium_change_percent: number;
  by_category: { category: Category; premium: number }[];
  renewals: { policy_id: string; category: Category; carrier: string; date: string; days: number }[];
  deductible_exposure: { items: { category: Category; deductible: number }[]; worst_case_total: number };
  claims_history: { claim_number: string; category: Category; status: string; date: string; amount: number }[];
  premium_history: { year: number; total: number }[];
}

interface Simulation {
  available: boolean;
  label: string;
  disclaimer: string;
  title: string;
  metrics: { label: string; before: number; after: number; range?: [number, number]; certainty: Certainty }[];
  insights: string[];
  assumptions: string[];
}

export default function InsightsPage() {
  const { data } = useQuery({ queryKey: ["analytics"], queryFn: () => api.get<Insights>("/analytics") });
  usePageContext({ section: "insights", title: "Insights" });

  return (
    <div className="space-y-10">
      <PageHeader eyebrow="Insights" title="What your insurance really costs" subtitle="Only the numbers that matter — no wall of charts." />
      {!data ? (
        <Skeleton className="h-80 rounded-card" />
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-3">
            <Card className="p-5">
              <p className="text-sm text-muted">Annual premium</p>
              <p className="mt-2 font-display text-4xl font-semibold"><AnimatedNumber value={data.annual_premium} format={(n) => money(n)} /></p>
              <p className="mt-1 text-sm text-muted">≈ {money(data.monthly_equivalent)} per month</p>
            </Card>
            <Card className="p-5">
              <p className="text-sm text-muted">Change vs. last term</p>
              <p className="mt-2 flex items-center gap-2 font-display text-4xl font-semibold">
                <TrendingUp className={cn("size-7", data.premium_change_percent > 0 ? "text-danger" : "text-ok")} aria-hidden />
                {data.premium_change_percent > 0 ? "+" : ""}{data.premium_change_percent}%
              </p>
              <p className="mt-1 text-sm text-muted">
                {data.premium_history.map((h) => `${h.year}: ${money(h.total)}`).join(" → ")}
              </p>
            </Card>
            <Card className="p-5">
              <p className="text-sm text-muted">Deductible exposure</p>
              <p className="mt-2 font-display text-4xl font-semibold"><AnimatedNumber value={data.deductible_exposure.worst_case_total} format={(n) => money(n)} /></p>
              <p className="mt-1 text-sm text-muted">If every policy had a claim this year</p>
            </Card>
          </div>

          <div className="grid gap-4 lg:grid-cols-[1.3fr_1fr]">
            <Card className="p-6">
              <SectionHeader title="Premium by category" subtitle="Annual premium, active policies" />
              <PremiumBars rows={data.by_category} />
            </Card>
            <Card className="p-6">
              <SectionHeader title="Upcoming renewals" icon={CalendarClock} />
              <ul className="space-y-2">
                {data.renewals.map((r) => (
                  <li key={r.policy_id}>
                    <Link href={`/policies/${r.policy_id}?tab=renewal`} className="flex items-center justify-between rounded-xl bg-surface px-3 py-2.5 text-sm hover:bg-surface-hover">
                      <span>{CATEGORY_META[r.category].label} · {r.carrier}</span>
                      <span className="text-muted">{shortDate(r.date)} <Badge tone={r.days <= 30 ? "warn" : "neutral"} className="ml-1">{r.days}d</Badge></span>
                    </Link>
                  </li>
                ))}
              </ul>
              <SectionHeader title="Claims history" />
              <ul className="space-y-2">
                {data.claims_history.map((c) => (
                  <li key={c.claim_number} className="flex items-center justify-between rounded-xl bg-surface px-3 py-2.5 text-sm">
                    <span>{CATEGORY_META[c.category].label} · {c.claim_number}</span>
                    <span className="text-muted">{money(c.amount)} · {titleCase(c.status)}</span>
                  </li>
                ))}
              </ul>
            </Card>
          </div>
        </>
      )}
      <Simulator />
    </div>
  );
}

/** Single-series horizontal bars: one hue, direct value labels, hover tooltip. */
function PremiumBars({ rows }: { rows: { category: Category; premium: number }[] }) {
  const max = Math.max(...rows.map((r) => r.premium), 1);
  const total = rows.reduce((a, r) => a + r.premium, 0);
  const [hover, setHover] = React.useState<string | null>(null);
  return (
    <ul className="space-y-3" aria-label="Annual premium by category">
      {rows.map((r, i) => {
        const meta = CATEGORY_META[r.category];
        return (
          <li key={r.category} className="relative" onMouseEnter={() => setHover(r.category)} onMouseLeave={() => setHover(null)}>
            <div className="mb-1 flex justify-between text-sm">
              <span className="flex items-center gap-2 text-fg"><meta.icon className="size-4 text-muted" aria-hidden /> {meta.label}</span>
              <span className="tabular text-muted">{money(r.premium)}</span>
            </div>
            <div className="h-2.5 rounded-full bg-surface-hover">
              <motion.div className="h-full rounded-r-[4px] rounded-l-full bg-accent" initial={{ width: 0 }} animate={{ width: `${(r.premium / max) * 100}%` }} transition={{ delay: i * 0.06, duration: 0.7 }} />
            </div>
            {hover === r.category && (
              <div role="tooltip" className="glass-strong absolute right-0 top-full z-10 mt-1 rounded-lg px-2.5 py-1.5 text-xs">
                {meta.label}: {money(r.premium)}/yr · {Math.round((r.premium / total) * 100)}% of total · {money(r.premium / 12)}/mo
              </div>
            )}
          </li>
        );
      })}
    </ul>
  );
}

const SCENARIOS = [
  { value: "deductible", label: "Raise auto deductible", params: { category: "auto", from: 1000, to: 2000 }, prompt: "What happens if I increase my deductible?" },
  { value: "teen_driver", label: "Add a teen driver", params: {}, prompt: "What happens if I add a teenage driver?" },
  { value: "switch_health_plan", label: "Switch health plans", params: { expected_medical_spend: 6000 }, prompt: "What happens if I switch health plans?" },
] as const;

function Simulator() {
  const [scenario, setScenario] = React.useState<(typeof SCENARIOS)[number]["value"]>("deductible");
  const [to, setTo] = React.useState(2000);
  const [spend, setSpend] = React.useState(6000);
  const m = useMutation({ mutationFn: (body: object) => api.post<Simulation>("/simulate", body) });
  const run = React.useCallback(() => {
    const s = SCENARIOS.find((x) => x.value === scenario)!;
    const params = scenario === "deductible" ? { ...s.params, to } : scenario === "switch_health_plan" ? { expected_medical_spend: spend } : s.params;
    m.mutate({ scenario, params });
  }, [scenario, to, spend]); // eslint-disable-line react-hooks/exhaustive-deps
  React.useEffect(() => { run(); }, [run]);

  return (
    <section>
      <SectionHeader title="Scenario simulator" subtitle="“What happens if…?” — clearly labeled simulations, not quotes." icon={FlaskConical} />
      <Card className="p-6">
        <FilterChips label="Scenario" value={scenario} onChange={setScenario} options={SCENARIOS.map((s) => ({ value: s.value, label: s.label }))} />
        <div className="mt-5">
          {scenario === "deductible" && (
            <label className="block max-w-md text-sm">
              New collision deductible: <strong className="tabular">{money(to)}</strong>
              <input type="range" min={500} max={2500} step={500} value={to} onChange={(e) => setTo(Number(e.target.value))} className="mt-2 w-full accent-[var(--accent)]" />
            </label>
          )}
          {scenario === "switch_health_plan" && (
            <label className="block max-w-md text-sm">
              Expected medical spending this year: <strong className="tabular">{money(spend)}</strong>
              <input type="range" min={0} max={20000} step={500} value={spend} onChange={(e) => setSpend(Number(e.target.value))} className="mt-2 w-full accent-[var(--accent)]" />
            </label>
          )}
        </div>
        {m.data?.available ? (
          <div className="mt-6 space-y-5">
            <div className="flex items-center gap-2">
              <Badge tone="accent">{m.data.label}</Badge>
              <p className="font-display text-lg font-semibold">{m.data.title}</p>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              {m.data.metrics.map((x) => (
                <div key={x.label} className="rounded-2xl border border-border bg-surface p-4">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-sm text-muted">{x.label}</p>
                    <CertaintyTag certainty={x.certainty} />
                  </div>
                  <div className="mt-2 flex items-center gap-3">
                    <span className="tabular text-lg text-muted">{money(x.before)}</span>
                    <ArrowRight className="size-4 text-subtle" aria-hidden />
                    <span className="font-display text-2xl font-semibold tabular">{money(x.after)}</span>
                  </div>
                  {x.range && <p className="mt-1 text-xs text-subtle">Likely range {money(x.range[0])}–{money(x.range[1])}</p>}
                </div>
              ))}
            </div>
            <ul className="space-y-1 text-sm text-muted">{m.data.insights.map((i) => <li key={i}>• {i}</li>)}</ul>
            <SafetyNote>{m.data.disclaimer} Assumptions: {m.data.assumptions.join("; ")}.</SafetyNote>
            <Button size="sm" variant="secondary" asChild><Link href="/assistant">Discuss with AI</Link></Button>
          </div>
        ) : (
          <Skeleton className="mt-6 h-40" />
        )}
      </Card>
    </section>
  );
}
