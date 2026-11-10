"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { CheckCircle2, CircleHelp, FlaskConical, ShieldAlert, ShieldX, UserRoundCheck, Workflow } from "lucide-react";
import * as React from "react";
import { Button } from "@/components/ui/button";
import { Field, Input, Textarea } from "@/components/ui/overlay";
import { Badge, Card, PageHeader, SafetyNote, SectionHeader, Skeleton, type Tone } from "@/components/ui/primitives";
import { api } from "@/lib/api";
import { usePageContext } from "@/lib/use-page-context";
import { cn, money } from "@/lib/utils";

type Path = "auto_approve" | "adjuster_review" | "fraud_review" | "not_covered" | "low_confidence";

interface TriageResult {
  path: Path;
  label: string;
  tone: Tone;
  next_step: string;
  confidence: number;
  coverage: string | null;
  deductible: number;
  estimated_payout: number | null;
  reasons: { rule: string; detail: string; source?: string }[];
  missing: string[];
  policy: string;
  disclaimer: string;
}

interface QueueItem {
  id: string;
  claim_number: string;
  claimant: string;
  title: string;
  expected_path: Path;
  intake: Record<string, string | number | boolean | null>;
  result: TriageResult;
}

interface Queue {
  items: QueueItem[];
  limits: { demo_mode: boolean; max_upload_mb: number; claims_per_hour: number | null; auto_approve_limit: number };
}

const PATH_ICON: Record<Path, typeof CheckCircle2> = {
  auto_approve: CheckCircle2, adjuster_review: UserRoundCheck, fraud_review: ShieldAlert, not_covered: ShieldX, low_confidence: CircleHelp,
};

export default function TriagePage() {
  usePageContext({ section: "claims", title: "Claims triage" });
  const { data, isLoading } = useQuery({ queryKey: ["triage-queue"], queryFn: () => api.get<Queue>("/claims/triage/queue") });
  const [selected, setSelected] = React.useState<string | null>(null);
  const items = data?.items ?? [];
  const current = items.find((i) => i.id === selected) ?? items[0];

  return (
    <div className="space-y-10">
      <PageHeader
        eyebrow="Carrier view · synthetic data"
        title="Claims triage"
        subtitle="Every new claim is routed in seconds: paid straight through, flagged for fraud review, declined as not covered, or sent to a person when the file is too thin to decide."
      />

      <section>
        <SectionHeader title="Sample queue" subtitle="Five synthetic claims, one for each route. Pick one to see why it went where it did." icon={Workflow} />
        {isLoading ? (
          <Skeleton className="h-80 rounded-card" />
        ) : (
          <div className="grid gap-6 lg:grid-cols-[360px_1fr]">
            <ul className="space-y-2" aria-label="Sample claims">
              {items.map((it) => {
                const Icon = PATH_ICON[it.result.path];
                const active = current?.id === it.id;
                return (
                  <li key={it.id}>
                    <button
                      type="button"
                      onClick={() => setSelected(it.id)}
                      aria-pressed={active}
                      data-testid={`triage-sample-${it.claim_number}`}
                      className={cn("w-full rounded-2xl border p-4 text-left transition-colors",
                        active ? "border-accent bg-accent-soft/40" : "border-border bg-surface hover:bg-surface-hover")}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="font-medium">{it.title}</p>
                          <p className="text-xs text-muted">{it.claim_number} · {it.claimant}</p>
                        </div>
                        <Badge tone={it.result.tone} className="shrink-0 whitespace-nowrap"><Icon aria-hidden /> {it.result.label}</Badge>
                      </div>
                    </button>
                  </li>
                );
              })}
            </ul>
            {current && (
              <Card className="p-6">
                <p className="mb-1 text-xs text-muted">{current.claim_number} · {current.claimant}</p>
                <p className="mb-4 text-sm text-muted">{String(current.intake.description)}</p>
                <IntakeFacts intake={current.intake} />
                <div className="mt-6"><ResultView r={current.result} /></div>
              </Card>
            )}
          </div>
        )}
      </section>

      <TryYourOwn limits={data?.limits} />
    </div>
  );
}

function IntakeFacts({ intake }: { intake: QueueItem["intake"] }) {
  const facts: [string, string][] = [
    ["Type", String(intake.incident_type)],
    ["Vehicle use", String(intake.vehicle_use)],
    ["Incident", String(intake.incident_date)],
    ["Reported", String(intake.reported_date)],
    ["Policy start", String(intake.policy_start_date)],
    ["Claimed", intake.amount_claimed ? money(Number(intake.amount_claimed)) : "Not given"],
    ["Vehicle value", money(Number(intake.vehicle_value))],
    ["Photos", String(intake.photos ?? 0)],
    ["Police report", intake.police_report ? "Yes" : "No"],
    ["Claims, last 12 mo", String(intake.prior_claims_12mo ?? 0)],
  ];
  return (
    <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm sm:grid-cols-5">
      {facts.map(([k, v]) => (
        <div key={k}>
          <dt className="text-xs text-subtle">{k}</dt>
          <dd className="capitalize">{v}</dd>
        </div>
      ))}
    </dl>
  );
}

