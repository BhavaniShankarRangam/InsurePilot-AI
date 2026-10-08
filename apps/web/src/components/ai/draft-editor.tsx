"use client";

import { Copy, Send } from "lucide-react";
import * as React from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/overlay";
import { api } from "@/lib/api";
import type { AIActionItem } from "@/lib/types";
import { titleCase } from "@/lib/utils";
import { ApprovalCard } from "./approval-card";

export interface Draft { kind: string; to: string | null; subject: string; body: string }

/** Editable communication draft. "Send" creates an approval request — it never sends directly. */
export function DraftEditor({ draft }: { draft: Draft }) {
  const [to, setTo] = React.useState(draft.to ?? "");
  const [subject, setSubject] = React.useState(draft.subject);
  const [body, setBody] = React.useState(draft.body);
  const [pending, setPending] = React.useState<AIActionItem | null>(null);
  const [loading, setLoading] = React.useState(false);
  const id = React.useId();

  if (pending) return <ApprovalCard action={pending} />;

  return (
    <div className="space-y-3 rounded-2xl border border-border bg-surface p-4">
      <p className="text-xs font-semibold uppercase tracking-wider text-subtle">Draft · {titleCase(draft.kind)}</p>
      <div className="grid gap-2">
        <label className="sr-only" htmlFor={`${id}-to`}>To</label>
        <Input id={`${id}-to`} value={to} onChange={(e) => setTo(e.target.value)} placeholder="To" className="h-9" />
        <label className="sr-only" htmlFor={`${id}-subject`}>Subject</label>
        <Input id={`${id}-subject`} value={subject} onChange={(e) => setSubject(e.target.value)} placeholder="Subject" className="h-9 font-medium" />
        <label className="sr-only" htmlFor={`${id}-body`}>Message</label>
        <Textarea id={`${id}-body`} value={body} onChange={(e) => setBody(e.target.value)} rows={9} className="text-[13px] leading-relaxed" />
      </div>
      <div className="flex flex-wrap gap-2">
        <Button
          size="sm"
          loading={loading}
          disabled={!to || !subject || !body}
          onClick={async () => {
            setLoading(true);
            try {
              setPending(await api.post<AIActionItem>("/ai/actions/send-draft", { to, subject, body }));
            } catch (e) {
              toast.error((e as Error).message);
            } finally {
              setLoading(false);
            }
          }}
        >
          <Send /> Review & send
        </Button>
        <Button
          size="sm"
          variant="secondary"
          onClick={() => {
            navigator.clipboard?.writeText(`${subject}\n\n${body}`);
            toast.success("Copied to clipboard");
          }}
        >
          <Copy /> Copy
        </Button>
      </div>
    </div>
  );
}
