"use client";

import { Box, Expand, LayoutGrid, Minimize2, Orbit } from "lucide-react";
import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import * as React from "react";
import { Universe2D } from "@/components/three/universe-2d";
import { Button } from "@/components/ui/button";
import { PageHeader, Skeleton } from "@/components/ui/primitives";
import { useWebGL } from "@/lib/hooks";
import { useGraph } from "@/lib/queries";
import { useUI } from "@/lib/store";
import { usePageContext } from "@/lib/use-page-context";
import { cn } from "@/lib/utils";

const UniverseScene = dynamic(() => import("@/components/three/universe-scene"), {
  ssr: false,
  loading: () => <div className="grid size-full place-items-center text-sm text-white/60">Loading your universe…</div>,
});

export default function UniversePage() {
  const { data } = useGraph();
  const router = useRouter();
  const { lowPower, reducedMotion } = useUI();
  const webgl = useWebGL();
  const [chosen, setMode] = React.useState<"3d" | "2d" | null>(null);
  const mode = chosen ?? (lowPower || reducedMotion || !webgl ? "2d" : "3d");
  const [immersive, setImmersive] = React.useState(false);
  usePageContext({ section: "universe", title: "Insurance Universe" });

  React.useEffect(() => {
    if (!immersive) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setImmersive(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [immersive]);

  return (
    <div>
      <PageHeader
        eyebrow="Insurance Universe"
        title="Your insurance, as one connected world"
        subtitle="Your Digital Twin: you at the center, everything you protect around you, linked to policies, carriers, claims and providers. Hover to inspect, click to fly in."
        actions={
          <div className="glass inline-flex rounded-xl p-1" role="radiogroup" aria-label="View mode">
            <button role="radio" aria-checked={mode === "3d"} onClick={() => setMode("3d")} className={cn("flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm", mode === "3d" ? "bg-surface-strong shadow-soft" : "text-muted")}><Box className="size-4" /> 3D</button>
            <button role="radio" aria-checked={mode === "2d"} onClick={() => setMode("2d")} className={cn("flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm", mode === "2d" ? "bg-surface-strong shadow-soft" : "text-muted")}><LayoutGrid className="size-4" /> 2D</button>
          </div>
        }
      />
      {!data ? (
        <Skeleton className="h-[600px] rounded-card" />
      ) : mode === "2d" ? (
        <Universe2D data={data} />
      ) : (
        <div className={cn("relative overflow-hidden bg-[#07080d] ring-1 ring-border", immersive ? "fixed inset-0 z-[60]" : "h-[640px] rounded-card")}>
          <UniverseScene data={data} immersive={immersive} onNavigate={(link) => { setImmersive(false); router.push(link); }} />
          <div className="pointer-events-none absolute inset-x-0 top-0 z-20 flex items-start justify-between p-4">
            <div className="pointer-events-auto rounded-2xl bg-black/50 px-3 py-2 text-xs text-white/80 backdrop-blur">
              <p className="flex items-center gap-1.5 font-medium text-white"><Orbit className="size-3.5" aria-hidden /> Legend</p>
              <p>✓ healthy · ? worth reviewing · ▲ needs attention · ○ inactive</p>
            </div>
            <Button size="sm" variant="secondary" className="pointer-events-auto" onClick={() => setImmersive((v) => !v)}>
              {immersive ? <><Minimize2 /> Exit immersive</> : <><Expand /> Immersive mode</>}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
