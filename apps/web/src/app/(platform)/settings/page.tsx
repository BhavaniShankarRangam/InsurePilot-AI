"use client";

import { useQueryClient } from "@tanstack/react-query";
import { Accessibility, Cpu, Monitor, Moon, Palette, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import * as React from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Field, Input, Switch } from "@/components/ui/overlay";
import { Card, PageHeader, SectionHeader } from "@/components/ui/primitives";
import { api } from "@/lib/api";
import { useMounted } from "@/lib/hooks";
import { keys, useMe } from "@/lib/queries";
import { useUI } from "@/lib/store";
import { usePageContext } from "@/lib/use-page-context";
import { cn } from "@/lib/utils";

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();
  const { data: me } = useMe();
  const { lowPower, setLowPower, reducedMotion, setReducedMotion } = useUI();
  const [draftName, setName] = React.useState<string | null>(null);
  const name = draftName ?? me?.preferred_name ?? "";
  const mounted = useMounted();
  const qc = useQueryClient();
  usePageContext({ section: "settings", title: "Settings" });

  const save = async (body: object) => {
    await api.patch("/users/me", body);
    qc.invalidateQueries({ queryKey: keys.me });
  };

  return (
    <div className="max-w-3xl space-y-8">
      <PageHeader eyebrow="Settings" title="Make InsurePilot yours" />
      <Card className="p-6">
        <SectionHeader title="Appearance" icon={Palette} />
        <div className="grid grid-cols-3 gap-3" role="radiogroup" aria-label="Theme">
          {[{ v: "light", l: "Light", i: Sun }, { v: "dark", l: "Dark", i: Moon }, { v: "system", l: "Auto", i: Monitor }].map(({ v, l, i: I }) => (
            <button key={v} role="radio" aria-checked={mounted && theme === v} onClick={() => { setTheme(v); save({ theme: v }); }}
              className={cn("glass flex flex-col items-center gap-2 rounded-2xl p-4 text-sm transition", mounted && theme === v && "ring-2 ring-accent")}>
              <I className="size-5" aria-hidden /> {l}
            </button>
          ))}
        </div>
      </Card>
      <Card className="p-6">
        <SectionHeader title="Accessibility & performance" icon={Accessibility} />
        <div className="space-y-5">
          <div className="flex items-center justify-between gap-4">
            <div><p className="font-medium">Reduce motion</p><p className="text-sm text-muted">Minimizes animations across the app.</p></div>
            <Switch checked={reducedMotion} onCheckedChange={(v) => { setReducedMotion(v); save({ reduced_motion: v }); }} label="Reduce motion" />
          </div>
          <div className="flex items-center justify-between gap-4">
            <div><p className="font-medium">Low-power mode</p><p className="text-sm text-muted">Uses the 2D Insurance Universe instead of 3D. Saves battery.</p></div>
            <Switch checked={lowPower} onCheckedChange={(v) => { setLowPower(v); save({ low_power_3d: v }); }} label="Low-power mode" />
          </div>
        </div>
      </Card>
      <Card className="p-6">
        <SectionHeader title="Profile" icon={Cpu} />
        <form onSubmit={async (e) => { e.preventDefault(); await save({ preferred_name: name }); toast.success("Saved"); }} className="flex items-end gap-3">
          <div className="flex-1"><Field label="What should we call you?" htmlFor="pname"><Input id="pname" value={name} onChange={(e) => setName(e.target.value)} maxLength={60} /></Field></div>
          <Button type="submit">Save</Button>
        </form>
        <p className="mt-3 text-sm text-muted">Signed in as {me?.email}</p>
      </Card>
    </div>
  );
}
