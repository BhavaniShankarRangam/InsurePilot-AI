"use client";

import type { LucideIcon } from "lucide-react";
import { AlertTriangle, ArrowRight, CalendarClock, ChevronDown, CircleCheck, HeartPulse, PiggyBank, Plus, Sparkles, Workflow } from "lucide-react";
import Link from "next/link";
import * as React from "react";
import { Orb } from "@/components/ai/orb";
import { ClaimTimeline } from "@/components/claims/timeline";
import { ActionCenter } from "@/components/dashboard/action-center";
import { PolicyCard } from "@/components/dashboard/policy-card";
import { ScoreRing } from "@/components/dashboard/score-ring";
import { Button } from "@/components/ui/button";
import { AnimatedNumber, Badge, Card, CertaintyTag, EmptyState, motion, Reveal, SectionHeader, Skeleton } from "@/components/ui/primitives";
import { CATEGORY_META } from "@/lib/categories";
import { useClaim, useDashboard } from "@/lib/queries";
import { useAssistant } from "@/lib/store";
import type { Dashboard } from "@/lib/types";
import { usePageContext } from "@/lib/use-page-context";
import { cn, money, shortDate } from "@/lib/utils";

export default function DashboardPage() {
  const { data, isLoading } = useDashboard();
  usePageContext({ section: "dashboard", title: "Home" });

  if (isLoading || !data) return <DashboardSkeleton />;

  const sections: Record<string, React.ReactNode> = {
    claims: <ClaimsPriority key="claims" d={data} />,
    renewal: <RenewalPriority key="renewal" d={data} />,
    health: <HealthPriority key="health" d={data} />,
    summary: null,
    actions: (
      <section key="actions" aria-labelledby="actions-h">
        <SectionHeader title="What needs your attention?" subtitle="Ranked by importance. Uncertain findings are labeled as possible." icon={AlertTriangle} />
        <ActionCenter items={data.actions} />
      </section>
    ),
    wallet: <WalletSection key="wallet" d={data} />,
    insights: <SavingsSection key="insights" d={data} />,
  };
  const priority = data.layout.filter((s) => ["claims", "renewal", "health"].includes(s));
  const rest = data.layout.filter((s) => !["claims", "renewal", "health", "summary"].includes(s));

  return (
    <div className="space-y-10">
      <Hero d={data} />
      {priority.length > 0 && (
        <section aria-label="Priorities right now">
          <p className="mb-3 flex items-center gap-2 text-xs font-medium uppercase tracking-[0.16em] text-subtle">
            <Sparkles className="size-3.5 text-accent" aria-hidden /> Arranged by AI for what’s happening now
          </p>
          <div className="grid gap-4 lg:grid-cols-3">{priority.map((s) => sections[s])}</div>
        </section>
      )}
      {rest.map((s) => sections[s])}
    </div>
  );
}

