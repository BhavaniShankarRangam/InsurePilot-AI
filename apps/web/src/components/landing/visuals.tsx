"use client";

import { useReducedMotion } from "framer-motion";
import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import { useWebGL } from "@/lib/hooks";
import type { GraphData } from "@/lib/types";

const HeroScene = dynamic(() => import("@/components/three/hero-scene"), { ssr: false });
const UniverseScene = dynamic(() => import("@/components/three/universe-scene"), { ssr: false });

function useCan3D() {
  const reduce = useReducedMotion();
  return useWebGL() && !reduce;
}

export function HeroVisual() {
  const can3D = useCan3D();
  if (!can3D)
    return (
      <div className="grid size-full place-items-center" aria-hidden>
        <div className="size-56 rounded-full bg-accent-gradient opacity-60 blur-3xl" />
      </div>
    );
  return <HeroScene />;
}

const DEMO_GRAPH: GraphData = {
  nodes: [
    { id: "u", type: "user", label: "You", status: "ok" },
    { id: "c-auto", type: "category", category: "auto", label: "Car", status: "attention", carrier: "Northstar Mutual", premium: 1916, summary: "Full coverage on your RAV4.", alerts: ["Premium +19% at renewal"], link: "/login" },
    { id: "c-home", type: "category", category: "home", label: "Home", status: "review", carrier: "Harborline", premium: 2184, summary: "HO-3 with water-backup endorsement.", alerts: ["Rebuild coverage may be low"], link: "/login" },
    { id: "c-health", type: "category", category: "health", label: "Health", status: "review", carrier: "Bluepeak Health", premium: 5880, summary: "PPO · $200 deductible left.", alerts: ["MRI authorization pending"], link: "/login" },
    { id: "c-life", type: "category", category: "life", label: "Life", status: "ok", carrier: "Evergreen Life", premium: 612, summary: "$750k term through 2043.", link: "/login" },
    { id: "c-pet", type: "category", category: "pet", label: "Pet", status: "ok", carrier: "Pawsure", premium: 456, summary: "Miso is covered.", link: "/login" },
    { id: "c-travel", type: "category", category: "travel", label: "Travel", status: "inactive", carrier: "Wayfarer", premium: 289, summary: "Expired last month.", link: "/login" },
    { id: "p-auto", type: "policy", category: "auto", label: "Auto policy", status: "ok" },
    { id: "cl-1", type: "claim", category: "auto", label: "Claim 39102", status: "attention", summary: "Rear-end collision", link: "/login" },
  ],
  links: [
    { source: "c-auto", target: "p-auto", kind: "insured_by" },
    { source: "p-auto", target: "cl-1", kind: "has_claim" },
  ],
};

export function UniversePreview() {
  const can3D = useCan3D();
  const router = useRouter();
  if (!can3D) return <div className="grid size-full place-items-center text-sm text-white/60">3D preview unavailable on this device.</div>;
  return <UniverseScene data={DEMO_GRAPH} onNavigate={(l) => router.push(l)} />;
}
