"use client";

import { useQuery } from "@tanstack/react-query";
import { GitCompare, Sparkles } from "lucide-react";
import { useSearchParams } from "next/navigation";
import * as React from "react";
import { ComparisonTable, type Comparison } from "@/components/policy/views";
import { Button } from "@/components/ui/button";
import { Card, EmptyState, FilterChips, PageHeader, Skeleton } from "@/components/ui/primitives";
import { api } from "@/lib/api";
import { useAssistant } from "@/lib/store";
import { usePageContext } from "@/lib/use-page-context";

export default function ComparePage() {
  return (
    <React.Suspense fallback={<Skeleton className="h-96 rounded-card" />}>
      <CompareInner />
    </React.Suspense>
  );
}

function CompareInner() {
  const initial = useSearchParams().get("category") ?? "auto";
  const [category, setCategory] = React.useState(initial);
  const ask = useAssistant((s) => s.ask);
  const { data, isLoading } = useQuery({ queryKey: ["compare", category], queryFn: () => api.get<Comparison & { message?: string }>(`/quotes/compare?category=${category}`) });
  usePageContext({ section: "compare", category, title: "Policy comparison" });

  return (
    <div>
      <PageHeader
        eyebrow="Compare & shop"
        title="Compare coverage, not just price"
        subtitle="InsurePilot builds a coverage profile from your current policy and normalizes every quote to the same fields. Differences are highlighted — no carrier is called “best”."
        actions={<Button onClick={() => ask(`Find equivalent ${category} coverage`)}><Sparkles /> Find equivalent coverage</Button>}
      />
      <div className="mb-6">
        <FilterChips label="Insurance type" value={category} onChange={setCategory} options={[{ value: "auto", label: "Auto" }, { value: "home", label: "Home" }, { value: "health", label: "Health" }]} />
      </div>
      {isLoading ? (
        <Skeleton className="h-96 rounded-card" />
      ) : !data?.available || data.columns.length < 2 ? (
        <EmptyState icon={GitCompare} title="No comparable quotes yet" body={data?.message ?? "Connect a quote marketplace or upload quotes, and InsurePilot will normalize them here."} />
      ) : (
        <Card className="p-6"><ComparisonTable c={data} /></Card>
      )}
    </div>
  );
}
