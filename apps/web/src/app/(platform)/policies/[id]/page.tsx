"use client";

import { useQuery } from "@tanstack/react-query";
import * as React from "react";
import { ArrowLeft, BookOpen, CircleCheck, CircleDashed, CircleMinus, FileText, Phone, Search, ShieldPlus, Sparkles, UserRound } from "lucide-react";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { ExplainThis } from "@/components/ai/explain-this";
import { PolicyExplainerView, PremiumChangeView, RenewalSteps, type PremiumChange } from "@/components/policy/views";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/overlay";
import { Badge, Card, EmptyState, PageHeader, Skeleton } from "@/components/ui/primitives";
import { api } from "@/lib/api";
import { CATEGORY_META } from "@/lib/categories";
import { usePolicy } from "@/lib/queries";
import { useAssistant } from "@/lib/store";
import { usePageContext } from "@/lib/use-page-context";
import { cn, money, shortDate } from "@/lib/utils";

const COV_STATUS = {
  covered: { icon: CircleCheck, label: "Covered", cls: "text-ok" },
  partial: { icon: CircleDashed, label: "Partially covered", cls: "text-info" },
  review: { icon: Search, label: "Needs review", cls: "text-warn" },
  not_covered: { icon: CircleMinus, label: "Not covered", cls: "text-danger" },
} as const;

export default function PolicyDetailPage() {
  return (
    <React.Suspense fallback={<Skeleton className="h-[600px] rounded-card" />}>
      <PolicyDetail />
    </React.Suspense>
  );
}

