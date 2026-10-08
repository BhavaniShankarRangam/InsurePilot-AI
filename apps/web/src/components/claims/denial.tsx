"use client";

import { BookOpen, FileWarning, MessageSquareQuote, PackageCheck, PenLine, ShieldMinus, ShieldPlus, UserCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge, CertaintyTag, SafetyNote } from "@/components/ui/primitives";
import { useAssistant } from "@/lib/store";
import type { DenialAnalysis } from "@/lib/types";
import { shortDate } from "@/lib/utils";

/** Claim Guardian policy analysis for a denied claim. */
export function DenialView({ a, claimNumber }: { a: DenialAnalysis; claimNumber?: string }) {
  const ask = useAssistant((s) => s.ask);
  const ref = claimNumber ?? a.claim_number;
  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-danger/30 bg-danger-soft/50 p-4">
        <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-danger">
          <FileWarning className="size-3.5" aria-hidden /> Denial reason
        </p>
        <p className="mt-1 text-sm">{a.denial_reason}</p>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        {a.findings.map((f) => (
          <div key={f.title} className="rounded-2xl border border-border bg-surface p-4">
            <div className="mb-1.5 flex items-center justify-between gap-2">
              <Badge tone={f.kind === "endorsement" ? "ok" : "danger"}>
                {f.kind === "endorsement" ? <ShieldPlus aria-hidden /> : <ShieldMinus aria-hidden />}
                {f.kind === "endorsement" ? "Adds coverage" : "Exclusion"}
              </Badge>
              <CertaintyTag certainty={f.certainty} />
            </div>
            <p className="font-medium">{f.title}</p>
            <p className="mt-1 text-sm text-muted">{f.detail}</p>
            <p className="mt-2 inline-flex items-center gap-1 text-xs text-subtle">
              <BookOpen className="size-3" aria-hidden /> {f.source}
            </p>
          </div>
        ))}
      </div>
      <p className="text-[15px] leading-relaxed">{a.explanation}</p>
      <div>
        <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-subtle">Open questions</p>
        <ul className="space-y-1.5 text-sm text-muted">
          {a.open_questions.map((q) => (
            <li key={q} className="flex gap-2">
              <span className="text-accent">?</span> {q}
            </li>
          ))}
        </ul>
      </div>
      {a.deadline && (
        <p className="text-sm">
          <span className="font-medium">Deadline:</span> {a.deadline.label} by <strong>{shortDate(a.deadline.due)}</strong>
        </p>
      )}
      <div className="flex flex-wrap gap-2">
        <Button size="sm" variant="secondary" onClick={() => ask(`Write questions for the adjuster about claim ${ref}`)}>
          <MessageSquareQuote /> Questions for adjuster
        </Button>
        <Button size="sm" variant="secondary" onClick={() => ask(`Prepare an evidence package for claim ${ref}`)}>
          <PackageCheck /> Evidence package
        </Button>
        <Button size="sm" variant="secondary" onClick={() => ask(`Draft an appeal letter for claim ${ref}`)}>
          <PenLine /> Appeal draft
        </Button>
        <Button size="sm" variant="ghost" onClick={() => ask("I want to talk to a licensed professional about my denied claim")}>
          <UserCheck /> Talk to a professional
        </Button>
      </div>
      <SafetyNote>Only your insurer (or an appraiser or court) can decide whether coverage applies.</SafetyNote>
    </div>
  );
}
