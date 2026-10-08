"use client";

import { useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import { Camera, ImagePlus, ScanSearch } from "lucide-react";
import * as React from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/overlay";
import { Badge, SafetyNote } from "@/components/ui/primitives";
import { api } from "@/lib/api";
import { keys } from "@/lib/queries";

interface Observation {
  label: string;
  damage_type: string;
  visible_areas: string[];
  evidence_category: string;
  confidence: string;
  notes: string;
  metadata: { filename: string; size_kb: number };
}

/** Camera-first Claim Photo AI: capture/upload → AI-assisted observations (never a repair estimate). */
export function PhotoUpload({ claimId, autoOpen }: { claimId: string; autoOpen?: boolean }) {
  const inputRef = React.useRef<HTMLInputElement>(null);
  const [description, setDescription] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [results, setResults] = React.useState<{ preview: string; obs: Observation }[]>([]);
  const [drag, setDrag] = React.useState(false);
  const qc = useQueryClient();

  React.useEffect(() => {
    if (autoOpen) inputRef.current?.click();
  }, [autoOpen]);

  async function upload(files: FileList | null) {
    if (!files?.length) return;
    setBusy(true);
    try {
      for (const file of Array.from(files)) {
        const fd = new FormData();
        fd.append("file", file);
        fd.append("description", description);
        const res = await api.post<{ observations: Observation }>(`/claims/${claimId}/photos`, fd);
        setResults((r) => [{ preview: URL.createObjectURL(file), obs: res.observations }, ...r]);
      }
      qc.invalidateQueries({ queryKey: keys.claim(claimId) });
      toast.success("Photo added to your claim");
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <div
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => { e.preventDefault(); setDrag(false); upload(e.dataTransfer.files); }}
        className={`rounded-2xl border-2 border-dashed p-6 text-center transition-colors ${drag ? "border-accent bg-accent-soft" : "border-border-strong"}`}
      >
        <ImagePlus className="mx-auto size-8 text-accent" aria-hidden />
        <p className="mt-2 font-medium">Add photos of the damage</p>
        <p className="text-sm text-muted">Drag photos here, or use your camera.</p>
        <div className="mx-auto mt-4 max-w-md space-y-2">
          <label htmlFor={`desc-${claimId}`} className="sr-only">Describe what the photo shows</label>
          <Input id={`desc-${claimId}`} value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Optional: what does it show? e.g. rear bumper dent" />
          <Button onClick={() => inputRef.current?.click()} loading={busy} className="w-full">
            <Camera /> Take or choose photos
          </Button>
        </div>
        <input ref={inputRef} type="file" accept="image/*" capture="environment" multiple className="sr-only" onChange={(e) => upload(e.target.files)} aria-label="Upload claim photos" />
      </div>
      <AnimatePresence>
        {results.map((r, i) => (
          <motion.div key={r.preview} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="flex gap-4 rounded-2xl border border-border bg-surface p-3">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={r.preview} alt={`Uploaded photo ${i + 1}`} className="size-24 shrink-0 rounded-xl object-cover" />
            <div className="min-w-0 space-y-1.5 text-sm">
              <p className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-subtle"><ScanSearch className="size-3.5" aria-hidden /> {r.obs.label}</p>
              <div className="flex flex-wrap gap-1.5">
                <Badge tone="accent">Type: {r.obs.damage_type}</Badge>
                {r.obs.visible_areas.map((a) => <Badge key={a}>{a}</Badge>)}
                <Badge tone={r.obs.confidence === "moderate" ? "info" : "warn"}>{r.obs.confidence.replace("_", " ")}</Badge>
              </div>
              <SafetyNote>{r.obs.notes}</SafetyNote>
            </div>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
