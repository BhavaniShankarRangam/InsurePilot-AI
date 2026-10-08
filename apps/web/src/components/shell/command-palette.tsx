"use client";

import type { LucideIcon } from "lucide-react";
import { Command } from "cmdk";
import {
  Camera,
  FileSearch,
  FileText,
  GitCompare,
  HeartPulse,
  Receipt,
  RefreshCcw,
  Search,
  ShieldCheck,
  Sparkles,
  Stethoscope,
  Upload,
  Workflow,
} from "lucide-react";
import { useRouter } from "next/navigation";
import * as React from "react";
import { Dialog, DialogContent } from "@/components/ui/overlay";
import { useSearch } from "@/lib/queries";
import { useAssistant, useUI } from "@/lib/store";

const TYPE_ICON: Record<string, LucideIcon> = {
  policy: ShieldCheck,
  claim: Workflow,
  document: FileText,
  provider: Stethoscope,
  bill: Receipt,
  benefit: HeartPulse,
  message: Sparkles,
};

/** Ctrl/Cmd+K: commands, AI questions and live global search across the portfolio. */
export function CommandPalette() {
  const { paletteOpen: open, setPalette } = useUI();
  const ask = useAssistant((s) => s.ask);
  const router = useRouter();
  const [q, setQ] = React.useState("");
  const [debounced, setDebounced] = React.useState("");
  const { data: results, isFetching } = useSearch(debounced);
  const inputRef = React.useRef<HTMLInputElement>(null);

  React.useEffect(() => {
    const t = setTimeout(() => setDebounced(q), 220);
    return () => clearTimeout(t);
  }, [q]);

  React.useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPalette(!useUI.getState().paletteOpen);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [setPalette]);

  const go = (fn: () => void) => {
    setPalette(false);
    setQ("");
    fn();
  };

  const commands = [
    { label: "Ask AI", icon: Sparkles, run: () => ask(q || "Handle my insurance") },
    { label: "Start a claim", icon: Workflow, run: () => ask("Someone hit my car") },
    { label: "Upload document", icon: Upload, run: () => router.push("/documents?upload=1") },
    { label: "Scan with camera", icon: Camera, run: () => router.push("/documents?camera=1") },
    { label: "Find policy", icon: ShieldCheck, run: () => router.push("/policies") },
    { label: "Open claims", icon: FileSearch, run: () => router.push("/claims") },
    { label: "Compare policies", icon: GitCompare, run: () => router.push("/compare") },
    { label: "Check renewal", icon: RefreshCcw, run: () => ask("Check my upcoming renewals") },
    { label: "Find provider", icon: Stethoscope, run: () => router.push("/health?tab=providers") },
    { label: "Explain bill", icon: Receipt, run: () => ask("Explain my hospital bill") },
  ];

  return (
    <Dialog open={open} onOpenChange={setPalette}>
      <DialogContent title="Command palette" onOpenAutoFocus={(e) => { e.preventDefault(); inputRef.current?.focus(); }} className="max-w-xl overflow-hidden p-0 [&>div:first-child]:sr-only">
        <Command label="Command palette" shouldFilter={false} className="flex flex-col">
          <div className="flex items-center gap-3 border-b border-border px-4">
            <Search className="size-4 text-subtle" aria-hidden />
            <Command.Input ref={inputRef} value={q} onValueChange={setQ} placeholder="Search or ask anything…" className="h-14 flex-1 bg-transparent text-[15px] placeholder:text-subtle focus:outline-none" />
            {isFetching && <span className="size-4 animate-spin rounded-full border-2 border-accent border-t-transparent" aria-label="Searching" />}
          </div>
          <Command.List className="max-h-[420px] overflow-y-auto p-2">
            <Command.Empty className="px-3 py-6 text-center text-sm text-muted">No matches. Press Enter on “Ask AI” to ask instead.</Command.Empty>
            {q.trim().length > 1 && (
              <Command.Group heading="Ask AI" className="mb-1 text-xs text-subtle [&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:py-1.5">
                <Command.Item value={`ask-${q}`} onSelect={() => go(() => ask(q))} className="flex cursor-pointer items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-fg data-[selected=true]:bg-surface-hover">
                  <Sparkles className="size-4 text-accent" /> Ask InsurePilot: “{q}”
                </Command.Item>
              </Command.Group>
            )}
            {results && results.length > 0 && (
              <Command.Group heading="Results" className="mb-1 text-xs text-subtle [&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:py-1.5">
                {results.slice(0, 8).map((r) => {
                  const Icon = TYPE_ICON[r.type] ?? FileText;
                  return (
                    <Command.Item key={`${r.type}-${r.id}-${r.title}`} value={`${r.type}-${r.id}-${r.title}`} onSelect={() => go(() => router.push(r.link))} className="flex cursor-pointer items-center gap-3 rounded-xl px-3 py-2 text-sm text-fg data-[selected=true]:bg-surface-hover">
                      <Icon className="size-4 shrink-0 text-muted" />
                      <span className="min-w-0">
                        <span className="block truncate">{r.title}</span>
                        {r.subtitle && <span className="block truncate text-xs text-subtle">{r.subtitle}</span>}
                      </span>
                      <span className="ml-auto text-[11px] capitalize text-subtle">{r.type}</span>
                    </Command.Item>
                  );
                })}
              </Command.Group>
            )}
            <Command.Group heading="Commands" className="text-xs text-subtle [&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:py-1.5">
              {commands
                .filter((c) => !q || c.label.toLowerCase().includes(q.toLowerCase()) || c.label === "Ask AI")
                .map((c) => (
                  <Command.Item key={c.label} value={c.label} onSelect={() => go(c.run)} className="flex cursor-pointer items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-fg data-[selected=true]:bg-surface-hover">
                    <c.icon className="size-4 text-muted" /> {c.label}
                  </Command.Item>
                ))}
            </Command.Group>
          </Command.List>
        </Command>
      </DialogContent>
    </Dialog>
  );
}
