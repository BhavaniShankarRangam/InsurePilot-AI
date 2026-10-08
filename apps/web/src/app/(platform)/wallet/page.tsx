"use client";

import { motion } from "framer-motion";
import { Phone, ShieldCheck, Wallet } from "lucide-react";
import Link from "next/link";
import * as React from "react";
import { Badge, EmptyState, FilterChips, PageHeader, Progress, Skeleton } from "@/components/ui/primitives";
import { CATEGORY_META } from "@/lib/categories";
import { usePolicies } from "@/lib/queries";
import type { PolicyCard } from "@/lib/types";
import { usePageContext } from "@/lib/use-page-context";
import { money, shortDate } from "@/lib/utils";

/** One simple screen with every policy, styled like cards in a wallet. Swipeable on mobile. */
export default function WalletPage() {
  const { data, isLoading } = usePolicies();
  const [filter, setFilter] = React.useState<"active" | "all">("active");
  usePageContext({ section: "wallet", title: "Insurance Wallet" });
  const shown = (data ?? []).filter((p) => filter === "all" || p.status !== "lapsed");

  return (
    <div>
      <PageHeader eyebrow="Insurance Wallet" title="Everything you're insured for" subtitle="Tap a card for details. Swipe on mobile." />
      <div className="mb-6">
        <FilterChips label="Show" value={filter} onChange={setFilter} options={[{ value: "active", label: "Active" }, { value: "all", label: "All, including expired" }]} />
      </div>
      {isLoading ? (
        <div className="grid gap-5 md:grid-cols-2">{[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-56 rounded-3xl" />)}</div>
      ) : shown.length === 0 ? (
        <EmptyState icon={Wallet} title="Your wallet is empty" body="Upload your first policy and InsurePilot will organize it for you." />
      ) : (
        <div className="-mx-4 flex snap-x snap-mandatory gap-4 overflow-x-auto px-4 pb-4 md:mx-0 md:grid md:grid-cols-2 md:overflow-visible md:px-0 xl:grid-cols-3">
          {shown.map((p, i) => <WalletPass key={p.id} p={p} index={i} />)}
        </div>
      )}
    </div>
  );
}

function WalletPass({ p, index }: { p: PolicyCard; index: number }) {
  const meta = CATEGORY_META[p.category];
  return (
    <motion.div
      initial={{ opacity: 0, y: 20, rotateX: -12 }}
      animate={{ opacity: 1, y: 0, rotateX: 0 }}
      transition={{ delay: index * 0.07, type: "spring", stiffness: 160, damping: 20 }}
      whileHover={{ y: -4 }}
      className="w-[84vw] shrink-0 snap-center md:w-auto"
      style={{ transformPerspective: 1000 }}
    >
      <Link
        href={`/policies/${p.id}`}
        className="relative block overflow-hidden rounded-3xl p-5 text-white shadow-lift ring-1 ring-white/10"
        style={{ background: `linear-gradient(135deg, color-mix(in oklab, ${meta.hue} 85%, #0b0d12) 0%, color-mix(in oklab, ${meta.hue} 35%, #0b0d12) 100%)` }}
      >
        <div aria-hidden className="absolute -right-12 -top-12 size-48 rounded-full bg-white/10 blur-2xl" />
        <div aria-hidden className="absolute inset-0 bg-[radial-gradient(circle_at_20%_120%,rgba(255,255,255,0.18),transparent_40%)]" />
        <div className="relative flex items-start justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-white/70">{meta.label}</p>
            <p className="mt-1 font-display text-xl font-semibold">{p.carrier.name}</p>
            <p className="text-sm text-white/75">{p.product_name}</p>
          </div>
          <meta.icon className="size-8 text-white/90" aria-hidden />
        </div>
        <div className="relative mt-6 grid grid-cols-2 gap-3 text-sm">
          <div>
            <p className="text-xs text-white/60">Premium</p>
            <p className="font-semibold tabular">{money(p.premium_annual)}/yr</p>
          </div>
          <div>
            <p className="text-xs text-white/60">{p.status === "lapsed" ? "Ended" : "Renews"}</p>
            <p className="font-semibold">{shortDate(p.expiration_date)}</p>
          </div>
          {p.category === "health" ? (
            <>
              <div className="col-span-2">
                <p className="flex justify-between text-xs text-white/60"><span>Deductible remaining</span><span>{money(p.deductible_remaining)}</span></p>
                <Progress value={p.deductible_progress ?? 0} className="mt-1 bg-white/15" tone="ok" label="Deductible met" />
              </div>
              <div className="col-span-2">
                <p className="flex justify-between text-xs text-white/60"><span>Out-of-pocket remaining</span><span>{money(p.oop_remaining)}</span></p>
              </div>
            </>
          ) : p.category === "life" ? (
            <>
              <div>
                <p className="text-xs text-white/60">Coverage</p>
                <p className="font-semibold tabular">{money(p.coverage_amount)}</p>
              </div>
              <div>
                <p className="text-xs text-white/60">Beneficiaries</p>
                <p className="text-xs font-medium">{p.beneficiary_status}</p>
              </div>
            </>
          ) : (
            <>
              <div>
                <p className="text-xs text-white/60">Deductible</p>
                <p className="font-semibold tabular">{money(p.deductible)}</p>
              </div>
              <div>
                <p className="text-xs text-white/60">Claim status</p>
                <p className="font-semibold capitalize">{p.claim_status?.replace("_", " ") ?? "None open"}</p>
              </div>
            </>
          )}
        </div>
        <div className="relative mt-5 flex items-center justify-between border-t border-white/15 pt-3 text-xs text-white/75">
          <span className="font-mono tracking-wider">{p.policy_number}</span>
          {p.alerts.length > 0 ? (
            <Badge className="border-white/20 bg-white/15 text-white">{p.alerts[0].title}</Badge>
          ) : (
            <span className="inline-flex items-center gap-1"><ShieldCheck className="size-3.5" aria-hidden /> All good</span>
          )}
        </div>
        {p.carrier.phone && (
          <p className="relative mt-2 inline-flex items-center gap-1 text-[11px] text-white/60"><Phone className="size-3" aria-hidden /> {p.carrier.phone}</p>
        )}
      </Link>
    </motion.div>
  );
}
