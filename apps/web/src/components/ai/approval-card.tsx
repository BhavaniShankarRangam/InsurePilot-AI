"use client";

import { useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Hand, Pencil, Send, ShieldCheck, X } from "lucide-react";
import * as React from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/overlay";
import { Badge, motion } from "@/components/ui/primitives";
import { api } from "@/lib/api";
import { keys, useActionDecision } from "@/lib/queries";
import { useAssistant } from "@/lib/store";
import type { AIActionItem } from "@/lib/types";

/** Human-in-the-loop confirmation: what the AI is about to do, why, and what will be shared. */
export function ApprovalCard({ action: initial }: { action: AIActionItem }) {
  const [action, setAction] = React.useState(initial);
  const [editing, setEditing] = React.useState(false);
  const [draft, setDraft] = React.useState(initial.preview ?? "");
  const decide = useActionDecision();
  const qc = useQueryClient();
  const setOrb = useAssistant((s) => s.setOrb);

  async function run(decision: "approve" | "cancel") {
    try {
      if (decision === "approve" && editing && draft !== action.preview) {
        await api.patch(`/ai/actions/${action.id}`, { payload_args: { body: draft } });
      }
      const res = await decide.mutateAsync({ id: action.id, decision });
      setAction({ ...action, ...res });
      setEditing(false);
      setOrb(decision === "approve" ? "completed" : "idle");
      toast.success(decision === "approve" ? "Done — completed with your approval" : "Cancelled. Nothing was sent.");
      qc.invalidateQueries({ queryKey: keys.notifications });
    } catch (e) {
      toast.error((e as Error).message);
    }
  }

  const done = action.status !== "pending";
  return (
    <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="overflow-hidden rounded-2xl border border-warn/40 bg-warn-soft/40">
      <div className="flex items-center gap-2 border-b border-warn/30 px-4 py-2.5">
        {done ? <CheckCircle2 className="size-4 text-ok" aria-hidden /> : <Hand className="size-4 text-warn" aria-hidden />}
        <p className="text-sm font-semibold">{done ? "Decision recorded" : "Needs your approval"}</p>
        <Badge tone={action.status === "executed" ? "ok" : action.status === "cancelled" ? "neutral" : action.status === "failed" ? "danger" : "warn"} className="ml-auto">
          {action.status === "pending" ? "Waiting" : action.status}
        </Badge>
      </div>
      <div className="space-y-3 px-4 py-3 text-sm">
        <p className="font-medium">{action.title}</p>
        <dl className="grid gap-2">
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wider text-subtle">What AI is about to do</dt>
            <dd className="text-muted">{action.what}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wider text-subtle">Why</dt>
            <dd className="text-muted">{action.why}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wider text-subtle">What information will be shared{action.recipient ? ` with ${action.recipient}` : ""}</dt>
            <dd>
              <ul className="mt-1 flex flex-wrap gap-1.5">
                {action.data_shared.map((d) => (
                  <li key={d}>
                    <Badge>{d}</Badge>
                  </li>
                ))}
              </ul>
            </dd>
          </div>
        </dl>
        {action.preview && (
          <div>
            <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-subtle">Message</p>
            {editing ? (
              <Textarea value={draft} onChange={(e) => setDraft(e.target.value)} rows={8} aria-label="Edit message" />
            ) : (
              <pre className="max-h-48 overflow-auto whitespace-pre-wrap rounded-xl bg-surface p-3 font-sans text-[13px] text-muted">{draft || action.preview}</pre>
            )}
          </div>
        )}
        {!done ? (
          <div className="flex flex-wrap gap-2 pt-1">
            <Button size="sm" onClick={() => run("approve")} loading={decide.isPending}>
              <Send /> Approve
            </Button>
            {action.preview && (
              <Button size="sm" variant="secondary" onClick={() => setEditing((v) => !v)}>
                <Pencil /> {editing ? "Done editing" : "Edit"}
              </Button>
            )}
            <Button size="sm" variant="ghost" onClick={() => run("cancel")} disabled={decide.isPending}>
              <X /> Cancel
            </Button>
          </div>
        ) : (
          <p className="flex items-center gap-1.5 text-xs text-subtle">
            <ShieldCheck className="size-3.5" aria-hidden /> Logged in your AI activity history.
          </p>
        )}
      </div>
    </motion.div>
  );
}