function ResultView({ r, testId = "triage-result" }: { r: TriageResult; testId?: string }) {
  const Icon = PATH_ICON[r.path];
  return (
    <motion.div key={r.path + r.confidence} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="space-y-4" data-testid={testId}>
      <div className="flex flex-wrap items-center gap-3">
        <Badge tone={r.tone} className="px-3 py-1 text-sm"><Icon aria-hidden /> {r.label}</Badge>
        <span className="text-sm text-muted">Data confidence {Math.round(r.confidence * 100)}%</span>
        {r.estimated_payout != null && (
          <span className="text-sm">Estimated payout <strong className="tabular">{money(r.estimated_payout)}</strong> after {money(r.deductible)} deductible</span>
        )}
      </div>
      <p className="text-sm">{r.next_step}</p>
      <ul className="divide-y divide-border rounded-2xl border border-border">
        {r.reasons.map((x, i) => (
          <li key={i} className="px-4 py-2.5 text-sm">
            <p className="font-medium">{x.rule}</p>
            <p className="text-muted">{x.detail}</p>
            {x.source && <p className="text-xs text-subtle">{x.source}</p>}
          </li>
        ))}
      </ul>
      <SafetyNote>{r.disclaimer}</SafetyNote>
    </motion.div>
  );
}

const today = () => new Date().toISOString().slice(0, 10);
const daysAgo = (n: number) => new Date(Date.now() - n * 864e5).toISOString().slice(0, 10);
const selectCls = "h-11 w-full rounded-xl border border-border bg-surface px-3 text-sm focus:border-accent focus:outline-none focus:ring-4 focus:ring-accent-soft";

function TryYourOwn({ limits }: { limits?: Queue["limits"] }) {
  const [f, setF] = React.useState({
    incident_type: "collision", vehicle_use: "personal",
    description: "Rear-ended at a red light. Rear bumper and trunk lid dented, nobody hurt.",
    incident_date: daysAgo(2), reported_date: today(), policy_start_date: daysAgo(180), amount_claimed: "2400",
    vehicle_value: "26000", photos: "3", police_report: false, prior_claims_12mo: "0",
  });
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
    setF((s) => ({ ...s, [k]: e.target.type === "checkbox" ? (e.target as HTMLInputElement).checked : e.target.value }));
  const m = useMutation({
    mutationFn: () => api.post<TriageResult>("/claims/triage", {
      ...f,
      policy_end_date: new Date(new Date(f.policy_start_date).getTime() + 365 * 864e5).toISOString().slice(0, 10),
      amount_claimed: f.amount_claimed ? Number(f.amount_claimed) : null,
      vehicle_value: Number(f.vehicle_value), photos: Number(f.photos || 0), prior_claims_12mo: Number(f.prior_claims_12mo || 0),
    }),
  });

  return (
    <section>
      <SectionHeader title="Try your own claim" subtitle="Change any detail and see how the route changes. Nothing you enter is saved." icon={FlaskConical} />
      <Card className="grid gap-6 p-6 lg:grid-cols-[420px_1fr]">
        <form onSubmit={(e) => { e.preventDefault(); m.mutate(); }} className="grid grid-cols-2 gap-4" aria-label="Triage a claim">
          <Field label="What happened" htmlFor="t-type">
            <select id="t-type" className={selectCls} value={f.incident_type} onChange={set("incident_type")}>
              {["collision", "glass", "theft", "vandalism", "weather", "other"].map((o) => <option key={o} value={o}>{o}</option>)}
            </select>
          </Field>
          <Field label="Vehicle use" htmlFor="t-use">
            <select id="t-use" className={selectCls} value={f.vehicle_use} onChange={set("vehicle_use")}>
              {["personal", "commute", "rideshare", "delivery", "racing"].map((o) => <option key={o} value={o}>{o}</option>)}
            </select>
          </Field>
          <div className="col-span-2">
            <Field label="Description" htmlFor="t-desc">
              <Textarea id="t-desc" rows={3} maxLength={1000} value={f.description} onChange={set("description")} />
            </Field>
          </div>
          <Field label="Incident date" htmlFor="t-inc"><Input id="t-inc" type="date" value={f.incident_date} onChange={set("incident_date")} /></Field>
          <Field label="Reported date" htmlFor="t-rep"><Input id="t-rep" type="date" value={f.reported_date} onChange={set("reported_date")} /></Field>
          <Field label="Policy start" htmlFor="t-pol"><Input id="t-pol" type="date" value={f.policy_start_date} onChange={set("policy_start_date")} /></Field>
          <Field label="Amount claimed ($)" htmlFor="t-amt"><Input id="t-amt" inputMode="decimal" value={f.amount_claimed} onChange={set("amount_claimed")} placeholder="Leave blank if unknown" /></Field>
          <Field label="Vehicle value ($)" htmlFor="t-val"><Input id="t-val" inputMode="decimal" value={f.vehicle_value} onChange={set("vehicle_value")} /></Field>
          <Field label="Photos" htmlFor="t-ph"><Input id="t-ph" type="number" min={0} max={50} value={f.photos} onChange={set("photos")} /></Field>
          <Field label="Claims, last 12 months" htmlFor="t-prior"><Input id="t-prior" type="number" min={0} max={20} value={f.prior_claims_12mo} onChange={set("prior_claims_12mo")} /></Field>
          <label className="flex items-center gap-2 self-end pb-3 text-sm">
            <input type="checkbox" checked={f.police_report} onChange={set("police_report")} /> Police report filed
          </label>
          <div className="col-span-2 space-y-2">
            <Button type="submit" loading={m.isPending} className="w-full"><Workflow /> Run triage</Button>
            {m.error && <p role="alert" className="text-sm text-danger">{(m.error as Error).message}</p>}
            {limits?.demo_mode && (
              <p className="text-xs text-subtle">Public demo: up to {limits.claims_per_hour} runs per hour, uploads up to {limits.max_upload_mb} MB.</p>
            )}
          </div>
        </form>
        <div>
          {m.data ? <ResultView r={m.data} testId="triage-own-result" /> : (
            <p className="grid h-full place-items-center rounded-2xl border border-dashed border-border-strong p-8 text-center text-sm text-muted">
              Try a rideshare trip, a theft reported weeks late, or a blank amount to see the other routes.
            </p>
          )}
        </div>
      </Card>
    </section>
  );
}
