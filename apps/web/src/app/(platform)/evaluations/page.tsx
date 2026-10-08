"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Activity, FlaskConical, Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge, Card, EmptyState, PageHeader, SectionHeader, Skeleton } from "@/components/ui/primitives";
import { api, ApiError } from "@/lib/api";
import { usePageContext } from "@/lib/use-page-context";
import { cn, timeAgo } from "@/lib/utils";

interface Run { id: string; suite: string; metrics: Record<string, number>; cases: Record<string, unknown>[]; notes: string | null; created_at: string }
interface Metrics { llm: { provider: string; model: string; task: string; calls: number; input_tokens: number; output_tokens: number; cost_usd: number; avg_latency_ms: number; errors: number }[]; tools: { tool: string; calls: number; avg_latency_ms: number; failures: number }[] }

const METRICS: { key: string; label: string; invert?: boolean; fmt?: (n: number) => string }[] = [
  { key: "faithfulness", label: "Faithfulness" },
  { key: "answer_relevance", label: "Answer relevance" },
  { key: "context_relevance", label: "Context relevance" },
  { key: "context_precision", label: "Context precision" },
  { key: "context_recall", label: "Context recall" },
  { key: "citation_accuracy", label: "Citation accuracy" },
  { key: "fact_coverage", label: "Fact coverage" },
  { key: "routing_accuracy", label: "Agent routing" },
  { key: "hallucination_risk", label: "Hallucination risk", invert: true },
  { key: "latency_ms", label: "Avg latency", fmt: (n) => `${Math.round(n)} ms` },
  { key: "cost_usd", label: "Cost", fmt: (n) => `$${n.toFixed(4)}` },
];

const pct = (n: number) => `${Math.round(n * 100)}%`;

