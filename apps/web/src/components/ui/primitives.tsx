"use client";

import type { LucideIcon } from "lucide-react";
import { AnimatePresence, animate, motion, useInView, useMotionValue, useReducedMotion, useSpring, useTransform } from "framer-motion";
import { AlertTriangle, CheckCircle2, CircleHelp, Info, ShieldAlert, UserCheck } from "lucide-react";
import * as React from "react";
import type { Certainty, Confidence, Severity } from "@/lib/types";
import { cn } from "@/lib/utils";

/* ---------------- Card ---------------- */
export function Card({ className, interactive, children, ...props }: React.HTMLAttributes<HTMLDivElement> & { interactive?: boolean }) {
  return (
    <div
      className={cn(
        "glass rounded-card relative overflow-hidden",
        interactive && "transition-all duration-300 hover:-translate-y-0.5 hover:shadow-lift hover:border-border-strong",
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
}

/** Card with subtle 3D tilt that follows the pointer. Disabled for reduced motion. */
export function TiltCard({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  const reduce = useReducedMotion();
  const x = useMotionValue(0.5);
  const y = useMotionValue(0.5);
  const rx = useSpring(useTransform(y, [0, 1], [4, -4]), { stiffness: 200, damping: 20 });
  const ry = useSpring(useTransform(x, [0, 1], [-4, 4]), { stiffness: 200, damping: 20 });
  const glowX = useTransform(x, (v) => `${v * 100}%`);
  const glowY = useTransform(y, (v) => `${v * 100}%`);
  return (
    <motion.div
      onPointerMove={(e) => {
        if (reduce) return;
        const r = e.currentTarget.getBoundingClientRect();
        x.set((e.clientX - r.left) / r.width);
        y.set((e.clientY - r.top) / r.height);
      }}
      onPointerLeave={() => {
        x.set(0.5);
        y.set(0.5);
      }}
      style={reduce ? undefined : { rotateX: rx, rotateY: ry, transformPerspective: 900 }}
      className={cn("glass rounded-card relative overflow-hidden transition-shadow duration-300 hover:shadow-lift group", className)}
      {...(props as React.ComponentProps<typeof motion.div>)}
    >
      <motion.div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-300 group-hover:opacity-100"
        style={{
          background: useTransform([glowX, glowY], ([gx, gy]) => `radial-gradient(420px circle at ${gx} ${gy}, var(--accent-soft), transparent 45%)`),
        }}
      />
      {children}
    </motion.div>
  );
}

/* ---------------- Badge ---------------- */
const tones = {
  neutral: "bg-surface-hover text-muted border-border",
  accent: "bg-accent-soft text-accent border-transparent",
  ok: "bg-ok-soft text-ok border-transparent",
  warn: "bg-warn-soft text-warn border-transparent",
  danger: "bg-danger-soft text-danger border-transparent",
  info: "bg-info-soft text-info border-transparent",
} as const;
export type Tone = keyof typeof tones;

export function Badge({ tone = "neutral", className, children, ...props }: React.HTMLAttributes<HTMLSpanElement> & { tone?: Tone }) {
  return (
    <span className={cn("inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium leading-5 [&_svg]:size-3", tones[tone], className)} {...props}>
      {children}
    </span>
  );
}

/* ---------------- Severity / certainty / confidence (icon + text, never color-only) ---------------- */
export const severityMeta: Record<Severity, { tone: Tone; label: string; icon: LucideIcon }> = {
  attention: { tone: "danger", label: "Needs attention", icon: AlertTriangle },
  review: { tone: "warn", label: "Worth reviewing", icon: CircleHelp },
  info: { tone: "info", label: "For your info", icon: Info },
};

export function SeverityBadge({ severity }: { severity: Severity }) {
  const m = severityMeta[severity];
  return (
    <Badge tone={m.tone}>
      <m.icon aria-hidden /> {m.label}
    </Badge>
  );
}

export function CertaintyTag({ certainty }: { certainty: Certainty }) {
  return certainty === "confirmed" ? (
    <Badge tone="neutral" title="Directly from your policy data or documents">
      <CheckCircle2 aria-hidden /> Confirmed
    </Badge>
  ) : (
    <Badge tone="neutral" title="An inference that needs verification">
      <CircleHelp aria-hidden /> Possible
    </Badge>
  );
}

const confidenceMeta: Record<Confidence, { label: string; tone: Tone; icon: LucideIcon; help: string }> = {
  high: { label: "High confidence", tone: "ok", icon: CheckCircle2, help: "Backed by your policy data and a matching document passage." },
  moderate: { label: "Moderate confidence", tone: "info", icon: Info, help: "Supported by your data, but some details depend on facts we don't have." },
  needs_verification: { label: "Needs verification", tone: "warn", icon: CircleHelp, help: "We couldn't fully verify this. Check the source or ask your insurer." },
  human_review: { label: "Human review recommended", tone: "danger", icon: UserCheck, help: "A licensed professional should weigh in on this." },
};

export function ConfidenceBadge({ confidence }: { confidence: Confidence }) {
  const m = confidenceMeta[confidence] ?? confidenceMeta.moderate;
  return (
    <Badge tone={m.tone} title={m.help}>
      <m.icon aria-hidden /> {m.label}
    </Badge>
  );
}

export function SafetyNote({ children }: { children: React.ReactNode }) {
  return (
    <p className="flex items-start gap-2 text-xs text-subtle">
      <ShieldAlert className="mt-0.5 size-3.5 shrink-0" aria-hidden />
      <span>{children}</span>
    </p>
  );
}

/* ---------------- Progress ---------------- */
export function Progress({ value, className, tone = "accent", label }: { value: number; className?: string; tone?: "accent" | "ok" | "warn"; label?: string }) {
  const pct = Math.max(0, Math.min(1, value));
  const bar = tone === "ok" ? "bg-ok" : tone === "warn" ? "bg-warn" : "bg-accent-gradient";
  return (
    <div className={cn("h-2 w-full overflow-hidden rounded-full bg-surface-hover", className)} role="progressbar" aria-valuenow={Math.round(pct * 100)} aria-valuemin={0} aria-valuemax={100} aria-label={label}>
      <motion.div className={cn("h-full rounded-full", bar)} initial={{ width: 0 }} animate={{ width: `${pct * 100}%` }} transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1] }} />
    </div>
  );
}

/* ---------------- Skeleton ---------------- */
export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("skeleton", className)} aria-hidden />;
}

