"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import { CalendarClock, Camera, CheckCircle2, CircleDollarSign, CreditCard, FileText, IdCard, ListChecks, LoaderCircle, Receipt, ScanLine, Sparkles, Trash2, TriangleAlert, Upload } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import * as React from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, SheetContent } from "@/components/ui/overlay";
import { Badge, Card, EmptyState, FilterChips, PageHeader, Skeleton } from "@/components/ui/primitives";
import { api } from "@/lib/api";
import { keys, useDocuments } from "@/lib/queries";
import { useAssistant } from "@/lib/store";
import type { DocumentItem } from "@/lib/types";
import { usePageContext } from "@/lib/use-page-context";
import { bytes, money, timeAgo, titleCase } from "@/lib/utils";

const SCAN_MODES = [
  { id: "accident_photo", label: "Accident photo", icon: Camera, sensitive: [] as string[] },
  { id: "insurance_card", label: "Insurance card", icon: CreditCard, sensitive: ["Member ID", "Group number", "Your name"] },
  { id: "policy", label: "Policy document", icon: FileText, sensitive: [] },
  { id: "eob", label: "EOB", icon: Receipt, sensitive: ["Medical services", "Provider names"] },
  { id: "medical_bill", label: "Medical bill", icon: Receipt, sensitive: ["Medical services", "Account number"] },
  { id: "drivers_license", label: "Driver's license", icon: IdCard, sensitive: ["License number", "Date of birth", "Address"] },
];

const MAX_UPLOAD_MB = 20;

/** Catches problems before uploading so the user gets an instant, actionable explanation. */
function checkUpload(file: File): string | null {
  if (file.size === 0)
    return "this file is empty (0 bytes). It may be an online-only OneDrive / Google Drive file or an incomplete download. Save a local copy and try again.";
  if (file.size > MAX_UPLOAD_MB * 1024 * 1024) return `this file is over ${MAX_UPLOAD_MB} MB. Try compressing it or uploading fewer pages.`;
  return null;
}

export default function DocumentsPage() {
  return (
    <React.Suspense fallback={<Skeleton className="h-96 rounded-card" />}>
      <DocumentsInner />
    </React.Suspense>
  );
}

