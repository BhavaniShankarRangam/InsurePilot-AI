"use client";

import { motion } from "framer-motion";
import { PanelLeftClose, PanelLeftOpen } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Logo } from "@/components/brand/logo";
import { useMe, usePendingActions } from "@/lib/queries";
import { useUI } from "@/lib/store";
import { cn } from "@/lib/utils";
import { NAV_PRIMARY, NAV_SECONDARY, type NavItem } from "./nav";

export function Sidebar() {
  const pathname = usePathname();
  const { sidebarCollapsed: collapsed, toggleSidebar } = useUI();
  const { data: me } = useMe();
  const { data: pending } = usePendingActions();

  const Item = ({ item }: { item: NavItem }) => {
    const active = pathname === item.href || pathname?.startsWith(`${item.href}/`);
    const badge = item.href === "/activity" && pending?.length ? pending.length : null;
    return (
      <Link
        href={item.href}
        aria-current={active ? "page" : undefined}
        title={collapsed ? item.label : undefined}
        className={cn(
          "group relative flex h-10 items-center gap-3 rounded-xl px-3 text-sm transition-colors",
          active ? "text-fg" : "text-muted hover:bg-surface-hover hover:text-fg",
          collapsed && "justify-center px-0",
        )}
      >
        {active && <motion.span layoutId="nav-active" className="absolute inset-0 rounded-xl bg-surface-strong shadow-soft ring-1 ring-border" transition={{ type: "spring", stiffness: 420, damping: 34 }} />}
        <item.icon className={cn("relative size-[18px] shrink-0", active && "text-accent")} aria-hidden />
        {!collapsed && <span className="relative truncate">{item.label}</span>}
        {badge && (
          <span className={cn("relative ml-auto grid min-w-5 place-items-center rounded-full bg-warn px-1.5 text-[10px] font-semibold text-black", collapsed && "absolute right-1 top-1 ml-0")} aria-label={`${badge} pending approvals`}>
            {badge}
          </span>
        )}
      </Link>
    );
  };

  return (
    <aside
      className={cn(
        "glass sticky top-0 z-30 hidden h-dvh shrink-0 flex-col rounded-none border-y-0 border-l-0 px-3 py-4 transition-[width] duration-300 md:flex",
        collapsed ? "w-[76px]" : "w-[248px]",
      )}
      aria-label="Main navigation"
    >
      <div className={cn("mb-6 flex items-center px-1", collapsed ? "justify-center" : "justify-between")}>
        <Link href="/dashboard" aria-label="InsurePilot home">
          <Logo compact={collapsed} />
        </Link>
      </div>
      <nav className="flex flex-1 flex-col gap-1 overflow-y-auto">
        {NAV_PRIMARY.map((i) => <Item key={i.href} item={i} />)}
        <div className="my-3 h-px bg-border" />
        {NAV_SECONDARY.filter((i) => !i.permission || me?.permissions.includes(i.permission)).map((i) => <Item key={i.href} item={i} />)}
      </nav>
      <button
        onClick={toggleSidebar}
        className={cn("mt-2 flex h-10 items-center gap-3 rounded-xl px-3 text-sm text-muted hover:bg-surface-hover hover:text-fg", collapsed && "justify-center px-0")}
        aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
      >
        {collapsed ? <PanelLeftOpen className="size-[18px]" /> : <PanelLeftClose className="size-[18px]" />}
        {!collapsed && "Collapse"}
      </button>
    </aside>
  );
}

export function MobileNav() {
  const pathname = usePathname();
  return (
    <nav className="glass-strong fixed inset-x-3 bottom-3 z-40 flex justify-around rounded-2xl px-2 py-1.5 md:hidden" aria-label="Main navigation">
      {NAV_PRIMARY.filter((i) => i.mobile).map((item) => {
        const active = pathname === item.href || pathname?.startsWith(`${item.href}/`);
        return (
          <Link key={item.href} href={item.href} aria-current={active ? "page" : undefined} className={cn("flex min-w-14 flex-col items-center gap-0.5 rounded-xl px-2 py-1.5 text-[10px]", active ? "text-accent" : "text-muted")}>
            <item.icon className="size-5" aria-hidden />
            {item.label.replace("Insurance ", "").replace("AI ", "")}
          </Link>
        );
      })}
    </nav>
  );
}
