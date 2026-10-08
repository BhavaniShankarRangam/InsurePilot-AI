"use client";

import { motion, useReducedMotion } from "framer-motion";
import { AnimatedNumber } from "@/components/ui/primitives";

/** Animated Insurance Health Score ring. */
export function ScoreRing({ score, size = 168 }: { score: number; size?: number }) {
  const reduce = useReducedMotion();
  const stroke = 12;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(100, score)) / 100;
  const band = score >= 85 ? "Healthy" : score >= 70 ? "Good" : "Needs attention";
  return (
    <div className="relative grid place-items-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90" role="img" aria-label={`Insurance Health Score ${score} out of 100, ${band}`}>
        <defs>
          <linearGradient id="score-g" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="var(--accent)" />
            <stop offset="100%" stopColor="var(--accent-2)" />
          </linearGradient>
        </defs>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--border-strong)" strokeWidth={stroke} />
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="url(#score-g)"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={c}
          initial={{ strokeDashoffset: c }}
          animate={{ strokeDashoffset: c * (1 - pct) }}
          transition={{ duration: reduce ? 0 : 1.4, ease: [0.22, 1, 0.36, 1], delay: 0.2 }}
          style={{ filter: "drop-shadow(0 0 10px color-mix(in oklab, var(--accent) 45%, transparent))" }}
        />
      </svg>
      <div className="absolute inset-0 grid place-items-center text-center">
        <div>
          <p className="font-display text-5xl font-semibold tracking-tight">
            <AnimatedNumber value={score} />
          </p>
          <p className="text-xs text-muted">out of 100 · {band}</p>
        </div>
      </div>
    </div>
  );
}