function DocumentsInner() {
  const params = useSearchParams();
  const router = useRouter();
  const { data, isLoading } = useDocuments();
  const [type, setType] = React.useState("all");
  const [openDoc, setOpenDoc] = React.useState<string | null>(params.get("doc"));
  const [scanOpen, setScanOpen] = React.useState(params.get("camera") === "1");
  const claimId = params.get("claim");
  usePageContext({ section: "documents", title: "Documents", document_id: openDoc ?? undefined });

  const types = Array.from(new Set((data ?? []).map((d) => d.doc_type)));
  const shown = (data ?? []).filter((d) => type === "all" || d.doc_type === type);

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Document Intelligence"
        title="Drop anything. We'll make sense of it."
        subtitle="Policies, EOBs, bills, letters, estimates — InsurePilot reads them, pulls out deadlines and amounts, and links them to the right policy or claim."
        actions={<Button variant="secondary" onClick={() => setScanOpen(true)}><ScanLine /> Scan with camera</Button>}
      />
      <Dropzone claimId={claimId} autoFocus={params.get("upload") === "1"} />

      <section>
        <div className="mb-5">
          <FilterChips label="Document type" value={type} onChange={setType} options={[{ value: "all", label: "All", count: data?.length }, ...types.map((t) => ({ value: t, label: titleCase(t) }))]} />
        </div>
        {isLoading ? (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-44 rounded-card" />)}</div>
        ) : shown.length === 0 ? (
          <EmptyState icon={FileText} title="Upload your first policy" body="InsurePilot will organize it for you and explain it in plain English." />
        ) : (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            <AnimatePresence>
              {shown.map((d, i) => (
                <motion.div key={d.id} layout initial={{ opacity: 0, scale: 0.97 }} animate={{ opacity: 1, scale: 1, transition: { delay: i * 0.03 } }} exit={{ opacity: 0, scale: 0.95 }}>
                  <DocCard d={d} onOpen={() => { setOpenDoc(d.id); router.replace(`/documents?doc=${d.id}`, { scroll: false }); }} />
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        )}
      </section>

      <Dialog open={!!openDoc} onOpenChange={(o) => { if (!o) { setOpenDoc(null); router.replace("/documents", { scroll: false }); } }}>
        <SheetContent title="Document">{openDoc && <DocDetail id={openDoc} />}</SheetContent>
      </Dialog>
      <ScanDialog open={scanOpen} onOpenChange={setScanOpen} />
    </div>
  );
}

function DocCard({ d, onOpen }: { d: DocumentItem; onOpen: () => void }) {
  return (
    <button onClick={onOpen} className="w-full text-left">
      <Card interactive className="h-full p-5">
        <div className="flex items-start gap-3">
          <div className="grid size-10 shrink-0 place-items-center rounded-xl bg-accent-soft">
            {d.status === "processing" ? <LoaderCircle className="size-5 animate-spin text-accent" aria-hidden /> : <FileText className="size-5 text-accent" aria-hidden />}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate font-medium">{d.title}</p>
            <div className="mt-1 flex flex-wrap gap-1.5">
              <Badge tone="accent">{titleCase(d.doc_type)}</Badge>
              {d.status === "processing" && <Badge tone="info">Reading…</Badge>}
              {d.status === "failed" && <Badge tone="danger"><TriangleAlert aria-hidden /> Couldn’t read</Badge>}
              {d.page_count > 0 && <Badge>{d.page_count} pages</Badge>}
            </div>
          </div>
        </div>
        <p className="mt-3 line-clamp-3 text-sm text-muted">{d.status === "processing" ? "InsurePilot is reading this document — OCR, classification, extraction and indexing…" : d.summary}</p>
        <div className="mt-3 flex flex-wrap gap-3 text-xs text-subtle">
          {d.extracted?.monetary_amounts?.length ? <span className="inline-flex items-center gap-1"><CircleDollarSign className="size-3.5" aria-hidden /> {d.extracted.monetary_amounts.length} amounts</span> : null}
          {d.extracted?.deadlines?.length ? <span className="inline-flex items-center gap-1 text-warn"><CalendarClock className="size-3.5" aria-hidden /> {d.extracted.deadlines.length} deadlines</span> : null}
          <span>{timeAgo(d.created_at)}</span>
        </div>
      </Card>
    </button>
  );
}

function Dropzone({ claimId, autoFocus }: { claimId: string | null; autoFocus?: boolean }) {
  const qc = useQueryClient();
  const [drag, setDrag] = React.useState(false);
  const [uploads, setUploads] = React.useState<{ name: string; state: "uploading" | "done" | "error"; size: number }[]>([]);
  const inputRef = React.useRef<HTMLInputElement>(null);
  React.useEffect(() => { if (autoFocus) inputRef.current?.focus(); }, [autoFocus]);

  async function handle(files: FileList | null) {
    if (!files) return;
    for (const file of Array.from(files)) {
      const problem = checkUpload(file);
      if (problem) {
        toast.error(`${file.name}: ${problem}`, { duration: 10000 });
        continue;
      }
      setUploads((u) => [{ name: file.name, state: "uploading", size: file.size }, ...u]);
      const fd = new FormData();
      fd.append("file", file);
      if (claimId) fd.append("claim_id", claimId);
      try {
        await api.post("/documents", fd);
        setUploads((u) => u.map((x) => (x.name === file.name ? { ...x, state: "done" } : x)));
        qc.invalidateQueries({ queryKey: keys.documents });
      } catch (e) {
        setUploads((u) => u.map((x) => (x.name === file.name ? { ...x, state: "error" } : x)));
        toast.error(`${file.name}: ${(e as Error).message}`);
      }
    }
  }

  return (
    <div>
      <motion.label
        htmlFor="doc-upload"
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => { e.preventDefault(); setDrag(false); handle(e.dataTransfer.files); }}
        animate={{ scale: drag ? 1.01 : 1 }}
        className={`glass relative flex cursor-pointer flex-col items-center justify-center overflow-hidden rounded-card border-2 border-dashed px-6 py-12 text-center transition-colors ${drag ? "border-accent bg-accent-soft" : "border-border-strong"}`}
      >
        <div aria-hidden className="grid-bg absolute inset-0 opacity-60" />
        <motion.div animate={drag ? { y: -6, scale: 1.08 } : { y: 0, scale: 1 }} className="relative grid size-16 place-items-center rounded-2xl bg-accent-gradient text-white shadow-glow">
          <Upload className="size-7" aria-hidden />
        </motion.div>
        <p className="relative mt-4 font-display text-lg font-semibold">{drag ? "Drop to upload" : "Drag & drop documents"}</p>
        <p className="relative text-sm text-muted">PDF, JPG, PNG or text · up to 20 MB{claimId ? " · will be linked to your claim" : ""}</p>
        <span className="relative mt-4 rounded-xl bg-surface-strong px-4 py-2 text-sm font-medium ring-1 ring-border">Browse files</span>
        <input id="doc-upload" ref={inputRef} type="file" multiple accept=".pdf,.txt,image/*" className="sr-only" onChange={(e) => handle(e.target.files)} />
      </motion.label>
      <AnimatePresence>
        {uploads.slice(0, 4).map((u) => (
          <motion.div key={u.name} initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0 }} className="mt-2 flex items-center gap-3 rounded-xl bg-surface px-4 py-2.5 text-sm">
            {u.state === "uploading" ? <LoaderCircle className="size-4 animate-spin text-accent" aria-hidden /> : u.state === "done" ? <CheckCircle2 className="size-4 text-ok" aria-hidden /> : <TriangleAlert className="size-4 text-danger" aria-hidden />}
            <span className="truncate">{u.name}</span>
            <span className="ml-auto text-xs text-subtle">{u.state === "uploading" ? "Uploading…" : u.state === "done" ? "Uploaded — AI is reading it" : "Failed"} · {bytes(u.size)}</span>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}

function DocDetail({ id }: { id: string }) {
  const { data: d } = useQuery({ queryKey: ["document", id], queryFn: () => api.get<DocumentItem & { sections: { section: string | null; page: number | null; text: string }[] }>(`/documents/${id}`) });
  const ask = useAssistant((s) => s.ask);
  const qc = useQueryClient();
  const router = useRouter();
  if (!d) return <div className="p-6"><Skeleton className="h-64" /></div>;
  const ex = d.extracted ?? {};
  return (
    <div className="flex h-full flex-col overflow-y-auto p-6">
      <p className="text-xs font-semibold uppercase tracking-wider text-accent">{titleCase(d.doc_type)}</p>
      <h2 className="mt-1 font-display text-xl font-semibold">{d.title}</h2>
      <p className="mt-2 text-sm text-muted">{d.summary}</p>
      <div className="mt-5 grid gap-3">
        {ex.monetary_amounts?.length ? (
          <div><p className="mb-1 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-subtle"><CircleDollarSign className="size-3.5" /> Amounts</p><div className="flex flex-wrap gap-1.5">{ex.monetary_amounts.map((a) => <Badge key={a}>{money(a, { cents: a % 1 !== 0 })}</Badge>)}</div></div>
        ) : null}
        {ex.deadlines?.length ? (
          <div><p className="mb-1 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-subtle"><CalendarClock className="size-3.5" /> Deadlines</p><ul className="text-sm text-muted">{ex.deadlines.map((x) => <li key={x}>• {x}</li>)}</ul></div>
        ) : null}
        {ex.action_items?.length ? (
          <div><p className="mb-1 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-subtle"><ListChecks className="size-3.5" /> Action items</p><ul className="text-sm text-muted">{ex.action_items.map((x) => <li key={x}>• {x}</li>)}</ul></div>
        ) : null}
        {ex.policy_terms?.length ? (
          <div><p className="mb-1 text-xs font-semibold uppercase tracking-wider text-subtle">Insurance terms found</p><div className="flex flex-wrap gap-1.5">{ex.policy_terms.map((t) => <Badge key={t} tone="accent">{t}</Badge>)}</div></div>
        ) : null}
      </div>
      <div className="mt-5 flex flex-wrap gap-2">
        <Button size="sm" onClick={() => ask(`Summarize "${d.title}" and tell me what I need to do`)}><Sparkles /> Ask about this document</Button>
        <Button
          size="sm"
          variant="danger"
          onClick={async () => {
            if (!confirm("Delete this document? This can't be undone.")) return;
            await api.del(`/documents/${d.id}`);
            qc.invalidateQueries({ queryKey: keys.documents });
            router.replace("/documents");
            toast.success("Document deleted");
          }}
        >
          <Trash2 /> Delete
        </Button>
      </div>
      <h3 className="mb-2 mt-8 text-xs font-semibold uppercase tracking-wider text-subtle">Parsed sections</h3>
      <ol className="space-y-3">
        {d.sections.map((s, i) => (
          <li key={i} className="rounded-xl border border-border bg-surface p-3">
            <p className="text-xs font-medium text-accent">{s.section ?? "Section"} · Page {s.page}</p>
            <p className="mt-1 text-sm text-muted">{s.text}</p>
          </li>
        ))}
      </ol>
    </div>
  );
}

function ScanDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (o: boolean) => void }) {
  const [mode, setMode] = React.useState<(typeof SCAN_MODES)[number] | null>(null);
  const [consent, setConsent] = React.useState(false);
  const inputRef = React.useRef<HTMLInputElement>(null);
  const qc = useQueryClient();
  const [busy, setBusy] = React.useState(false);

  async function upload(files: FileList | null) {
    if (!files?.length || !mode) return;
    const problem = checkUpload(files[0]);
    if (problem) {
      toast.error(problem, { duration: 10000 });
      return;
    }
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("file", files[0]);
      fd.append("title", `${mode.label} scan`);
      await api.post("/documents", fd);
      qc.invalidateQueries({ queryKey: keys.documents });
      toast.success(`${mode.label} captured — AI is extracting details`);
      onOpenChange(false);
      setMode(null);
      setConsent(false);
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o) => { onOpenChange(o); if (!o) { setMode(null); setConsent(false); } }}>
      <DialogContent title="Camera mode" description="Choose what you're scanning. Your camera opens on mobile.">
        {!mode ? (
          <div className="grid grid-cols-2 gap-2">
            {SCAN_MODES.map((m) => (
              <button key={m.id} onClick={() => setMode(m)} className="glass flex flex-col items-center gap-2 rounded-2xl p-4 text-sm transition hover:-translate-y-0.5 hover:text-accent">
                <m.icon className="size-6" aria-hidden /> {m.label}
              </button>
            ))}
          </div>
        ) : (
          <div className="space-y-4">
            <p className="font-medium">{mode.label}</p>
            {mode.sensitive.length > 0 && (
              <div className="rounded-2xl border border-warn/40 bg-warn-soft/40 p-4 text-sm">
                <p className="font-medium">This scan contains sensitive information</p>
                <p className="mt-1 text-muted">InsurePilot will extract and store: {mode.sensitive.join(", ")}. Fields are encrypted at rest and never shared without your approval.</p>
                <label className="mt-3 flex items-center gap-2">
                  <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} className="size-4 accent-[var(--accent)]" />
                  I confirm InsurePilot may store these details
                </label>
              </div>
            )}
            <Button className="w-full" loading={busy} disabled={mode.sensitive.length > 0 && !consent} onClick={() => inputRef.current?.click()}>
              <Camera /> Open camera
            </Button>
            <Button variant="ghost" className="w-full" onClick={() => setMode(null)}>Back</Button>
            <input ref={inputRef} type="file" accept="image/*,.pdf" capture="environment" className="sr-only" onChange={(e) => upload(e.target.files)} aria-label={`Capture ${mode.label}`} />
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
