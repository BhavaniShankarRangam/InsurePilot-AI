"use client";

import { Camera, CircleCheck, Phone, ShieldAlert, Star, UserRound } from "lucide-react";
import Link from "next/link";
import { ClaimTimeline } from "@/components/claims/timeline";
import { DecisionView } from "@/components/claims/decision";
import { DenialView } from "@/components/claims/denial";
import { PriorAuthView, ProcedureView, ReconciliationView } from "@/components/health/views";
import { ComparisonTable, PolicyExplainerView, PremiumChangeView, RenewalSteps, RiskList } from "@/components/policy/views";
import { Badge, Progress } from "@/components/ui/primitives";
import type { AICard } from "@/lib/types";
import { money, titleCase } from "@/lib/utils";
import { DraftEditor } from "./draft-editor";

function Frame({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-border bg-surface/60 p-4">
      <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-subtle">{title}</p>
      {children}
    </div>
  );
}

/** Renders structured agent output as rich, interactive cards. */
export function AICardView({ card }: { card: AICard }) {
  const d = card.data;
  switch (card.type) {
    case "claim_decision":
      return <Frame title="Claim decision assistant"><DecisionView d={d} /></Frame>;
    case "denial_analysis":
      return <Frame title="Claim Guardian · denial analysis"><DenialView a={d} /></Frame>;
    case "draft":
      return <DraftEditor draft={d} />;
    case "reconciliation":
      return <Frame title="Bill vs. EOB"><ReconciliationView r={d} /></Frame>;
    case "procedure_check":
      return d?.steps ? <Frame title="Procedure check"><ProcedureView r={d} /></Frame> : null;
    case "prior_auth":
      return <Frame title="Prior authorization"><PriorAuthView a={d} /></Frame>;
    case "premium_change":
      return <Frame title="Premium change explained"><PremiumChangeView pc={d} /></Frame>;
    case "renewal":
      return <Frame title="Renewal autopilot"><RenewalSteps r={d} /></Frame>;
    case "comparison":
      return <Frame title="Side-by-side comparison"><ComparisonTable c={d} /></Frame>;
    case "policy_explainer":
      return <Frame title={d.title}><PolicyExplainerView p={d} compact /></Frame>;
    case "risks":
      return <Frame title="What needs your attention"><RiskList items={d.items} /></Frame>;
    case "claim_timeline":
      return (
        <Frame title={`Claim ${d.claim_number} timeline`}>
          <ClaimTimeline events={d.events} explain={false} />
        </Frame>
      );
    case "deductibles":
      return (
        <Frame title="Your deductibles">
          <ul className="grid gap-2 sm:grid-cols-2">
            {d.rows.map((r: { category: string; name: string; amount: number }) => (
              <li key={r.category + r.name} className="flex items-center justify-between rounded-xl bg-surface px-3 py-2 text-sm">
                <span className="text-muted">{titleCase(r.category)} · {r.name}</span>
                <span className="font-semibold tabular">{money(r.amount)}</span>
              </li>
            ))}
          </ul>
        </Frame>
      );
    case "coverage_matches":
      return (
        <Frame title="What your policy says">
          <ul className="space-y-2">
            {d.items.map((m: { name: string; status: string; detail: string; source: string; kind: string }) => (
              <li key={m.name} className="rounded-xl bg-surface px-3 py-2">
                <div className="flex items-center gap-2">
                  <Badge tone={m.status === "covered" ? "ok" : m.status === "not_covered" ? "danger" : m.status === "partial" ? "info" : "warn"}>
                    {m.status === "covered" ? "Covered" : m.status === "not_covered" ? "Not covered" : m.status === "partial" ? "Partially covered" : "Needs review"}
                  </Badge>
                  <span className="text-sm font-medium">{m.name}</span>
                </div>
                <p className="mt-1 text-sm text-muted">{m.detail}</p>
                <p className="mt-0.5 text-xs text-subtle">{m.source}</p>
              </li>
            ))}
          </ul>
        </Frame>
      );
    case "providers":
      return (
        <Frame title="In-network providers">
          <ul className="space-y-1.5">
            {d.items.map((p: { id: string; name: string; specialty: string; city: string; rating: number }) => (
              <li key={p.id} className="flex items-center justify-between rounded-xl bg-surface px-3 py-2 text-sm">
                <span>
                  <span className="font-medium">{p.name}</span> <span className="text-muted">· {p.specialty}, {p.city}</span>
                </span>
                <span className="inline-flex items-center gap-1 text-muted"><Star className="size-3.5" aria-hidden /> {p.rating}</span>
              </li>
            ))}
          </ul>
        </Frame>
      );
    case "guided_flow":
      return (
        <Frame title="Accident report · step by step">
          <Progress value={(d.step + 1) / (d.total + 1)} label="Report progress" />
          <ol className="mt-3 flex flex-wrap gap-1.5">
            {d.steps.map((s: string, i: number) => (
              <li key={s}>
                <Badge tone={i < d.step ? "ok" : i === d.step ? "accent" : "neutral"}>
                  {i < d.step && <CircleCheck aria-hidden />} {s}
                </Badge>
              </li>
            ))}
          </ol>
          {d.step === 2 && (
            <Link href="/claims?camera=1" className="mt-3 inline-flex items-center gap-1.5 text-sm text-accent hover:underline">
              <Camera className="size-4" aria-hidden /> Open camera to add photos
            </Link>
          )}
        </Frame>
      );
    case "emergency":
      return (
        <a href="tel:911" className="flex items-center gap-3 rounded-2xl bg-danger px-4 py-3 font-semibold text-white">
          <Phone className="size-5" aria-hidden /> Call 911
        </a>
      );
    case "fnol_summary":
      return (
        <Frame title="Claim draft prepared">
          <dl className="space-y-1.5 text-sm">
            {Object.entries(d.answers as Record<string, string>).map(([k, v]) => (
              <div key={k} className="flex gap-3">
                <dt className="w-28 shrink-0 text-subtle">{titleCase(k)}</dt>
                <dd>{v}</dd>
              </div>
            ))}
          </dl>
          {d.claim_id && <Link href={`/claims/${d.claim_id}`} className="mt-3 inline-block text-sm text-accent hover:underline">Open claim draft →</Link>}
        </Frame>
      );
    case "claim_packet":
      return (
        <Frame title={`Claim ${d.claim_number} packet`}>
          <p className="text-sm"><span className="text-subtle">Included:</span> {d.documents_included.join(", ") || "None yet"}</p>
          <p className="text-sm"><span className="text-subtle">Missing:</span> {d.documents_missing.join(", ") || "Nothing"}</p>
        </Frame>
      );
    case "fraud_signals":
      return (
        <Frame title="Warning signs">
          <ul className="space-y-1 text-sm">
            {d.signals.map((s: string) => (
              <li key={s} className="flex gap-2"><ShieldAlert className="mt-0.5 size-4 shrink-0 text-warn" aria-hidden /> {s}</li>
            ))}
          </ul>
        </Frame>
      );
    case "escalation":
      return (
        <Frame title="Case summary for a licensed professional">
          <p className="flex items-center gap-2 text-sm"><UserRound className="size-4 text-accent" aria-hidden /> {d.topic}</p>
          {d.open_items.length > 0 && <p className="mt-1 text-sm text-muted">Open items: {d.open_items.join(", ")}</p>}
        </Frame>
      );
    case "health_score":
    case "coverage_profile":
    case "payments":
    case "document":
    case "network_status":
      return null;
    default:
      return null;
  }
}
