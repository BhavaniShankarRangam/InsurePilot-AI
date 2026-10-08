"use client";

import { useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowRight, Check, FileUp, Link2, LoaderCircle, Network, Pencil, Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";
import * as React from "react";
import { Logo } from "@/components/brand/logo";
import { Orb } from "@/components/ai/orb";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/overlay";
import { Card, Progress } from "@/components/ui/primitives";
import { api } from "@/lib/api";
import { keys, useMe } from "@/lib/queries";
import type { DocumentItem } from "@/lib/types";
import { money, titleCase } from "@/lib/utils";

const STEPS = ["Welcome", "Connect", "Extract", "Confirm", "Digital Twin", "Ready"];
const CARRIERS = ["Northstar Mutual", "Harborline Insurance", "Bluepeak Health", "Evergreen Life"];

export default function OnboardingPage() {
  const [step, setStep] = React.useState(0);
  const [doc, setDoc] = React.useState<DocumentItem | null>(null);
  const [carrier, setCarrier] = React.useState<string | null>(null);
  const [fields, setFields] = React.useState<{ label: string; value: string }[]>([]);
  const { data: me } = useMe();
  const router = useRouter();
  const qc = useQueryClient();

  const next = () => setStep((s) => Math.min(STEPS.length - 1, s + 1));

  async function upload(file: File) {
    const fd = new FormData();
    fd.append("file", file);
    const created = await api.post<DocumentItem>("/documents", fd);
    setDoc(created);
    next();
    for (let i = 0; i < 30; i++) {
      await new Promise((r) => setTimeout(r, 700));
      const d = await api.get<DocumentItem>(`/documents/${created.id}`);
      if (d.status !== "processing") {
        setDoc(d);
        setFields([
          { label: "Document type", value: titleCase(d.doc_type) },
          ...(d.extracted.monetary_amounts?.slice(0, 3).map((a, i) => ({ label: i === 0 ? "Largest amount" : `Amount ${i + 1}`, value: money(a) })) ?? []),
          ...(d.extracted.dates?.slice(0, 2).map((x, i) => ({ label: i === 0 ? "Key date" : "Other date", value: x })) ?? []),
        ]);
        return;
      }
    }
  }

  async function finish() {
    await api.post("/users/me/onboarding");
    qc.invalidateQueries({ queryKey: keys.me });
    router.push("/dashboard");
  }

  return (
    <div className="relative grid min-h-dvh place-items-center px-4 py-10">
      <div className="ambient" aria-hidden />
      <main id="main" className="relative z-10 w-full max-w-xl">
        <div className="mb-8 flex items-center justify-between">
          <Logo />
          <span className="text-sm text-muted">Step {step + 1} of {STEPS.length}</span>
        </div>
        <Progress value={(step + 1) / STEPS.length} label="Onboarding progress" className="mb-3" />
        <ol className="mb-8 flex justify-between text-[11px] text-subtle">
          {STEPS.map((s, i) => <li key={s} className={i <= step ? "text-accent" : ""}>{s}</li>)}
        </ol>
        <Card className="p-8">
          <AnimatePresence mode="wait">
            <motion.div key={step} initial={{ opacity: 0, x: 24, filter: "blur(4px)" }} animate={{ opacity: 1, x: 0, filter: "blur(0px)" }} exit={{ opacity: 0, x: -24, filter: "blur(4px)" }} transition={{ duration: 0.35 }}>
              {step === 0 && (
                <div className="text-center">
                  <Orb size={96} />
                  <h1 className="mt-6 font-display text-3xl font-semibold tracking-tight">Hi {me?.preferred_name ?? "there"} 👋</h1>
                  <p className="mt-2 text-muted">I’m InsurePilot. Let’s bring your insurance together — it takes about five minutes, and you’ll never need to fill in a big form.</p>
                  <Button size="lg" className="mt-8" onClick={next}>Let’s go <ArrowRight /></Button>
                </div>
              )}
              {step === 1 && (
                <div>
                  <h2 className="font-display text-2xl font-semibold">Connect your insurance</h2>
                  <p className="mt-1 text-muted">Upload a policy, or connect a carrier.</p>
                  <label className="mt-6 flex cursor-pointer flex-col items-center gap-2 rounded-2xl border-2 border-dashed border-border-strong p-8 text-center transition hover:border-accent">
                    <FileUp className="size-8 text-accent" aria-hidden />
                    <span className="font-medium">Upload a policy (PDF, photo or text)</span>
                    <span className="text-sm text-muted">The AI will read it for you</span>
                    <input type="file" accept=".pdf,.txt,image/*" className="sr-only" onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])} />
                  </label>
                  <p className="my-5 text-center text-xs text-subtle">or connect a carrier (sandbox)</p>
                  <div className="grid grid-cols-2 gap-2">
                    {CARRIERS.map((c) => (
                      <button key={c} onClick={() => { setCarrier(c); setFields([{ label: "Carrier", value: c }, { label: "Connection", value: "Sandbox (mock API)" }, { label: "Policies found", value: "Available once the carrier integration is enabled" }]); setStep(2); }}
                        className="glass flex items-center gap-2 rounded-xl px-3 py-2.5 text-left text-sm hover:text-accent">
                        <Link2 className="size-4" aria-hidden /> {c}
                      </button>
                    ))}
                  </div>
                  <button onClick={() => setStep(3)} className="mt-5 w-full text-center text-sm text-muted hover:text-fg">Skip for now</button>
                </div>
              )}
              {step === 2 && (
                <div className="text-center">
                  <Orb state={doc?.status === "processing" || (!doc && !carrier) ? "analyzing" : "completed"} size={80} />
                  <h2 className="mt-6 font-display text-2xl font-semibold">{carrier ? `Connecting to ${carrier}…` : doc?.status === "processing" || !doc ? "Reading your policy…" : "Done reading"}</h2>
                  <ul className="mx-auto mt-6 max-w-xs space-y-2 text-left text-sm">
                    {["Running OCR", "Classifying the document", "Extracting coverages & amounts", "Finding deadlines", "Linking to your Digital Twin"].map((s, i) => {
                      const finished = carrier || (doc && doc.status !== "processing");
                      return (
                        <motion.li key={s} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.35 }} className="flex items-center gap-2">
                          {finished ? <Check className="size-4 text-ok" aria-hidden /> : <LoaderCircle className="size-4 animate-spin text-accent" aria-hidden />} {s}
                        </motion.li>
                      );
                    })}
                  </ul>
                  <Button className="mt-8" onClick={next} disabled={!carrier && (!doc || doc.status === "processing")}>Review details <ArrowRight /></Button>
                </div>
              )}
              {step === 3 && (
                <div>
                  <h2 className="font-display text-2xl font-semibold">Does this look right?</h2>
                  <p className="mt-1 text-muted">Confirm or fix anything before we save it.</p>
                  {fields.length === 0 ? (
                    <p className="mt-6 rounded-xl bg-surface p-4 text-sm text-muted">Nothing to confirm yet — you can add policies any time from Documents.</p>
                  ) : (
                    <ul className="mt-6 space-y-2">
                      {fields.map((f, i) => (
                        <li key={f.label} className="flex items-center gap-3 rounded-xl bg-surface px-3 py-2">
                          <span className="w-32 shrink-0 text-sm text-subtle">{f.label}</span>
                          <label htmlFor={`f-${i}`} className="sr-only">{f.label}</label>
                          <Input id={`f-${i}`} value={f.value} onChange={(e) => setFields((all) => all.map((x, j) => (j === i ? { ...x, value: e.target.value } : x)))} className="h-9" />
                          <Pencil className="size-4 shrink-0 text-subtle" aria-hidden />
                        </li>
                      ))}
                    </ul>
                  )}
                  <Button className="mt-6 w-full" onClick={next}>Looks good <Check /></Button>
                </div>
              )}
              {step === 4 && <TwinStep onDone={next} />}
              {step === 5 && (
                <div className="text-center">
                  <Sparkles className="mx-auto size-10 text-accent" aria-hidden />
                  <h2 className="mt-4 font-display text-3xl font-semibold">Your dashboard is ready</h2>
                  <p className="mt-2 text-muted">I’ll keep watching for renewals, gaps, deadlines and billing problems — and I’ll always ask before doing anything important.</p>
                  <Button size="lg" className="mt-8" onClick={finish}>Open my dashboard <ArrowRight /></Button>
                </div>
              )}
            </motion.div>
          </AnimatePresence>
        </Card>
      </main>
    </div>
  );
}

