"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Database, Download, Link2, Link2Off, Lock, ShieldCheck, Sparkles, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import * as React from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTrigger, Input, Switch } from "@/components/ui/overlay";
import { Badge, Card, PageHeader, SectionHeader, Skeleton } from "@/components/ui/primitives";
import { api } from "@/lib/api";
import { usePageContext } from "@/lib/use-page-context";
import { shortDate, titleCase } from "@/lib/utils";

interface Privacy {
  data_inventory: { kind: string; count: number; purpose: string; sensitive?: boolean }[];
  consents: { id: string; scope: string; purpose: string; granted: boolean; granted_at: string | null }[];
  integrations: { id: string; provider: string; kind: string; status: string; data_shared: string[]; connected_on: string | null }[];
  ai_activity: { tool_calls: number; actions_requested: number };
  shared_data: { recipient: string; items: string[]; date: string }[];
  retention: string;
}

export default function PrivacyPage() {
  const { data } = useQuery({ queryKey: ["privacy"], queryFn: () => api.get<Privacy>("/privacy") });
  const qc = useQueryClient();
  const router = useRouter();
  const [confirmText, setConfirmText] = React.useState("");
  usePageContext({ section: "privacy", title: "Privacy Center" });
  const refresh = () => qc.invalidateQueries({ queryKey: ["privacy"] });

  if (!data) return <Skeleton className="h-[600px] rounded-card" />;
  return (
    <div className="space-y-10">
      <PageHeader eyebrow="Privacy Center" title="Your data, your rules" subtitle="See exactly what InsurePilot knows, why, and who it's shared with. Change your mind any time." actions={
        <Button variant="secondary" asChild><a href="/api/privacy/export" download><Download /> Export my data</a></Button>
      } />
      <section>
        <SectionHeader title="What data exists — and why" icon={Database} />
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {data.data_inventory.map((d) => (
            <Card key={d.kind} className="p-5">
              <div className="flex items-start justify-between gap-2">
                <p className="font-medium">{d.kind}</p>
                <span className="font-display text-2xl font-semibold tabular">{d.count}</span>
              </div>
              <p className="mt-1 text-sm text-muted">Used to: {d.purpose}</p>
              {d.sensitive && <Badge tone="warn" className="mt-2"><Lock aria-hidden /> Sensitive · encrypted</Badge>}
            </Card>
          ))}
        </div>
      </section>
      <section>
        <SectionHeader title="Consent" subtitle="Turn any AI use of your data on or off" icon={ShieldCheck} />
        <Card className="divide-y divide-border p-0">
          {data.consents.map((c) => (
            <div key={c.id} className="flex items-center justify-between gap-4 px-5 py-4">
              <div>
                <p className="font-medium">{titleCase(c.scope.replace(".", " · "))}</p>
                <p className="text-sm text-muted">{c.purpose}</p>
                {c.granted_at && <p className="text-xs text-subtle">Granted {shortDate(c.granted_at)}</p>}
              </div>
              <Switch
                checked={c.granted}
                label={c.purpose}
                onCheckedChange={async (v) => {
                  await api.patch(`/privacy/consents/${c.id}`, { granted: v });
                  toast.success(v ? "Consent granted" : "Consent revoked");
                  refresh();
                }}
              />
            </div>
          ))}
        </Card>
      </section>
      <div className="grid gap-6 lg:grid-cols-2">
        <section>
          <SectionHeader title="Connected services" icon={Link2} />
          <div className="space-y-3">
            {data.integrations.map((i) => (
              <Card key={i.id} className="p-5">
                <div className="flex items-center justify-between gap-2">
                  <p className="font-medium">{i.provider}</p>
                  <Badge tone={i.status === "connected" ? "ok" : "neutral"}>{i.status}</Badge>
                </div>
                <p className="mt-1 text-sm text-muted">Shares: {i.data_shared.join(", ")}</p>
                {i.status === "connected" && (
                  <Button size="sm" variant="ghost" className="mt-2" onClick={async () => { await api.del(`/privacy/integrations/${i.id}`); toast.success("Integration revoked"); refresh(); }}>
                    <Link2Off /> Revoke access
                  </Button>
                )}
              </Card>
            ))}
          </div>
        </section>
        <section>
          <SectionHeader title="AI activity & sharing" icon={Sparkles} />
          <Card className="p-5">
            <p className="text-sm"><strong className="tabular">{data.ai_activity.tool_calls}</strong> data lookups by AI · <strong className="tabular">{data.ai_activity.actions_requested}</strong> actions proposed</p>
            <p className="mt-3 text-sm font-medium">Shared with third parties (after your approval)</p>
            {data.shared_data.length === 0 ? <p className="text-sm text-muted">Nothing has been shared.</p> : (
              <ul className="mt-1 space-y-1 text-sm text-muted">{data.shared_data.map((s, i) => <li key={i}>{shortDate(s.date)} · {s.recipient}: {s.items.join(", ")}</li>)}</ul>
            )}
            <Button size="sm" variant="ghost" className="mt-3" onClick={() => router.push("/activity")}>View full AI activity log</Button>
          </Card>
          <p className="mt-3 text-xs text-subtle">{data.retention}</p>
        </section>
      </div>
      <section>
        <SectionHeader title="Delete account" />
        <Card className="flex flex-col items-start gap-3 border-danger/30 p-5 md:flex-row md:items-center md:justify-between">
          <p className="text-sm text-muted">Permanently delete your account, policies, claims, documents and AI history.</p>
          <Dialog>
            <DialogTrigger asChild><Button variant="danger"><Trash2 /> Delete account</Button></DialogTrigger>
            <DialogContent title="Delete your account?" description="This permanently removes all your data. It can't be undone.">
              <label htmlFor="confirm-del" className="text-sm">Type <strong>DELETE</strong> to confirm</label>
              <Input id="confirm-del" value={confirmText} onChange={(e) => setConfirmText(e.target.value)} className="mt-2" />
              <Button variant="danger" className="mt-4 w-full" disabled={confirmText !== "DELETE"} onClick={async () => { await api.del("/privacy/account"); qc.clear(); router.push("/"); }}>
                Permanently delete
              </Button>
            </DialogContent>
          </Dialog>
        </Card>
      </section>
    </div>
  );
}
