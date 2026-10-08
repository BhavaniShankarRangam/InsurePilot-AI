"use client";

import * as Dropdown from "@radix-ui/react-dropdown-menu";
import { useQueryClient } from "@tanstack/react-query";
import { Bell, Command, LogOut, Monitor, Moon, Search, Settings, Sun, UserRound } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTheme } from "next-themes";
import { LogoMark } from "@/components/brand/logo";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/primitives";
import { api } from "@/lib/api";
import { useIsMac, useMounted } from "@/lib/hooks";
import { keys, useMe, useNotifications } from "@/lib/queries";
import { useUI } from "@/lib/store";
import { cn, timeAgo } from "@/lib/utils";

const menuCls = "glass-strong z-50 min-w-56 rounded-2xl p-1.5 text-sm shadow-lift";
const itemCls = "flex cursor-pointer items-center gap-2 rounded-xl px-3 py-2 outline-none data-[highlighted]:bg-surface-hover";

export function Topbar() {
  const setPalette = useUI((s) => s.setPalette);
  const mac = useIsMac();

  return (
    <header className="sticky top-0 z-20 flex h-16 items-center gap-3 border-b border-border bg-bg/70 px-4 backdrop-blur-xl md:px-8">
      <Link href="/dashboard" className="md:hidden" aria-label="Home">
        <LogoMark />
      </Link>
      <button
        onClick={() => setPalette(true)}
        className="glass flex h-10 flex-1 items-center gap-2.5 rounded-xl px-3.5 text-sm text-subtle transition hover:text-muted md:max-w-md"
        aria-label="Search everything (Ctrl+K)"
      >
        <Search className="size-4" aria-hidden />
        <span className="truncate">Search policies, claims, documents…</span>
        <kbd className="ml-auto hidden items-center gap-0.5 rounded-md border border-border px-1.5 py-0.5 font-mono text-[11px] sm:inline-flex">
          {mac ? <Command className="size-3" /> : "Ctrl"} K
        </kbd>
      </button>
      <div className="ml-auto flex items-center gap-1.5">
        <ThemeMenu />
        <Notifications />
        <UserMenu />
      </div>
    </header>
  );
}

function ThemeMenu() {
  const { theme, setTheme } = useTheme();
  const mounted = useMounted();
  const Icon = !mounted ? Monitor : theme === "dark" ? Moon : theme === "light" ? Sun : Monitor;
  return (
    <Dropdown.Root>
      <Dropdown.Trigger asChild>
        <Button variant="ghost" size="icon" aria-label="Change theme">
          <Icon />
        </Button>
      </Dropdown.Trigger>
      <Dropdown.Portal>
        <Dropdown.Content align="end" sideOffset={8} className={menuCls}>
          {[
            { v: "light", l: "Light", i: Sun },
            { v: "dark", l: "Dark", i: Moon },
            { v: "system", l: "System", i: Monitor },
          ].map(({ v, l, i: I }) => (
            <Dropdown.Item key={v} className={itemCls} onSelect={() => setTheme(v)}>
              <I className="size-4" /> {l}
              {mounted && theme === v && <span className="ml-auto text-accent">●</span>}
            </Dropdown.Item>
          ))}
        </Dropdown.Content>
      </Dropdown.Portal>
    </Dropdown.Root>
  );
}

function Notifications() {
  const { data } = useNotifications();
  const qc = useQueryClient();
  const router = useRouter();
  const unread = data?.filter((n) => !n.read).length ?? 0;
  return (
    <Dropdown.Root>
      <Dropdown.Trigger asChild>
        <Button variant="ghost" size="icon" aria-label={`Notifications, ${unread} unread`}>
          <Bell />
          {unread > 0 && <span className="absolute right-2 top-2 size-2 rounded-full bg-danger ring-2 ring-bg" aria-hidden />}
        </Button>
      </Dropdown.Trigger>
      <Dropdown.Portal>
        <Dropdown.Content align="end" sideOffset={8} className={cn(menuCls, "w-[min(380px,calc(100vw-2rem))] p-0")}>
          <div className="flex items-center justify-between border-b border-border px-4 py-3">
            <p className="font-semibold">Notifications</p>
            {unread > 0 && (
              <button
                className="text-xs text-accent hover:underline"
                onClick={async () => {
                  await api.post("/notifications/read-all");
                  qc.invalidateQueries({ queryKey: keys.notifications });
                }}
              >
                Mark all read
              </button>
            )}
          </div>
          <div className="max-h-[420px] overflow-y-auto p-1.5">
            {data?.length === 0 && <p className="px-3 py-8 text-center text-sm text-muted">You’re all caught up.</p>}
            {data?.map((n) => (
              <Dropdown.Item
                key={n.id}
                className={cn(itemCls, "items-start py-2.5")}
                onSelect={async () => {
                  if (!n.read) await api.post(`/notifications/${n.id}/read`);
                  qc.invalidateQueries({ queryKey: keys.notifications });
                  if (n.link) router.push(n.link);
                }}
              >
                <span className={cn("mt-1.5 size-2 shrink-0 rounded-full", n.read ? "bg-transparent" : n.priority === 1 ? "bg-danger" : "bg-accent")} aria-hidden />
                <span className="min-w-0">
                  <span className="flex items-center gap-2">
                    <span className={cn("font-medium", n.read && "text-muted")}>{n.title}</span>
                    {n.priority === 1 && <Badge tone="danger">Important</Badge>}
                  </span>
                  <span className="block text-xs text-muted">{n.body}</span>
                  <span className="block text-[11px] text-subtle">{timeAgo(n.created_at)}</span>
                </span>
              </Dropdown.Item>
            ))}
          </div>
        </Dropdown.Content>
      </Dropdown.Portal>
    </Dropdown.Root>
  );
}

function UserMenu() {
  const { data: me } = useMe();
  const router = useRouter();
  const qc = useQueryClient();
  const initials = me?.full_name.split(" ").map((p) => p[0]).join("").slice(0, 2) ?? "";
  return (
    <Dropdown.Root>
      <Dropdown.Trigger asChild>
        <button className="ml-1 grid size-9 place-items-center rounded-full bg-accent-gradient text-xs font-semibold text-white shadow-glow" aria-label="Account menu">
          {initials || <UserRound className="size-4" />}
        </button>
      </Dropdown.Trigger>
      <Dropdown.Portal>
        <Dropdown.Content align="end" sideOffset={8} className={menuCls}>
          <div className="px-3 py-2">
            <p className="font-medium">{me?.full_name}</p>
            <p className="text-xs text-muted">{me?.email}</p>
            {me?.is_demo && <Badge tone="accent" className="mt-1.5">Demo profile</Badge>}
          </div>
          <Dropdown.Separator className="my-1 h-px bg-border" />
          <Dropdown.Item className={itemCls} onSelect={() => router.push("/settings")}>
            <Settings className="size-4" /> Settings
          </Dropdown.Item>
          <Dropdown.Item
            className={itemCls}
            onSelect={async () => {
              await api.post("/auth/logout");
              qc.clear();
              router.push("/");
            }}
          >
            <LogOut className="size-4" /> Sign out
          </Dropdown.Item>
        </Dropdown.Content>
      </Dropdown.Portal>
    </Dropdown.Root>
  );
}