function PolicyDetail() {
  const { id } = useParams<{ id: string }>();
  const tab = useSearchParams().get("tab") ?? "explained";
  const { data: p, isLoading } = usePolicy(id);
  const ask = useAssistant((s) => s.ask);
  const premium = useQuery({ queryKey: ["premium-change", id], queryFn: () => api.get<PremiumChange>(`/policies/${id}/premium-change`), enabled: !!id });
  const renewal = useQuery({
    queryKey: ["renewals"],
    queryFn: () => api.get<{ policy_id: string; steps: never[]; renewal_date: string; days_until_renewal: number }[]>("/renewals"),
  });
  usePageContext({ section: "policies", policy_id: id, category: p?.category, title: p ? `${CATEGORY_META[p.category].label} policy` : undefined });

  if (isLoading || !p) return <Skeleton className="h-[600px] rounded-card" />;
  const meta = CATEGORY_META[p.category];
  const myRenewal = renewal.data?.find((r) => r.policy_id === id);

  return (
    <div>
      <Link href="/policies" className="mb-4 inline-flex items-center gap-1 text-sm text-muted hover:text-fg"><ArrowLeft className="size-4" /> All policies</Link>
      <PageHeader
        eyebrow={`${meta.label} insurance`}
        title={<span className="flex items-center gap-3"><meta.icon className="size-8" style={{ color: meta.hue }} aria-hidden />{p.carrier.name} · {p.product_name}</span>}
        subtitle={p.summary}
        actions={
          <>
            <Button onClick={() => ask(`Explain my ${meta.label.toLowerCase()} insurance`)}><Sparkles /> Explain my policy</Button>
            {p.carrier.phone && <Button variant="secondary" asChild><a href={`tel:${p.carrier.phone}`}><Phone /> Call carrier</a></Button>}
          </>
        }
      />
      <div className="mb-8 grid grid-cols-2 gap-3 md:grid-cols-4">
        {[
          ["Premium", `${money(p.premium_annual)}/yr`],
          ["Deductible", money(p.deductible)],
          [p.status === "lapsed" ? "Ended" : "Renews", shortDate(p.expiration_date)],
          ["Policy number", p.policy_number],
        ].map(([l, v]) => (
          <Card key={l} className="p-4">
            <p className="text-xs text-subtle">{l}</p>
            <p className="mt-1 font-semibold tabular">{v}</p>
          </Card>
        ))}
      </div>

      <Tabs defaultValue={tab}>
        <TabsList>
          <TabsTrigger value="explained">Explained simply</TabsTrigger>
          <TabsTrigger value="coverages">Coverages</TabsTrigger>
          <TabsTrigger value="renewal">Renewal & premium</TabsTrigger>
          <TabsTrigger value="documents">Documents</TabsTrigger>
        </TabsList>

        <TabsContent value="explained">
          <Card className="p-6"><PolicyExplainerView p={p.explainer} /></Card>
        </TabsContent>

        <TabsContent value="coverages">
          <div className="grid gap-3 md:grid-cols-2">
            {p.coverages.map((c) => {
              const s = COV_STATUS[c.status];
              return (
                <Card key={c.id} className="p-5">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-medium">{c.name}</p>
                      <p className={cn("mt-0.5 inline-flex items-center gap-1 text-xs", s.cls)}><s.icon className="size-3.5" aria-hidden /> {s.label}</p>
                    </div>
                    <div className="text-right">
                      <p className="font-semibold tabular">{c.limit ?? money(c.limit_amount)}</p>
                      {c.deductible ? <p className="text-xs text-subtle">{money(c.deductible)} deductible</p> : null}
                    </div>
                  </div>
                  <p className="mt-2 text-sm text-muted">{c.plain_language}</p>
                  <div className="mt-3 flex flex-wrap items-center gap-2">
                    <ExplainThis kind="coverage" refId={c.id} label={c.name} />
                    {c.source.section && <span className="inline-flex items-center gap-1 text-xs text-subtle"><BookOpen className="size-3" aria-hidden /> {c.source.section} · Page {c.source.page}</span>}
                  </div>
                </Card>
              );
            })}
            {p.endorsements.map((e) => (
              <Card key={e.id} className="border-accent/30 p-5">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-medium">{e.name}</p>
                    <Badge tone="accent" className="mt-1"><ShieldPlus aria-hidden /> Endorsement {e.code}</Badge>
                  </div>
                  <p className="font-semibold tabular">{money(e.limit_amount)}</p>
                </div>
                <p className="mt-2 text-sm text-muted">{e.plain_language}</p>
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <ExplainThis kind="endorsement" refId={e.id} label={e.name} />
                  <span className="text-xs text-subtle">{e.source.section} · Page {e.source.page}</span>
                </div>
              </Card>
            ))}
            {p.exclusions.map((e) => (
              <Card key={e.id} className="p-5">
                <p className="font-medium">{e.name}</p>
                <p className="mt-0.5 inline-flex items-center gap-1 text-xs text-danger"><CircleMinus className="size-3.5" aria-hidden /> Exclusion</p>
                <p className="mt-2 text-sm text-muted">{e.plain_language}</p>
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <ExplainThis kind="exclusion" refId={e.id} label={e.name} />
                  <span className="text-xs text-subtle">{e.source.section} · Page {e.source.page}</span>
                </div>
              </Card>
            ))}
          </div>
          {p.beneficiaries.length > 0 && (
            <Card className="mt-4 p-5">
              <p className="mb-2 font-medium">Beneficiaries</p>
              <ul className="space-y-1 text-sm">
                {p.beneficiaries.map((b) => (
                  <li key={b.name} className="flex items-center gap-2"><UserRound className="size-4 text-muted" aria-hidden /> {b.name} · {b.relationship} · {b.designation} · {b.share}%</li>
                ))}
              </ul>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="renewal">
          <div className="grid gap-4 lg:grid-cols-2">
            <Card className="p-6">
              <p className="mb-4 font-display text-lg font-semibold">Premium change explained</p>
              {premium.data ? <PremiumChangeView pc={premium.data} /> : <Skeleton className="h-48" />}
            </Card>
            <Card className="p-6">
              <p className="mb-4 font-display text-lg font-semibold">Renewal autopilot</p>
              {myRenewal ? <RenewalSteps r={myRenewal} /> : <p className="text-sm text-muted">This policy doesn’t renew in the next 120 days. InsurePilot will start the review automatically when it’s closer.</p>}
              <div className="mt-5 flex flex-wrap gap-2">
                <Button size="sm" variant="secondary" asChild><Link href={`/compare?category=${p.category}`}>Compare alternatives</Link></Button>
                <Button size="sm" variant="ghost" onClick={() => ask(`Draft an email asking ${p.carrier.name} about renewal discounts`)}>Ask carrier about discounts</Button>
              </div>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="documents">
          {p.documents.length === 0 ? (
            <EmptyState icon={FileText} title="No documents yet" body="Upload this policy's PDF and InsurePilot will translate it." />
          ) : (
            <div className="grid gap-3 md:grid-cols-2">
              {p.documents.map((d) => (
                <Link key={d.id} href={`/documents?doc=${d.id}`}>
                  <Card interactive className="flex gap-3 p-4">
                    <FileText className="size-5 shrink-0 text-accent" aria-hidden />
                    <div className="min-w-0">
                      <p className="font-medium">{d.title}</p>
                      <p className="line-clamp-2 text-sm text-muted">{d.summary}</p>
                    </div>
                  </Card>
                </Link>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
