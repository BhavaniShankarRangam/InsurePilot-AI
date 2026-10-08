"use client";

import { useQuery } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import { CircleCheck, CircleDashed, CircleMinus, Search } from "lucide-react";
import * as React from "react";
import { FilterChips, Skeleton } from "@/components/ui/primitives";
import { api } from "@/lib/api";
import { CATEGORY_META } from "@/lib/categories";
import type { Category } from "@/lib/types";
import { cn } from "@/lib/utils";

interface Item { category: Category; policy_id: string; name: string; status: "covered" | "partial" | "not_covered" | "review"; detail: string; limit: string | null }

// Each status has an icon, a label AND a fill pattern so meaning never depends on color alone.
const STATUS = {
  covered: { label: "Covered", icon: CircleCheck, cls: "border-ok/40 bg-ok-soft text-ok", pattern: "" },
  partial: { label: "Partially covered", icon: CircleDashed, cls: "border-info/40 bg-info-soft text-info", pattern: "bg-[repeating-linear-gradient(135deg,transparent_0_6px,var(--info-soft)_6px_8px)]" },
  review: { label: "Needs review", icon: Search, cls: "border-warn/50 bg-warn-soft text-warn", pattern: "border-dashed" },
  not_covered: { label: "May not be covered", icon: CircleMinus, cls: "border-danger/40 bg-danger-soft text-danger", pattern: "bg-[radial-gradient(var(--danger-soft)_1px,transparent_1px)] [background-size:6px_6px]" },
} as const;

export function CoverageMap() {
  const { data, isLoading } = useQuery({ queryKey: ["coverage-map"], queryFn: () => api.get<Item[]>("/policies/coverage-map") });
  const [status, setStatus] = React.useState<"all" | Item["status"]>("all");
  const [selected, setSelected] = React.useState<Item | null>(null);
  if (isLoading || !data) return <Skeleton className="h-96 rounded-card" />;

  const cats = Array.from(new Set(data.map((d) => d.category)));
  const count = (s: Item["status"]) => data.filter((d) => d.status === s).length;

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
      <div>
        <FilterChips
          label="Coverage status"
          value={status}
          onChange={setStatus}
          options={[
            { value: "all", label: "Everything", count: data.length },
            { value: "covered", label: "Covered", count: count("covered") },
            { value: "partial", label: "Partial", count: count("partial") },
            { value: "review", label: "Needs review", count: count("review") },
            { value: "not_covered", label: "May not be covered", count: count("not_covered") },
          ]}
        />
        <div className="mt-6 space-y-6">
          {cats.map((cat) => {
            const meta = CATEGORY_META[cat];
            const items = data.filter((d) => d.category === cat && (status === "all" || d.status === status));
            if (!items.length) return null;
            return (
              <section key={cat} aria-label={`${meta.label} coverage`}>
                <p className="mb-2 flex items-center gap-2 text-sm font-semibold">
                  <meta.icon className="size-4" style={{ color: meta.hue }} aria-hidden /> {meta.label}
                </p>
                <ul className="flex flex-wrap gap-2">
                  {items.map((it) => {
                    const s = STATUS[it.status];
                    return (
                      <li key={it.name}>
                        <motion.button
                          layout
                          whileHover={{ y: -2 }}
                          onClick={() => setSelected(it)}
                          aria-pressed={selected?.name === it.name}
                          className={cn("flex items-center gap-1.5 rounded-xl border px-3 py-2 text-sm transition-shadow hover:shadow-soft", s.cls, s.pattern, selected?.name === it.name && "ring-2 ring-accent")}
                        >
                          <s.icon className="size-4" aria-hidden />
                          <span className="text-fg">{it.name}</span>
                          <span className="sr-only">— {s.label}</span>
                        </motion.button>
                      </li>
                    );
                  })}
                </ul>
              </section>
            );
          })}
        </div>
        <ul className="mt-6 flex flex-wrap gap-4 text-xs text-muted" aria-label="Legend">
          {Object.entries(STATUS).map(([k, s]) => (
            <li key={k} className="flex items-center gap-1.5"><s.icon className="size-3.5" aria-hidden /> {s.label}</li>
          ))}
        </ul>
      </div>
      <div className="lg:sticky lg:top-24 lg:self-start">
        <AnimatePresence mode="wait">
          {selected ? (
            <motion.div key={selected.name} initial={{ opacity: 0, x: 12 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0 }} className="glass rounded-card p-5">
              <p className="text-xs font-semibold uppercase tracking-wider text-subtle">{CATEGORY_META[selected.category].label}</p>
              <p className="mt-1 font-display text-lg font-semibold">{selected.name}</p>
              <p className={cn("mt-2 inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs", STATUS[selected.status].cls)}>
                {React.createElement(STATUS[selected.status].icon, { className: "size-3.5", "aria-hidden": true })} {STATUS[selected.status].label}
              </p>
              <p className="mt-3 text-sm text-muted">{selected.detail}</p>
              {selected.limit && <p className="mt-2 text-sm"><span className="text-subtle">Limit:</span> {selected.limit}</p>}
            </motion.div>
          ) : (
            <motion.div key="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="rounded-card border border-dashed border-border-strong p-6 text-center text-sm text-muted">
              Select any item to see what it means in plain English.
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
