"use client";

import { AlertTriangle, ArrowUpRight, CalendarClock, CircleCheck, CircleHelp, Sparkles } from "lucide-react";
import Link from "next/link";
import { Badge, Progress, TiltCard } from "@/components/ui/primitives";
import { CATEGORY_META } from "@/lib/categories";
import { useAssistant } from "@/lib/store";
import type { PolicyCard as P } from "@/lib/types";
import { cn, money, relativeDays, shortDate } from "@/lib/utils";

const HEALTH = {
  healthy: { tone: "ok", label: "Coverage healthy", icon: CircleCheck },
  review: { tone: "warn", label: "Worth reviewing", icon: CircleHelp },
  attention: { tone: "danger", label: "Needs attention", icon: AlertTriangle },
  inactive: { tone: "neutral", label: "Expired", icon: CalendarClock },
} as const;

/** Visually rich policy card used on the dashboard and in the Insurance Wallet. */
export function PolicyCard({ p, variant = "full" }: { p: P; variant?: "full" | "wallet" }) {
  const meta = CATEGORY_META[p.category];
  const health = HEALTH[p.coverage_health];
  const ask = useAssistant((s) => s.ask);
  const change = p.prior_premium_annual ? Math.round(((p.premium_annual - p.prior_premium_annual) / p.prior_premium_annual) * 100) : 0;

  return (
    <TiltCard className={cn("flex h-full flex-col p-5", p.status === "lapsed" && "opacity-75")}>
      <div aria-hidden className="pointer-events-none absolute -right-10 -top-10 size-36 rounded-full opacity-25 blur-3xl" style={{ background: meta.hue }} />
      <div className="relative flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="grid size-11 place-items-center rounded-2xl ring-1 ring-border" style={{ background: `color-mix(in oklab, ${meta.hue} 16%, transparent)` }}>
            <meta.icon className="size-5" style={{ color: meta.hue }} aria-hidden />
          </div>
          <div>
            <p className="text-xs font-medium uppercase tracking-wider text-subtle">{meta.label}</p>
            <p className="font-display font-semibold leading-tight">{p.carrier.name}</p>
          </div>
        </div>
        <Badge tone={health.tone as never}>
          <health.icon aria-hidden /> {health.label}
        </Badge>
      </div>

      <p className="relative mt-3 line-clamp-2 text-sm text-muted">{p.summary}</p>

      <dl className="relative mt-4 grid grid-cols-2 gap-3 text-sm">
        <div>
          <dt className="text-xs text-subtle">Premium</dt>
          <dd className="font-semibold tabular">
            {money(p.premium_monthly)}<span className="text-xs font-normal text-subtle">/mo</span>
            {change >= 10 && <span className="ml-1.5 text-xs font-medium text-danger">+{change}%</span>}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-subtle">{p.status === "lapsed" ? "Ended" : "Renews"}</dt>
          <dd className="font-medium">
            {shortDate(p.expiration_date)}
            {p.days_until_renewal >= 0 && p.days_until_renewal <= 45 && <span className="block text-xs text-warn">{relativeDays(p.days_until_renewal)}</span>}
          </dd>
        </div>
        {p.category === "health" && p.deductible_remaining !== undefined && (
          <>
            <div className="col-span-2">
              <dt className="flex justify-between text-xs text-subtle"><span>Deductible remaining</span><span className="tabular">{money(p.deductible_remaining)}</span></dt>
              <dd className="mt-1"><Progress value={p.deductible_progress ?? 0} tone="ok" label="Deductible met" /></dd>
            </div>
            <div className="col-span-2">
              <dt className="flex justify-between text-xs text-subtle"><span>Out-of-pocket remaining</span><span className="tabular">{money(p.oop_remaining)}</span></dt>
              <dd className="mt-1"><Progress value={p.oop_progress ?? 0} label="Out-of-pocket met" /></dd>
            </div>
          </>
        )}
        {p.category === "life" && (
          <>
            <div>
              <dt className="text-xs text-subtle">Coverage</dt>
              <dd className="font-semibold tabular">{money(p.coverage_amount)}</dd>
            </div>
            <div>
              <dt className="text-xs text-subtle">Beneficiaries</dt>
              <dd className="text-xs font-medium text-warn">{p.beneficiary_status}</dd>
            </div>
          </>
        )}
        {p.category !== "health" && p.category !== "life" && variant === "full" && (
          <div>
            <dt className="text-xs text-subtle">Deductible</dt>
            <dd className="font-medium tabular">{money(p.deductible)}</dd>
          </div>
        )}
        {p.claim_status && (
          <div>
            <dt className="text-xs text-subtle">Claim</dt>
            <dd className="font-medium capitalize">{p.claim_status.replace("_", " ")}</dd>
          </div>
        )}
      </dl>

      {p.alerts.length > 0 && (
        <ul className="relative mt-3 space-y-1">
          {p.alerts.slice(0, 2).map((a) => (
            <li key={a.title} className="flex items-start gap-1.5 text-xs text-muted">
              <AlertTriangle className={cn("mt-px size-3.5 shrink-0", a.severity === "attention" ? "text-danger" : "text-warn")} aria-hidden />
              {a.title}
            </li>
          ))}
        </ul>
      )}

      <div className="relative mt-auto flex gap-2 pt-4">
        <Link href={`/policies/${p.id}`} className="inline-flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-medium text-fg ring-1 ring-border transition hover:bg-surface-hover">
          Details <ArrowUpRight className="size-3.5" aria-hidden />
        </Link>
        <button onClick={() => ask(`Explain my ${meta.label.toLowerCase()} insurance`)} className="inline-flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-medium text-accent transition hover:bg-accent-soft">
          <Sparkles className="size-3.5" aria-hidden /> Explain
        </button>
      </div>
    </TiltCard>
  );
}