function Hero({ d }: { d: Dashboard }) {
  const [open, setOpen] = React.useState(false);
  const ask = useAssistant((s) => s.ask);
  const attention = d.stats.actions_needed;
  return (
    <Reveal>
      <Card className="p-6 md:p-8">
        <div aria-hidden className="grid-bg pointer-events-none absolute inset-0 opacity-70" />
        <div className="relative grid gap-8 lg:grid-cols-[1fr_auto]">
          <div className="flex flex-col">
            <p className="text-sm text-muted">{new Date().toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" })}</p>
            <h1 className="mt-1 font-display text-3xl font-semibold tracking-tight md:text-[42px] md:leading-[1.1]">
              {d.greeting}, {d.name}.
            </h1>
            <p className="mt-2 text-xl text-muted md:text-2xl">
              {attention === 0 ? "Your insurance looks healthy." : (
                <>You have <span className="text-gradient font-semibold">{attention} item{attention === 1 ? "" : "s"}</span> that need attention.</>
              )}
            </p>
            <div className="mt-5 flex items-start gap-3 rounded-2xl border border-border bg-surface p-4">
              <Orb state="idle" size={30} />
              <div className="min-w-0 text-sm">
                <p className="font-medium">Today’s summary</p>
                <p className="text-muted">{d.daily_summary.headline}</p>
                <ul className="mt-1.5 space-y-0.5 text-muted">
                  {d.daily_summary.items.map((i) => (
                    <li key={i}>• {i}</li>
                  ))}
                </ul>
              </div>
            </div>
            <div className="mt-5 flex flex-wrap gap-2">
              <Button onClick={() => ask("Handle my insurance")}>
                <Sparkles /> Handle my insurance
              </Button>
              <Button variant="secondary" onClick={() => ask("Find coverage gaps")}>Find coverage gaps</Button>
            </div>
          </div>
          <div className="flex flex-col items-center">
            <p className="mb-2 text-xs font-medium uppercase tracking-[0.16em] text-subtle">Insurance Health Score</p>
            <ScoreRing score={d.health_score.score} />
            <button onClick={() => setOpen((v) => !v)} aria-expanded={open} className="mt-3 inline-flex items-center gap-1 text-sm text-accent hover:underline">
              Why your score is {d.health_score.score}
              <ChevronDown className={cn("size-4 transition-transform", open && "rotate-180")} aria-hidden />
            </button>
          </div>
        </div>
        <motion.div initial={false} animate={{ height: open ? "auto" : 0, opacity: open ? 1 : 0 }} className="relative overflow-hidden">
          <div className="mt-6 grid gap-6 border-t border-border pt-6 md:grid-cols-2">
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-ok">Working well</p>
              <ul className="space-y-1.5 text-sm">
                {d.health_score.positives.map((p) => (
                  <li key={p.label} className="flex gap-2"><CircleCheck className="mt-0.5 size-4 shrink-0 text-ok" aria-hidden /> {p.label}</li>
                ))}
              </ul>
            </div>
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-warn">Lowering your score</p>
              <ul className="space-y-1.5 text-sm">
                {d.health_score.factors.map((f) => (
                  <li key={f.label} className="flex items-start justify-between gap-2">
                    <span className="flex gap-2"><AlertTriangle className={cn("mt-0.5 size-4 shrink-0", f.severity === "attention" ? "text-danger" : "text-warn")} aria-hidden /> {f.label}</span>
                    <span className="flex shrink-0 items-center gap-1.5"><CertaintyTag certainty={f.certainty} /><span className="tabular text-xs text-subtle">{f.impact}</span></span>
                  </li>
                ))}
              </ul>
            </div>
            <p className="text-xs text-subtle md:col-span-2">{d.health_score.disclaimer}</p>
          </div>
        </motion.div>
        <div className="relative mt-8 grid grid-cols-2 gap-3 md:grid-cols-4">
          {[
            { label: "Action needed", value: d.stats.actions_needed, icon: AlertTriangle, tone: "text-danger", fmt: (n: number) => String(Math.round(n)) },
            { label: "Renewal upcoming", value: d.stats.renewals_upcoming, icon: CalendarClock, tone: "text-warn", fmt: (n: number) => String(Math.round(n)) },
            { label: "Potential savings", value: d.stats.potential_savings, icon: PiggyBank, tone: "text-ok", fmt: (n: number) => money(n) },
            { label: "Active claims", value: d.stats.active_claims, icon: Workflow, tone: "text-info", fmt: (n: number) => String(Math.round(n)) },
          ].map((s, i) => (
            <motion.div key={s.label} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 + i * 0.07 }} className="rounded-2xl border border-border bg-surface p-4">
              <s.icon className={cn("size-5", s.tone)} aria-hidden />
              <p className="mt-3 font-display text-2xl font-semibold"><AnimatedNumber value={s.value} format={s.fmt} /></p>
              <p className="text-sm text-muted">{s.label}</p>
            </motion.div>
          ))}
        </div>
      </Card>
    </Reveal>
  );
}

function PriorityCard({ title, icon: Icon, tone, children, href, cta }: { title: string; icon: LucideIcon; tone: string; children: React.ReactNode; href: string; cta: string }) {
  return (
    <Card interactive className="flex flex-col p-5">
      <p className={cn("mb-3 flex items-center gap-2 text-sm font-semibold", tone)}>
        <Icon className="size-4" aria-hidden /> {title}
      </p>
      <div className="flex-1">{children}</div>
      <Link href={href} className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-accent hover:underline">
        {cta} <ArrowRight className="size-4" aria-hidden />
      </Link>
    </Card>
  );
}

function ClaimsPriority({ d }: { d: Dashboard }) {
  const claim = d.claims.find((c) => ["in_review", "submitted"].includes(c.status));
  const { data: detail } = useClaim(claim?.id ?? "");
  if (!claim) return null;
  return (
    <PriorityCard title="Active claim" icon={Workflow} tone="text-info" href={`/claims/${claim.id}`} cta="Open Claim Guardian">
      <p className="font-medium">{claim.title}</p>
      <p className="mb-4 text-xs text-muted">Claim {claim.claim_number} · {claim.stage}</p>
      {detail ? <ClaimTimeline events={detail.events.slice(-4)} explain={false} /> : <Skeleton className="h-32" />}
      {claim.missing_documents.length > 0 && <Badge tone="warn" className="mt-3"><AlertTriangle aria-hidden /> Needs: {claim.missing_documents.join(", ")}</Badge>}
    </PriorityCard>
  );
}

