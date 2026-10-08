"use client";

import { useQuery } from "@tanstack/react-query";
import { Bot, Cpu, Wrench } from "lucide-react";
import { ChatPanel } from "@/components/ai/chat-panel";
import { Badge, Card } from "@/components/ui/primitives";
import { api } from "@/lib/api";
import { usePageContext } from "@/lib/use-page-context";

export default function AssistantPage() {
  usePageContext({ section: "assistant", title: "AI Assistant" });
  const { data: agents } = useQuery({ queryKey: ["agents"], queryFn: () => api.get<{ name: string; description: string; tools: string[] }[]>("/ai/agents") });
  const { data: status } = useQuery({ queryKey: ["ai-status"], queryFn: () => api.get<{ provider: string; live: boolean; mode: string; models: Record<string, string> }>("/ai/status") });

  return (
    <div className="grid gap-6 xl:grid-cols-[1fr_320px]">
      <Card className="h-[calc(100dvh-10rem)] min-h-[560px] overflow-hidden p-0">
        <ChatPanel variant="page" />
      </Card>
      <aside className="hidden space-y-4 xl:block">
        <Card className="p-5">
          <p className="flex items-center gap-2 font-medium"><Cpu className="size-4 text-accent" aria-hidden /> AI engine</p>
          <p className="mt-1 text-sm text-muted">{status?.mode}</p>
          {status && (
            <div className="mt-2 flex flex-wrap gap-1.5">
              <Badge tone={status.live ? "ok" : "accent"}>{status.provider}</Badge>
              {Object.entries(status.models).map(([k, v]) => <Badge key={k}>{k}: {v}</Badge>)}
            </div>
          )}
          <p className="mt-3 text-xs text-subtle">Answers are grounded in your structured policy data, retrieved documents and verified tool results. Small models handle routing; large models handle reasoning.</p>
        </Card>
        <Card className="max-h-[calc(100dvh-22rem)] overflow-y-auto p-5">
          <p className="mb-3 flex items-center gap-2 font-medium"><Bot className="size-4 text-accent" aria-hidden /> Specialist agents</p>
          <ul className="space-y-3">
            {agents?.map((a) => (
              <li key={a.name}>
                <p className="text-sm font-medium">{a.name}</p>
                <p className="text-xs text-muted">{a.description}</p>
                <p className="mt-0.5 flex items-center gap-1 text-[11px] text-subtle"><Wrench className="size-3" aria-hidden /> {a.tools.length} tools</p>
              </li>
            ))}
          </ul>
        </Card>
      </aside>
    </div>
  );
}
