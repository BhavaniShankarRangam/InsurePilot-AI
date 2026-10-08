"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Check, Hand, Mic, TriangleAlert, UserCheck } from "lucide-react";
import type { OrbState } from "@/lib/types";
import { cn } from "@/lib/utils";

const PALETTE: Record<OrbState, { a: string; b: string; speed: number; label: string }> = {
  idle: { a: "var(--accent)", b: "var(--accent-2)", speed: 14, label: "Ready" },
  listening: { a: "#3cc8f5", b: "#5b8cff", speed: 6, label: "Listening" },
  understanding: { a: "var(--accent)", b: "#c084fc", speed: 4, label: "Understanding" },
  retrieving: { a: "#5b8cff", b: "var(--accent-2)", speed: 3, label: "Retrieving" },
  analyzing: { a: "#8b7bff", b: "#22d3ee", speed: 2.5, label: "Analyzing" },
  tool: { a: "#22d3ee", b: "#8b7bff", speed: 2, label: "Taking action" },
  generating: { a: "var(--accent)", b: "var(--accent-2)", speed: 3.5, label: "Writing" },
  awaiting_confirmation: { a: "#f5b544", b: "#fb923c", speed: 8, label: "Waiting for your approval" },
  completed: { a: "#3ddbbd", b: "#22c55e", speed: 12, label: "Done" },
  error: { a: "#ff6b84", b: "#f97316", speed: 10, label: "Something went wrong" },
  human_review: { a: "#c084fc", b: "#f5b544", speed: 9, label: "Human review recommended" },
};

const BUSY: OrbState[] = ["understanding", "retrieving", "analyzing", "tool", "generating"];

/**
 * Animated AI Orb. Visual state is always paired with an accessible text label
 * (aria-label + optional caption) so meaning never relies on animation or color.
 */
export function Orb({ state = "idle", size = 56, level = 0, className, showCaption }: { state?: OrbState; size?: number; level?: number; className?: string; showCaption?: boolean }) {
  const reduce = useReducedMotion();
  const p = PALETTE[state];
  const busy = BUSY.includes(state);
  const audioScale = state === "listening" ? 1 + Math.min(level, 1) * 0.25 : 1;

  return (
    <div className={cn("relative inline-flex flex-col items-center", className)}>
      <div role="img" aria-label={`AI assistant: ${p.label}`} className="relative" style={{ width: size, height: size }}>
        {/* aura */}
        <motion.div
          aria-hidden
          className="absolute -inset-[35%] rounded-full blur-2xl"
          style={{ background: `radial-gradient(circle, ${p.a} 0%, transparent 65%)` }}
          animate={reduce ? { opacity: 0.35 } : { opacity: busy ? [0.35, 0.65, 0.35] : [0.25, 0.42, 0.25], scale: busy ? [0.95, 1.08, 0.95] : [0.96, 1.03, 0.96] }}
          transition={{ duration: busy ? 1.6 : 4.2, repeat: Infinity, ease: "easeInOut" }}
        />
        {/* swirling ring */}
        <motion.div
          aria-hidden
          className="absolute inset-0 rounded-full"
          style={{ background: `conic-gradient(from 0deg, ${p.a}, ${p.b}, transparent 55%, ${p.a})`, padding: 2, WebkitMask: "radial-gradient(farthest-side, transparent calc(100% - 2.5px), #000 calc(100% - 2px))", mask: "radial-gradient(farthest-side, transparent calc(100% - 2.5px), #000 calc(100% - 2px))" }}
          animate={reduce ? undefined : { rotate: 360 }}
          transition={{ duration: p.speed, repeat: Infinity, ease: "linear" }}
        />
        {/* core */}
        <motion.div
          aria-hidden
          className="absolute inset-[9%] overflow-hidden rounded-full"
          style={{ background: `radial-gradient(circle at 32% 28%, rgba(255,255,255,0.95) 0%, ${p.a} 22%, ${p.b} 62%, #0b0d12 120%)`, boxShadow: `0 0 24px -4px ${p.a}` }}
          animate={reduce ? { scale: audioScale } : { scale: state === "listening" ? audioScale : busy ? [1, 0.94, 1] : [1, 1.035, 1] }}
          transition={state === "listening" ? { type: "spring", stiffness: 300, damping: 15 } : { duration: busy ? 1.1 : 3.6, repeat: Infinity, ease: "easeInOut" }}
        >
          {/* inner liquid highlight */}
          <motion.div
            className="absolute -inset-1/4 opacity-60 mix-blend-screen"
            style={{ background: `conic-gradient(from 90deg, transparent, ${p.b}, transparent 40%)` }}
            animate={reduce ? undefined : { rotate: -360 }}
            transition={{ duration: p.speed * 1.4, repeat: Infinity, ease: "linear" }}
          />
          <div className="absolute inset-x-[22%] top-[12%] h-[22%] rounded-full bg-white/50 blur-[3px]" />
        </motion.div>

        {/* orbiting dots while using tools */}
        {(state === "tool" || state === "retrieving") && !reduce && (
          <motion.div aria-hidden className="absolute -inset-[14%]" animate={{ rotate: 360 }} transition={{ duration: 2.2, repeat: Infinity, ease: "linear" }}>
            {[0, 120, 240].map((deg) => (
              <span key={deg} className="absolute inset-0" style={{ transform: `rotate(${deg}deg)` }}>
                <span className="absolute left-1/2 top-0 size-1.5 -translate-x-1/2 rounded-full bg-white shadow-[0_0_8px_2px_var(--accent-2)]" />
              </span>
            ))}
          </motion.div>
        )}

        {/* state glyph */}
        <AnimatePresence>
          {["completed", "listening", "error", "awaiting_confirmation", "human_review"].includes(state) && size >= 44 && (
            <motion.div
              key={state}
              aria-hidden
              initial={{ opacity: 0, scale: 0.5 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.5 }}
              className="absolute inset-0 grid place-items-center text-white drop-shadow"
            >
              {state === "completed" && <Check className="size-[38%]" strokeWidth={3} />}
              {state === "listening" && <Mic className="size-[34%]" />}
              {state === "error" && <TriangleAlert className="size-[34%]" />}
              {state === "awaiting_confirmation" && <Hand className="size-[34%]" />}
              {state === "human_review" && <UserCheck className="size-[34%]" />}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
      {showCaption && (
        <span className="mt-3 text-xs font-medium text-muted" aria-live="polite">
          {p.label}
        </span>
      )}
    </div>
  );
}

export const orbLabel = (s: OrbState) => PALETTE[s].label;
