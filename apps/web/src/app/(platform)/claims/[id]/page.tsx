"use client";

import { AlertTriangle, ArrowLeft, CalendarClock, Camera, FileCheck2, FileText, Mail, Sparkles, UserRound } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { DenialView } from "@/components/claims/denial";
import { PhotoUpload } from "@/components/claims/photo-upload";
import { ClaimTimeline } from "@/components/claims/timeline";
import { Button } from "@/components/ui/button";
import { Badge, Card, PageHeader, SectionHeader, Skeleton } from "@/components/ui/primitives";
import { useClaim } from "@/lib/queries";
import { useAssistant } from "@/lib/store";
import { usePageContext } from "@/lib/use-page-context";
import { daysUntil, money, relativeDays, shortDate, titleCase } from "@/lib/utils";

export default function ClaimDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data: c, isLoading } = useClaim(id);
  const ask = useAssistant((s) => s.ask);
  usePageContext({ section: "claims", claim_id: id, category: c?.category, title: c ? `Claim ${c.claim_number}` : undefined });

  if (isLoading || !c) return <Skeleton className="h-[600px] rounded-card" />;

  return (
    <div className="space-y-8">
      <div>
        <Link href="/claims" className="mb-4 inline-flex items-center gap-1 text-sm text-muted hover:text-fg"><ArrowLeft className="size-4" /> All claims</Link>
        <PageHeader
          eyebrow={`Claim ${c.claim_number}`}
          title={c.title}
          subtitle={c.description}
          actions={
            <>
              <Button onClick={() => ask(c.status === "denied" ? `Why was claim ${c.claim_number} denied?` : `What's the status of claim ${c.claim_number}?`)}><Sparkles /> Ask about this claim</Button>
              {c.adjuster && <Button variant="secondary" onClick={() => ask(`Draft an email to my adjuster about claim ${c.claim_number}`)}><Mail /> Email adjuster</Button>}
            </>
          }
        />
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="p-4"><p className="text-xs text-subtle">Status</p><p className="mt-1 font-semibold">{titleCase(c.status)}</p></Card>
        <Card className="p-4"><p className="text-xs text-subtle">Incident date</p><p className="mt-1 font-semibold">{shortDate(c.incident_date)}</p></Card>
        <Card className="p-4"><p className="text-xs text-subtle">Amount</p><p className="mt-1 font-semibold tabular">{money(c.amount_claimed)}{c.amount_paid ? <span className="text-sm text-ok"> · paid {money(c.amount_paid)}</span> : null}</p></Card>
        <Card className="p-4">
          <p className="text-xs text-subtle">Adjuster</p>
          <p className="mt-1 flex items-center gap-1.5 font-semibold"><UserRound className="size-4 text-muted" aria-hidden />{c.adjuster?.name ?? "Not assigned"}</p>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.2fr_1fr]">
        <Card className="p-6">
          <SectionHeader title="Claim timeline" subtitle="Every step, as it happens" />
          <ClaimTimeline events={c.events} />
        </Card>
        <div className="space-y-6">
          {(c.missing_documents.length > 0 || c.deadlines.length > 0) && (
            <Card className="border-warn/40 p-6">
              <SectionHeader title="Needs your attention" icon={AlertTriangle} />
              {c.missing_documents.map((d) => (
                <div key={d} className="mb-3 flex items-center justify-between gap-3 rounded-xl bg-warn-soft/50 px-3 py-2.5">
                  <span className="flex items-center gap-2 text-sm font-medium"><FileText className="size-4 text-warn" aria-hidden /> Missing: {d}</span>
                  <Button size="sm" variant="secondary" asChild><Link href={`/documents?upload=1&claim=${c.id}`}>Upload</Link></Button>
                </div>
              ))}
              {c.deadlines.map((d) => (
                <p key={d.label} className="flex items-start gap-2 text-sm">
                  <CalendarClock className="mt-0.5 size-4 shrink-0 text-warn" aria-hidden />
                  <span><strong>{d.label}</strong> by {shortDate(d.due)} ({relativeDays(daysUntil(d.due))})<span className="block text-xs text-subtle">{d.source}</span></span>
                </p>
              ))}
            </Card>
          )}
          <Card className="p-6">
            <SectionHeader title="Claim packet" icon={FileCheck2} />
            <p className="text-sm"><span className="text-subtle">Included:</span> {c.packet.documents_included.join(", ") || "Nothing yet"}</p>
            <p className="mt-1 text-sm"><span className="text-subtle">Missing:</span> {c.packet.documents_missing.join(", ") || "Nothing"}</p>
            <Badge tone={c.packet.ready_to_submit ? "ok" : "warn"} className="mt-3">{c.packet.ready_to_submit ? "Ready" : "Incomplete"}</Badge>
            <div className="mt-4">
              <Button size="sm" variant="secondary" onClick={() => ask(`Prepare my claim ${c.claim_number}`)}>Prepare packet with AI</Button>
            </div>
          </Card>
        </div>
      </div>

      {c.denial_analysis && (
        <Card className="p-6">
          <SectionHeader title="Policy analysis" subtitle="Claim Guardian compared the denial with your policy" icon={Sparkles} />
          <DenialView a={c.denial_analysis} claimNumber={c.claim_number} />
        </Card>
      )}

      {["auto", "home"].includes(c.category) && c.status !== "denied" && (
        <Card className="p-6">
          <SectionHeader title="Claim Photo AI" subtitle="AI-assisted observations — clearly labeled, never a repair estimate" icon={Camera} />
          <PhotoUpload claimId={c.id} />
        </Card>
      )}
    </div>
  );
}