/** Internal RAG / agent evaluation dashboard. */
export default function EvaluationsPage() {
  const qc = useQueryClient();
  const runs = useQuery({ queryKey: ["evals"], queryFn: () => api.get<Run[]>("/ai/evaluations") });
  const metrics = useQuery({ queryKey: ["metrics"], queryFn: () => api.get<Metrics>("/admin/metrics") });
  const run = useMutation({ mutationFn: () => api.post<Run>("/ai/evaluations/run"), onSuccess: () => { qc.invalidateQueries({ queryKey: ["evals"] }); qc.invalidateQueries({ queryKey: ["metrics"] }); } });
  usePageContext({ section: "evaluations", title: "AI Evaluations" });

  if (runs.error instanceof ApiError && runs.error.status === 403) return <EmptyState icon={FlaskConical} title="Analyst access required" body="Evaluations are available to analyst and admin roles." />;
  const latest = runs.data?.[0];

  return (
    <div className="space-y-10">
      <PageHeader eyebrow="Internal" title="AI evaluation dashboard" subtitle="Golden-set evaluation of retrieval quality, grounding, citations, routing, latency and cost. RAGAS-compatible metrics." actions={<Button onClick={() => run.mutate()} loading={run.isPending}><Play /> Run evaluation</Button>} />
      {runs.isLoading ? <Skeleton className="h-64 rounded-card" /> : !latest ? (
        <EmptyState icon={FlaskConical} title="No evaluation runs yet" body="Run the golden-set suite to measure retrieval and answer quality." action={<Button onClick={() => run.mutate()} loading={run.isPending}>Run evaluation</Button>} />
      ) : (
        <>
          <section>
            <SectionHeader title={`Latest run · ${latest.suite}`} subtitle={`${latest.metrics.cases} cases · ${timeAgo(latest.created_at)}`} />
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-6">
              {METRICS.map((m) => {
                const v = latest.metrics[m.key] ?? 0;
                const good = m.fmt ? true : m.invert ? v <= 0.1 : v >= 0.8;
                const warn = !m.fmt && (m.invert ? v > 0.1 && v <= 0.25 : v >= 0.5 && v < 0.8);
                return (
                  <Card key={m.key} className="p-4">
                    <p className="text-xs text-subtle">{m.label}</p>
                    <p className="mt-1 font-display text-2xl font-semibold tabular">{m.fmt ? m.fmt(v) : pct(v)}</p>
                    {!m.fmt && <Badge tone={good ? "ok" : warn ? "warn" : "danger"} className="mt-1">{good ? "Pass" : warn ? "Watch" : "Below target"}</Badge>}
                  </Card>
                );
              })}
            </div>
            {latest.notes && <p className="mt-3 text-xs text-subtle">{latest.notes}</p>}
          </section>
          <section>
            <SectionHeader title="Cases" />
            <div className="overflow-x-auto rounded-card border border-border">
              <table className="w-full min-w-[900px] text-sm">
                <thead className="bg-surface text-left text-xs text-subtle">
                  <tr>{["Question", "Agent", "Routing", "Precision", "Recall", "Faithful", "Citations", "Confidence", "Latency"].map((h) => <th key={h} scope="col" className="px-3 py-2.5 font-medium">{h}</th>)}</tr>
                </thead>
                <tbody>
                  {latest.cases.map((c, i) => (
                    <tr key={i} className="border-t border-border">
                      <td className="max-w-xs px-3 py-2.5">{String(c.question)}</td>
                      <td className="px-3 py-2.5 text-muted">{String(c.agent)}</td>
                      <td className="px-3 py-2.5">{c.routing_correct ? "✓" : "✗"}</td>
                      {["context_precision", "context_recall", "faithfulness", "citation_accuracy"].map((k) => (
                        <td key={k} className={cn("px-3 py-2.5 tabular", Number(c[k]) < 0.5 && "text-danger")}>{pct(Number(c[k]))}</td>
                      ))}
                      <td className="px-3 py-2.5 text-muted">{String(c.confidence)}</td>
                      <td className="px-3 py-2.5 tabular text-muted">{String(c.latency_ms)} ms</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
      <section>
        <SectionHeader title="Observability" subtitle="LLM usage, latency, errors and tool reliability" icon={Activity} />
        <div className="grid gap-4 lg:grid-cols-2">
          <Card className="overflow-x-auto p-0">
            <table className="w-full text-sm">
              <caption className="px-4 pt-4 text-left font-medium">Model calls</caption>
              <thead className="text-left text-xs text-subtle"><tr>{["Model", "Task", "Calls", "Tokens in/out", "Cost", "Errors"].map((h) => <th key={h} className="px-4 py-2 font-medium">{h}</th>)}</tr></thead>
              <tbody>
                {metrics.data?.llm.map((r) => (
                  <tr key={r.model + r.task} className="border-t border-border"><td className="px-4 py-2">{r.model}</td><td className="px-4 py-2 text-muted">{r.task}</td><td className="px-4 py-2 tabular">{r.calls}</td><td className="px-4 py-2 tabular">{r.input_tokens}/{r.output_tokens}</td><td className="px-4 py-2 tabular">${r.cost_usd.toFixed(4)}</td><td className="px-4 py-2 tabular">{r.errors}</td></tr>
                ))}
                {!metrics.data?.llm.length && <tr><td colSpan={6} className="px-4 py-6 text-center text-muted">No model calls yet.</td></tr>}
              </tbody>
            </table>
          </Card>
          <Card className="overflow-x-auto p-0">
            <table className="w-full text-sm">
              <caption className="px-4 pt-4 text-left font-medium">Tool reliability</caption>
              <thead className="text-left text-xs text-subtle"><tr>{["Tool", "Calls", "Avg latency", "Failures"].map((h) => <th key={h} className="px-4 py-2 font-medium">{h}</th>)}</tr></thead>
              <tbody>
                {metrics.data?.tools.map((t) => (
                  <tr key={t.tool} className="border-t border-border"><td className="px-4 py-2 font-mono text-xs">{t.tool}</td><td className="px-4 py-2 tabular">{t.calls}</td><td className="px-4 py-2 tabular">{t.avg_latency_ms} ms</td><td className={cn("px-4 py-2 tabular", t.failures > 0 && "text-danger")}>{t.failures}</td></tr>
                ))}
              </tbody>
            </table>
          </Card>
        </div>
      </section>
    </div>
  );
}