function RenewalPriority({ d }: { d: Dashboard }) {
  const p = d.policies.find((x) => x.days_until_renewal >= 0 && x.days_until_renewal <= 45 && x.status !== "lapsed");
  if (!p) return null;
  const change = p.prior_premium_annual ? Math.round(((p.premium_annual - p.prior_premium_annual) / p.prior_premium_annual) * 100) : 0;
  const meta = CATEGORY_META[p.category];
  return (
    <PriorityCard title="Renewal coming up" icon={CalendarClock} tone="text-warn" href={`/policies/${p.id}?tab=renewal`} cta="Review renewal">
      <p className="font-medium">{meta.label} · {p.carrier.name}</p>
      <p className="text-xs text-muted">Renews {shortDate(p.expiration_date)} · in {p.days_until_renewal} days</p>
      <div className="mt-5 flex items-end gap-3">
        <span className="text-sm text-subtle line-through tabular">{money(p.prior_premium_annual)}</span>
        <span className="font-display text-3xl font-semibold tabular">{money(p.premium_annual)}</span>
        <span className="text-sm text-subtle">/yr</span>
      </div>
      {change !== 0 && <Badge tone={change > 0 ? "danger" : "ok"} className="mt-2">{change > 0 ? "+" : ""}{change}% vs last term</Badge>}
      <p className="mt-3 text-sm text-muted">InsurePilot found the confirmed reasons and {d.savings.items.length} ways to save. Nothing changes without your approval.</p>
    </PriorityCard>
  );
}

function HealthPriority({ d }: { d: Dashboard }) {
  const a = d.authorizations.find((x) => ["pending", "submitted"].includes(x.status));
  if (!a) return null;
  return (
    <PriorityCard title="Health authorization pending" icon={HeartPulse} tone="text-ok" href="/health?tab=authorizations" cta="Open health navigator">
      <p className="font-medium">{a.procedure}</p>
      <p className="text-xs text-muted">Decision expected {shortDate(a.decision_due)}</p>
      {a.missing.length > 0 && (
        <div className="mt-4 rounded-xl border border-warn/40 bg-warn-soft/40 p-3 text-sm">
          <p className="flex items-center gap-1.5 font-medium"><AlertTriangle className="size-4 text-warn" aria-hidden /> Possibly missing</p>
          <p className="text-muted">{a.missing.join(", ")}</p>
        </div>
      )}
    </PriorityCard>
  );
}

function WalletSection({ d }: { d: Dashboard }) {
  return (
    <section aria-labelledby="wallet-h">
      <SectionHeader title="Your insurance" subtitle={`${d.policies.filter((p) => p.status !== "lapsed").length} active policies`} action={<Link href="/wallet" className="text-sm text-accent hover:underline">Open wallet</Link>} />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {d.policies.map((p, i) => (
          <Reveal key={p.id} delay={i * 0.05} className="h-full">
            <PolicyCard p={p} />
          </Reveal>
        ))}
        {d.empty_categories.map((c) => {
          const meta = CATEGORY_META[c];
          return (
            <Link key={c} href="/documents?upload=1" className="group flex min-h-48 flex-col items-center justify-center gap-2 rounded-card border border-dashed border-border-strong p-6 text-center text-muted transition hover:border-accent hover:text-fg">
              <meta.icon className="size-6" aria-hidden />
              <p className="font-medium">{meta.label} insurance</p>
              <p className="text-xs">Upload a policy and InsurePilot will organize it for you.</p>
              <span className="mt-1 inline-flex items-center gap-1 text-xs text-accent"><Plus className="size-3.5" aria-hidden /> Add policy</span>
            </Link>
          );
        })}
      </div>
    </section>
  );
}

function SavingsSection({ d }: { d: Dashboard }) {
  if (!d.savings.items.length) return <EmptyState icon={PiggyBank} title="No savings found right now" body="We'll keep looking as your policies renew." />;
  return (
    <section aria-labelledby="savings-h">
      <SectionHeader title="Potential savings" subtitle="Estimates — each one needs your review before anything changes." icon={PiggyBank} />
      <div className="grid gap-3 md:grid-cols-3">
        {d.savings.items.map((s) => (
          <Card key={s.label} className="p-5">
            <p className="font-display text-2xl font-semibold text-ok tabular">{money(s.amount)}</p>
            <p className="mt-1 font-medium">{s.label}</p>
            <p className="mt-1 text-sm text-muted">{s.note}</p>
            <div className="mt-3"><CertaintyTag certainty={s.certainty} /></div>
          </Card>
        ))}
      </div>
    </section>
  );
}

function DashboardSkeleton() {
  return (
    <div className="space-y-8" aria-busy="true" aria-label="Loading your dashboard">
      <Skeleton className="h-[420px] w-full rounded-card" />
      <div className="grid gap-4 lg:grid-cols-3">
        {[0, 1, 2].map((i) => <Skeleton key={i} className="h-64 rounded-card" />)}
      </div>
    </div>
  );
}