/* ---------------- Animated number ---------------- */
export function AnimatedNumber({ value, format = (n) => Math.round(n).toLocaleString(), className }: { value: number; format?: (n: number) => string; className?: string }) {
  const ref = React.useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true });
  const reduce = useReducedMotion();
  React.useEffect(() => {
    if (!ref.current) return;
    if (reduce || !inView) {
      ref.current.textContent = format(value);
      return;
    }
    const controls = animate(0, value, {
      duration: 1.1,
      ease: [0.22, 1, 0.36, 1],
      onUpdate: (v) => {
        if (ref.current) ref.current.textContent = format(v);
      },
    });
    return () => controls.stop();
  }, [value, inView, reduce, format]);
  return <span ref={ref} className={cn("tabular", className)}>{format(reduce ? value : 0)}</span>;
}

/* ---------------- Section header ---------------- */
export function SectionHeader({ title, subtitle, action, icon: Icon }: { title: string; subtitle?: string; action?: React.ReactNode; icon?: LucideIcon }) {
  return (
    <div className="mb-4 flex items-end justify-between gap-4 [&:not(:first-child)]:mt-7">
      <div className="min-w-0">
        <h2 className="flex items-center gap-2 font-display text-lg font-semibold tracking-tight">
          {Icon && <Icon className="size-5 text-accent" aria-hidden />}
          {title}
        </h2>
        {subtitle && <p className="mt-0.5 text-sm text-muted">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

/* ---------------- Page header ---------------- */
export function PageHeader({ title, subtitle, actions, eyebrow }: { title: React.ReactNode; subtitle?: React.ReactNode; actions?: React.ReactNode; eyebrow?: string }) {
  return (
    <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
      <div>
        {eyebrow && <p className="mb-2 text-xs font-medium uppercase tracking-[0.18em] text-accent">{eyebrow}</p>}
        <h1 className="font-display text-3xl font-semibold tracking-tight md:text-4xl">{title}</h1>
        {subtitle && <p className="mt-2 max-w-2xl text-muted">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
}

/* ---------------- Filter chips ---------------- */
export function FilterChips<T extends string>({ options, value, onChange, label }: { options: { value: T; label: string; count?: number }[]; value: T; onChange: (v: T) => void; label: string }) {
  return (
    <div role="radiogroup" aria-label={label} className="flex flex-wrap gap-2">
      {options.map((o) => {
        const active = o.value === value;
        return (
          <button
            key={o.value}
            role="radio"
            aria-checked={active}
            onClick={() => onChange(o.value)}
            className={cn("relative rounded-full px-3.5 py-1.5 text-sm transition-colors", active ? "text-accent-fg" : "glass text-muted hover:text-fg")}
          >
            {active && <motion.span layoutId={`chip-${label}`} className="absolute inset-0 rounded-full bg-accent-gradient" transition={{ type: "spring", stiffness: 400, damping: 32 }} />}
            <span className={cn("relative", active && "text-white")}>
              {o.label}
              {o.count !== undefined && <span className="ml-1.5 opacity-70">{o.count}</span>}
            </span>
          </button>
        );
      })}
    </div>
  );
}

/* ---------------- Empty state ---------------- */
export function EmptyState({ icon: Icon, title, body, action }: { icon: LucideIcon; title: string; body?: string; action?: React.ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-card border border-dashed border-border-strong px-6 py-14 text-center">
      <div className="relative mb-5">
        <div className="absolute inset-0 animate-float rounded-full bg-accent-gradient opacity-30 blur-2xl" aria-hidden />
        <div className="glass relative grid size-16 place-items-center rounded-2xl">
          <Icon className="size-7 text-accent" aria-hidden />
        </div>
      </div>
      <h3 className="font-display text-lg font-semibold">{title}</h3>
      {body && <p className="mt-1 max-w-sm text-sm text-muted">{body}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

/* ---------------- Fade-in on mount ---------------- */
export function Reveal({ children, delay = 0, className }: { children: React.ReactNode; delay?: number; className?: string }) {
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: 12, filter: "blur(4px)" }}
      animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
      transition={{ duration: 0.5, delay, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </motion.div>
  );
}

export { AnimatePresence, motion };
