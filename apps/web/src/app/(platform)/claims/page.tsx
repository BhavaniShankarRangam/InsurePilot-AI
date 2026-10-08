"use client";

import { useMutation } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { AlertTriangle, Calculator, Camera, PartyPopper, Plus, Workflow } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import * as React from "react";
import { DecisionView, type DecisionData } from "@/components/claims/decision";
import { PhotoUpload } from "@/components/claims/photo-upload";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, Field, Input } from "@/components/ui/overlay";
import { Badge, Card, EmptyState, FilterChips, PageHeader, Progress, SectionHeader, Skeleton } from "@/components/ui/primitives";
import { api } from "@/lib/api";
import { CATEGORY_META } from "@/lib/categories";
import { useClaims } from "@/lib/queries";
import { useAssistant } from "@/lib/store";
import { usePageContext } from "@/lib/use-page-context";
import { money, shortDate, titleCase } from "@/lib/utils";

const STATUS_TONE: Record<string, "ok" | "warn" | "danger" | "info" | "neutral"> = {
  draft: "neutral", submitted: "info", in_review: "info", approved: "ok", paid: "ok", denied: "danger", closed: "neutral",
};

export default function ClaimsPage() {
  return (
    <React.Suspense fallback={<Skeleton className="h-96 rounded-card" />}>
      <ClaimsInner />
    </React.Suspense>
  );
}

function ClaimsInner() {
  const { data, isLoading } = useClaims();
  const camera = useSearchParams().get("camera") === "1";
  const [status, setStatus] = React.useState("all");
  const [cameraOpen, setCameraOpen] = React.useState(camera);
  const ask = useAssistant((s) => s.ask);
  usePageContext({ section: "claims", title: "Claims" });
  const shown = (data ?? []).filter((c) => status === "all" || (status === "open" ? ["draft", "submitted", "in_review"].includes(c.status) : c.status === status));
  const openClaim = data?.find((c) => ["in_review", "submitted", "draft"].includes(c.status));

  return (
    <div className="space-y-10">
      <PageHeader
        eyebrow="Claim Guardian"
        title="Your claims, guarded"
        subtitle="Track every step, catch missing documents, and understand decisions — with AI in your corner."
        actions={
          <>
            <Button onClick={() => ask("Someone hit my car")}><Plus /> Start a claim</Button>
            <Button variant="secondary" onClick={() => setCameraOpen(true)} disabled={!openClaim}><Camera /> Add claim photos</Button>
          </>
        }
      />

      <section>
        <div className="mb-5">
          <FilterChips label="Claim status" value={status} onChange={setStatus} options={[
            { value: "all", label: "All", count: data?.length },
            { value: "open", label: "Open" },
            { value: "denied", label: "Denied" },
            { value: "paid", label: "Paid" },
          ]} />
        </div>
        {isLoading ? (
          <div className="grid gap-4 md:grid-cols-2">{[0, 1].map((i) => <Skeleton key={i} className="h-48 rounded-card" />)}</div>
        ) : shown.length === 0 ? (
          <EmptyState icon={PartyPopper} title="No claims — that's a good thing." body="If something happens, tell the AI what happened and it will guide you step by step." action={<Button onClick={() => ask("Someone hit my car")}>Start a claim</Button>} />
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {shown.map((c, i) => {
              const meta = CATEGORY_META[c.category];
              return (
                <motion.div key={c.id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}>
                  <Link href={`/claims/${c.id}`}>
                    <Card interactive className="p-5">
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex items-center gap-3">
                          <div className="grid size-10 place-items-center rounded-xl ring-1 ring-border" style={{ background: `color-mix(in oklab, ${meta.hue} 14%, transparent)` }}>
                            <meta.icon className="size-[18px]" style={{ color: meta.hue }} aria-hidden />
                          </div>
                          <div>
                            <p className="font-medium">{c.title}</p>
                            <p className="text-xs text-muted">Claim {c.claim_number} · {shortDate(c.incident_date)}</p>
                          </div>
                        </div>
                        <Badge tone={STATUS_TONE[c.status] ?? "neutral"}>{titleCase(c.status)}</Badge>
                      </div>
                      <div className="mt-4">
                        <div className="mb-1.5 flex justify-between text-xs text-muted"><span>{c.stage}</span><span>{Math.round(c.progress * 100)}%</span></div>
                        <Progress value={c.progress} label={`Claim progress ${Math.round(c.progress * 100)}%`} />
                      </div>
                      <div className="mt-3 flex flex-wrap items-center gap-2 text-sm">
                        {c.amount_claimed ? <span className="text-muted">Claimed {money(c.amount_claimed)}</span> : null}
                        {c.amount_paid ? <span className="text-ok">· Paid {money(c.amount_paid)}</span> : null}
                        {c.missing_documents.length > 0 && <Badge tone="warn"><AlertTriangle aria-hidden /> Needs {c.missing_documents.join(", ")}</Badge>}
                      </div>
                    </Card>
                  </Link>
                </motion.div>
              );
            })}
          </div>
        )}
      </section>

      <DecisionAssistant />

      <Dialog open={cameraOpen} onOpenChange={setCameraOpen}>
        <DialogContent title="Claim Photo AI" description={openClaim ? `Adding to claim ${openClaim.claim_number}` : undefined}>
          {openClaim ? <PhotoUpload claimId={openClaim.id} autoOpen={camera} /> : <p className="text-sm text-muted">Start a claim first.</p>}
        </DialogContent>
      </Dialog>
    </div>
  );
}

function DecisionAssistant() {
  const [estimate, setEstimate] = React.useState("1200");
  const m = useMutation({ mutationFn: (v: number) => api.post<DecisionData>("/claims/decision", { category: "auto", repair_estimate: v }) });
  const value = Number(estimate.replace(/[^0-9.]/g, ""));
  return (
    <section>
      <SectionHeader title="Should I file a claim?" subtitle="See the math before you decide. InsurePilot never decides for you." icon={Calculator} />
      <Card className="grid gap-6 p-6 lg:grid-cols-[300px_1fr]">
        <form onSubmit={(e) => { e.preventDefault(); if (value > 0) m.mutate(value); }} className="space-y-4">
          <Field label="Repair estimate (auto)" htmlFor="estimate" hint="From your body shop or adjuster">
            <Input id="estimate" inputMode="decimal" value={estimate} onChange={(e) => setEstimate(e.target.value)} />
          </Field>
          <Button type="submit" loading={m.isPending} disabled={!(value > 0)} className="w-full"><Workflow /> Compare options</Button>
          {m.error && <p role="alert" className="text-sm text-danger">{(m.error as Error).message}</p>}
        </form>
        <div>{m.data ? <DecisionView d={m.data} /> : <p className="grid h-full place-items-center rounded-2xl border border-dashed border-border-strong p-8 text-center text-sm text-muted">Enter an estimate to compare filing a claim with paying out of pocket.</p>}</div>
      </Card>
    </section>
  );
}
