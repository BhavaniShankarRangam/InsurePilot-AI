"use client";

import { ShieldCheck, Upload } from "lucide-react";
import Link from "next/link";
import * as React from "react";
import { PolicyCard } from "@/components/dashboard/policy-card";
import { CoverageMap } from "@/components/policy/coverage-map";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/overlay";
import { EmptyState, FilterChips, PageHeader, Reveal, Skeleton } from "@/components/ui/primitives";
import { CATEGORY_META } from "@/lib/categories";
import { usePolicies } from "@/lib/queries";
import { usePageContext } from "@/lib/use-page-context";

export default function PoliciesPage() {
  const { data, isLoading } = usePolicies();
  const [cat, setCat] = React.useState<string>("all");
  usePageContext({ section: "policies", title: "Policies" });
  const cats = Array.from(new Set((data ?? []).map((p) => p.category)));
  const shown = (data ?? []).filter((p) => cat === "all" || p.category === cat);

  return (
    <div>
      <PageHeader
        eyebrow="Policies"
        title="Your coverage, in plain English"
        subtitle="Every policy translated — what's covered, what isn't, and what to watch."
        actions={
          <Button asChild variant="secondary">
            <Link href="/documents?upload=1"><Upload /> Upload a policy</Link>
          </Button>
        }
      />
      <Tabs defaultValue="policies">
        <TabsList>
          <TabsTrigger value="policies">Policies</TabsTrigger>
          <TabsTrigger value="map">Coverage map</TabsTrigger>
        </TabsList>
        <TabsContent value="policies">
          <div className="mb-5">
            <FilterChips
              label="Insurance type"
              value={cat}
              onChange={setCat}
              options={[{ value: "all", label: "All" }, ...cats.map((c) => ({ value: c, label: CATEGORY_META[c].label }))]}
            />
          </div>
          {isLoading ? (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-72 rounded-card" />)}</div>
          ) : shown.length === 0 ? (
            <EmptyState icon={ShieldCheck} title="No policies yet" body="Upload your first policy and InsurePilot will organize it for you." />
          ) : (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {shown.map((p, i) => (
                <Reveal key={p.id} delay={i * 0.04} className="h-full"><PolicyCard p={p} /></Reveal>
              ))}
            </div>
          )}
        </TabsContent>
        <TabsContent value="map">
          <CoverageMap />
        </TabsContent>
      </Tabs>
    </div>
  );
}
