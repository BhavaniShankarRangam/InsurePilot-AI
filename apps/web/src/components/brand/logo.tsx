import { cn } from "@/lib/utils";

/** Minimal mark: a soft shield silhouette drawn as an orbit, with an AI spark at its apex. */
export function LogoMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={cn("size-8", className)} aria-hidden>
      <defs>
        <linearGradient id="ip-g" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="var(--accent)" />
          <stop offset="1" stopColor="var(--accent-2)" />
        </linearGradient>
      </defs>
      <rect x="1" y="1" width="30" height="30" rx="9" fill="url(#ip-g)" opacity="0.14" />
      <path d="M16 6.5c3.2 2 6.2 2.6 8.5 2.6v6.3c0 5.2-3.6 8.8-8.5 10.6-4.9-1.8-8.5-5.4-8.5-10.6V9.1c2.3 0 5.3-.6 8.5-2.6Z" fill="none" stroke="url(#ip-g)" strokeWidth="2" strokeLinejoin="round" />
      <path d="M16 11.2l1.15 2.65 2.65 1.15-2.65 1.15L16 18.8l-1.15-2.65L12.2 15l2.65-1.15L16 11.2Z" fill="url(#ip-g)" />
    </svg>
  );
}

export function Logo({ className, compact }: { className?: string; compact?: boolean }) {
  return (
    <span className={cn("inline-flex items-center gap-2.5", className)}>
      <LogoMark />
      {!compact && (
        <span className="font-display text-[17px] font-semibold tracking-tight">
          InsurePilot<span className="ml-1 text-accent">AI</span>
        </span>
      )}
    </span>
  );
}