function TwinStep({ onDone }: { onDone: () => void }) {
  React.useEffect(() => {
    const t = setTimeout(onDone, 2600);
    return () => clearTimeout(t);
  }, [onDone]);
  const nodes = ["Policies", "Assets", "Claims", "Documents", "Providers", "Benefits"];
  return (
    <div className="text-center">
      <h2 className="font-display text-2xl font-semibold">Building your Insurance Digital Twin</h2>
      <div className="relative mx-auto mt-8 size-64">
        <motion.div className="absolute left-1/2 top-1/2 grid size-16 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-full bg-accent-gradient text-white shadow-glow" animate={{ scale: [1, 1.08, 1] }} transition={{ repeat: Infinity, duration: 1.6 }}>
          <Network className="size-7" aria-hidden />
        </motion.div>
        {nodes.map((n, i) => {
          const a = (i / nodes.length) * Math.PI * 2;
          return (
            <motion.span key={n} className="glass absolute -translate-x-1/2 -translate-y-1/2 rounded-full px-2.5 py-1 text-xs" style={{ left: `${50 + Math.cos(a) * 42}%`, top: `${50 + Math.sin(a) * 42}%` }}
              initial={{ opacity: 0, scale: 0.4 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.2 + i * 0.3 }}>
              {n}
            </motion.span>
          );
        })}
      </div>
      <p className="mt-4 text-sm text-muted" aria-live="polite">Linking everything you protect to the policies that protect it…</p>
    </div>
  );
}
