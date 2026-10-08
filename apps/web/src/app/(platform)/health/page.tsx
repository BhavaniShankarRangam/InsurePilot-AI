"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { HeartPulse, MessageSquareText, Search, Stethoscope, Star } from "lucide-react";
import { useSearchParams } from "next/navigation";
import * as React from "react";
import { ExplainThis } from "@/components/ai/explain-this";
import { PriorAuthView, ProcedureView, ReconciliationView, type PriorAuth, type ProcedureCheck, type Reconciliation } from "@/components/health/views";
import { Button } from "@/components/ui/button";
import { Field, Input, Switch, Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/overlay";
import { AnimatedNumber, Badge, Card, EmptyState, PageHeader, Progress, SectionHeader, Skeleton } from "@/components/ui/primitives";
import { api } from "@/lib/api";
import { useAssistant } from "@/lib/store";
import { usePageContext } from "@/lib/use-page-context";
import { money, shortDate, titleCase } from "@/lib/utils";

interface HealthSummary {
  plan: { name: string; type: string; network: string; plan_year_end: string; copays: Record<string, number>; benefits: { name: string; coverage: string }[]; coinsurance_in: number; coinsurance_out: number };
  accumulators: { deductible: number; deductible_met: number; oop_max: number; oop_met: number };
  authorizations: (PriorAuth & { id: string })[];
  bills: { id: string; service: string; date: string; total: number; amount_due: number; due_date: string | null }[];
  terms: Record<string, string>;
}

export default function HealthPage() {
  return (
    <React.Suspense fallback={<Skeleton className="h-96 rounded-card" />}>
      <HealthInner />
    </React.Suspense>
  );
}

function HealthInner() {
  const tab = useSearchParams().get("tab") ?? "overview";
  const { data, isLoading, error } = useQuery({ queryKey: ["health-summary"], queryFn: () => api.get<HealthSummary>("/health/summary") });
  usePageContext({ section: "health", category: "health", title: "Health benefits" });

  if (error) return <EmptyState icon={HeartPulse} title="No health plan yet" body="Upload your benefits summary or insurance card and InsurePilot will set this up." />;
  if (isLoading || !data) return <Skeleton className="h-[600px] rounded-card" />;
  const a = data.accumulators;

  return (
    <div>
      <PageHeader eyebrow="Health Insurance AI" title={data.plan.name} subtitle={`${data.plan.type} · ${data.plan.network} network · plan year ends ${shortDate(data.plan.plan_year_end)}`} />
      <div className="mb-8 grid gap-4 md:grid-cols-2">
        <Card className="p-5">
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted">Deductible</p>
            <ExplainThis kind="term" refId="deductible" label="Deductible" />
          </div>
          <p className="mt-2 font-display text-3xl font-semibold"><AnimatedNumber value={a.deductible - a.deductible_met} format={(n) => money(n)} /> <span className="text-base font-normal text-muted">left</span></p>
          <Progress value={a.deductible_met / a.deductible} tone="ok" className="mt-3" label="Deductible met" />
          <p className="mt-1.5 text-xs text-subtle">{money(a.deductible_met)} of {money(a.deductible)} met</p>
        </Card>
        <Card className="p-5">
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted">Out-of-pocket maximum</p>
            <ExplainThis kind="term" refId="out_of_pocket_max" label="Out-of-pocket maximum" />
          </div>
          <p className="mt-2 font-display text-3xl font-semibold"><AnimatedNumber value={a.oop_max - a.oop_met} format={(n) => money(n)} /> <span className="text-base font-normal text-muted">left</span></p>
          <Progress value={a.oop_met / a.oop_max} className="mt-3" label="Out-of-pocket met" />
          <p className="mt-1.5 text-xs text-subtle">{money(a.oop_met)} of {money(a.oop_max)} spent</p>
        </Card>
      </div>

      <Tabs defaultValue={tab}>
        <TabsList>
          <TabsTrigger value="overview">Benefits</TabsTrigger>
          <TabsTrigger value="procedure">Procedure checker</TabsTrigger>
          <TabsTrigger value="bills">Bills & EOBs</TabsTrigger>
          <TabsTrigger value="authorizations">Prior authorization</TabsTrigger>
          <TabsTrigger value="providers">Find a provider</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <div className="grid gap-4 lg:grid-cols-2">
            <Card className="p-6">
              <SectionHeader title="What you pay" />
              <ul className="space-y-2 text-sm">
                {Object.entries(data.plan.copays).map(([k, v]) => (
                  <li key={k} className="flex justify-between rounded-xl bg-surface px-3 py-2"><span>{titleCase(k)}</span><span className="font-semibold tabular">{money(v)} copay</span></li>
                ))}
                <li className="flex items-center justify-between rounded-xl bg-surface px-3 py-2">
                  <span className="flex items-center gap-2">Coinsurance <ExplainThis kind="term" refId="coinsurance" label="Coinsurance" small /></span>
                  <span className="font-semibold">{data.plan.coinsurance_in}% in-network · {data.plan.coinsurance_out}% out</span>
                </li>
              </ul>
              <SectionHeader title="Benefits" />
              <ul className="space-y-2 text-sm">
                {data.plan.benefits.map((b) => (
                  <li key={b.name} className="flex justify-between gap-3 rounded-xl bg-surface px-3 py-2"><span>{b.name}</span><span className="text-right text-muted">{b.coverage}</span></li>
                ))}
              </ul>
            </Card>
            <Card className="p-6">
              <SectionHeader title="Insurance words, explained" subtitle="You never need to learn these — but here they are." />
              <dl className="space-y-3">
                {Object.entries(data.terms).map(([k, v]) => (
                  <div key={k} className="rounded-xl bg-surface px-3 py-2.5">
                    <dt className="text-sm font-medium">{titleCase(k)}</dt>
                    <dd className="text-sm text-muted">{v}</dd>
                  </div>
                ))}
              </dl>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="procedure"><ProcedureChecker /></TabsContent>
        <TabsContent value="bills"><Bills bills={data.bills} /></TabsContent>
        <TabsContent value="authorizations">
          {data.authorizations.length === 0 ? (
            <EmptyState icon={Stethoscope} title="No authorizations" body="When your doctor requests approval for a procedure, it'll show up here." />
          ) : (
            data.authorizations.map((auth) => (
              <Card key={auth.id} className="mb-4 p-6">
                <SectionHeader title={auth.procedure} subtitle={auth.provider ?? undefined} action={<AskButton prompt={`Check my ${auth.procedure.split(",")[0]} prior authorization`} />} />
                <PriorAuthView a={auth} />
              </Card>
            ))
          )}
        </TabsContent>
        <TabsContent value="providers"><Providers /></TabsContent>
      </Tabs>
    </div>
  );
}

function AskButton({ prompt }: { prompt: string }) {
  const ask = useAssistant((s) => s.ask);
  return <Button size="sm" variant="secondary" onClick={() => ask(prompt)}><MessageSquareText /> Ask AI</Button>;
}

function ProcedureChecker() {
  const [procedure, setProcedure] = React.useState("MRI of lower back");
  const [provider, setProvider] = React.useState("St. Brightwater Medical Center");
  const m = useMutation({ mutationFn: () => api.post<ProcedureCheck>("/health/procedure-check", { procedure, provider }) });
  return (
    <Card className="grid gap-6 p-6 lg:grid-cols-[320px_1fr]">
      <form onSubmit={(e) => { e.preventDefault(); m.mutate(); }} className="space-y-4">
        <p className="font-display text-lg font-semibold">“Can I get this procedure here?”</p>
        <Field label="Procedure" htmlFor="proc"><Input id="proc" value={procedure} onChange={(e) => setProcedure(e.target.value)} /></Field>
        <Field label="Hospital or provider" htmlFor="prov"><Input id="prov" value={provider} onChange={(e) => setProvider(e.target.value)} /></Field>
        <Button type="submit" loading={m.isPending} className="w-full"><Search /> Check coverage & cost</Button>
      </form>
      <div>{m.data ? <ProcedureView r={m.data} /> : <p className="grid h-full min-h-48 place-items-center rounded-2xl border border-dashed border-border-strong p-8 text-center text-sm text-muted">We’ll check your plan, the provider’s network, the likely procedure code, your deductible, coinsurance and authorization rules — with sources.</p>}</div>
    </Card>
  );
}

function Bills({ bills }: { bills: HealthSummary["bills"] }) {
  const { data } = useQuery({ queryKey: ["reconciliation"], queryFn: () => api.get<Reconciliation & { available: boolean }>("/health/reconciliation") });
  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_1.3fr]">
      <Card className="p-6">
        <SectionHeader title="Medical bills" />
        <ul className="space-y-2">
          {bills.map((b) => (
            <li key={b.id} className="rounded-xl bg-surface p-3">
              <p className="font-medium">{b.service}</p>
              <p className="text-sm text-muted">{shortDate(b.date)} · billed {money(b.total)}</p>
              <p className="mt-1 text-sm">Amount due <strong className="tabular">{money(b.amount_due)}</strong>{b.due_date && <span className="text-subtle"> by {shortDate(b.due_date)}</span>}</p>
            </li>
          ))}
        </ul>
        <div className="mt-4"><AskButton prompt="Explain my hospital bill" /></div>
      </Card>
      <Card className="p-6">
        <SectionHeader title="Hospital bill vs. insurer EOB" subtitle="Every amount compared — discrepancies highlighted" action={<ExplainThis kind="term" refId="eob" label="EOB" />} />
        {data?.available ? <ReconciliationView r={data} /> : <Skeleton className="h-64" />}
      </Card>
    </div>
  );
}

