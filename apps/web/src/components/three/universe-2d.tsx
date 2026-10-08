"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { CATEGORY_META } from "@/lib/categories";
import type { Category, GraphData } from "@/lib/types";
import { cn } from "@/lib/utils";

const STATUS = {
  ok: { label: "Healthy", cls: "text-ok", ring: "ring-ok/50" },
  review: { label: "Worth reviewing", cls: "text-warn", ring: "ring-warn/60 ring-dashed" },
  attention: { label: "Needs attention", cls: "text-danger", ring: "ring-danger/60" },
  inactive: { label: "Inactive", cls: "text-subtle", ring: "ring-border" },
} as const;

/** Accessible, low-power 2D alternative to the 3D Insurance Universe. */
export function Universe2D({ data }: { data: GraphData }) {
  const cats = data.nodes.filter((n) => n.type === "category");
  const user = data.nodes.find((n) => n.type === "user");
  const size = 520;
  const R = 190;
  return (
    <div className="grid gap-8 lg:grid-cols-[minmax(0,560px)_1fr]">
      <div className="relative mx-auto aspect-square w-full max-w-[560px]">
        <svg viewBox={`0 0 ${size} ${size}`} className="absolute inset-0 size-full" aria-hidden>
          <circle cx={size / 2} cy={size / 2} r={R} fill="none" stroke="var(--border-strong)" strokeDasharray="4 6" />
          {cats.map((c, i) => {
            const a = (i / cats.length) * Math.PI * 2 - Math.PI / 2;
            return (
              <motion.line key={c.id} x1={size / 2} y1={size / 2} x2={size / 2 + Math.cos(a) * R} y2={size / 2 + Math.sin(a) * R}
                stroke="var(--accent)" strokeOpacity={0.4} strokeWidth={1.5} strokeDasharray="6 6"
                initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ delay: i * 0.08, duration: 0.8 }} />
            );
          })}
        </svg>
        <div className="absolute left-1/2 top-1/2 grid size-24 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-full bg-accent-gradient text-center text-sm font-semibold text-white shadow-glow">
          {user?.label}
        </div>
        {cats.map((c, i) => {
          const a = (i / cats.length) * Math.PI * 2 - Math.PI / 2;
          const meta = CATEGORY_META[c.category as Category];
          const s = STATUS[c.status as keyof typeof STATUS] ?? STATUS.ok;
          return (
            <Link
              key={c.id}
              href={c.link ?? "#"}
              className={cn("glass absolute grid size-20 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-2xl text-center ring-2 transition hover:scale-105", s.ring)}
              style={{ left: `${50 + (Math.cos(a) * R * 100) / size}%`, top: `${50 + (Math.sin(a) * R * 100) / size}%` }}
              aria-label={`${meta.label}: ${s.label}`}
            >
              <span>
                <meta.icon className="mx-auto size-6" style={{ color: meta.hue }} aria-hidden />
                <span className="mt-1 block text-[11px] font-medium">{meta.label}</span>
              </span>
            </Link>
          );
        })}
      </div>
      <ul className="space-y-2" aria-label="Your insurance network">
        {cats.map((c) => {
          const meta = CATEGORY_META[c.category as Category];
          const s = STATUS[c.status as keyof typeof STATUS] ?? STATUS.ok;
          const kids = data.links.filter((l) => l.source === c.id).flatMap((l) => data.links.filter((x) => x.source === l.target && x.kind !== "issued_by")).map((l) => data.nodes.find((n) => n.id === l.target)).filter(Boolean);
          return (
            <li key={c.id} className="glass rounded-2xl p-4">
              <Link href={c.link ?? "#"} className="flex items-center gap-3">
                <meta.icon className="size-5" style={{ color: meta.hue }} aria-hidden />
                <span className="font-medium">{meta.label}</span>
                <span className="text-sm text-muted">· {c.carrier}</span>
                <span className={cn("ml-auto text-xs font-medium", s.cls)}>{s.label}</span>
              </Link>
              {c.alerts && c.alerts.length > 0 && <p className="mt-1.5 text-sm text-muted">{c.alerts[0]}</p>}
              {kids.length > 0 && <p className="mt-1 text-xs text-subtle">Connected: {kids.map((k) => k!.label).join(", ")}</p>}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
