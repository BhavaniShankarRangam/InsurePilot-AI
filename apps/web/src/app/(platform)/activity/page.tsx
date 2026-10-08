"use client";

import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Check, Hand, ShieldCheck, Sparkles, X } from "lucide-react";
import { ApprovalCard } from "@/components/ai/approval-card";
import { Badge, EmptyState, PageHeader, SectionHeader, Skeleton } from "@/components/ui/primitives";
import { api } from "@/lib/api";
import { keys, usePendingActions } from "@/lib/queries";
import { usePageContext } from "@/lib/use-page-context";
import { cn, timeAgo } from "@/lib/utils";

interface ActivityItem { id: string; kind: "tool" | "action"; agent: string; tool: string; summary: string; ok: boolean; status?: string; latency_ms?: number; at: string }

/** Transparent AI execution history, as an elegant workflow timeline. */
export default function ActivityPage() {
  const { data, isLoading } = useQuery({ queryKey: keys.activity, queryFn: () => api.get<ActivityItem[]>("/ai/activity") });
  const { data: pending } = usePendingActions();
  usePageContext({ section: "activity", title: "AI Activity" });

  return (
    <div className="space-y-10">
      <PageHeader eyebrow="AI Activity Log" title="Everything the AI did — and why" subtitle="Every tool the AI used and every action it proposed. High-impact actions only run after your approval." />
      {pending && pending.length > 0 && (
        <section>
          <SectionHeader title="Waiting for your approval" icon={Hand} />
          <div className="grid gap-4 lg:grid-cols-2">{pending.map((a) => <ApprovalCard key={a.id} action={a} />)}</div>
        </section>
      )}
      <section>
        <SectionHeader title="Timeline" icon={Sparkles} />
        {isLoading ? (
          <Skeleton className="h-96 rounded-card" />
        ) : !data?.length ? (
          <EmptyState icon={ShieldCheck} title="No AI activity yet" body="Ask the assistant something — every step it takes will appear here." />
        ) : (
          <ol className="relative ml-3 border-l border-border-strong pl-8">
            {data.map((e, i) => {
              const Icon = e.kind === "action" ? (e.status === "pending" ? Hand : e.status === "cancelled" ? X : ShieldCheck) : e.ok ? Check : X;
              return (
                <motion.li key={e.id} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: Math.min(i, 12) * 0.03 }} className="relative pb-6">
                  <span className={cn("absolute -left-[45px] grid size-7 place-items-center rounded-full ring-4 ring-bg",
                    e.kind === "action" ? (e.status === "pending" ? "bg-warn text-black" : e.status === "cancelled" ? "bg-surface-hover text-muted" : "bg-ok text-white") : e.ok ? "bg-accent-soft text-accent" : "bg-danger-soft text-danger")}>
                    <Icon className="size-3.5" aria-hidden />
                  </span>
                  <div className="glass rounded-2xl px-4 py-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-medium">{e.summary}</p>
                      {e.kind === "action" && <Badge tone={e.status === "pending" ? "warn" : e.status === "executed" ? "ok" : "neutral"}>{e.status}</Badge>}
                    </div>
                    <p className="mt-0.5 text-xs text-subtle">
                      {e.agent} · <code className="font-mono">{e.tool}</code>{e.latency_ms ? ` · ${e.latency_ms} ms` : ""} · {timeAgo(e.at)}
                    </p>
                  </div>
                </motion.li>
              );
            })}
          </ol>
        )}
      </section>
    </div>
  );
}