function Providers() {
  const [q, setQ] = React.useState("");
  const [inNet, setInNet] = React.useState(true);
  const { data, isFetching } = useQuery({
    queryKey: ["providers", q, inNet],
    queryFn: () => api.get<{ id: string; name: string; kind: string; specialty: string; city: string; in_network: boolean; rating: number; accepting: boolean }[]>(`/providers?q=${encodeURIComponent(q)}&in_network_only=${inNet}`),
  });
  return (
    <Card className="p-6">
      <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center">
        <label htmlFor="prov-q" className="sr-only">Search providers</label>
        <Input id="prov-q" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Imaging, orthopedic, primary care…" className="sm:max-w-sm" />
        <label className="flex items-center gap-2 text-sm text-muted">
          <Switch checked={inNet} onCheckedChange={setInNet} label="In-network only" /> In-network only
        </label>
        {isFetching && <span className="text-xs text-subtle">Searching…</span>}
      </div>
      <ul className="grid gap-3 md:grid-cols-2">
        {data?.map((p) => (
          <li key={p.id} className="rounded-2xl border border-border bg-surface p-4">
            <div className="flex items-start justify-between gap-2">
              <div>
                <p className="font-medium">{p.name}</p>
                <p className="text-sm text-muted">{p.specialty} · {p.city}</p>
              </div>
              <Badge tone={p.in_network ? "ok" : "warn"}>{p.in_network ? "In-network" : "Out-of-network"}</Badge>
            </div>
            <p className="mt-2 inline-flex items-center gap-1 text-xs text-subtle"><Star className="size-3.5" aria-hidden /> {p.rating} · {p.accepting ? "Accepting new patients" : "Not accepting"}</p>
          </li>
        ))}
      </ul>
      {data?.length === 0 && <p className="py-8 text-center text-sm text-muted">No providers match. Try a broader search.</p>}
    </Card>
  );
}
