"use client";

import { AnimatePresence, motion, useInView } from "framer-motion";
import { BookOpen, Check, LoaderCircle } from "lucide-react";
import * as React from "react";
import { Orb } from "@/components/ai/orb";
import { Badge } from "@/components/ui/primitives";

const SCRIPTS = [
  {
    q: "Why was my basement water claim denied?",
    steps: ["Reading the denial letter", "Checking exclusions", "Checking endorsements"],
    a: "Your policy excludes drain backups — but you also have a Water Backup endorsement with a $10,000 limit. Whether it applies depends on the cause of loss.",
    cite: "Home Policy · Endorsement HO-WB · Page 31",
    conf: "Moderate confidence",
  },
  {
    q: "My car repair is $1,200. Should I file a claim?",
    steps: ["Retrieving your deductible", "Checking claim history"],
    a: "Your collision deductible is $1,000, so your insurer would pay about $200. Filing may affect your premium at renewal. It's your call — here are both options.",
    cite: "Auto Policy · Section 4 — Collision · Page 18",
    conf: "High confidence",
  },
  {
    q: "Can I get an MRI at Lakeside Imaging?",
    steps: ["Checking network", "Identifying procedure code", "Checking prior authorization"],
    a: "Lakeside is in-network. Estimated cost to you: about $390. Prior authorization is required — one document may be missing.",
    cite: "Health Plan · Section 7 — Prior Authorization · Page 22",
    conf: "Moderate confidence",
  },
];

/** Scripted, looping demo of the AI Command Center for the marketing page. */
export function DemoChat() {
  const ref = React.useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { amount: 0.4 });
  const [i, setI] = React.useState(0);
  const [phase, setPhase] = React.useState(0); // 0 question, 1..n steps, n+1 answer
  const s = SCRIPTS[i];

  React.useEffect(() => {
    if (!inView) return;
    const total = s.steps.length + 2;
    const t = setTimeout(() => {
      if (phase < total) setPhase(phase + 1);
      else {
        setPhase(0);
        setI((i + 1) % SCRIPTS.length);
      }
    }, phase === total ? 4200 : phase === 0 ? 900 : 650);
    return () => clearTimeout(t);
  }, [phase, inView, i, s.steps.length]);

  const answering = phase > s.steps.length;
  return (
    <div ref={ref} className="glass-strong mx-auto w-full max-w-xl rounded-3xl p-5" aria-label="Example conversation with InsurePilot">
      <div className="mb-4 flex items-center gap-3 border-b border-border pb-3">
        <Orb state={answering ? "completed" : phase > 0 ? "analyzing" : "idle"} size={32} />
        <p className="font-medium">InsurePilot</p>
        <Badge tone="accent" className="ml-auto">Live demo</Badge>
      </div>
      <AnimatePresence mode="wait">
        <motion.div key={i} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="min-h-[250px] space-y-3">
          <div className="flex justify-end">
            <p className="max-w-[85%] rounded-2xl rounded-br-md bg-accent-gradient px-4 py-2.5 text-sm text-white">{s.q}</p>
          </div>
          <ul className="space-y-1 text-xs">
            {s.steps.slice(0, Math.max(0, phase)).map((st, k) => (
              <motion.li key={st} initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }} className="flex items-center gap-2 text-muted">
                {k === phase - 1 && !answering ? <LoaderCircle className="size-3 animate-spin text-accent" aria-hidden /> : <Check className="size-3 text-ok" aria-hidden />} {st}
              </motion.li>
            ))}
          </ul>
          {answering && (
            <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="space-y-2.5">
              <p className="text-[15px] leading-relaxed">{s.a}</p>
              <p className="inline-flex items-center gap-1.5 rounded-xl border border-border bg-surface px-2.5 py-1.5 text-xs text-muted">
                <BookOpen className="size-3.5 text-accent" aria-hidden /> {s.cite}
              </p>
              <div><Badge tone="info">{s.conf}</Badge></div>
            </motion.div>
          )}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
